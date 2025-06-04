import requests
from app.config import settings
from app.logger import logger
from app.schemas import KubernetesEvent
from app.models import IncidentModel, ExecutionAttemptModel, SolutionModel
from app.database import engine
from sqlmodel import Session, select
from typing import Dict, Any, List
from datetime import datetime

def enforce_remediation_plan(solution, incident_id: str):
    """
    Convert LLM solution into executable actions and determine executor
    """
    try:
        logger.info(f"Enforcer processing solution for incident: {incident_id}")
        
        # Determine executor based on solution steps
        executor_name = _determine_executor(solution.steps)
        
        # Check execution attempts
        attempt_count = _get_execution_attempts_count(incident_id)
        
        if attempt_count >= 3:
            logger.warning(f"Maximum attempts reached for incident {incident_id}")
            return {
                "status": "max_attempts_reached",
                "incident_id": incident_id,
                "message": "Maximum execution attempts reached. Manual intervention required."
            }
        
        # Prepare enforcer instructions
        instructions = []
        for step in solution.steps:
            instructions.append({
                "step_id": step.step_id,
                "action": step.action_type,
                "component": _map_action_to_component(step.action_type),
                "description": step.description,
                "target_resource": step.target_resource,
                "command_or_payload": step.command_or_payload,
                "expected_outcome": step.expected_outcome
            })
        
        enforcer_result = {
            "incident_id": incident_id,
            "solution_id": solution.solution_id,
            "executor_name": executor_name,
            "attempt_number": attempt_count + 1,
            "instructions": instructions,
            "summary": solution.summary,
            "severity_level": solution.severity_level,
            "estimated_time_mins": solution.estimated_time_to_resolve_mins
        }
        
        # Save execution attempt
        _save_execution_attempt(enforcer_result)
        
        # Save solution to database
        _save_solution_to_db(solution, incident_id)
        
        logger.info(f"Enforcer assigned executor '{executor_name}' for incident {incident_id}")
        return enforcer_result
        
    except Exception as e:
        logger.error(f"Enforcer failed for incident {incident_id}: {str(e)}")
        return {
            "status": "error",
            "incident_id": incident_id,
            "error": str(e)
        }

def _determine_executor(steps: List) -> str:
    """Determine which executor should handle the solution based on steps"""
    kubectl_actions = ["KUBECTL_GET_LOGS", "KUBECTL_DESCRIBE", "KUBECTL_SCALE", "KUBECTL_APPLY", "KUBECTL_DELETE"]
    argocd_actions = ["ARGOCD_SYNC", "ARGOCD_ROLLBACK", "ARGOCD_REFRESH"]
    crossplane_actions = ["CROSSPLANE_APPLY", "CROSSPLANE_DELETE", "CROSSPLANE_PATCH"]
    
    action_types = [step.action_type for step in steps]
    
    # Priority-based executor selection
    if any(action in action_types for action in argocd_actions):
        return "ArgoCD"
    elif any(action in action_types for action in crossplane_actions):
        return "Crossplane"
    elif any(action in action_types for action in kubectl_actions):
        return "kubectl"
    else:
        return "kubectl"  # Default executor

def _map_action_to_component(action_type: str) -> str:
    """Map action type to component"""
    if action_type.startswith("KUBECTL_"):
        return "kubectl"
    elif action_type.startswith("ARGOCD_"):
        return "ArgoCD"
    elif action_type.startswith("CROSSPLANE_"):
        return "Crossplane"
    else:
        return "kubectl"

def _get_execution_attempts_count(incident_id: str) -> int:
    """Get number of execution attempts for an incident"""
    try:
        with Session(engine) as session:
            attempts = session.exec(
                select(ExecutionAttemptModel).where(
                    ExecutionAttemptModel.incident_id == incident_id
                )
            ).all()
            return len(attempts)
    except Exception as e:
        logger.error(f"Error getting execution attempts count: {str(e)}")
        return 0

def _save_execution_attempt(enforcer_result: Dict[str, Any]):
    """Save execution attempt to database"""
    try:
        with Session(engine) as session:
            attempt = ExecutionAttemptModel(
                incident_id=enforcer_result["incident_id"],
                solution_id=enforcer_result["solution_id"],
                attempt_number=enforcer_result["attempt_number"],
                executor_name=enforcer_result["executor_name"],
                status="in_progress",
                execution_result=enforcer_result
            )
            session.add(attempt)
            session.commit()
            logger.info(f"Saved execution attempt {enforcer_result['attempt_number']} for incident {enforcer_result['incident_id']}")
    except Exception as e:
        logger.error(f"Error saving execution attempt: {str(e)}")

def _save_solution_to_db(solution, incident_id: str):
    """Save LLM solution to database"""
    try:
        with Session(engine) as session:
            solution_model = SolutionModel(
                solution_id=solution.solution_id,
                incident_id=incident_id,
                summary=solution.summary,
                analysis=solution.analysis,
                steps=[step.model_dump() for step in solution.steps],
                confidence_score=solution.confidence_score,
                estimated_time_mins=solution.estimated_time_to_resolve_mins,
                severity_level=solution.severity_level,
                recommendations=solution.recommendations
            )
            session.add(solution_model)
            session.commit()
            logger.info(f"Saved solution {solution.solution_id} to database")
    except Exception as e:
        logger.error(f"Error saving solution to database: {str(e)}")
