import logging
import time
import os
import uuid
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

from app.models import Plan, Action, ExecutionResult, Incident
from app.agents.executors import get_executor, BaseExecutor

# Load environment variables from .env file
load_dotenv(override=True)

logger = logging.getLogger(__name__)

class EnforcerAgent:
    """
    Enforces a remediation Plan by executing its Actions via appropriate Executors.
    Handles retries and reports overall success or failure.
    """

    def __init__(self, max_retries: int = 3, retry_delay_seconds: int = 5):
        """
        Initializes the EnforcerAgent.

        Args:
            max_retries: Maximum number of times to retry a failed action.
            retry_delay_seconds: Delay between retries in seconds.
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay_seconds
        # Load configuration needed for executor initialization
        # This could be expanded into a dedicated config object/class
        self.executor_config = {
            # Config for original KubectlExecutor (kept for potential fallback/other uses)
            "KUBE_CONFIG_PATH": os.getenv("KUBE_CONFIG_PATH"),
            # Config for ArgoCDExecutor
            "ARGOCD_SERVER_URL": os.getenv("ARGOCD_SERVER_URL"),
            "ARGOCD_API_TOKEN": os.getenv("ARGOCD_API_TOKEN"),
            "ARGOCD_VERIFY_SSL": os.getenv("ARGOCD_VERIFY_SSL", "true"), # Added from previous step
            # Config for the new KubectlExecutor using AI Agent
            "KUBECTL_AI_AGENT_URL": os.getenv("KUBECTL_AI_AGENT_URL"),
            "KUBECTL_AI_AGENT_TOKEN": os.getenv("KUBECTL_AI_AGENT_TOKEN"),
            "KUBECTL_AI_AGENT_VERIFY_SSL": os.getenv("KUBECTL_AI_AGENT_VERIFY_SSL", "true"),
            # Add other necessary config keys here
        }
        logger.info(f"EnforcerAgent initialized with max_retries={max_retries}, retry_delay={retry_delay_seconds}")
        # Mask secrets in logs more robustly
        masked_config = {
            k: ('******' if 'TOKEN' in k or 'KEY' in k else v)
            for k, v in self.executor_config.items() if v is not None
        }
        logger.debug(f"Executor config loaded: {masked_config}")


    def enforce_plan(self, plan: Plan, incident: Incident) -> List[ExecutionResult]:
        """
        Executes all actions in a given plan sequentially.

        Args:
            plan: The Plan object containing actions to execute.
            incident: The associated Incident object (used for context, status updates).

        Returns:
            A list of ExecutionResult objects, one for each action attempt.
            Updates the incident status based on the outcome.
        """
        logger.info(f"Starting enforcement of Plan ID: {plan.plan_id} for Incident ID: {incident.incident_id}")
        incident.status = "remediating" # Update incident status
        all_results: List[ExecutionResult] = []
        plan_successful = True

        for action in plan.actions:
            logger.info(f"Processing Action ID: {action.action_id} (Executor: {action.executor}, Command: {action.command})")
            action_successful = False
            last_result = None

            for attempt in range(self.max_retries + 1): # +1 to include the initial attempt
                try:
                    executor: BaseExecutor = get_executor(action.executor, self.executor_config)
                    result = executor.execute(action)
                    
                    # Ensure execution_id is set
                    if not hasattr(result, 'execution_id') or not result.execution_id:
                        result.execution_id = str(uuid.uuid4())
                    
                    # Ensure plan_id is set
                    if not hasattr(result, 'plan_id') or not result.plan_id:
                        result.plan_id = plan.plan_id
                    
                    all_results.append(result)
                    last_result = result # Keep track of the last result for this action

                    if result.status == "success":
                        logger.info(f"Action ID: {action.action_id} succeeded on attempt {attempt + 1}.")
                        action_successful = True
                        break # Move to the next action
                    else:
                        logger.warning(f"Action ID: {action.action_id} failed on attempt {attempt + 1}. Status: {result.status}, Error: {result.error}")
                        if attempt < self.max_retries:
                            logger.info(f"Retrying Action ID: {action.action_id} in {self.retry_delay} seconds...")
                            time.sleep(self.retry_delay)
                        else:
                            logger.error(f"Action ID: {action.action_id} failed after {self.max_retries + 1} attempts.")
                            plan_successful = False # Mark the overall plan as failed
                            break # Stop retrying this action

                except ValueError as e:
                    logger.error(f"Failed to get or use executor for Action ID {action.action_id}: {e}", exc_info=True)
                    error_msg = f"Executor configuration error: {e}"
                    result = ExecutionResult(
                        execution_id=str(uuid.uuid4()),
                        plan_id=plan.plan_id,
                        action_id=action.action_id,
                        status="failure",
                        error=error_msg
                    )
                    all_results.append(result)
                    last_result = result
                    plan_successful = False # Configuration error means plan fails
                    break # Cannot proceed with this action
                except Exception as e:
                     logger.error(f"Unexpected error during execution of Action ID {action.action_id}: {e}", exc_info=True)
                     error_msg = f"Unexpected execution error: {e}"
                     result = ExecutionResult(
                        execution_id=str(uuid.uuid4()),
                        plan_id=plan.plan_id,
                        action_id=action.action_id,
                        status="failure",
                        error=error_msg
                     )
                     all_results.append(result)
                     last_result = result
                     plan_successful = False # Unexpected error means plan fails
                     break # Cannot proceed with this action

            if not action_successful:
                logger.error(f"Plan enforcement failed because Action ID {action.action_id} could not be completed successfully.")
                break # Stop processing further actions in this plan if one fails definitively

        # Update incident status based on final outcome
        if plan_successful:
            incident.status = "resolved" # Or potentially 'pending_validation'
            logger.info(f"Successfully enforced Plan ID: {plan.plan_id}. Incident {incident.incident_id} marked as {incident.status}.")
        else:
            incident.status = "failed_remediation" # Or keep 'remediating' if retries might happen later
            logger.error(f"Failed to enforce Plan ID: {plan.plan_id}. Incident {incident.incident_id} marked as {incident.status}.")

        return all_results

# End of EnforcerAgent class
