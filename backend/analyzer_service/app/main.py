from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.llm_client import analyze_kubernetes_incident_sync, IncidentSolution
from fastapi import BackgroundTasks
from app.schemas import KubernetesEvent, IncidentStats
from app.incident_processor import parse_flexible_incident_data, process_flexible_incidents
from app.logger import logger
from app.email_client import send_incident_email
from app.database import create_db_and_tables, get_session, engine
from app.models import IncidentModel,ExecutorStatusModel
from sqlmodel import Session, select

from typing import List, Optional, Dict, Any, Union
import datetime
import uuid
import json

# Create FastAPI app with metadata for documentation
app = FastAPI(
    title="KubeSage Analyzer Service",
    description="""
    The Analyzer Service processes Kubernetes events and incidents, determines their severity,
    and takes appropriate actions. Critical incidents require user approval via email,
    while normal incidents are processed automatically.
    
    Supports flexible incident formats from various sources including Kubernetes events,
    monitoring systems, and custom incident data.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

@app.on_event("startup")
def on_startup():
    """Initialize database on startup"""
    try:
        logger.info("Creating database tables...")
        create_db_and_tables()
        logger.info("Database tables created successfully")
        
        # Remove the migration code since AlertModel no longer exists
        # logger.info("Running database migration...")
        # from app.migrations.db_utils import migrate_database
        # migrate_database()
        # logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    logger.info("Database initialization completed")

@app.post("/incidents", 
    summary="Process incoming Kubernetes incidents/events",
    description="""
    Receives and processes Kubernetes events and incidents from various monitoring systems.
    
    Supported formats:
    - Kubernetes native events
    - Custom incident formats
    - Monitoring system alerts converted to incidents
    
    The API automatically detects the format and processes accordingly.
    """,
    response_description="Confirmation of incident processing",
    tags=["Incidents"])
async def receive_incidents(
    background_tasks: BackgroundTasks,
    request_data: Dict[str, Any] = Body(..., 
        description="Incident data in any format",
    )
):
    """
    Process incoming Kubernetes incidents with flexible format support.
    
    - Automatically detects incident format
    - Sends email notifications for Warning incidents
    - For Warning incidents: Waits for user approval before remediation
    - For Normal incidents: Automatically proceeds with remediation
    """
    try:
        logger.info("Received incident batch - processing with flexible format support")
        
        flexible_incidents = parse_flexible_incident_data(request_data)
        await process_flexible_incidents(flexible_incidents, background_tasks)
        
        return {"status": "Incidents processed successfully"}
        
    except Exception as e:
        logger.error(f"Error processing incidents: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Unable to process incident data: {str(e)}")

@app.get("/incidents", 
    summary="Get all incidents",
    description="Retrieves all incidents from the database with optional filtering.",
    response_model=List[IncidentModel],
    tags=["Incidents"])
async def get_incidents(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    type: Optional[str] = None,
    namespace: Optional[str] = None,
    involved_object_kind: Optional[str] = None
):
    """
    Get all incidents with optional filtering.
    
    Parameters:
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **type**: Filter by incident type (Normal, Warning)
    - **namespace**: Filter by namespace
    - **involved_object_kind**: Filter by involved object kind (Pod, Service, etc.)
    """
    query = select(IncidentModel)
    
    # Apply filters if provided
    if type:
        query = query.where(IncidentModel.type == type)
    
    if namespace:
        query = query.where(IncidentModel.metadata_namespace == namespace)
        
    if involved_object_kind:
        query = query.where(IncidentModel.involved_object_kind == involved_object_kind)
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    results = session.exec(query).all()
    
    return results

@app.get("/incidents/{incident_id}", 
    summary="Get incident by ID",
    description="Retrieves a specific incident by its ID.",
    response_model=IncidentModel,
    tags=["Incidents"])
async def get_incident(incident_id: str, session: Session = Depends(get_session)):
    """
    Get a specific incident by ID.
    
    Parameters:
    - **incident_id**: Unique identifier for the incident
    """
    incident = session.exec(select(IncidentModel).where(IncidentModel.id == incident_id)).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident



@app.post("/analyze-incident", response_model=dict)
async def analyze_incident_endpoint(
    incident_data: dict,
):
    """
    Analyze a Kubernetes incident using LLM and return structured solution
    
    Args:
        incident_data: Dictionary containing incident information
        
    Returns:
        Structured solution with analysis and remediation steps
    """
    try:
        logger.info(f"Received incident analysis request for: {incident_data.get('id', 'unknown')}")
        
        # Analyze incident using LLM (now using sync function with timeout handling)
        solution = analyze_kubernetes_incident_sync(incident_data)
        
        # Convert to dict for response
        solution_dict = solution.model_dump()
        
        logger.info(f"Successfully analyzed incident: {incident_data.get('id', 'unknown')}")
        
        return {
            "success": True,
            "incident_id": incident_data.get('id'),
            "solution": solution_dict,
            "message": "Incident analyzed successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze incident: {str(e)}")
        # Still return a response even if analysis fails
        return {
            "success": False,
            "incident_id": incident_data.get('id', 'unknown'),
            "error": str(e),
            "message": "Incident analysis failed, but basic information recorded"
        }

@app.get("/analyze-incident/{incident_id}")
async def analyze_incident_by_id_endpoint(
    incident_id: str,
    session: Session = Depends(get_session)
):
    """
    Analyze an existing incident by ID
    
    Args:
        incident_id: ID of the incident to analyze
        
    Returns:
        Structured solution with analysis and remediation steps
    """
    try:
        # Get incident from database
        incident = session.exec(
            select(IncidentModel).where(IncidentModel.id == incident_id)
        ).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Convert incident model to dict
        incident_data = {
            'id': incident.id,
            'type': incident.type,
            'reason': incident.reason,
            'message': incident.message,
            'metadata_namespace': incident.metadata_namespace,
            'metadata_creation_timestamp': incident.metadata_creation_timestamp.isoformat() if incident.metadata_creation_timestamp else None,
            'involved_object_kind': incident.involved_object_kind,
            'involved_object_name': incident.involved_object_name,
            'source_component': incident.source_component,
            'source_host': incident.source_host,
            'reporting_component': incident.reporting_component,
            'count': incident.count,
            'first_timestamp': incident.first_timestamp.isoformat() if incident.first_timestamp else None,
            'last_timestamp': incident.last_timestamp.isoformat() if incident.last_timestamp else None,
            'involved_object_labels': incident.involved_object_labels or {},
            'involved_object_annotations': incident.involved_object_annotations or {}
        }
        
        # Analyze incident using LLM (now using sync function)
        solution = analyze_kubernetes_incident_sync(incident_data)
        
        return {
            "success": True,
            "incident_id": incident_id,
            "solution": solution.model_dump(),
            "message": "Incident analyzed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze incident {incident_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze incident: {str(e)}"
        )


# Executor Status Endpoints
@app.get("/executors/status",
    summary="Get all executor statuses",
    description="Get the current status of all executors (Active/Inactive)",
    tags=["Executors"])
async def get_executor_status(session: Session = Depends(get_session)):
    """
    Get status of all executors
    
    Returns:
    - List of executors with their current status (0=Active, 1=Inactive)
    """
    try:
        executors = session.exec(select(ExecutorStatusModel)).all()
        return {
            "executors": [
                {
                    "name": executor.executor_name,
                    "status": executor.status,
                    "status_text": "Active" if executor.status == 0 else "Inactive",
                    "updated_at": executor.updated_at
                }
                for executor in executors
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting executor status: {str(e)}")

@app.post("/executors/{executor_name}/status",
    summary="Update executor status",
    description="Update the status of a specific executor (0=Active, 1=Inactive)",
    tags=["Executors"])
async def update_executor_status(
    executor_name: str,
    status: int = Body(..., description="0 for Active, 1 for Inactive"),
    session: Session = Depends(get_session)
):
    """
    Update executor status
    
    Parameters:
    - **executor_name**: Name of executor (kubectl, crossplane, argocd)
    - **status**: 0 for Active, 1 for Inactive
    """
    try:
        if executor_name not in ["kubectl", "crossplane", "argocd"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid executor name. Must be: kubectl, crossplane, or argocd"
            )
        
        if status not in [0, 1]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid status. Must be 0 (Active) or 1 (Inactive)"
            )
        
        # Find and update executor
        executor = session.exec(
            select(ExecutorStatusModel).where(ExecutorStatusModel.executor_name == executor_name)
        ).first()
        
        if not executor:
            # Create new executor if doesn't exist
            executor = ExecutorStatusModel(executor_name=executor_name, status=status)
            session.add(executor)
        else:
            executor.status = status
            executor.updated_at = datetime.datetime.now(timezone.utc)
        
        session.commit()
        session.refresh(executor)
        
        status_text = "Active" if status == 0 else "Inactive"
        logger.info(f"Updated executor '{executor_name}' status to {status_text}")
        
        return {
            "success": True,
            "executor_name": executor_name,
            "status": status,
            "status_text": status_text,
            "message": f"Executor '{executor_name}' is now {status_text}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating executor status: {str(e)}")

@app.get("/executors/active",
    summary="Get active executors",
    description="Get list of currently active executors",
    tags=["Executors"])
async def get_active_executors(session: Session = Depends(get_session)):
    """
    Get list of active executors
    
    Returns:
    - List of executor names that are currently active
    """
    try:
        active_executors = session.exec(
            select(ExecutorStatusModel).where(ExecutorStatusModel.status == 0)
        ).all()
        
        return {
            "active_executors": [executor.executor_name for executor in active_executors],
            "count": len(active_executors)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting active executors: {str(e)}")

