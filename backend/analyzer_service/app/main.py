from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
# Update the import statement at the top of main.py
from app.llm_client import analyze_kubernetes_incident_sync, IncidentSolution, analyze_kubernetes_remediation_sync
from fastapi import BackgroundTasks
from app.schemas import KubernetesEvent, IncidentStats
from app.incident_processor import parse_flexible_incident_data, process_flexible_incidents
from app.logger import logger
from app.email_client import send_incident_email
from app.database import create_db_and_tables, get_session, engine
from app.models import IncidentModel, ExecutorStatusModel, SolutionModel, RemediationHistoryModel, CommandExecutionHistoryModel
from sqlmodel import Session, select, func
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware

from typing import List, Optional, Dict, Any, Union
import datetime
from datetime import timezone
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
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.on_event("startup")
def on_startup():
    """Initialize database on startup"""
    try:
        logger.info("Creating database tables...")
        create_db_and_tables()
        logger.info("Database tables created successfully")
        
        # Initialize default executors
        logger.info("Initializing default executors...")
        with Session(engine) as session:
            # Check if executors exist, if not create them
            executors_to_create = ["kubectl", "crossplane", "argocd"]
            
            for executor_name in executors_to_create:
                existing_executor = session.exec(
                    select(ExecutorStatusModel).where(ExecutorStatusModel.executor_name == executor_name)
                ).first()
                
                if not existing_executor:
                    new_executor = ExecutorStatusModel(
                        executor_name=executor_name,
                        status=0 if executor_name == "kubectl" else 1  # kubectl active by default
                    )
                    session.add(new_executor)
                    logger.info(f"Created executor: {executor_name}")
            
            session.commit()
        
        logger.info("Default executors initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    logger.info("Database initialization completed")



#  api_1 -Incident data processing and store in database 
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
        print(f"\n🚀 RECEIVED INCIDENT BATCH - STARTING PROCESSING")
        print("="*80)
        print(f"📥 REQUEST DATA TYPE: {type(request_data)}")
        print(f"📥 REQUEST DATA: {request_data}")
        print("="*80)
        
        logger.info("Received incident batch - processing with flexible format support")
        
        flexible_incidents = parse_flexible_incident_data(request_data)
        print(f"📋 PARSED {len(flexible_incidents)} FLEXIBLE INCIDENTS")
        
        await process_flexible_incidents(flexible_incidents, background_tasks)
        
        print(f"✅ INCIDENT PROCESSING COMPLETED SUCCESSFULLY")
        return {"status": "Incidents processed successfully"}
        
    except Exception as e:
        print(f"Error processing incidents: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Unable to process incident data: {str(e)}")

#  api_2 - Get all incidents
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

#  api_3 - Get incident by ID
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



#  api_4 - analyze incident and llm give solution after analysis
@app.post("/analyze-incident", response_model=dict)
async def analyze_incident_endpoint(
    incident_data: dict,
    session: Session = Depends(get_session)
):
    """
    Analyze a Kubernetes incident using LLM and return structured solution
    
    Args:
        incident_data: Dictionary containing incident information
        
    Returns:
        Structured solution with analysis and remediation steps
    """
    try:

        incident_id = incident_data.get('id', 'unknown')
        logger.info(f"🚀 Received incident analysis request for: {incident_id}")
        
        # Get active executors
        active_executors = session.exec(
            select(ExecutorStatusModel).where(ExecutorStatusModel.status == 0)
        ).all()
        active_executor_names = [executor.executor_name for executor in active_executors]
        
        if not active_executor_names:
            active_executor_names = ["kubectl"]
        
        logger.info(f"🔧 Active executors: {active_executor_names}")
        
        # Analyze incident using LLM (now using sync function with timeout handling)
        solution = analyze_kubernetes_incident_sync(incident_data, active_executor_names)
        
        # Save solution to database
        try:
            logger.info(f"💾 Saving solution to database for incident: {incident_id}")
            
            solution_model = SolutionModel(
                solution_id=solution.solution_id,
                incident_id=solution.incident_id,
                summary=solution.summary,
                analysis=solution.analysis,
                steps=[step.model_dump() for step in solution.steps],  # Convert to dict
                confidence_score=solution.confidence_score,
                estimated_time_to_resolve_mins=solution.estimated_time_to_resolve_mins,  # Fixed field name
                severity_level=solution.severity_level,
                recommendations=solution.recommendations,
                executed_at=None,
                execution_result=None
            )
            
            session.add(solution_model)
            session.commit()
            session.refresh(solution_model)
            
            logger.info(f"✅ Solution saved to database with ID: {solution_model.id}")
            
        except Exception as db_error:
            logger.error(f"⚠️ Error saving solution to database: {str(db_error)}")
            # Continue even if database save fails - don't block the response
        
        # Return dynamic LLM response
        return {
            "success": True,
            "incident_id": incident_id,
            "solution": solution.model_dump(),
            "message": "Incident analyzed successfully using LLM",
            "llm_service_status": "active",
            "analysis_type": "dynamic",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in incident analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Incident analysis failed: {str(e)}"
        )

#  api_5 - analyze incident by id
@app.get("/analyze-incident/{incident_id}")
async def analyze_incident_by_id_endpoint(
    incident_id: str,
    session: Session = Depends(get_session)
):
    """
    Analyze an existing incident by ID using LLM
    """
    try:
        # Get incident from database
        incident = session.exec(
            select(IncidentModel).where(IncidentModel.id == incident_id)
        ).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Get active executors
        active_executors = session.exec(
            select(ExecutorStatusModel).where(ExecutorStatusModel.status == 0)
        ).all()
        active_executor_names = [executor.executor_name for executor in active_executors]
        
        if not active_executor_names:
            active_executor_names = ["kubectl"]
        
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
        
        # Analyze incident using LLM - NO FALLBACK
        try:
            solution = analyze_kubernetes_incident_sync(incident_data, active_executor_names)
            
            return {
                "success": True,
                "incident_id": incident_id,
                "solution": solution.model_dump(),
                "message": "Incident analyzed successfully using LLM",
                "llm_service_status": "active",
                "analysis_type": "dynamic",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
        except Exception as llm_error:
            logger.error(f"❌ LLM analysis failed for incident {incident_id}: {str(llm_error)}")
            raise HTTPException(
                status_code=503,
                detail=f"LLM analysis service unavailable: {str(llm_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to analyze incident {incident_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze incident: {str(e)}"
        )

#  api_6 - get executor status
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

#  api_7 - give executor status
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

#  api_8 - get active executors
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

#  api_9 -  Analyze Kubernetes issue and get remediation command
@app.post("/remediate", 
    summary="Analyze Kubernetes issue and get remediation command",
    description="Analyze a Kubernetes alert/issue and get a single remediation command using LLM",
    tags=["Remediation"])
async def analyze_remediation(
    alert_data: Dict[str, Any] = Body(...,
        description="Alert/issue data for analysis",
        example={
            "alert_name": "HighCPUUsage",
            "namespace": "default",
            "pod_name": "backend-xyz-123",
            "usage": "95%",
            "threshold": "80%",
            "duration": "15m"
        }
    ),
    session: Session = Depends(get_session)
):
    """
    Analyze Kubernetes issue and provide remediation command using LLM
    """
    try:
        # Validate required fields
        if not alert_data.get("alert_name"):
            raise HTTPException(status_code=400, detail="alert_name is required")
        
        # Get active executors
        active_executors = session.exec(
            select(ExecutorStatusModel).where(ExecutorStatusModel.status == 0)
        ).all()
        active_executor_names = [executor.executor_name for executor in active_executors]
        
        if not active_executor_names:
            active_executor_names = ["kubectl"]
        
        # Analyze using LLM - NO FALLBACK
        try:
            remediation = analyze_kubernetes_remediation_sync(alert_data, active_executor_names)
            
            return {
                "success": True,
                "alert_name": alert_data.get("alert_name"),
                "remediation": {
                    "issue_summary": remediation.issue_summary,
                    "suggestion": remediation.suggestion,
                    "command": f"kubectl {remediation.command}",
                    "is_executable": remediation.is_executable,
                    "severity_level": remediation.severity_level,
                    "estimated_time_mins": remediation.estimated_time_mins,
                    "confidence_score": remediation.confidence_score,
                    "active_executors": remediation.active_executors
                },
                "llm_service_status": "active",
                "analysis_type": "dynamic",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
        except Exception as llm_error:
            logger.error(f"❌ LLM remediation analysis failed: {str(llm_error)}")
            raise HTTPException(
                status_code=503,
                detail=f"LLM remediation service unavailable: {str(llm_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing remediation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Remediation analysis failed: {str(e)}")

#  api_10 - Execute remediation command
@app.post("/remediate/execute",
    summary="Execute remediation command",
    description="Execute the provided remediation command with safety checks",
    tags=["Remediation"])
async def execute_remediation(
    execution_data: Dict[str, Any] = Body(...,
        description="Execution data with command details",
        example={
            "command": "get pods -n default",
            "is_executable": True,
            "executor": "kubectl",
            "confirm_execution": True
        }
    ),
    session: Session = Depends(get_session)
):
    """
    Execute a remediation command with safety checks
    
    Expected input:
    
    {
        "command": "get pods -n default",
        "is_executable": true,
        "executor": "kubectl", 
        "confirm_execution": true
    }
    
    
    Safety features:
    - Only executes commands marked as safe
    - Blocks destructive operations
    - Requires explicit confirmation
    - Timeout protection (30s limit)
    """
    try:
        # Require explicit confirmation
        if not execution_data.get("confirm_execution", False):
            raise HTTPException(
                status_code=400,
                detail="Execution requires explicit confirmation. Set 'confirm_execution': true"
            )
        
        # Import execution function
        from app.executor_client import execute_single_remediation_command
        
        # Execute the command
        start_time = datetime.datetime.utcnow()
        result = execute_single_remediation_command(execution_data)
        end_time = datetime.datetime.utcnow()
        
        # Save to remediation history
        try:
            history_record = RemediationHistoryModel(
                alert_name=execution_data.get("alert_name", "Manual Execution"),
                namespace=execution_data.get("namespace", "unknown"),
                resource_name=execution_data.get("resource_name"),
                command_executed=f"kubectl {execution_data.get('command', '')}",
                execution_status=result.get("status", "unknown"),
                execution_output=result.get("output", "")[:1000] if result.get("output") else None,
                error_message=result.get("error"),
                confidence_score=execution_data.get("confidence_score"),
                severity_level=execution_data.get("severity_level", "UNKNOWN"),
                execution_time_ms=int((end_time - start_time).total_seconds() * 1000)
            )
            session.add(history_record)
            session.commit()
        except Exception as history_error:
            logger.error(f"Failed to save remediation history: {str(history_error)}")
        
        return {
            "execution_result": result,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "safety_checks_passed": result.get("status") not in ["blocked", "skipped"],
            "execution_time_ms": int((end_time - start_time).total_seconds() * 1000)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing remediation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")

# api_11 - Analyze and Execute Remediation
@app.post("/remediate/analyze-and-execute",
    summary="Analyze issue and optionally execute remediation",
    description="Complete workflow: analyze Kubernetes issue and execute safe remediation",
    tags=["Remediation"])
async def analyze_and_execute_remediation(
    request_data: Dict[str, Any] = Body(...,
        description="Request with alert data and execution preferences",
        example={
            "alert_data": {
                "alert_name": "HighCPUUsage",
                "namespace": "default",
                "pod_name": "backend-xyz-123",
                "usage": "95%",
                "threshold": "80%",
                "duration": "15m"
            },
            "auto_execute": False,
            "confirm_execution": False
        }
    ),
    session: Session = Depends(get_session)
):
    """
    Complete remediation workflow: analyze + optional execution
    
    Input format:
    
    {
        "alert_data": {
            "alert_name": "HighCPUUsage",
            "namespace": "default", 
            "pod_name": "backend-xyz-123",
            "usage": "95%",
            "threshold": "80%",
            "duration": "15m"
        },
        "auto_execute": false,
        "confirm_execution": false
    }
    
    
    Workflow:
    1. Analyze the Kubernetes issue
    2. Generate safe remediation command
    3. Optionally execute if auto_execute=true and command is safe
    """
    try:
        alert_data = request_data.get("alert_data", {})
        auto_execute = request_data.get("auto_execute", False)
        confirm_execution = request_data.get("confirm_execution", False)
        
        # Step 1: Analyze the issue
        active_executors = session.exec(
            select(ExecutorStatusModel).where(ExecutorStatusModel.status == 0)
        ).all()
        active_executor_names = [executor.executor_name for executor in active_executors]
        
        if not active_executor_names:
            active_executor_names = ["kubectl"]
        
        from app.llm_client import analyze_kubernetes_remediation_sync
        
        remediation = analyze_kubernetes_remediation_sync(alert_data, active_executor_names)
        
        response = {
            "analysis": {
                "issue_summary": remediation.issue_summary,
                "suggestion": remediation.suggestion,
                "command": f"kubectl {remediation.command}",
                "is_executable": remediation.is_executable,
                "severity_level": remediation.severity_level,
                "confidence_score": remediation.confidence_score
            },
            "execution_result": None,
            "auto_executed": False
        }
        
        # Step 2: Optionally execute if conditions are met
        if auto_execute and remediation.is_executable and confirm_execution:
            from app.executor_client import execute_single_remediation_command
            
            execution_data = {
                "command": remediation.command,
                "is_executable": remediation.is_executable,
                "executor": "kubectl",
                "alert_name": alert_data.get("alert_name"),
                "namespace": alert_data.get("namespace"),
                "resource_name": alert_data.get("pod_name", alert_data.get("resource_name")),
                "confidence_score": remediation.confidence_score,
                "severity_level": remediation.severity_level
            }
            
            start_time = datetime.datetime.utcnow()
            execution_result = execute_single_remediation_command(execution_data)
            end_time = datetime.datetime.utcnow()
            
            response["execution_result"] = execution_result
            response["auto_executed"] = True
            
            # Save to history
            try:
                history_record = RemediationHistoryModel(
                    alert_name=alert_data.get("alert_name", "Auto Execution"),
                    namespace=alert_data.get("namespace", "unknown"),
                    resource_name=alert_data.get("pod_name", alert_data.get("resource_name")),
                    command_executed=f"kubectl {remediation.command}",
                    execution_status=execution_result.get("status", "unknown"),
                    execution_output=execution_result.get("output", "")[:1000] if execution_result.get("output") else None,
                    error_message=execution_result.get("error"),
                    confidence_score=remediation.confidence_score,
                    severity_level=remediation.severity_level,
                    execution_time_ms=int((end_time - start_time).total_seconds() * 1000)
                )
                session.add(history_record)
                session.commit()
            except Exception as history_error:
                logger.error(f"Failed to save remediation history: {str(history_error)}")
            
            logger.info(f"Auto-executed remediation for {alert_data.get('alert_name', 'unknown')}")
        
        elif auto_execute and not confirm_execution:
            response["execution_result"] = {
                "status": "skipped",
                "reason": "Auto-execution requires explicit confirmation"
            }
        
        elif auto_execute and not remediation.is_executable:
            response["execution_result"] = {
                "status": "skipped", 
                "reason": "Command not marked as safe for automatic execution"
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in analyze-and-execute workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

# api_12 - Get Remediation History
@app.get("/remediation/history",
    summary="Get remediation history",
    description="Get history of executed remediation commands",
    tags=["Remediation"])
async def get_remediation_history(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 50,
    alert_name: Optional[str] = None,
    namespace: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Get remediation execution history with optional filtering
    
    Parameters:
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    - **alert_name**: Filter by alert name
    - **namespace**: Filter by namespace
    - **status**: Filter by execution status (success, failed, skipped, blocked)
    """
    try:
        # Import here if needed
        from app.models import RemediationHistoryModel
        
        query = select(RemediationHistoryModel)
        
        if alert_name:
            query = query.where(RemediationHistoryModel.alert_name == alert_name)
        if namespace:
            query = query.where(RemediationHistoryModel.namespace == namespace)
        if status:
            query = query.where(RemediationHistoryModel.execution_status == status)
        
        query = query.order_by(RemediationHistoryModel.executed_at.desc())
        query = query.offset(skip).limit(limit)
        
        results = session.exec(query).all()
        
        return {
            "history": [
                {
                    "id": record.id,
                    "alert_name": record.alert_name,
                    "namespace": record.namespace,
                    "resource_name": record.resource_name,
                    "command": record.command_executed,
                    "status": record.execution_status,
                    "executed_at": record.executed_at,
                    "confidence_score": record.confidence_score,
                    "severity_level": record.severity_level,
                    "execution_time_ms": record.execution_time_ms,
                    "error_message": record.error_message if record.execution_status == "failed" else None
                }
                for record in results
            ],
            "total": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting remediation history: {str(e)}")

# api_13 - Get Remediation Statistics
@app.get("/remediation/stats",
    summary="Get remediation statistics",
    description="Get statistics about remediation executions",
    tags=["Remediation"])
async def get_remediation_stats(session: Session = Depends(get_session)):
    """
    Get remediation execution statistics
    """
    try:
        # Import here if needed
        from app.models import RemediationHistoryModel
        
        # Get total executions by status
        status_stats = session.exec(
            select(
                RemediationHistoryModel.execution_status,
                func.count(RemediationHistoryModel.id).label("count")
            ).group_by(RemediationHistoryModel.execution_status)
        ).all()
        
        # Get top alert types
        alert_stats = session.exec(
            select(
                RemediationHistoryModel.alert_name,
                func.count(RemediationHistoryModel.id).label("count")
            ).group_by(RemediationHistoryModel.alert_name)
            .order_by(func.count(RemediationHistoryModel.id).desc())
            .limit(10)
        ).all()
        
        # Get recent activity (last 24 hours)
        from datetime import timedelta
        recent_cutoff = datetime.datetime.utcnow() - timedelta(hours=24)
        recent_count = session.exec(
            select(func.count(RemediationHistoryModel.id))
            .where(RemediationHistoryModel.executed_at >= recent_cutoff)
        ).first()
        
        return {
            "execution_stats": {
                status.execution_status: status.count 
                for status in status_stats
            },
            "top_alerts": [
                {"alert_name": alert.alert_name, "count": alert.count}
                for alert in alert_stats
            ],
            "recent_activity": {
                "last_24_hours": recent_count or 0
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting remediation stats: {str(e)}")

# api_14 - Get Remediation Recommendations
@app.get("/incidents/{incident_id}/recommendations",
    summary="Get recommendations for specific incident",
    description="Get LLM-generated recommendations and commands for a specific incident",
    tags=["Recommendations"])
async def get_incident_recommendations(
    incident_id: str,
    session: Session = Depends(get_session)
):
    """
    Get recommendations and commands for a specific incident
    
    This API:
    1. Fetches incident from database by ID
    2. Analyzes it with LLM to get recommendations
    3. Returns structured recommendations with executable commands
    """
    try:
        # Get incident from database
        incident = session.exec(
            select(IncidentModel).where(IncidentModel.id == incident_id)
        ).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Get active executors
        active_executors = session.exec(
            select(ExecutorStatusModel).where(ExecutorStatusModel.status == 0)
        ).all()
        active_executor_names = [executor.executor_name for executor in active_executors]
        
        if not active_executor_names:
            active_executor_names = ["kubectl"]
        
        # Prepare incident data for LLM
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
        
        # Analyze with LLM
        solution = analyze_kubernetes_incident_sync(incident_data, active_executor_names)
        
        # Format response with executable commands
        recommendations = []
        for step in solution.steps:
            recommendations.append({
                "step_id": step.step_id,
                "description": step.description,
                "command": f"kubectl {step.command_or_payload.get('command', '')}",
                "action_type": step.action_type,
                "target_resource": step.target_resource,
                "expected_outcome": step.expected_outcome,
                "executor": step.executor,
                "is_executable": step.action_type in ["KUBECTL_GET_LOGS", "KUBECTL_DESCRIBE", "KUBECTL_GET", "MONITOR"]
            })
        
        return {
            "success": True,
            "incident_id": incident_id,
            "incident_summary": {
                "type": incident.type,
                "reason": incident.reason,
                "message": incident.message,
                "namespace": incident.metadata_namespace,
                "object": f"{incident.involved_object_kind}/{incident.involved_object_name}"
            },
            "analysis": {
                "summary": solution.summary,
                "severity_level": solution.severity_level,
                "confidence_score": solution.confidence_score,
                "estimated_time_mins": solution.estimated_time_to_resolve_mins
            },
            "recommendations": recommendations,
            "general_recommendations": solution.recommendations,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations for incident {incident_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

# api_15 - Execute Command
@app.post("/execute-command",
    summary="Execute kubectl command with safety checks",
    description="Execute a specific kubectl command with comprehensive safety checks and logging",
    tags=["Command Execution"])
async def execute_kubectl_command(
    command_data: Dict[str, Any] = Body(...,
        description="Command execution data",
        example={
            "incident_id": "123e4567-e89b-12d3-a456-426614174000",
            "command": "get pods -n default",
            "executor": "kubectl",
            "confirm_execution": True,
            "step_id": 1,
            "expected_outcome": "List of pods in default namespace"
        }
    ),
    session: Session = Depends(get_session)
):
    """
    Execute kubectl command with safety checks
    
    Required fields:
    - incident_id: ID of the related incident
    - command: kubectl command (without 'kubectl' prefix)
    - confirm_execution: Must be true to execute
    
    Optional fields:
    - executor: Executor to use (default: kubectl)
    - step_id: Step ID from recommendations
    - expected_outcome: What should happen
    """
    try:
        incident_id = command_data.get("incident_id")
        command = command_data.get("command", "")
        confirm_execution = command_data.get("confirm_execution", False)
        executor = command_data.get("executor", "kubectl")
        step_id = command_data.get("step_id")
        expected_outcome = command_data.get("expected_outcome", "Command execution")
        
        # Validation
        if not incident_id:
            raise HTTPException(status_code=400, detail="incident_id is required")
        
        if not command:
            raise HTTPException(status_code=400, detail="command is required")
        
        if not confirm_execution:
            raise HTTPException(status_code=400, detail="confirm_execution must be true")
        
        # Verify incident exists
        incident = session.exec(
            select(IncidentModel).where(IncidentModel.id == incident_id)
        ).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Check if executor is active
        executor_status = session.exec(
            select(ExecutorStatusModel).where(
                ExecutorStatusModel.executor_name == executor,
                ExecutorStatusModel.status == 0
            )
        ).first()
        
        if not executor_status:
            raise HTTPException(
                status_code=400, 
                detail=f"Executor '{executor}' is not active"
            )
        
        # Execute command using existing function
        from app.executor_client import execute_single_remediation_command
        
        execution_data = {
            "command": command,
            "is_executable": True,
            "executor": executor,
            "incident_id": incident_id,
            "step_id": step_id,
            "expected_outcome": expected_outcome
        }
        
        start_time = datetime.datetime.utcnow()
        execution_result = execute_single_remediation_command(execution_data)
        end_time = datetime.datetime.utcnow()
        
        # Save execution history
        try:
            from app.models import CommandExecutionHistoryModel
            
            history_record = CommandExecutionHistoryModel(
                incident_id=incident_id,
                command_executed=f"kubectl {command}",
                executor_used=executor,
                execution_status=execution_result.get("status", "unknown"),
                execution_output=execution_result.get("output", "")[:2000] if execution_result.get("output") else None,
                error_message=execution_result.get("error"),
                step_id=step_id,
                expected_outcome=expected_outcome,
                execution_time_ms=int((end_time - start_time).total_seconds() * 1000)
            )
            session.add(history_record)
            session.commit()
            logger.info(f"Saved command execution history for incident {incident_id}")
        except Exception as history_error:
            logger.error(f"Failed to save execution history: {str(history_error)}")
        
        return {
            "success": execution_result.get("status") == "success",
            "incident_id": incident_id,
            "command": f"kubectl {command}",
            "executor": executor,
            "execution_result": execution_result,
            "execution_time_ms": int((end_time - start_time).total_seconds() * 1000),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")

# api_16 - Get command execution history for incident
@app.get("/incidents/{incident_id}/execution-history",
    summary="Get command execution history for incident",
    description="Get history of all commands executed for a specific incident",
    tags=["Command Execution"])
async def get_incident_execution_history(
    incident_id: str,
    session: Session = Depends(get_session)
):
    """
    Get command execution history for a specific incident
    """
    try:
        # Verify incident exists
        incident = session.exec(
            select(IncidentModel).where(IncidentModel.id == incident_id)
        ).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Get execution history
        from app.models import CommandExecutionHistoryModel
        
        history = session.exec(
            select(CommandExecutionHistoryModel)
            .where(CommandExecutionHistoryModel.incident_id == incident_id)
            .order_by(CommandExecutionHistoryModel.executed_at.desc())
        ).all()
        
        return {
            "incident_id": incident_id,
            "execution_history": [
                {
                    "id": record.id,
                    "command": record.command_executed,
                    "executor": record.executor_used,
                    "status": record.execution_status,
                    "executed_at": record.executed_at,
                    "execution_time_ms": record.execution_time_ms,
                    "step_id": record.step_id,
                    "expected_outcome": record.expected_outcome,
                    "output": record.execution_output[:500] + "..." if record.execution_output and len(record.execution_output) > 500 else record.execution_output,
                    "error": record.error_message if record.execution_status == "failed" else None
                }
                for record in history
            ],
            "total_executions": len(history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting execution history: {str(e)}")