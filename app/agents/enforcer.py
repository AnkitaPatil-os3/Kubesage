import logging
import time
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from app.models import Plan, Action, ExecutionResult, Incident
from app.agents.executors import get_executor, BaseExecutor

# Load environment variables from .env file
load_dotenv()

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
            "KUBE_CONFIG_PATH": os.getenv("KUBE_CONFIG_PATH"),
            "ARGOCD_SERVER_URL": os.getenv("ARGOCD_SERVER_URL"),
            "ARGOCD_API_TOKEN": os.getenv("ARGOCD_API_TOKEN"),
            # Add other necessary config keys here
        }
        logger.info(f"EnforcerAgent initialized with max_retries={max_retries}, retry_delay={retry_delay_seconds}")
        logger.debug(f"Executor config loaded: { {k: ('******' if 'TOKEN' in k or 'KEY' in k else v) for k, v in self.executor_config.items()} }") # Mask secrets in logs


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
                    result = ExecutionResult(action_id=action.action_id, status="failure", error=error_msg)
                    all_results.append(result)
                    last_result = result
                    plan_successful = False # Configuration error means plan fails
                    break # Cannot proceed with this action
                except Exception as e:
                     logger.error(f"Unexpected error during execution of Action ID {action.action_id}: {e}", exc_info=True)
                     error_msg = f"Unexpected execution error: {e}"
                     result = ExecutionResult(action_id=action.action_id, status="failure", error=error_msg)
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

# Example Usage (for testing purposes)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print("\n--- Running EnforcerAgent Example ---")

    # Create a sample incident and plan
    sample_incident = Incident(
        incident_id="inc-123",
        affected_resource={"kind": "Pod", "name": "bad-pod-7xyz", "namespace": "testing"},
        failure_type="CrashLoopBackOff",
        description="Pod keeps crashing.",
        severity="critical"
    )

    # Plan with potentially failing and succeeding actions
    sample_plan = Plan(
        plan_id="plan-abc",
        incident_id=sample_incident.incident_id,
        actions=[
            Action(executor="kubectl", command="get_pod_logs", parameters={"name": "bad-pod-7xyz", "namespace": "testing"}, description="Get logs from the crashing pod"),
            Action(executor="kubectl", command="delete_pod", parameters={"name": "bad-pod-7xyz", "namespace": "testing"}, description="Delete the crashing pod (will be recreated by ReplicaSet/Deployment)"),
            Action(executor="unknown_executor", command="do_something", parameters={}, description="This action will fail due to unknown executor"), # Intentionally failing action
            Action(executor="kubectl", command="get_pod", parameters={"name": "bad-pod-7xyz", "namespace": "testing"}, description="Check pod status after deletion (should be recreated or gone)")
        ]
    )

    print(f"Sample Incident (before):\n{sample_incident.model_dump_json(indent=2)}")
    print(f"\nSample Plan:\n{sample_plan.model_dump_json(indent=2)}")

    # Initialize Enforcer (assumes Kube config is available, Argo config might be missing)
    enforcer = EnforcerAgent(max_retries=1, retry_delay_seconds=1)

    # Enforce the plan
    execution_results = enforcer.enforce_plan(sample_plan, sample_incident)

    print("\n--- Execution Results ---")
    for result in execution_results:
        print(result.model_dump_json(indent=2))

    print(f"\nSample Incident (after):\n{sample_incident.model_dump_json(indent=2)}") # Check the final status
