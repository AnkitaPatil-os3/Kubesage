import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

# Kubernetes client library
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

# HTTP client for potential API interactions (e.g., ArgoCD)
import httpx

from app.models import Action, ExecutionResult

logger = logging.getLogger(__name__)

class BaseExecutor(ABC):
    """Abstract base class for all executors."""

    @abstractmethod
    def execute(self, action: Action) -> ExecutionResult:
        """
        Executes the given action.

        Args:
            action: The Action object containing execution details.

        Returns:
            An ExecutionResult object indicating success or failure.
        """
        pass

    def _create_result(self, action: Action, status: str, output: Optional[str] = None, error: Optional[str] = None) -> ExecutionResult:
        """Helper method to create an ExecutionResult."""
        return ExecutionResult(
            action_id=action.action_id,
            status=status,
            output=output,
            error=error,
            executed_at=datetime.utcnow()
        )

class KubectlExecutor(BaseExecutor):
    """Executes actions using the Kubernetes Python client."""

    def __init__(self, kubeconfig_path: Optional[str] = None):
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
                logger.info(f"Loaded Kubernetes config from: {kubeconfig_path}")
            else:
                config.load_incluster_config() # Assumes running inside a cluster
                logger.info("Loaded in-cluster Kubernetes config.")
            self.core_v1_api = client.CoreV1Api()
            self.apps_v1_api = client.AppsV1Api()
            # Add other API clients as needed (e.g., BatchV1Api for Jobs)
        except config.ConfigException as e:
            logger.error(f"Could not configure Kubernetes client: {e}", exc_info=True)
            raise RuntimeError(f"Kubernetes client configuration failed: {e}") from e

    def execute(self, action: Action) -> ExecutionResult:
        """Executes kubectl-like commands."""
        command = action.command.lower().replace("_", " ").replace("-", " ") # Normalize command
        params = action.parameters
        name = params.get("name")
        namespace = params.get("namespace", "default") # Default namespace if not provided

        logger.info(f"Executing kubectl action: '{command}' on resource '{name}' in namespace '{namespace}'")

        try:
            # --- Pod Operations ---
            if command == "get pod" or command == "describe pod":
                if not name: return self._create_result(action, "failure", error="Missing 'name' parameter for get/describe pod.")
                pod = self.core_v1_api.read_namespaced_pod(name=name, namespace=namespace)
                output = pod.to_str() if command == "describe pod" else str(pod.status)
                return self._create_result(action, "success", output=output)

            elif command == "delete pod":
                if not name: return self._create_result(action, "failure", error="Missing 'name' parameter for delete pod.")
                self.core_v1_api.delete_namespaced_pod(name=name, namespace=namespace)
                return self._create_result(action, "success", output=f"Pod '{name}' deleted successfully.")

            elif command == "get pod logs":
                if not name: return self._create_result(action, "failure", error="Missing 'name' parameter for get pod logs.")
                # Add optional 'container' parameter support if needed
                logs = self.core_v1_api.read_namespaced_pod_log(name=name, namespace=namespace)
                return self._create_result(action, "success", output=logs)

            # --- Deployment Operations ---
            elif command == "get deployment" or command == "describe deployment":
                 if not name: return self._create_result(action, "failure", error="Missing 'name' parameter for get/describe deployment.")
                 deployment = self.apps_v1_api.read_namespaced_deployment(name=name, namespace=namespace)
                 output = deployment.to_str() if command == "describe deployment" else str(deployment.status)
                 return self._create_result(action, "success", output=output)

            elif command == "restart deployment":
                 if not name: return self._create_result(action, "failure", error="Missing 'name' parameter for restart deployment.")
                 # This performs a rolling restart by patching the deployment template annotations
                 patch = {
                     "spec": {
                         "template": {
                             "metadata": {
                                 "annotations": {
                                     "kubectl.kubernetes.io/restartedAt": datetime.utcnow().isoformat()
                                 }
                             }
                         }
                     }
                 }
                 self.apps_v1_api.patch_namespaced_deployment(name=name, namespace=namespace, body=patch)
                 return self._create_result(action, "success", output=f"Deployment '{name}' restart initiated.")

            # --- Add more commands as needed (e.g., get service, apply manifest) ---

            else:
                logger.warning(f"Unsupported kubectl command: {action.command}")
                return self._create_result(action, "failure", error=f"Unsupported kubectl command: {action.command}")

        except ApiException as e:
            logger.error(f"Kubernetes API error executing action {action.action_id}: {e.reason} (Status: {e.status})", exc_info=True)
            return self._create_result(action, "failure", error=f"K8s API Error: {e.reason} (Status: {e.status}) Body: {e.body}")
        except Exception as e:
            logger.error(f"Unexpected error executing kubectl action {action.action_id}: {e}", exc_info=True)
            return self._create_result(action, "failure", error=f"Unexpected error: {str(e)}")


