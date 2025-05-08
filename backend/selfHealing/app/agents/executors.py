import logging
import subprocess
import uuid
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
            execution_id=str(uuid.uuid4()),
            action_id=action.action_id,
            plan_id=getattr(action, 'plan_id', None),
            status=status,
            output=output,
            error=error,
            executed_at=datetime.utcnow()
        )

class KubectlExecutor(BaseExecutor):
    """Executes actions by calling an external Kubectl AI Agent service."""

    def __init__(self, agent_url: str, agent_token: Optional[str] = None, verify_ssl: bool = True):
        if not agent_url:
            raise ValueError("KUBECTL_AI_AGENT_URL must be configured for KubectlExecutor.")

        self.agent_url = agent_url.rstrip('/') + "/ai/execute" # Ensure correct endpoint path
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        if agent_token:
            self.headers["Authorization"] = f"Bearer {agent_token}"

        # Use a timeout to prevent hanging indefinitely
        self.client = httpx.Client(headers=self.headers, verify=verify_ssl, timeout=60.0)
        logger.info(f"KubectlExecutor initialized for AI Agent: {agent_url} (SSL Verification: {verify_ssl})")

    def execute(self, action: Action) -> ExecutionResult:
        """Executes the provided kubectl command string via the AI Agent service."""
        # The ReasonerAgent now provides the exact command string via /ai/generate
        kubectl_command_str = action.command

        if not kubectl_command_str or not kubectl_command_str.strip().startswith("kubectl"):
            error_msg = f"Invalid or missing kubectl command provided for action {action.action_id}: '{kubectl_command_str}'"
            logger.error(error_msg)
            return self._create_result(action, "failure", error=error_msg)

        logger.info(f"Sending command to Kubectl AI Agent /execute endpoint: '{kubectl_command_str}'")
        request_body = {"execute": kubectl_command_str}

        try:
            response = self.client.post(self.agent_url, json=request_body)

            # Handle different status codes
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"AI Agent execution successful for action {action.action_id}.")
                logger.debug(f"AI Agent Response: {response_data}")
                # Check if the agent reported an internal execution error
                exec_error = response_data.get("execution_error")
                if exec_error:
                     logger.warning(f"AI Agent reported execution error: {exec_error}")
                     return self._create_result(action, "failure", output=response_data.get("execution_result"), error=exec_error)
                else:
                     return self._create_result(action, "success", output=response_data.get("execution_result"))
            elif response.status_code == 400:
                 error_msg = f"AI Agent Error 400: Invalid or unsafe command. Response: {response.text}"
                 logger.error(error_msg)
                 return self._create_result(action, "failure", error=error_msg)
            elif response.status_code == 401:
                 error_msg = f"AI Agent Error 401: Unauthorized. Check KUBECTL_AI_AGENT_TOKEN."
                 logger.error(error_msg)
                 return self._create_result(action, "failure", error=error_msg)
            elif response.status_code == 429:
                 error_msg = f"AI Agent Error 429: Rate limit exceeded."
                 logger.error(error_msg)
                 return self._create_result(action, "failure", error=error_msg) # Consider retry logic here?
            elif response.status_code == 500:
                 error_msg = f"AI Agent Error 500: Internal server error. Response: {response.text}"
                 logger.error(error_msg)
                 return self._create_result(action, "failure", error=error_msg)
            elif response.status_code == 504:
                 error_msg = f"AI Agent Error 504: Gateway timeout during execution."
                 logger.error(error_msg)
                 return self._create_result(action, "failure", error=error_msg)
            else:
                 # Handle other unexpected status codes
                 error_msg = f"AI Agent Error {response.status_code}: Unexpected status. Response: {response.text}"
                 logger.error(error_msg)
                 return self._create_result(action, "failure", error=error_msg)

        except httpx.RequestError as e:
            logger.error(f"HTTP request error calling Kubectl AI Agent for action {action.action_id}: {e}", exc_info=True)
            return self._create_result(action, "failure", error=f"HTTP Request Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error executing kubectl action {action.action_id} via AI Agent: {e}", exc_info=True)
            return self._create_result(action, "failure", error=f"Unexpected error: {str(e)}")


class ArgoCDExecutor(BaseExecutor):
    """Executes actions via the Argo CD API (Placeholder)."""

    def __init__(self, argocd_server_url: str, api_token: str, verify_ssl: bool = True):
        self.server_url = argocd_server_url
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.client = httpx.Client(base_url=self.server_url, headers=self.headers, verify=verify_ssl)
        logger.info(f"ArgoCD Executor initialized for server: {self.server_url} (SSL Verification: {verify_ssl})")

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
        # Use AI Agent configuration
        agent_url = config.get("KUBECTL_AI_AGENT_URL")
        agent_token = config.get("KUBECTL_AI_AGENT_TOKEN")
        verify_ssl_str = config.get("KUBECTL_AI_AGENT_VERIFY_SSL", "true") # Default to true
        verify_ssl = verify_ssl_str.lower() == "true"
        if not agent_url:
             raise ValueError("KUBECTL_AI_AGENT_URL must be configured to use KubectlExecutor.")
        return KubectlExecutor(agent_url=agent_url, agent_token=agent_token, verify_ssl=verify_ssl)
    elif name_lower == "argocd":
        # Ensure required config for ArgoCD is present
        server_url = config.get("ARGOCD_SERVER_URL")
        api_token = config.get("ARGOCD_API_TOKEN")
        verify_ssl_str = config.get("ARGOCD_VERIFY_SSL", "true") # Default to true if not set
        verify_ssl = verify_ssl_str.lower() == "true"

        if not server_url or not api_token:
            raise ValueError("ARGOCD_SERVER_URL and ARGOCD_API_TOKEN must be configured for ArgoCDExecutor.")

        return ArgoCDExecutor(
            argocd_server_url=server_url,
            api_token=api_token,
            verify_ssl=verify_ssl
        )
    elif name_lower == "custom_script":
        return CustomScriptExecutor()
    # Add other executors here (e.g., KEDA, Crossplane)
    else:
        logger.error(f"Unknown executor requested: {executor_name}")
        raise ValueError(f"Unknown executor: {executor_name}")

# End of executor definitions and factory function
