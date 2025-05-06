import os
import logging
import json
import httpx # Added for AI Agent client
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

        # Basic prompt template - can be significantly enhanced
        prompt = f"""
You are an expert Kubernetes Site Reliability Engineer (SRE).
You have received the following incident report:

Incident ID: {incident.incident_id}
Affected Resource: {incident.affected_resource}
Failure Type: {incident.failure_type}
Severity: {incident.severity}
Description: {incident.description}
Status: {incident.status}
Occurred At: {incident.created_at}

Based on this incident, generate a step-by-step remediation plan.
The plan should consist of a list of actions. Each action must specify:
1.  `executor`: The tool to use ('kubectl', 'argocd', 'custom_script', etc.).
2.  `description`: A brief explanation of the action's purpose.
3.  `natural_language_query`: **ONLY if the executor is 'kubectl'**, provide a comprehensive natural language query describing all needed kubectl operations (e.g., "list all pods and describe the nginx pod in default namespace", "get logs for frontend pod and restart the deployment"). The query may generate multiple commands.
4.  `command`: **ONLY if the executor is NOT 'kubectl'**, provide the specific command or operation (e.g., 'sync_app', '/app/scripts/cleanup.sh').
5.  `parameters`: **ONLY if the executor is NOT 'kubectl'**, provide a dictionary of key-value pairs for the command (e.g., {{"name": "guestbook"}} for argocd sync_app).

Return the plan STRICTLY as a JSON object conforming to the following Pydantic model structure (note the conditional fields based on executor):

```json
{{
  "plan_id": "string (generate a new UUID)",
  "incident_id": "{incident.incident_id}",
  "actions": [
    {{
      "action_id": "string (generate a new UUID)",
      "executor": "string",
      "description": "string (optional)",
      // --- Include ONE of the following based on executor ---
      "natural_language_query": "string (if executor is 'kubectl')",
      // OR
      "command": "string (if executor is NOT 'kubectl')",
      "parameters": {{}} // (if executor is NOT 'kubectl')
    }}
    // ... more actions if needed
  ],
  "created_at": "string (current UTC timestamp in ISO format)"
}}
```

Analyze the incident carefully and provide the most logical and safe sequence of actions to resolve it. Prioritize non-destructive actions first (e.g., checking logs, describing resources) before considering potentially disruptive actions (e.g., deleting pods, restarting deployments). If unsure, suggest diagnostic steps.
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
            )

            raw_json_output = response.choices[0].message.content
            logger.debug(f"Raw LLM JSON output:\n{raw_json_output}")

            if not raw_json_output:
                raise ValueError("LLM returned an empty response.")

            # Parse the JSON output
            initial_plan_data = json.loads(raw_json_output)

            # Ensure the incident_id matches
            if initial_plan_data.get("incident_id") != incident.incident_id:
                 logger.warning(f"LLM plan incident_id '{initial_plan_data.get('incident_id')}' does not match request '{incident.incident_id}'. Overwriting.")
                 initial_plan_data["incident_id"] = incident.incident_id # Force correct ID

            processed_actions = []
            actions_data = initial_plan_data.get("actions", [])

            # 2. Process actions, generating kubectl commands if needed
            logger.info(f"Processing {len(actions_data)} actions from initial plan...")
            for action_data in actions_data:
                executor = action_data.get("executor", "").lower()
                action_id = action_data.get("action_id") # Keep the ID from the LLM

                if executor == "kubectl":
                    if not self.ai_agent_client:
                        logger.error(f"Skipping kubectl action {action_id} because AI Agent client is not configured.")
                        # Optionally: raise error, return partial plan, or skip action
                        raise ValueError(f"Cannot process kubectl action {action_id}: AI Agent URL not configured.")

                    nl_query = action_data.get("natural_language_query")
                    if not nl_query:
                        logger.error(f"Missing 'natural_language_query' for kubectl action {action_id}. Skipping.")
                        raise ValueError(f"Missing 'natural_language_query' for kubectl action {action_id}.")

                    # Call AI Agent /ai/kubectl-command
                    logger.info(f"Generating kubectl command for action {action_id} using query: '{nl_query}'")
                    try:
                        gen_response = self.ai_agent_client.post(self.ai_agent_generate_url, json={"query": nl_query})
                        gen_response.raise_for_status() # Raise exception for 4xx/5xx

                        gen_data = gen_response.json()
                        kubectl_commands = gen_data.get("kubectl_command", [])

                        if not kubectl_commands:
                            logger.error(f"AI Agent did not return any kubectl command for action {action_id} query: '{nl_query}'. Response: {gen_data}")
                            raise ValueError(f"AI Agent failed to generate command for action {action_id}.")

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
                                description=f"{action_data.get('description', '')} (Command {i+1})" if len(kubectl_commands) > 1 else action_data.get("description")
                            ))

                    except httpx.RequestError as e:
                         logger.error(f"HTTP request error calling AI Agent /kubectl-command for action {action_id}: {e}", exc_info=True)
                         raise ValueError(f"Failed to contact AI Agent /kubectl-command for action {action_id}: {e}") from e
                    except httpx.HTTPStatusError as e:
                         logger.error(f"AI Agent /kubectl-command returned error status {e.response.status_code} for action {action_id}. Response: {e.response.text}", exc_info=True)
                         raise ValueError(f"AI Agent /kubectl-command failed for action {action_id} with status {e.response.status_code}") from e
                    except Exception as e:
                         logger.error(f"Unexpected error processing AI Agent /kubectl-command response for action {action_id}: {e}", exc_info=True)
                         raise ValueError(f"Error processing AI Agent /kubectl-command response for action {action_id}: {e}") from e

                else:
                    # For non-kubectl executors, use command/parameters directly
                    processed_actions.append(Action(
                        action_id=action_id,
                        executor=executor,
                        command=action_data.get("command"),
                        parameters=action_data.get("parameters", {}),
                        description=action_data.get("description")
                    ))

            # 3. Create and validate the final Plan object
            final_plan_data = {
                "plan_id": initial_plan_data.get("plan_id"),
                "incident_id": initial_plan_data.get("incident_id"),
                "actions": processed_actions,
                "created_at": initial_plan_data.get("created_at")
            }

            plan = Plan(**final_plan_data) # Validate using Pydantic model
            logger.info(f"Successfully generated and validated final Plan ID: {plan.plan_id} for Incident ID: {incident.incident_id}")
            print(plan)
            return plan

        except OpenAIError as e:
            logger.error(f"OpenAI API error during plan generation: {e}", exc_info=True)
            raise  # Re-raise the OpenAI specific error
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse or validate LLM plan JSON: {e}", exc_info=True)
            logger.error(f"Problematic JSON received: {raw_json_output}")
            raise ValueError(f"LLM output failed validation: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during plan generation: {e}", exc_info=True)
            raise ValueError(f"Unexpected error generating plan: {e}") from e


# End of ReasonerAgent class
