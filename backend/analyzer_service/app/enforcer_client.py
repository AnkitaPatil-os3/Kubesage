import requests
from app.config import settings
from app.logger import logger
from app.schemas import Alert
from app.models import AlertModel
from app.database import engine
from sqlmodel import Session, select

def enforce_remediation_plan(solution):
    """
    Convert LLM solution into executable actions
    """
    instructions = []
    for step in solution.steps:
        instructions.append({
            "action": step.get("action"),
            "component": step.get("component"),  # kubectl, Helm, ArgoCD, etc.
            "parameters": step.get("parameters", {})
        })
    
    return {
        "incident_id": solution.solution_id,
        "instructions": instructions,
        "summary": solution.summary
    }
