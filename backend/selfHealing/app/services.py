from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json

from app.models import RawEvent, Incident, Plan, Action, ExecutionResult
from app.logger import logger
from app.agents.analyzer import AnalyzerAgent
from app.agents.reasoner import ReasonerAgent
from app.agents.enforcer import EnforcerAgent
from app.queue import (
    publish_incident_created,
    publish_incident_updated,
    publish_plan_generated,
    publish_plan_executed,
    publish_remediation_failed,
    publish_remediation_succeeded
)
from app.cache import cache_flush_user
from app.schemas import ExecutionResultResponse

# Initialize agents
analyzer = AnalyzerAgent()
reasoner = ReasonerAgent()
enforcer = EnforcerAgent()

async def process_raw_event(
    event_data: Dict[str, Any],
    user_id: Optional[int] = None,
    session: Session = None
) -> List[ExecutionResultResponse]:
    """
    Process a raw event through the self-healing pipeline.
    
    Args:
        event_data: The raw event data
        user_id: Optional user ID
        session: Database session
        
    Returns:
        List of execution results
    """
    # 1. Create and save raw event
    raw_event = RawEvent(event_data=event_data, user_id=user_id)
    session.add(raw_event)
    session.commit()
    session.refresh(raw_event)
    
    # 2. Analyze: Transform raw event into a structured Incident
    try:
        incident = analyzer.process_event(raw_event)
        incident.user_id = user_id
        
        # Save incident to database
        db_incident = Incident(
            incident_id=incident.incident_id,
            affected_resource=incident.affected_resource,
            failure_type=incident.failure_type,
            description=incident.description,
            severity=incident.severity,
            status=incident.status,
            user_id=user_id
        )
        session.add(db_incident)
        session.commit()
        session.refresh(db_incident)
        
        # Publish incident created event
        incident_data = {
            "incident_id": db_incident.incident_id,
            "affected_resource": db_incident.affected_resource,
            "failure_type": db_incident.failure_type,
            "severity": db_incident.severity,
            "user_id": user_id
        }
        publish_incident_created(incident_data)
        
        # 3. Reason: Generate a remediation Plan using an LLM
        plan = reasoner.generate_plan(incident)
        
        # Save plan to database
        db_plan = Plan(
            plan_id=plan.plan_id,
            incident_id=plan.incident_id,
            status="created",
            user_id=user_id
        )
        session.add(db_plan)
        session.commit()
        session.refresh(db_plan)
        
        # Save actions to database
        for i, action in enumerate(plan.actions):
            db_action = Action(
                action_id=action.action_id,
                plan_id=plan.plan_id,
                executor=action.executor,
                command=action.command,
                parameters=action.parameters,
                description=action.description,
                order=i
            )
            session.add(db_action)
        session.commit()
        
        # Publish plan generated event
        plan_data = {
            "plan_id": db_plan.plan_id,
            "incident_id": db_plan.incident_id,
            "user_id": user_id
        }
        publish_plan_generated(plan_data)
        
        # 4. Enforce: Execute the Plan's actions
        results = enforcer.enforce_plan(plan, incident)
        
        # Save execution results to database
        db_results = []
        for result in results:
            db_result = ExecutionResult(
                execution_id=str(uuid.uuid4()),
                plan_id=plan.plan_id,
                action_id=result.action_id,
                status=result.status,
                output=result.output,
                error=result.error,
                executed_at=result.executed_at,
                user_id=user_id
            )
            session.add(db_result)
            db_results.append(db_result)
        session.commit()
        
        # Update incident status based on results
        db_incident.status = incident.status
        db_incident.updated_at = datetime.utcnow()
        session.add(db_incident)
        
        # Update plan status
        db_plan.status = "executed"
        session.add(db_plan)
        session.commit()
        
        # Publish appropriate events
        execution_data = {
            "plan_id": db_plan.plan_id,
            "incident_id": db_incident.incident_id,
            "status": incident.status,
            "user_id": user_id
        }
        publish_plan_executed(execution_data)
        
        if incident.status == "resolved":
            publish_remediation_succeeded(execution_data)
        elif incident.status == "failed_remediation":
            publish_remediation_failed(execution_data)
        
        # Return execution results
        return db_results
        
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        raise
        
