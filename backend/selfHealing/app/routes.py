from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from app.database import get_session
from app.models import RawEvent, Incident, Plan, Action, ExecutionResult
from app.schemas import (  # Pydantic schemas for API
    RawEventCreate, RawEventResponse,
    IncidentCreate, IncidentResponse, IncidentList,
    PlanCreate, PlanResponse, PlanList,
    ActionCreate, ActionResponse,
    ExecutionResultCreate, ExecutionResultResponse,
    MessageResponse
)
from app.auth import get_current_user
from app.services import (
    process_raw_event,
    get_incident,
    list_incidents,
    generate_plan,
    get_plan,
    list_plans,
    execute_plan,
    get_execution_result,
    list_execution_results
)
from app.queue import (
    publish_incident_created,
    publish_incident_updated,
    publish_plan_generated,
    publish_plan_executed,
    publish_remediation_failed,
    publish_remediation_succeeded
)
from app.logger import logger

self_healing_router = APIRouter()

@self_healing_router.post("/self-heal", response_model=List[ExecutionResultResponse])
async def self_heal_endpoint(
    raw_event: RawEventCreate,
    session: Session = Depends(get_session),
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    Receives a raw event, processes it through the self-healing pipeline:
    1. Analyze: Transform raw event into a structured Incident.
    2. Reason: Generate a remediation Plan using an LLM.
    3. Enforce: Execute the Plan's actions.
    """
    user_id = current_user["id"] if current_user else None
    logger.info(f"Received event for self-healing from user {user_id}")
    
    try:
        # Create a RawEvent object from the raw_event data
        event_obj = RawEvent(
            event_data=raw_event.event_data,
            user_id=user_id,
            received_at=datetime.utcnow()
        )
        
        # Save the raw event to the database
        session.add(event_obj)
        session.commit()
        session.refresh(event_obj)
        
        # Process the event through the analyzer to create an incident
        try:
            from app.agents.analyzer import AnalyzerAgent
            analyzer = AnalyzerAgent()
            incident = analyzer.process_event(event_obj)
            incident.user_id = user_id  # Ensure user_id is set
            
            # Save the incident to the database
            session.add(incident)
            session.commit()
            session.refresh(incident)
            
            # Publish incident created event
            incident_data = {
                "incident_id": incident.incident_id,
                "affected_resource": incident.affected_resource,
                "failure_type": incident.failure_type,
                "severity": incident.severity,
                "user_id": user_id
            }
            publish_incident_created(incident_data)
            logger.info(f"Created incident {incident.incident_id} for event")
            
        except Exception as e:
            logger.error(f"Error analyzing event: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to analyze event: {str(e)}")
        
        # Generate a remediation plan using the reasoner
        try:
            from app.agents.reasoner import ReasonerAgent
            reasoner = ReasonerAgent()
            plan = reasoner.generate_plan(incident)
            
            # Validate that the plan has the required 'actions' field
            if not hasattr(plan, 'actions') or not plan.actions:
                logger.error("Generated plan does not have required 'actions' field")
                # Create a fallback plan with at least one action
                plan = Plan(
                    plan_id=str(uuid.uuid4()),
                    incident_id=incident.incident_id,
                    actions=[
                        Action(
                            action_id=str(uuid.uuid4()),
                            executor="kubectl",
                            command="kubectl get pods -A",
                            parameters={},
                            description="Basic diagnostic command (fallback)"
                        )
                    ],
                    created_at=datetime.utcnow()
                )
            
            # First, save the plan to the database
            plan_obj = Plan(
                plan_id=plan.plan_id,
                incident_id=incident.incident_id,
                created_at=datetime.utcnow(),
                status="created"
            )
            session.add(plan_obj)
            session.commit()  # Commit to get the plan_id in the database
            
            # Now save the plan actions to the database
            for action in plan.actions:
                action_obj = Action(
                    action_id=action.action_id,
                    plan_id=plan.plan_id,
                    executor=action.executor,
                    command=action.command,
                    parameters=action.parameters,
                    description=action.description
                )
                session.add(action_obj)
            
            session.commit()
            
            # Publish plan generated event
            plan_data = {
                "plan_id": plan.plan_id,
                "incident_id": incident.incident_id,
                "user_id": user_id,
                "action_count": len(plan.actions)
            }
            publish_plan_generated(plan_data)
            logger.info(f"Generated plan {plan.plan_id} with {len(plan.actions)} actions")
            
        except Exception as e:
            logger.error(f"Error generating plan: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate remediation plan: {str(e)}")

        
        # Execute the plan using the enforcer
        try:
            from app.agents.enforcer import EnforcerAgent
            enforcer = EnforcerAgent()
            results = enforcer.enforce_plan(plan, incident)
            
            # Save execution results to the database
            for result in results:
                result.user_id = user_id
                session.add(result)
            
            session.commit()
            
            # Update incident status based on results
            success_count = sum(1 for r in results if r.status == "success")
            total_count = len(results)
            
            if success_count == total_count:
                incident.status = "resolved"
                publish_remediation_succeeded({
                    "incident_id": incident.incident_id,
                    "plan_id": plan.plan_id,
                    "user_id": user_id
                })
            elif success_count > 0:
                incident.status = "partially_remediated"
                publish_remediation_failed({
                    "incident_id": incident.incident_id,
                    "plan_id": plan.plan_id,
                    "user_id": user_id,
                    "reason": "Some actions failed"
                })
            else:
                incident.status = "failed_remediation"
                publish_remediation_failed({
                    "incident_id": incident.incident_id,
                    "plan_id": plan.plan_id,
                    "user_id": user_id,
                    "reason": "All actions failed"
                })
            
            incident.updated_at = datetime.utcnow()
            session.add(incident)
            session.commit()
            
            # Convert results to response format
            response_results = []
            for result in results:
                response_results.append(ExecutionResultResponse(
                    execution_id=result.execution_id,
                    plan_id=result.plan_id,
                    action_id=result.action_id,
                    status=result.status,
                    output=result.output,
                    error=result.error,
                    executed_at=result.executed_at
                ))
            
            return response_results
            
        except Exception as e:
            logger.error(f"Error executing plan: {str(e)}", exc_info=True)
            # Update incident status to indicate failure
            incident.status = "failed_remediation"
            incident.updated_at = datetime.utcnow()
            session.add(incident)
            session.commit()
            
            publish_remediation_failed({
                "incident_id": incident.incident_id,
                "plan_id": plan.plan_id if 'plan' in locals() else None,
                "user_id": user_id,
                "reason": str(e)
            })
            
            raise ValueError(f"Failed to execute remediation plan: {str(e)}")
        
    except ValueError as e:
        logger.error(f"Error processing event: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing self-healing request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))




@self_healing_router.get("/incidents", response_model=IncidentList)
async def get_incidents(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    List incidents with optional filtering.
    """
    user_id = current_user["id"]
    incidents = await list_incidents(
        user_id=user_id,
        session=session,
        limit=limit,
        offset=offset,
        status=status,
        severity=severity
    )
    return {"incidents": incidents}

@self_healing_router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident_by_id(
    incident_id: str,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a specific incident by ID.
    """
    user_id = current_user["id"]
    incident = await get_incident(
        incident_id=incident_id,
        user_id=user_id,
        session=session
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@self_healing_router.post("/incidents/{incident_id}/plans", response_model=PlanResponse)
async def create_plan(
    incident_id: str,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate a remediation plan for an incident.
    """
    user_id = current_user["id"]
    
    # Check if incident exists
    incident = await get_incident(
        incident_id=incident_id,
        user_id=user_id,
        session=session
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Generate plan
    plan = await generate_plan(
        incident=incident,
        user_id=user_id,
        session=session
    )
    
    return plan

@self_healing_router.get("/plans", response_model=PlanList)
async def get_plans(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    incident_id: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    List remediation plans with optional filtering.
    """
    user_id = current_user["id"]
    plans = await list_plans(
        user_id=user_id,
        session=session,
        limit=limit,
        offset=offset,
        status=status,
        incident_id=incident_id
    )
    return {"plans": plans}

@self_healing_router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan_by_id(
    plan_id: str,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a specific remediation plan by ID.
    """
    user_id = current_user["id"]
    plan = await get_plan(
        plan_id=plan_id,
        user_id=user_id,
        session=session
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@self_healing_router.post("/plans/{plan_id}/execute", response_model=List[ExecutionResultResponse])
async def execute_plan_by_id(
    plan_id: str,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    Execute a remediation plan.
    """
    user_id = current_user["id"]
    
    # Check if plan exists
    plan = await get_plan(
        plan_id=plan_id,
        user_id=user_id,
        session=session
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Execute plan
    results = await execute_plan(
        plan=plan,
        user_id=user_id,
        session=session
    )
    
    return results

@self_healing_router.get("/execution-results", response_model=List[ExecutionResultResponse])
async def get_execution_results(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    plan_id: Optional[str] = None,
    action_id: Optional[str] = None,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """
    List execution results with optional filtering.
    """
    user_id = current_user["id"]
    results = await list_execution_results(
        user_id=user_id,
        session=session,
        limit=limit,
        offset=offset,
        plan_id=plan_id,
        action_id=action_id,
        status=status
    )
    return results
