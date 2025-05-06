import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from app.models import Incident, Action, Plan

class ExecutionLogger:
    """Handles structured logging for incidents, actions and plans"""
    
    def __init__(self):
        self.logger = logging.getLogger("execution_logger")
        self.logger.setLevel(logging.INFO)
        
    def log_incident(self, incident: Incident):
        """Log incident details"""
        self.logger.info(
            "Incident Log",
            extra={
                "type": "incident",
                "id": incident.incident_id,
                "resource": incident.affected_resource,
                "failure_type": incident.failure_type,
                "severity": incident.severity,
                "status": incident.status
            }
        )
        
    def log_action(self, action: Action, result: Dict):
        """Log action execution details"""
        self.logger.info(
            "Action Log", 
            extra={
                "type": "action",
                "id": action.action_id,
                "executor": action.executor,
                "command": action.command,
                "status": result.get("status"),
                "output": result.get("output"),
                "error": result.get("error")
            }
        )
        
    def log_plan(self, plan: Plan):
        """Log plan details"""
        self.logger.info(
            "Plan Log",
            extra={
                "type": "plan",
                "id": plan.plan_id,
                "incident_id": plan.incident_id,
                "action_count": len(plan.actions),
                "created_at": plan.created_at.isoformat()
            }
        )

class BaseExecutor(ABC):
    """Abstract base executor with enhanced logging"""
    
    def __init__(self):
        self.logger = ExecutionLogger()
        
    @abstractmethod
    def execute(self, action: Action, incident: Incident, plan: Plan) -> Dict:
        """Execute action with full context logging"""
        self.logger.log_incident(incident)
        self.logger.log_plan(plan)
        
class KubernetesExecutor(BaseExecutor):
    """Kubernetes executor with enhanced logging"""
    
    def __init__(self, kubeconfig: Optional[str] = None):
        super().__init__()
        try:
            if kubeconfig:
                config.load_kube_config(config_file=kubeconfig)
            else:
                config.load_incluster_config()
            self.core_v1 = client.CoreV1Api()
        except Exception as e:
            self.logger.logger.error(f"Kubernetes init failed: {e}")
            raise

    def execute(self, action: Action, incident: Incident, plan: Plan) -> Dict:
        """Execute Kubernetes action with full logging"""
        super().execute(action, incident, plan)
        
        try:
            # Example command implementation
            if action.command == "get_pod":
                pod = self.core_v1.read_namespaced_pod(
                    name=action.parameters["name"],
                    namespace=action.parameters.get("namespace", "default")
                )
                result = {
                    "status": "success",
                    "output": pod.status.to_dict()
                }
            else:
                result = {
                    "status": "failed", 
                    "error": f"Unsupported command: {action.command}"
                }
                
            self.logger.log_action(action, result)
