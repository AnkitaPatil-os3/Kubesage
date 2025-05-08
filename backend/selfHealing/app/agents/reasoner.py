import os
import logging
import json
import uuid
import httpx
from datetime import datetime
from openai import OpenAI, OpenAIError
from pydantic import ValidationError
from dotenv import load_dotenv

from app.models import Incident, Plan, Action

# Load environment variables from .env file
load_dotenv(override=True)

logger = logging.getLogger(__name__)

class ReasonerAgent:
    """
    Uses an LLM (OpenAI GPT) to generate a remediation Plan for a given Incident.
    """

    def __init__(self):
        # --- OpenAI Client Setup ---
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment variables.")
            raise ValueError("OPENAI_API_KEY must be set.")

        self.openai_base_url = os.getenv("OPENAI_BASE_URL")
        if self.openai_base_url and not self.openai_base_url.startswith(("http://", "https://")):
            logger.warning(f"OPENAI_BASE_URL '{self.openai_base_url}' is missing protocol. Adding https://")
            self.openai_base_url = f"https://{self.openai_base_url}"

        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")

        openai_client_kwargs = {"api_key": self.openai_api_key}
        if self.openai_base_url:
            openai_client_kwargs["base_url"] = self.openai_base_url
        self.openai_client = OpenAI(**openai_client_kwargs)
        logger.info(f"OpenAI client initialized for model: {self.openai_model}")

        # --- Kubectl AI Agent Client Setup ---
        self.ai_agent_url = os.getenv("KUBECTL_AI_AGENT_URL")
        self.ai_agent_token = os.getenv("KUBECTL_AI_AGENT_TOKEN")
        verify_ssl_str = os.getenv("KUBECTL_AI_AGENT_VERIFY_SSL", "true")
        self.ai_agent_verify_ssl = verify_ssl_str.lower() == "true"

        if not self.ai_agent_url:
            logger.warning("KUBECTL_AI_AGENT_URL not set. Kubectl command generation via AI agent will be skipped.")
            self.ai_agent_client = None
            self.ai_agent_generate_url = None
        else:
            self.ai_agent_generate_url = self.ai_agent_url.rstrip('/') + "/ai/kubectl-command" # Generate endpoint
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
            }
            if self.ai_agent_token:
                headers["Authorization"] = f"Bearer {self.ai_agent_token}"

            self.ai_agent_client = httpx.Client(
                headers=headers,
                verify=self.ai_agent_verify_ssl,
                timeout=30.0 # Timeout for generation
            )
            logger.info(f"Kubectl AI Agent client initialized for URL: {self.ai_agent_url} (SSL Verification: {self.ai_agent_verify_ssl})")

    def _create_prompt(self, incident: Incident) -> str:
        """Creates the prompt for the LLM based on the incident."""

        # Simplified prompt to reduce token usage and avoid truncation
        prompt = f"""
You are an expert Kubernetes SRE. Create a remediation plan for this incident:

Incident ID: {incident.incident_id}
Resource: {incident.affected_resource}
Failure: {incident.failure_type}
Severity: {incident.severity}
Description: {incident.description}

Return a JSON plan with:
1. plan_id (UUID)
2. incident_id (copy from above)
3. actions (array) with:
   - action_id (UUID)
   - executor (string: kubectl, argocd, etc)
   - description (string)
   - natural_language_query (ONLY for kubectl executor)
   - command (ONLY for non-kubectl executors)
   - parameters (ONLY for non-kubectl executors)
4. created_at (ISO timestamp)

IMPORTANT: Return ONLY valid JSON without markdown formatting.
Keep the plan simple with 1-2 diagnostic actions to avoid truncation.
"""
        return prompt.strip()

    def generate_plan(self, incident: Incident) -> Plan:
        """
        Generates a remediation Plan for the given Incident using the LLM.

        Args:
            incident: The Incident object.

        Returns:
            A Plan object containing the remediation steps.
            Raises ValueError or OpenAIError on failure.
        """
        prompt = self._create_prompt(incident)
        logger.info(f"Generating plan for Incident ID: {incident.incident_id}")
        logger.debug(f"Using prompt:\n{prompt}")

        try:
            # 1. Generate initial plan outline using OpenAI LLM
            logger.info(f"Generating initial plan outline for Incident ID: {incident.incident_id} using OpenAI model {self.openai_model}")
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a helpful Kubernetes SRE assistant designed to output JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}, # Request JSON output
                temperature=0.2, # Lower temperature for more deterministic plans
                max_tokens=1000  # Limit tokens to avoid truncation
            )

            raw_json_output = response.choices[0].message.content
            logger.debug(f"Raw LLM JSON output:\n{raw_json_output}")

            if not raw_json_output:
                logger.warning("LLM returned an empty response. Using fallback plan.")
                return self._create_fallback_plan(incident)
            
            # Clean up the JSON output - handle Markdown code blocks
            cleaned_json = raw_json_output.strip()
            
            # Remove markdown code block markers if present
            if cleaned_json.startswith("```json") and cleaned_json.endswith("```"):
                cleaned_json = cleaned_json[7:-3].strip()
            elif cleaned_json.startswith("```") and cleaned_json.endswith("```"):
                cleaned_json = cleaned_json[3:-3].strip()
            
            # Log the cleaned JSON for debugging
            logger.debug(f"Cleaned JSON before parsing:\n{cleaned_json}")
            
            # Try to parse the JSON with multiple fallback methods
            try:
                # First attempt: Try to parse as is
                initial_plan_data = json.loads(cleaned_json)
                logger.info("Successfully parsed JSON on first attempt")
            except json.JSONDecodeError as e:
                logger.warning(f"Initial JSON parsing failed: {e}. Using fallback plan.")
                return self._create_fallback_plan(incident)

            # Ensure the incident_id matches
            if initial_plan_data.get("incident_id") != incident.incident_id:
                logger.warning(f"LLM plan incident_id '{initial_plan_data.get('incident_id')}' does not match request '{incident.incident_id}'. Overwriting.")
                initial_plan_data["incident_id"] = incident.incident_id # Force correct ID

            # Validate required fields
            if "actions" not in initial_plan_data or not initial_plan_data["actions"]:
                logger.warning("No actions in plan. Using fallback plan.")
                return self._create_fallback_plan(incident)

            processed_actions = []
            actions_data = initial_plan_data.get("actions", [])

            # 2. Process actions, generating kubectl commands if needed
            logger.info(f"Processing {len(actions_data)} actions from initial plan...")
            for action_data in actions_data:
                executor = action_data.get("executor", "").lower()
                action_id = action_data.get("action_id", str(uuid.uuid4())) # Generate ID if missing

                if executor == "kubectl":
                    if not self.ai_agent_client:
                        logger.error(f"Skipping kubectl action {action_id} because AI Agent client is not configured.")
                        # Create a simple kubectl command as fallback
                        processed_actions.append(Action(
                            action_id=action_id,
                            executor="kubectl",
                            command=f"kubectl get pods -n {incident.affected_resource.get('namespace', 'default')}",
                            parameters={},
                            description=action_data.get("description", "Fallback diagnostic command")
                        ))
                        continue

                    nl_query = action_data.get("natural_language_query")
                    if not nl_query:
                        logger.error(f"Missing 'natural_language_query' for kubectl action {action_id}. Using fallback command.")
                        processed_actions.append(Action(
                            action_id=action_id,
                            executor="kubectl",
                            command=f"kubectl get pods -n {incident.affected_resource.get('namespace', 'default')}",
                            parameters={},
                            description=action_data.get("description", "Fallback diagnostic command")
                        ))
                        continue

                    # Call AI Agent /ai/kubectl-command
                    logger.info(f"Generating kubectl command for action {action_id} using query: '{nl_query}'")
                    try:
                        gen_response = self.ai_agent_client.post(self.ai_agent_generate_url, json={"query": nl_query})
                        gen_response.raise_for_status() # Raise exception for 4xx/5xx

                        gen_data = gen_response.json()
                        kubectl_commands = gen_data.get("kubectl_command", [])

                        if not kubectl_commands:
                            logger.error(f"AI Agent did not return any kubectl command for action {action_id}. Using fallback command.")
                            processed_actions.append(Action(
                                action_id=action_id,
                                executor="kubectl",
                                command=f"kubectl get pods -n {incident.affected_resource.get('namespace', 'default')}",
                                parameters={},
                                description=action_data.get("description", "Fallback diagnostic command")
                            ))
                            continue

                        # Create a separate action for each generated command
                        for i, generated_command in enumerate(kubectl_commands):
                            # Generate a new action_id for each command
                            cmd_action_id = f"{action_id}-{i}" if len(kubectl_commands) > 1 else action_id
                            logger.info(f"Generated kubectl command {i+1}/{len(kubectl_commands)} for action {action_id}: '{generated_command}'")

                            # Create the final Action object
                            processed_actions.append(Action(
                                action_id=cmd_action_id,
                                executor=executor,
                                command=generated_command, # Use the generated command
                                parameters={}, # Parameters are now part of the command string
                                description=f"{action_data.get('description', '')} (Command {i+1})" if len(kubectl_commands) > 1 else action_data.get("description", "")
                            ))

                    except Exception as e:
                        logger.error(f"Error generating kubectl command: {e}. Using fallback command.")
                        processed_actions.append(Action(
                            action_id=action_id,
                            executor="kubectl",
                            command=f"kubectl get pods -n {incident.affected_resource.get('namespace', 'default')}",
                            parameters={},
                            description=action_data.get("description", "Fallback diagnostic command")
                        ))

                else:
                    # For non-kubectl executors, use command/parameters directly
                    processed_actions.append(Action(
                        action_id=action_id,
                        executor=executor,
                        command=action_data.get("command", ""),
                        parameters=action_data.get("parameters", {}),
                        description=action_data.get("description", "")
                    ))

            # If no actions were processed successfully, use fallback plan
            if not processed_actions:
                logger.warning("No actions were processed successfully. Using fallback plan.")
                return self._create_fallback_plan(incident)

            # 3. Create and validate the final Plan object
            try:
                # Generate a plan_id if not provided
                plan_id = initial_plan_data.get("plan_id", str(uuid.uuid4()))
                
                # Create a Plan object without actions first
                plan = Plan(
                    plan_id=plan_id,
                    incident_id=incident.incident_id,
                    created_at=initial_plan_data.get("created_at", datetime.utcnow().isoformat()),
                    status="pending"
                )
                
                # Set the actions after the plan is created
                plan.actions = processed_actions
                
                logger.info(f"Successfully generated and validated final Plan ID: {plan.plan_id} for Incident ID: {incident.incident_id}")
                return plan
            except Exception as e:
                logger.error(f"Error creating Plan object: {e}. Using fallback plan.")
                return self._create_fallback_plan(incident)

        except Exception as e:
            logger.error(f"An unexpected error occurred during plan generation: {e}", exc_info=True)
            return self._create_fallback_plan(incident)

    def _create_fallback_plan(self, incident: Incident) -> Plan:
        """
        Create a simple fallback plan when the normal plan generation fails.
        
        Args:
            incident: The Incident object
            
        Returns:
            A simple Plan object with basic diagnostic actions
        """
        logger.info(f"Creating fallback plan for incident {incident.incident_id}")
        
        # Create a simple diagnostic action based on the affected resource
        resource_kind = incident.affected_resource.get('kind', 'Unknown')
        resource_name = incident.affected_resource.get('name', 'Unknown')
        namespace = incident.affected_resource.get('namespace', 'default')
        
        # Generate a plan_id
        plan_id = str(uuid.uuid4())
        
        # Create a Plan object first
        plan = Plan(
            plan_id=plan_id,
            incident_id=incident.incident_id,
            created_at=datetime.utcnow().isoformat(),
            status="pending"
        )
        
                # Create diagnostic actions
        actions = []
        
        # Action 1: Get basic resource info
        actions.append(Action(
            action_id=str(uuid.uuid4()),
            executor="kubectl",
            command=f"kubectl get {resource_kind.lower()}s -n {namespace} -o wide",
            parameters={},
            description=f"List all {resource_kind}s in the {namespace} namespace"
        ))
        
        # Action 2: Describe the specific resource if it's known
        if resource_name != "Unknown":
            actions.append(Action(
                action_id=str(uuid.uuid4()),
                executor="kubectl",
                command=f"kubectl describe {resource_kind.lower()} {resource_name} -n {namespace}",
                parameters={},
                description=f"Describe the {resource_kind} {resource_name} in {namespace} namespace"
            ))
        
        # Action 3: Check pod logs if applicable
        if resource_kind.lower() in ["pod", "deployment", "statefulset", "daemonset", "replicaset"]:
            actions.append(Action(
                action_id=str(uuid.uuid4()),
                executor="kubectl",
                command=f"kubectl logs {resource_name if resource_name != 'Unknown' else '-l app=' + resource_kind.lower()} -n {namespace} --tail=100",
                parameters={},
                description=f"Check logs for the {resource_kind} {resource_name} in {namespace} namespace"
            ))
        
        # Set the actions on the plan
        plan.actions = actions
        
        # If there are no actions, add at least one basic diagnostic action
        if not plan.actions:
            plan.actions = [
                Action(
                    action_id=str(uuid.uuid4()),
                    executor="kubectl",
                    command="kubectl get pods -A",
                    parameters={},
                    description="Basic diagnostic command"
                )
            ]
        
        logger.info(f"Created fallback plan {plan.plan_id} with {len(plan.actions)} actions")
        return plan