class ArgoCDExecutor(BaseExecutor):
    """Executes actions via the Argo CD API (Placeholder)."""

    def __init__(self, argocd_server_url: str, api_token: str):
        self.server_url = argocd_server_url
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.client = httpx.Client(base_url=self.server_url, headers=self.headers, verify=False) # Consider SSL verification in production
        logger.info(f"ArgoCD Executor initialized for server: {self.server_url}")

    def execute(self, action: Action) -> ExecutionResult:
        command = action.command.lower()
        params = action.parameters
        app_name = params.get("name")

        logger.info(f"Executing ArgoCD action: '{command}' on app '{app_name}'")

        # --- Placeholder for actual Argo CD API calls ---
        if command == "sync app":
            if not app_name: return self._create_result(action, "failure", error="Missing 'name' parameter for sync app.")
            logger.warning(f"ArgoCD 'sync app' for '{app_name}' is not implemented yet.")
            # Example (conceptual):
            # try:
            #     response = self.client.post(f"/api/v1/applications/{app_name}/sync")
            #     response.raise_for_status()
            #     return self._create_result(action, "success", output=f"ArgoCD sync initiated for app '{app_name}'.")
            # except httpx.HTTPStatusError as e:
            #     return self._create_result(action, "failure", error=f"ArgoCD API Error: {e.response.status_code} - {e.response.text}")
            return self._create_result(action, "pending", output="ArgoCD sync app not implemented.")
        else:
             logger.warning(f"Unsupported ArgoCD command: {action.command}")
             return self._create_result(action, "failure", error=f"Unsupported ArgoCD command: {action.command}")


class CustomScriptExecutor(BaseExecutor):
    """Executes actions by running local scripts (Placeholder/Example)."""

    def execute(self, action: Action) -> ExecutionResult:
        script_path = action.command # Assuming command is the path to the script
        args = action.parameters.get("args", []) # Expecting args as a list

        logger.info(f"Executing custom script action: '{script_path}' with args: {args}")

        try:
            # Example: Running a script. Be VERY careful with security here.
            # Consider sandboxing or strict validation of script_path and args.
            # This is highly dependent on security requirements.
            if not isinstance(args, list):
                 return self._create_result(action, "failure", error="Script 'args' parameter must be a list.")

            # Basic safety check (example - needs refinement)
            allowed_scripts_dir = "/app/scripts" # Example directory
            if not script_path.startswith(allowed_scripts_dir):
                 logger.error(f"Attempted to execute script outside allowed directory: {script_path}")
                 return self._create_result(action, "failure", error="Script execution outside allowed directory is forbidden.")

            command_list = [script_path] + args
            result = subprocess.run(command_list, capture_output=True, text=True, check=False, timeout=60) # Added timeout

            if result.returncode == 0:
                logger.info(f"Custom script '{script_path}' executed successfully.")
                return self._create_result(action, "success", output=result.stdout)
            else:
                logger.error(f"Custom script '{script_path}' failed with code {result.returncode}. Stderr: {result.stderr}")
                return self._create_result(action, "failure", output=result.stdout, error=f"Script failed with code {result.returncode}: {result.stderr}")

        except FileNotFoundError:
            logger.error(f"Custom script not found: {script_path}")
            return self._create_result(action, "failure", error=f"Script not found: {script_path}")
        except subprocess.TimeoutExpired:
             logger.error(f"Custom script '{script_path}' timed out.")
             return self._create_result(action, "failure", error="Script execution timed out.")
        except Exception as e:
            logger.error(f"Error executing custom script '{script_path}': {e}", exc_info=True)
            return self._create_result(action, "failure", error=f"Unexpected error executing script: {str(e)}")


