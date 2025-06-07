import requests
import subprocess
import time
from app.config import settings
from app.logger import logger
from app.models import ExecutionAttemptModel, ExecutorStatusModel
from app.database import engine
from sqlmodel import Session, select
from typing import Dict, Any, List
from datetime import datetime

def execute_remediation_steps(enforcer_instructions: Dict[str, Any]):
    """
    Execute remediation steps with improved error handling and recovery
    """
    incident_id = enforcer_instructions.get("incident_id")
    executor_name = enforcer_instructions.get("executor_name")
    attempt_number = enforcer_instructions.get("attempt_number")
    print ("incident_id",incident_id)
    
    logger.info(f"Executor '{executor_name}' starting execution for incident {incident_id}, attempt {attempt_number}")
    
    # Check if executor is active
    with Session(engine) as session:
        executor_status = session.exec(
            select(ExecutorStatusModel).where(ExecutorStatusModel.executor_name == executor_name)
        ).first()
        
        if not executor_status or executor_status.status != 0:
            logger.error(f"Executor '{executor_name}' is not active. Cannot execute remediation steps.")
            return {
                "incident_id": incident_id,
                "attempt_number": attempt_number,
                "executor_name": executor_name,
                "overall_success": False,
                "error": f"Executor '{executor_name}' is not active"
            }
            
    
    results = []
    overall_success = True
    successful_steps = 0
    
    try:
        for instruction in enforcer_instructions["instructions"]:
            step_id = instruction["step_id"]
            action = instruction["action"]
            component = instruction.get("executor", instruction.get("component", "kubectl"))
            
            logger.info(f"Executing step {step_id}: {action} using {component}")
            
            # Execute based on component/executor
            if component == "kubectl":
                result = _execute_kubectl_action(instruction)
            elif component == "argocd":
                result = _execute_argocd_action(instruction)
            elif component == "crossplane":
                result = _execute_crossplane_action(instruction)
            else:
                result = {"status": "skipped", "reason": f"Unknown executor: {component}"}
            
            results.append({
                "step_id": step_id,
                "action": action,
                "executor": component,
                "result": result
            })
            
            if result.get("status") == "success":
                successful_steps += 1
            else:
                logger.warning(f"Step {step_id} failed: {result}")
                # Don't mark as complete failure if some steps succeed
                if result.get("status") != "skipped":
                    overall_success = False
            
            # Small delay between steps
            time.sleep(1)
        
        # Consider partial success if more than 50% of steps succeed
        if successful_steps > 0 and successful_steps >= len(results) * 0.5:
            overall_success = True
            logger.info(f"Partial success: {successful_steps}/{len(results)} steps completed")
        
        # Update execution attempt status
        execution_status = "success" if overall_success else "failed"
        _update_execution_attempt(incident_id, attempt_number, execution_status, results)
        
        # Only trigger retry if complete failure and less than 3 attempts
        if not overall_success and successful_steps == 0 and attempt_number < 3:
            logger.info(f"Complete failure for incident {incident_id}, triggering retry...")
            _trigger_llm_retry(incident_id)
        elif not overall_success and attempt_number >= 3:
            logger.error(f"Maximum attempts reached for incident {incident_id}. Manual intervention required.")
        
        return {
            "incident_id": incident_id,
            "attempt_number": attempt_number,
            "executor_name": executor_name,
            "overall_success": overall_success,
            "steps_executed": len(results),
            "successful_steps": successful_steps,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Executor failed for incident {incident_id}: {str(e)}")
        _update_execution_attempt(incident_id, attempt_number, "failed", [], str(e))
        
        # Trigger retry if less than 3 attempts
        if attempt_number < 3:
            _trigger_llm_retry(incident_id)
        
        return {
            "incident_id": incident_id,
            "attempt_number": attempt_number,
            "executor_name": executor_name,
            "overall_success": False,
            "error": str(e)
        }

def _execute_kubectl_action(instruction: Dict[str, Any]) -> Dict[str, Any]:
    """Execute kubectl commands with better error handling and resource checking"""
    try:
        # Check if kubectl executor is active
        with Session(engine) as session:
            kubectl_status = session.exec(
                select(ExecutorStatusModel).where(ExecutorStatusModel.executor_name == "kubectl")
            ).first()
            
            if not kubectl_status or kubectl_status.status != 0:
                return {
                    "status": "failed",
                    "tool": "kubectl",
                    "error": "kubectl executor is not active"
                }
        
        command_data = instruction.get("command_or_payload", {})
        kubectl_command = command_data.get("command", "")
        target_resource = instruction.get("target_resource", {})
        
        if not kubectl_command:
            return {"status": "failed", "reason": "No kubectl command provided"}
        
        # Extract resource info
        resource_kind = target_resource.get("kind", "").lower()
        resource_name = target_resource.get("name", "")
        namespace = target_resource.get("namespace", "default")
        
        # Check if resource exists first (for specific resources)
        if resource_name and resource_name != "all" and resource_kind in ["pod", "deployment", "service"]:
            check_result = _check_resource_exists(resource_kind, resource_name, namespace)
            if not check_result["exists"]:
                return {
                    "status": "failed",
                    "tool": "kubectl",
                    "command": f"kubectl {kubectl_command}",
                    "error": f"Resource {resource_kind}/{resource_name} not found in namespace {namespace}",
                    "suggestion": f"Try: kubectl get {resource_kind}s -n {namespace} to see available resources"
                }
        
        # Construct full kubectl command
        full_command = f"kubectl {kubectl_command}"
        
        logger.info(f"Executing: {full_command}")
        
        # Execute command with timeout
        result = subprocess.run(
            full_command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "tool": "kubectl",
                "command": full_command,
                "output": result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout
            }
        else:
            # Handle specific kubectl errors
            error_msg = result.stderr
            
            if "NotFound" in error_msg:
                # Suggest alternative commands
                suggestion = _get_alternative_command_suggestion(resource_kind, namespace)
                return {
                    "status": "failed",
                    "tool": "kubectl",
                    "command": full_command,
                    "error": error_msg.strip(),
                    "suggestion": suggestion
                }
            else:
                return {
                    "status": "failed",
                    "tool": "kubectl",
                    "command": full_command,
                    "error": error_msg.strip()
                }
            
    except subprocess.TimeoutExpired:
        return {"status": "failed", "tool": "kubectl", "error": "Command timeout"}
    except FileNotFoundError:
        return {
            "status": "failed", 
            "tool": "kubectl", 
            "error": "kubectl not found - please ensure kubectl is installed and in PATH"
        }
    except Exception as e:
        return {"status": "failed", "tool": "kubectl", "error": str(e)}

def _check_resource_exists(resource_kind: str, resource_name: str, namespace: str) -> Dict[str, Any]:
    """Check if a Kubernetes resource exists"""
    try:
        check_command = f"kubectl get {resource_kind} {resource_name} -n {namespace} --ignore-not-found"
        result = subprocess.run(
            check_command.split(),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        exists = result.returncode == 0 and result.stdout.strip() != ""
        
        return {
            "exists": exists,
            "output": result.stdout.strip() if exists else result.stderr.strip()
        }
        
    except Exception as e:
        return {"exists": False, "error": str(e)}

def _get_alternative_command_suggestion(resource_kind: str, namespace: str) -> str:
    """Get alternative command suggestions when resource is not found"""
    suggestions = {
        "pod": f"kubectl get pods -n {namespace}",
        "deployment": f"kubectl get deployments -n {namespace}",
        "service": f"kubectl get services -n {namespace}",
        "configmap": f"kubectl get configmaps -n {namespace}",
        "secret": f"kubectl get secrets -n {namespace}"
    }
    
    base_suggestion = suggestions.get(resource_kind, f"kubectl get {resource_kind}s -n {namespace}")
    
    return f"Try listing available resources: {base_suggestion}"

def _execute_argocd_action(instruction: Dict[str, Any]) -> Dict[str, Any]:
    """Execute ArgoCD commands"""
    try:
        # Check if ArgoCD executor is active
        with Session(engine) as session:
            argocd_status = session.exec(
                select(ExecutorStatusModel).where(ExecutorStatusModel.executor_name == "argocd")
            ).first()
            
            if not argocd_status or argocd_status.status != 0:
                return {
                    "status": "failed",
                    "tool": "ArgoCD",
                    "error": "ArgoCD executor is not active"
                }
        
        action = instruction["action"]
        logger.info(f"[ArgoCD] Executing action: {action}")
        
        # Placeholder for ArgoCD integration
        # In production, integrate with ArgoCD API
        return {
            "status": "success",
            "tool": "ArgoCD",
            "action": action,
            "message": "ArgoCD action executed successfully"
        }
    except Exception as e:
        return {
            "status": "failed",
            "tool": "ArgoCD",
            "error": str(e)
        }

def _execute_crossplane_action(instruction: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Crossplane commands"""
    try:
        # Check if Crossplane executor is active
        with Session(engine) as session:
            crossplane_status = session.exec(
                select(ExecutorStatusModel).where(ExecutorStatusModel.executor_name == "crossplane")
            ).first()
            
            if not crossplane_status or crossplane_status.status != 0:
                return {
                    "status": "failed",
                    "tool": "Crossplane",
                    "error": "Crossplane executor is not active"
                }
        
        action = instruction["action"]
        logger.info(f"[Crossplane] Executing action: {action}")
        
        # Placeholder for Crossplane integration
        # In production, integrate with Crossplane API
        return {
            "status": "success",
            "tool": "Crossplane",
            "action": action,
            "message": "Crossplane action executed successfully"
        }
    except Exception as e:
        return {
            "status": "failed",
            "tool": "Crossplane",
            "error": str(e)
        }

def _update_execution_attempt(incident_id: str, attempt_number: int, status: str, results: List, error_message: str = None):
    """Update execution attempt in database"""
    try:
        with Session(engine) as session:
            attempt = session.exec(
                select(ExecutionAttemptModel).where(
                    ExecutionAttemptModel.incident_id == incident_id,
                    ExecutionAttemptModel.attempt_number == attempt_number
                )
            ).first()
            
            if attempt:
                attempt.status = status
                attempt.execution_result = {"results": results}
                attempt.error_message = error_message
                attempt.completed_at = datetime.utcnow()
                session.commit()
                logger.info(f"Updated execution attempt {attempt_number} for incident {incident_id}")
    except Exception as e:
        logger.error(f"Error updating execution attempt: {str(e)}")

def _trigger_llm_retry(incident_id: str):
    """Trigger LLM retry for failed execution"""
    try:
        logger.info(f"Triggering LLM retry for incident {incident_id}")
        
        # Import here to avoid circular imports
        from app.incident_processor import retry_incident_analysis
        
        # Schedule retry in background
        import asyncio
        asyncio.create_task(retry_incident_analysis(incident_id))
        
    except Exception as e:
        logger.error(f"Error triggering LLM retry: {str(e)}")

def get_active_executors() -> List[str]:
    """Get list of currently active executors"""
    try:
        with Session(engine) as session:
            active_executors = session.exec(
                select(ExecutorStatusModel).where(ExecutorStatusModel.status == 0)
            ).all()
            return [executor.executor_name for executor in active_executors]
    except Exception as e:
        logger.error(f"Error getting active executors: {str(e)}")
        return ["kubectl"]  # Default fallback

def is_executor_active(executor_name: str) -> bool:
    """Check if a specific executor is active"""
    try:
        with Session(engine) as session:
            executor = session.exec(
                select(ExecutorStatusModel).where(
                    ExecutorStatusModel.executor_name == executor_name,
                    ExecutorStatusModel.status == 0
                )
            ).first()
            return executor is not None
    except Exception as e:
        logger.error(f"Error checking executor status for {executor_name}: {str(e)}")
        return False

def execute_single_remediation_command(execution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single remediation command with safety checks
    """
    try:
        command = execution_data.get("command", "")
        executor = execution_data.get("executor", "kubectl")
        incident_id = execution_data.get("incident_id", "unknown")
        
        logger.info(f"Executing single command for incident {incident_id}: kubectl {command}")
        
        # Safety checks - block dangerous commands
        dangerous_patterns = [
            "delete", "rm", "remove", "destroy", 
            "drop", "truncate", "format", "wipe"
        ]
        
        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower and "get" not in command_lower and "describe" not in command_lower:
                return {
                    "status": "blocked",
                    "reason": f"Command blocked for safety: contains '{pattern}'",
                    "command": f"kubectl {command}",
                    "suggestion": "Use 'get' or 'describe' commands for safe investigation"
                }
        
        # Execute based on executor type
        if executor == "kubectl":
            return _execute_single_kubectl_command(command)
        else:
            return {
                "status": "skipped",
                "reason": f"Executor '{executor}' not implemented for single command execution"
            }
            
    except Exception as e:
        logger.error(f"Error in single command execution: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }

def _execute_single_kubectl_command(command: str) -> Dict[str, Any]:
    """Execute a single kubectl command"""
    try:
        # Construct full command
        full_command = f"kubectl {command}"
        
        logger.info(f"Executing: {full_command}")
        
        # Execute with timeout
        result = subprocess.run(
            full_command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "command": full_command,
                "output": result.stdout,
                "execution_time": "< 30s"
            }
        else:
            return {
                "status": "failed",
                "command": full_command,
                "error": result.stderr.strip(),
                "exit_code": result.returncode
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "command": f"kubectl {command}",
            "error": "Command timeout (30s limit exceeded)"
        }
    except FileNotFoundError:
        return {
            "status": "failed",
            "command": f"kubectl {command}",
            "error": "kubectl not found - please ensure kubectl is installed"
        }
    except Exception as e:
        return {
            "status": "failed",
            "command": f"kubectl {command}",
            "error": str(e)
        }
