import os
import logging
import json
from openai import OpenAI, OpenAIError
from pydantic import ValidationError
from dotenv import load_dotenv

from app.models import Incident, Plan, Action

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class ReasonerAgent:
    """
    Uses an LLM (OpenAI GPT) to generate a remediation Plan for a given Incident.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY not found in environment variables.")
            raise ValueError("OPENAI_API_KEY must be set.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o" # Or another suitable model like gpt-3.5-turbo

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
1.  `executor`: The tool to use (e.g., 'kubectl', 'argocd', 'custom_script'). Choose the most appropriate one.
2.  `command`: The specific command or operation (e.g., 'delete pod', 'restart deployment', 'apply manifest').
3.  `parameters`: A dictionary of key-value pairs for the command (e.g., {{"name": "{incident.affected_resource.get('name', 'unknown')}", "namespace": "{incident.affected_resource.get('namespace', 'default')}"}}).
4.  `description`: (Optional) A brief explanation of the action.

Return the plan STRICTLY as a JSON object conforming to the following Pydantic model structure:

```json
{{
  "plan_id": "string (generate a new UUID)",
  "incident_id": "{incident.incident_id}",
  "actions": [
    {{
      "action_id": "string (generate a new UUID)",
      "executor": "string",
      "command": "string",
      "parameters": {{}},
      "description": "string (optional)"
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
            response = self.client.chat.completions.create(
                model=self.model,
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
            plan_data = json.loads(raw_json_output)

            # Validate the plan data against the Pydantic model
            # Ensure the incident_id matches
            if plan_data.get("incident_id") != incident.incident_id:
                 logger.warning(f"LLM plan incident_id '{plan_data.get('incident_id')}' does not match request '{incident.incident_id}'. Overwriting.")
                 plan_data["incident_id"] = incident.incident_id # Force correct ID

            plan = Plan(**plan_data)
            logger.info(f"Successfully generated and validated Plan ID: {plan.plan_id} for Incident ID: {incident.incident_id}")
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


# Example Usage (for testing purposes)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Check if API key is present for the example
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "YOUR_OPENAI_API_KEY_HERE":
        print("\nSkipping ReasonerAgent example: Set a valid OPENAI_API_KEY in your .env file.")
    else:
        print("\n--- Running ReasonerAgent Example ---")
        # Create a sample incident
        sample_incident = Incident(
            affected_resource={"kind": "Pod", "name": "checkout-service-pod-5fgh7", "namespace": "production"},
            failure_type="CrashLoopBackOff",
            description="Container 'server' is restarting frequently.",
            severity="critical"
        )

        print(f"Sample Incident:\n{sample_incident.model_dump_json(indent=2)}")

        reasoner = ReasonerAgent()

        try:
            generated_plan = reasoner.generate_plan(sample_incident)
            print("\n--- Generated Plan ---")
            print(generated_plan.model_dump_json(indent=2))
        except (ValueError, OpenAIError) as e:
            print(f"\nError generating plan: {e}")
        except Exception as e:
             print(f"\nAn unexpected error occurred: {e}")