# --- Executor Factory ---
# This allows selecting the correct executor based on the action
# Note: Initialization parameters (like kubeconfig, Argo URL/token) need to be managed,
# potentially via configuration or dependency injection in the main app.

def get_executor(executor_name: str, config: Dict[str, Any]) -> BaseExecutor:
    """
    Factory function to get an executor instance.
    Requires configuration details for initialization.
    """
    name_lower = executor_name.lower()
    if name_lower == "kubectl":
        return KubectlExecutor(kubeconfig_path=config.get("KUBE_CONFIG_PATH"))
    elif name_lower == "argocd":
        # Ensure required config for ArgoCD is present
        if not config.get("ARGOCD_SERVER_URL") or not config.get("ARGOCD_API_TOKEN"):
            raise ValueError("ARGOCD_SERVER_URL and ARGOCD_API_TOKEN must be configured for ArgoCDExecutor.")
        return ArgoCDExecutor(
            argocd_server_url=config["ARGOCD_SERVER_URL"],
            api_token=config["ARGOCD_API_TOKEN"]
        )
    elif name_lower == "custom_script":
        return CustomScriptExecutor()
    # Add other executors here (e.g., KEDA, Crossplane)
    else:
        logger.error(f"Unknown executor requested: {executor_name}")
        raise ValueError(f"Unknown executor: {executor_name}")

# Example Usage (for testing individual executors)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- KubectlExecutor Example ---
    print("\n--- Testing KubectlExecutor ---")
    try:
        # Assumes ~/.kube/config exists or in-cluster config is available
        # Pass kubeconfig_path=os.getenv("KUBE_CONFIG_PATH") if needed
        kube_executor = KubectlExecutor()

        # Example: Get pod (replace with a real pod name/namespace if testing against a cluster)
        get_pod_action = Action(executor="kubectl", command="get_pod", parameters={"name": "some-pod-that-might-not-exist", "namespace": "default"})
        result = kube_executor.execute(get_pod_action)
        print(f"Get Pod Result: Status={result.status}, Error={result.error}") # Expect failure if pod doesn't exist

        # Example: Restart deployment (replace with real deployment)
        restart_deploy_action = Action(executor="kubectl", command="restart_deployment", parameters={"name": "my-deployment", "namespace": "dev"})
        result = kube_executor.execute(restart_deploy_action)
        print(f"Restart Deployment Result: Status={result.status}, Error={result.error}") # Expect failure if deployment doesn't exist

    except RuntimeError as e:
        print(f"KubectlExecutor init failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during Kubectl testing: {e}")


    # --- ArgoCDExecutor Example (Placeholder) ---
    print("\n--- Testing ArgoCDExecutor (Placeholder) ---")
    # Requires ARGOCD_SERVER_URL and ARGOCD_API_TOKEN in config/env
    argo_config = {"ARGOCD_SERVER_URL": "https://your-argocd.example.com", "ARGOCD_API_TOKEN": "dummy-token"}
    try:
        argo_executor = get_executor("argocd", argo_config)
        sync_action = Action(executor="argocd", command="sync_app", parameters={"name": "guestbook"})
        result = argo_executor.execute(sync_action)
        print(f"Argo Sync Result: Status={result.status}, Output={result.output}, Error={result.error}")
    except ValueError as e:
        print(f"Could not get ArgoCD executor: {e}") # Expected if config missing
    except Exception as e:
        print(f"An unexpected error occurred during ArgoCD testing: {e}")


    # --- CustomScriptExecutor Example (Placeholder) ---
    print("\n--- Testing CustomScriptExecutor (Placeholder) ---")
    # Create a dummy script for testing if needed
    # e.g., echo "Script executed with args: $@" > /app/scripts/test.sh && chmod +x /app/scripts/test.sh
    script_config = {} # No specific config needed for this basic version
    try:
        script_executor = get_executor("custom_script", script_config)
        # IMPORTANT: This path MUST exist and be within the allowed directory if safety checks are active
        script_action = Action(executor="custom_script", command="/app/scripts/test.sh", parameters={"args": ["arg1", "value2"]})
        result = script_executor.execute(script_action)
        print(f"Custom Script Result: Status={result.status}, Output={result.output}, Error={result.error}") # Expect failure if script/path doesn't exist
    except ValueError as e:
         print(f"Could not get CustomScript executor: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during CustomScript testing: {e}")