async def get_incident(
    incident_id: str,
    user_id: Optional[int] = None,
    session: Session = None
) -> Optional[Dict[str, Any]]:
    """
    Get an incident by ID.
    
    Args:
        incident_id: The incident ID
        user_id: Optional user ID for filtering
        session: Database session
        
    Returns:
        Incident data or None if not found
    """
    query = select(Incident).where(Incident.incident_id == incident_id)
    if user_id is not None:
        query = query.where(Incident.user_id == user_id)
    
    incident = session.exec(query).first()
    if not incident:
        return None
    
    return {
        "incident_id": incident.incident_id,
        "affected_resource": incident.affected_resource,
        "failure_type": incident.failure_type,
        "description": incident.description,
        "severity": incident.severity,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at,
        "status": incident.status
    }

async def list_incidents(
    user_id: Optional[int] = None,
    session: Session = None,
    limit: int = 10,
    offset: int = 0,
    status: Optional[str] = None,
    severity: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List incidents with optional filtering.
    
    Args:
        user_id: Optional user ID for filtering
        session: Database session
        limit: Maximum number of incidents to return
        offset: Number of incidents to skip
        status: Optional status filter
        severity: Optional severity filter
        
    Returns:
        List of incidents
    """
    query = select(Incident)
    if user_id is not None:
        query = query.where(Incident.user_id == user_id)
    if status is not None:
        query = query.where(Incident.status == status)
    if severity is not None:
        query = query.where(Incident.severity == severity)
    
    query = query.order_by(Incident.created_at.desc()).offset(offset).limit(limit)
    incidents = session.exec(query).all()
    
    result = []
    for incident in incidents:
        result.append({
            "incident_id": incident.incident_id,
            "affected_resource": incident.affected_resource,
            "failure_type": incident.failure_type,
            "description": incident.description,
            "severity": incident.severity,
            "created_at": incident.created_at,
            "updated_at": incident.updated_at,
            "status": incident.status
        })
    
    return result

async def generate_plan(
    incident: Dict[str, Any],
    user_id: Optional[int] = None,
    session: Session = None
) -> Dict[str, Any]:
    """
    Generate a remediation plan for an incident.
    
    Args:
        incident: The incident data
        user_id: Optional user ID
        session: Database session
        
    Returns:
        Generated plan
    """
    # Convert incident dict to Incident object for the reasoner
    incident_obj = Incident(
        incident_id=incident["incident_id"],
        affected_resource=incident["affected_resource"],
        failure_type=incident["failure_type"],
        description=incident["description"],
        severity=incident["severity"],
        status=incident["status"],
        created_at=incident["created_at"],
        updated_at=incident["updated_at"],
        user_id=user_id
    )
    
    # Generate plan
    plan = reasoner.generate_plan(incident_obj)
    
    # Save plan to database
    db_plan = Plan(
        plan_id=plan.plan_id,
        incident_id=plan.incident_id,
        status="created",
        user_id=user_id
    )
    session.add(db_plan)
    session.commit()
    session.refresh(db_plan)
    
    # Save actions to database
    actions = []
    for i, action in enumerate(plan.actions):
        db_action = Action(
            action_id=action.action_id,
            plan_id=plan.plan_id,
            executor=action.executor,
            command=action.command,
            parameters=action.parameters,
            description=action.description,
            order=i
        )
        session.add(db_action)
        actions.append({
            "action_id": action.action_id,
            "executor": action.executor,
            "command": action.command,
            "parameters": action.parameters,
            "description": action.description,
            "order": i,
            "created_at": datetime.utcnow()
        })
    session.commit()
    
    # Publish plan generated event
    plan_data = {
        "plan_id": db_plan.plan_id,
        "incident_id": db_plan.incident_id,
        "user_id": user_id
    }
    publish_plan_generated(plan_data)
    
    return {
        "plan_id": db_plan.plan_id,
        "incident_id": db_plan.incident_id,
        "actions": actions,
        "created_at": db_plan.created_at,
        "status": db_plan.status
    }

async def get_plan(
    plan_id: str,
    user_id: Optional[int] = None,
    session: Session = None
) -> Optional[Dict[str, Any]]:
    """
    Get a plan by ID.
    
    Args:
        plan_id: The plan ID
        user_id: Optional user ID for filtering
        session: Database session
        
    Returns:
        Plan data or None if not found
    """
    query = select(Plan).where(Plan.plan_id == plan_id)
    if user_id is not None:
        query = query.where(Plan.user_id == user_id)
    
    plan = session.exec(query).first()
    if not plan:
        return None
    
    # Get actions for this plan
    actions_query = select(Action).where(Action.plan_id == plan_id).order_by(Action.order)
    actions = session.exec(actions_query).all()
    
    actions_data = []
    for action in actions:
        actions_data.append({
            "action_id": action.action_id,
            "executor": action.executor,
            "command": action.command,
            "parameters": action.parameters,
            "description": action.description,
            "order": action.order,
            "created_at": action.created_at
        })
    
    return {
        "plan_id": plan.plan_id,
        "incident_id": plan.incident_id,
        "actions": actions_data,
        "created_at": plan.created_at,
        "status": plan.status
    }

async def list_plans(
    user_id: Optional[int] = None,
    session: Session = None,
    limit: int = 10,
    offset: int = 0,
    status: Optional[str] = None,
    incident_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List plans with optional filtering.
    
    Args:
        user_id: Optional user ID for filtering
        session: Database session
        limit: Maximum number of plans to return
        offset: Number of plans to skip
        status: Optional status filter
        incident_id: Optional incident ID filter
        
    Returns:
        List of plans
    """
    query = select(Plan)
    if user_id is not None:
        query = query.where(Plan.user_id == user_id)
    if status is not None:
        query = query.where(Plan.status == status)
    if incident_id is not None:
        query = query.where(Plan.incident_id == incident_id)
    
    query = query.order_by(Plan.created_at.desc()).offset(offset).limit(limit)
    plans = session.exec(query).all()
    
    result = []
    for plan in plans:
        # Get actions for this plan
        actions_query = select(Action).where(Action.plan_id == plan.plan_id).order_by(Action.order)
        actions = session.exec(actions_query).all()
        
        actions_data = []
        for action in actions:
            actions_data.append({
                "action_id": action.action_id,
                "executor": action.executor,
                "command": action.command,
                "parameters": action.parameters,
                "description": action.description,
                "order": action.order,
                "created_at": action.created_at
            })
        
        result.append({
            "plan_id": plan.plan_id,
            "incident_id": plan.incident_id,
            "actions": actions_data,
            "created_at": plan.created_at,
            "status": plan.status
        })
    
    return result

async def execute_plan(
    plan: Dict[str, Any],
    user_id: Optional[int] = None,
    session: Session = None
) -> List[Dict[str, Any]]:
    """
    Execute a remediation plan.
    
    Args:
        plan: The plan data
        user_id: Optional user ID
        session: Database session
        
    Returns:
        List of execution results
    """
    # Get the incident
    incident_query = select(Incident).where(Incident.incident_id == plan["incident_id"])
    if user_id is not None:
        incident_query = incident_query.where(Incident.user_id == user_id)
    
    db_incident = session.exec(incident_query).first()
    if not db_incident:
        raise ValueError(f"Incident {plan['incident_id']} not found")
    
    # Convert to objects for the enforcer
    incident_obj = Incident(
        incident_id=db_incident.incident_id,
        affected_resource=db_incident.affected_resource,
        failure_type=db_incident.failure_type,
        description=db_incident.description,
        severity=db_incident.severity,
        status=db_incident.status,
        created_at=db_incident.created_at,
        updated_at=db_incident.updated_at,
        user_id=db_incident.user_id
    )
    
    actions = []
    for action_data in plan["actions"]:
        actions.append(Action(
            action_id=action_data["action_id"],
            executor=action_data["executor"],
            command=action_data["command"],
            parameters=action_data["parameters"],
            description=action_data["description"]
        ))
    
    plan_obj = Plan(
        plan_id=plan["plan_id"],
        incident_id=plan["incident_id"],
        actions=actions,
        created_at=plan["created_at"]
    )
    
    # Execute plan
    results = enforcer.enforce_plan(plan_obj, incident_obj)
    
    # Save execution results to database
    db_results = []
    for result in results:
        db_result = ExecutionResult(
            execution_id=str(uuid.uuid4()),
            plan_id=plan["plan_id"],
            action_id=result.action_id,
            status=result.status,
            output=result.output,
            error=result.error,
            executed_at=result.executed_at,
            user_id=user_id
        )
        session.add(db_result)
        db_results.append({
            "execution_id": db_result.execution_id,
            "plan_id": db_result.plan_id,
            "action_id": db_result.action_id,
            "status": db_result.status,
            "output": db_result.output,
            "error": db_result.error,
            "executed_at": db_result.executed_at
        })
    session.commit()
    
    # Update incident status
    db_incident.status = incident_obj.status
    db_incident.updated_at = datetime.utcnow()
    session.add(db_incident)
    
    # Update plan status
    plan_query = select(Plan).where(Plan.plan_id == plan["plan_id"])
    db_plan = session.exec(plan_query).first()
    db_plan.status = "executed"
    session.add(db_plan)
    session.commit()
    
    # Publish appropriate events
    execution_data = {
        "plan_id": plan["plan_id"],
        "incident_id": db_incident.incident_id,
        "status": db_incident.status,
        "user_id": user_id
    }
    publish_plan_executed(execution_data)
    
    if db_incident.status == "resolved":
        publish_remediation_succeeded(execution_data)
    elif db_incident.status == "failed_remediation":
        publish_remediation_failed(execution_data)
    
    return db_results

async def get_execution_result(
    execution_id: str,
    user_id: Optional[int] = None,
    session: Session = None
) -> Optional[Dict[str, Any]]:
    """
    Get an execution result by ID.
    
    Args:
        execution_id: The execution result ID
        user_id: Optional user ID for filtering
        session: Database session
        
    Returns:
        Execution result data or None if not found
    """
    query = select(ExecutionResult).where(ExecutionResult.execution_id == execution_id)
    if user_id is not None:
        query = query.where(ExecutionResult.user_id == user_id)
    
    result = session.exec(query).first()
    if not result:
        return None
    
    return {
        "execution_id": result.execution_id,
        "plan_id": result.plan_id,
        "action_id": result.action_id,
        "status": result.status,
        "output": result.output,
        "error": result.error,
        "executed_at": result.executed_at
    }

async def list_execution_results(
    user_id: Optional[int] = None,
    session: Session = None,
    limit: int = 10,
    offset: int = 0,
    plan_id: Optional[str] = None,
    action_id: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List execution results with optional filtering.
    
    Args:
        user_id: Optional user ID for filtering
        session: Database session
        limit: Maximum number of results to return
        offset: Number of results to skip
        plan_id: Optional plan ID filter
        action_id: Optional action ID filter
        status: Optional status filter
        
    Returns:
        List of execution results
    """
    query = select(ExecutionResult)
    if user_id is not None:
        query = query.where(ExecutionResult.user_id == user_id)
    if plan_id is not None:
        query = query.where(ExecutionResult.plan_id == plan_id)
    if action_id is not None:
        query = query.where(ExecutionResult.action_id == action_id)
    if status is not None:
        query = query.where(ExecutionResult.status == status)
    
    query = query.order_by(ExecutionResult.executed_at.desc()).offset(offset).limit(limit)
    results = session.exec(query).all()
    
    result_list = []
    for result in results:
        result_list.append({
            "execution_id": result.execution_id,
            "plan_id": result.plan_id,
            "action_id": result.action_id,
            "status": result.status,
            "output": result.output,
            "error": result.error,
            "executed_at": result.executed_at
        })
    
    return result_list

def delete_user_data(user_id: int):
    """
    Delete all data belonging to a specific user when they are deleted.
    
    Args:
        user_id: The user ID
    """
    from sqlmodel import Session
    from app.database import engine
    
    try:
        with Session(engine) as session:
            # Delete incidents
            incidents = session.exec(select(Incident).where(Incident.user_id == user_id)).all()
            for incident in incidents:
                session.delete(incident)
            
            # Delete plans
            plans = session.exec(select(Plan).where(Plan.user_id == user_id)).all()
            for plan in plans:
                # Delete associated actions
                actions = session.exec(select(Action).where(Action.plan_id == plan.plan_id)).all()
                for action in actions:
                    session.delete(action)
                session.delete(plan)
            
            # Delete execution results
            results = session.exec(select(ExecutionResult).where(ExecutionResult.user_id == user_id)).all()
            for result in results:
                session.delete(result)
            
            # Delete raw events
            events = session.exec(select(RawEvent).where(RawEvent.user_id == user_id)).all()
            for event in events:
                session.delete(event)
            
            session.commit()
            
            # Clear user cache
            cache_flush_user(user_id)
            
            logger.info(f"Deleted all data for user {user_id}")
    except Exception as e:
        logger.error(f"Error deleting data for user {user_id}: {str(e)}")


