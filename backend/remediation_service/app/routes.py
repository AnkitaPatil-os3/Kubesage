from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks , Header , Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, select, update
from typing import Any,List, Dict, Optional
import json
import uuid
from datetime import datetime, timezone
from app.database import get_session
from app.models import Incident, Executor, ExecutorType, ExecutorStatus, IncidentType
from app.schemas import (
    IncidentWebhookPayload, IncidentCreate, IncidentResponse, IncidentList,
    ExecutorCreate, ExecutorUpdate, ExecutorResponse, ExecutorList,
    RemediationRequest, RemediationResponse, RemediationSolution
)
from app.config import settings
from app.logger import logger
from app.queue import publish_message
from app.llm_service import RemediationLLMService
from app.api_auth import authenticate_api_key_from_body
from app.models import WebhookUser 
# Replace the existing import section with:
from app.executors import KubectlExecutor, ArgoCDExecutor, CrossplaneExecutor
from app.api_auth import authenticate_api_key_from_header
import os

remediation_router = APIRouter()

# Executor instances cache
_executor_cache = {}

def get_executor_instance(executor_type: ExecutorType, config: Dict = None):
    """Get executor instance with caching"""
    cache_key = f"{executor_type.value}_{hash(str(config))}"
    
    if cache_key not in _executor_cache:
        if executor_type == ExecutorType.KUBECTL:
            _executor_cache[cache_key] = KubectlExecutor(config)
        elif executor_type == ExecutorType.ARGOCD:
            _executor_cache[cache_key] = ArgoCDExecutor(config)
        elif executor_type == ExecutorType.CROSSPLANE:
            _executor_cache[cache_key] = CrossplaneExecutor(config)
        else:
            raise ValueError(f"Unknown executor type: {executor_type}")
    
    return _executor_cache[cache_key]

def _clean_dict_for_llm(data: Dict) -> Dict:
    """Clean dictionary for LLM processing"""
    if not data:
        return {}
    
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str) and len(value) < 1000:  # Limit string length
            cleaned[key] = value
        elif isinstance(value, (int, float, bool)):
            cleaned[key] = value
        elif isinstance(value, dict) and len(str(value)) < 1000:
            cleaned[key] = value
    
    return cleaned

def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse timestamp string to datetime object"""
    if not timestamp_str:
        return None
    
    try:
        # Handle different timestamp formats
        if timestamp_str.endswith('Z'):
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            return datetime.fromisoformat(timestamp_str)
    except Exception as e:
        logger.error(f"Error parsing timestamp {timestamp_str}: {str(e)}")
        return None


# Webhook endpoint for receiving incidents

@remediation_router.post("/webhook/incidents", 
                        summary="Receive Incident Webhook",
                        description="Webhook endpoint to receive Kubernetes incidents")
async def receive_incident_webhook(
    payload: IncidentWebhookPayload,
    request: Request,  # ADD THIS to access headers
    session: Session = Depends(get_session),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_cluster_name: Optional[str] = Header(None, alias="X-Cluster-Name"),  # ADD cluster header
    x_cluster_server: Optional[str] = Header(None, alias="X-Cluster-Server"),  # ADD server header
    x_cluster_context: Optional[str] = Header(None, alias="X-Cluster-Context"),  # ADD context header
    x_namespace: Optional[str] = Header(None, alias="X-Namespace"),  # ADD namespace header
    user_agent: Optional[str] = Header(None, alias="User-Agent"),  # ADD user agent
    content_type: Optional[str] = Header(None, alias="Content-Type"),  # ADD content type
):
    """
    Webhook endpoint to receive Kubernetes incidents and store important data in database.
    Requires valid API key in X-API-Key header.
    """
    print("=" * 80)
    print("WEBHOOK INCIDENT RECEIVED")
    print("=" * 80)
    
    # Print all headers
    print("📋 ALL REQUEST HEADERS:")
    for header_name, header_value in request.headers.items():
        print(f"   {header_name}: {header_value}")
    
    print("\n🔑 AUTHENTICATION INFO:")
    print(f"   X-API-Key: {x_api_key}")
    
    print("\n🌐 CLUSTER INFORMATION:")
    print(f"   X-Cluster-Name: {x_cluster_name}")
    print(f"   X-Cluster-Server: {x_cluster_server}")
    print(f"   X-Cluster-Context: {x_cluster_context}")
    print(f"   X-Namespace: {x_namespace}")
    
    print("\n📡 REQUEST METADATA:")
    print(f"   User-Agent: {user_agent}")
    print(f"   Content-Type: {content_type}")
    print(f"   Request Method: {request.method}")
    print(f"   Request URL: {request.url}")
    print(f"   Client Host: {request.client.host if request.client else 'Unknown'}")
    
    print("\n📦 PAYLOAD SUMMARY:")
    print(f"   Incident Type: {payload.type}")
    print(f"   Reason: {payload.reason}")
    print(f"   Message: {payload.message[:100]}..." if len(payload.message) > 100 else f"   Message: {payload.message}")
    print(f"   Namespace: {payload.metadata.get('namespace', 'N/A')}")
    print(f"   Object Kind: {payload.involvedObject.get('kind', 'N/A')}")
    print(f"   Object Name: {payload.involvedObject.get('name', 'N/A')}")
    print(f"   Count: {payload.count}")
    
    print("\n🔍 DETAILED PAYLOAD:")
    print("---------------------- Incoming payload ------------------")
    print(payload)
    print("----------------------------- x_api_key -----------------:")
    print(x_api_key)
    print("----------------------------- session -----------------:")
    print(session)
    
    # Print cluster-specific headers if present
    if any([x_cluster_name, x_cluster_server, x_cluster_context, x_namespace]):
        print("\n🎯 EXTRACTED CLUSTER HEADERS:")
        if x_cluster_name:
            print(f"   Cluster Name: {x_cluster_name}")
        if x_cluster_server:
            print(f"   Cluster Server: {x_cluster_server}")
        if x_cluster_context:
            print(f"   Cluster Context: {x_cluster_context}")
        if x_namespace:
            print(f"   Target Namespace: {x_namespace}")
    else:
        print("\n⚠️  NO CLUSTER HEADERS FOUND")
        print("   Expected headers: X-Cluster-Name, X-Cluster-Server, X-Cluster-Context, X-Namespace")
    
    print("=" * 80)

    try:
        # Authenticate using API key from request header
        webhook_user = await authenticate_api_key_from_header(x_api_key, session)
        
        logger.info(f"Webhook called by user: {webhook_user.username} (ID: {webhook_user.user_id})")
        print(f"\n✅ AUTHENTICATED USER: {webhook_user.username} (ID: {webhook_user.user_id})")
        
        # Generate unique incident ID if not provided
        incident_id = payload.metadata.get("uid", str(uuid.uuid4()))
        
        # Check if incident already exists
        existing_incident = session.exec(
            select(Incident).where(
                Incident.incident_id == incident_id
            )
        ).first()
        
        if existing_incident:
            # Update existing incident count and timestamps
            existing_incident.count = payload.count or existing_incident.count
            existing_incident.last_timestamp = parse_timestamp(payload.lastTimestamp) or existing_incident.last_timestamp
            existing_incident.updated_at = datetime.utcnow()
            session.add(existing_incident)
            session.commit()
            
            logger.info(f"Updated existing incident: {incident_id}")
            print(f"📝 UPDATED EXISTING INCIDENT: {incident_id}")
            return JSONResponse(content={"message": "Incident updated", "incident_id": incident_id}, status_code=200)
        
        # Extract important incident data
        incident_data = IncidentCreate(
            incident_id=incident_id,
            type=IncidentType(payload.type) if payload.type in [t.value for t in IncidentType] else IncidentType.NORMAL,
            reason=payload.reason,
            message=payload.message,
            metadata_namespace=payload.metadata.get("namespace"),
            metadata_creation_timestamp=parse_timestamp(payload.metadata.get("creationTimestamp")),
            involved_object_kind=payload.involvedObject.get("kind"),
            involved_object_name=payload.involvedObject.get("name"),
            source_component=payload.source.get("component") if payload.source else None,
            source_host=payload.source.get("host") if payload.source else None,
            reporting_component=payload.reportingComponent,
            count=payload.count or 1,
            first_timestamp=parse_timestamp(payload.firstTimestamp),
            last_timestamp=parse_timestamp(payload.lastTimestamp),
            involved_object_labels=payload.involvedObject.get("labels", {}),
            involved_object_annotations=payload.involvedObject.get("annotations", {})
        )
        
        # Create incident record - EXCLUDE user_id from dict()
        incident_dict = incident_data.dict()
        # Remove any user_id if it exists
        incident_dict.pop('user_id', None)
        
        incident = Incident(**incident_dict)
        
        # Link incident to webhook user
        incident.webhook_user_id = webhook_user.id
        # Save cluster name from header
        incident.cluster_name = x_cluster_name
        
        # Convert labels and annotations to JSON strings BEFORE saving
        if incident_data.involved_object_labels:
            incident.involved_object_labels = json.dumps(_clean_dict_for_llm(incident_data.involved_object_labels))
        else:
            incident.involved_object_labels = None
            
        if incident_data.involved_object_annotations:
            incident.involved_object_annotations = json.dumps(_clean_dict_for_llm(incident_data.involved_object_annotations))
        else:
            incident.involved_object_annotations = None
        
        session.add(incident)
        session.commit()
        session.refresh(incident)
        
        logger.info(f"Created new incident: {incident_id}")
        print(f"✨ CREATED NEW INCIDENT: {incident_id} (Internal ID: {incident.id})")
        print("=" * 80)
        
        return JSONResponse(content={
            "message": "Incident received and stored",
            "incident_id": incident_id,
            "internal_id": incident.id
        }, status_code=201)
        
    except Exception as e:
        logger.error(f"Error processing incident webhook: {str(e)}")
        print(f"❌ ERROR PROCESSING WEBHOOK: {str(e)}")
        print("=" * 80)
        raise HTTPException(status_code=500, detail=f"Error processing incident: {str(e)}")


# Executor management endpoints
@remediation_router.get("/executors", response_model=ExecutorList,
                       summary="List Executors",
                       description="Get list of all executors and their status")
async def list_executors(
    session: Session = Depends(get_session),
):
    """List all executors and their status"""
    executors = session.exec(select(Executor)).all()
    
    # Convert executors to response format with proper config parsing
    executor_responses = []
    for executor in executors:
        # Parse config if it exists
        config = None
        if executor.config:
            try:
                config = json.loads(executor.config)
            except (json.JSONDecodeError, TypeError):
                config = None
        
        executor_dict = {
            "id": executor.id,
            "name": executor.name,
            "status": executor.status,
            "description": executor.description,
            "config": config,  # This will be None or a proper dict
            "created_at": executor.created_at,
            "updated_at": executor.updated_at
        }
        executor_responses.append(executor_dict)
    
    return ExecutorList(executors=executor_responses)

@remediation_router.post("/executors", response_model=ExecutorResponse,
                        summary="Create Executor",
                        description="Create a new executor")
async def create_executor(
    executor_data: ExecutorCreate,
    session: Session = Depends(get_session),
):
    """Create a new executor"""
    # Check if executor already exists
    existing = session.exec(
        select(Executor).where(Executor.name == executor_data.name)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Executor {executor_data.name.value} already exists")
    
    executor = Executor(
        name=executor_data.name,
        status=executor_data.status,
        description=executor_data.description,
        config=json.dumps(executor_data.config) if executor_data.config else None
    )
    
    session.add(executor)
    session.commit()
    session.refresh(executor)
    
    logger.info(f"Created executor: {executor.name.value}")
    return executor

@remediation_router.put("/executors/{executor_id}", response_model=ExecutorResponse,
                       summary="Update Executor",
                       description="Update executor status and configuration")
async def update_executor(
    executor_id: int,
    executor_data: ExecutorUpdate,
    session: Session = Depends(get_session),
):
    """Update executor status and configuration"""
    executor = session.get(Executor, executor_id)
    if not executor:
        raise HTTPException(status_code=404, detail="Executor not found")
    
    # Update fields
    if executor_data.status is not None:
        executor.status = executor_data.status
    if executor_data.description is not None:
        executor.description = executor_data.description
    if executor_data.config is not None:
        executor.config = json.dumps(executor_data.config)
    
    executor.updated_at = datetime.utcnow()
    
    session.add(executor)
    session.commit()
    session.refresh(executor)
    
    logger.info(f"Updated executor {executor.name.value}: status={executor.status.value}")
    return executor

@remediation_router.post("/executors/{executor_id}/activate",
                        summary="Activate Executor",
                        description="Activate an executor and deactivate others")
async def activate_executor(
    executor_id: int,
    session: Session = Depends(get_session),
):
    """Activate an executor and deactivate all others"""
    executor = session.get(Executor, executor_id)
    if not executor:
        raise HTTPException(status_code=404, detail="Executor not found")
    
    # Deactivate all executors
    session.exec(
        update(Executor).values(status=ExecutorStatus.INACTIVE, updated_at=datetime.utcnow())
    )
    
    # Activate the selected executor
    executor.status = ExecutorStatus.ACTIVE
    executor.updated_at = datetime.utcnow()
    session.add(executor)
    session.commit()
    
    logger.info(f"Activated executor: {executor.name.value}")
    return JSONResponse(content={"message": f"Executor {executor.name.value} activated"}, status_code=200)

from .auth import get_current_user

# Incident management endpoints
@remediation_router.get("/incidents", response_model=IncidentList,
                       summary="List Incidents",
                       description="Get list of incidents with filtering options")
async def list_incidents(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    incident_type: Optional[IncidentType] = Query(None),
    namespace: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """List incidents with filtering and pagination for authenticated user"""
    
    # Get user ID from current_user
    user_id = current_user["id"]
    
    # Base query - join with webhook_users to filter by current user
    query = select(Incident).join(WebhookUser).where(WebhookUser.user_id == user_id)
    
    # Apply additional filters
    if incident_type:
        query = query.where(Incident.type == incident_type)
    if namespace:
        query = query.where(Incident.metadata_namespace == namespace)
    if resolved is not None:
        query = query.where(Incident.is_resolved == resolved)
    
    # Count query with same filters
    total_query = select(Incident).join(WebhookUser).where(WebhookUser.user_id == user_id)
    if incident_type:
        total_query = total_query.where(Incident.type == incident_type)
    if namespace:
        total_query = total_query.where(Incident.metadata_namespace == namespace)
    if resolved is not None:
        total_query = total_query.where(Incident.is_resolved == resolved)
    
    total = len(session.exec(total_query).all())
    
    # Apply pagination and ordering
    query = query.order_by(Incident.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    incidents = session.exec(query).all()
    
    # Convert incidents to response format with proper JSON parsing
    incident_responses = []
    for incident in incidents:
        # Parse labels and annotations if they exist
        labels = None
        if incident.involved_object_labels:
            try:
                labels = json.loads(incident.involved_object_labels)
            except (json.JSONDecodeError, TypeError):
                labels = None
        
        annotations = None
        if incident.involved_object_annotations:
            try:
                annotations = json.loads(incident.involved_object_annotations)
            except (json.JSONDecodeError, TypeError):
                annotations = None
        
        incident_dict = {
            "id": incident.id,
            "incident_id": incident.incident_id,
            "type": incident.type,
            "reason": incident.reason,
            "message": incident.message,
            "metadata_namespace": incident.metadata_namespace,
            "metadata_creation_timestamp": incident.metadata_creation_timestamp,
            "involved_object_kind": incident.involved_object_kind,
            "involved_object_name": incident.involved_object_name,
            "source_component": incident.source_component,
            "source_host": incident.source_host,
            "reporting_component": incident.reporting_component,
            "count": incident.count,
            "first_timestamp": incident.first_timestamp,
            "last_timestamp": incident.last_timestamp,
            "involved_object_labels": labels,
            "involved_object_annotations": annotations,
            "is_resolved": incident.is_resolved,
            "resolution_attempts": incident.resolution_attempts,
            "last_resolution_attempt": incident.last_resolution_attempt,
            "webhook_user_id": incident.webhook_user_id,
            "executor_id": incident.executor_id,
            "created_at": incident.created_at,
            "updated_at": incident.updated_at
        }
        incident_responses.append(incident_dict)
    
    return IncidentList(
        incidents=incident_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@remediation_router.get("/incidents/{id}", response_model=IncidentResponse,
                       summary="Get Incident",
                       description="Get detailed information about a specific incident")
async def get_incident(
    id: int,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)):

    """Get detailed information about a specific incident for authenticated user"""

    # CHANGED: Get user_id from current_user
    user_id = current_user["id"]
    
    # CHANGED: Get incident with webhook_user filter based on current_user
    incident = session.exec(
        select(Incident).join(WebhookUser).where(
            Incident.id == id,
            WebhookUser.user_id == user_id
        )
    ).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Parse labels and annotations if they exist
    labels = None
    if incident.involved_object_labels:
        try:
            labels = json.loads(incident.involved_object_labels)
        except (json.JSONDecodeError, TypeError):
            labels = None
    
    annotations = None
    if incident.involved_object_annotations:
        try:
            annotations = json.loads(incident.involved_object_annotations)
        except (json.JSONDecodeError, TypeError):
            annotations = None
    
    # Create response dict with parsed JSON
    incident_dict = {
        "id": incident.id,
        "incident_id": incident.incident_id,
        "type": incident.type,
        "reason": incident.reason,
        "message": incident.message,
        "metadata_namespace": incident.metadata_namespace,
        "metadata_creation_timestamp": incident.metadata_creation_timestamp,
        "involved_object_kind": incident.involved_object_kind,
        "involved_object_name": incident.involved_object_name,
        "source_component": incident.source_component,
        "source_host": incident.source_host,
        "reporting_component": incident.reporting_component,
        "count": incident.count,
        "first_timestamp": incident.first_timestamp,
        "last_timestamp": incident.last_timestamp,
        "involved_object_labels": labels,  # Parsed JSON or None
        "involved_object_annotations": annotations,  # Parsed JSON or None
        "is_resolved": incident.is_resolved,
        "resolution_attempts": incident.resolution_attempts,
        "last_resolution_attempt": incident.last_resolution_attempt,
        "webhook_user_id": incident.webhook_user_id,
        "executor_id": incident.executor_id,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at
    }
    
    return IncidentResponse(**incident_dict)


 
import os
import json
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
 
from fastapi import HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
 
from app.executors.kubectl import KubectlExecutor
from app.logger import logger
# ... your other imports (Incident, WebhookUser, Executor, ExecutorType, ExecutorStatus, remediation_router, get_session, get_current_user, etc.)
 
KUBECONFIG_SERVICE_URL = os.getenv("KUBECONFIG_SERVICE_URL", "http://kubeconfig-service:8000")
 
 
# -------------------------
# ADD THIS HELPER IN routes.py
# -------------------------





async def get_cluster_info(incident_id: str, user_token: str) -> Optional[Dict[str, Any]]:
    """Get cluster information using incident ID."""
    try:
        # Get database session
        session = next(get_session())
        
        # Get incident from database
        incident = session.get(Incident, incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        if not incident.cluster_name:
            raise HTTPException(status_code=400, detail="Incident is not associated with any cluster")


        cluster_name = incident.cluster_name
        logger.info(f"Fetching cluster info for cluster: {cluster_name} from incident: {incident_id}")

        # Get cluster credentials from kubeconfig service
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            url = f"{KUBECONFIG_SERVICE_URL}/kubeconfig/cluster/{cluster_name}/credentials"
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {user_token}"}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("cluster"):
                    return data["cluster"]

            logger.error(f"Failed to get cluster info for {cluster_name}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error getting cluster info: {e}")
        return None



@remediation_router.post("/incidents/{id}/execute",
                        summary="Execute Remediation Steps",
                        description="Execute specific remediation steps for an incident")
async def execute_remediation_steps(
    id: int,
    request: Dict[str, Any],
    executor_type: Optional[ExecutorType] = Query(None),
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)):
 
    """Execute specific remediation steps for an incident"""
 
    user_id = current_user["id"]
    print("------------------------ user_id", user_id)
 
    # First get the incident to fetch cluster_name
    incident = session.exec(
        select(Incident).join(WebhookUser).where(
            Incident.id == id,
            Incident.webhook_user.has(WebhookUser.user_id == user_id)
        )
    ).first()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if not incident.cluster_name:
        raise HTTPException(status_code=400, detail="Incident is not associated with any cluster")

    cluster_name = incident.cluster_name
    print("------------------------ cluster_name from incident:", cluster_name)

    # Now fetch cluster credentials using the incident ID
    kube_cluster = await get_cluster_info(
        incident_id=str(incident.id),
        user_token=current_user.get("token", "")
    )
    
    print("------------------------ kube_cluster", kube_cluster)
    if not kube_cluster:
        raise HTTPException(status_code=404, detail=f"Failed to resolve cluster credentials for cluster '{cluster_name}'")
 
 
    server_url = kube_cluster.get("server_url")
    token = kube_cluster.get("token") or kube_cluster.get("bearer_token")
    use_secure_tls = kube_cluster.get("use_secure_tls", True)
    namespace = kube_cluster.get("namespace", "default")
 
    if not server_url or not token:
        raise HTTPException(status_code=400, detail="Cluster credentials incomplete (server_url/token missing)")
 
    # Filter incident with user
    incident = session.exec(
        select(Incident).join(WebhookUser).where(
            Incident.id == id,
            Incident.webhook_user.has(WebhookUser.user_id == user_id)
        )
    ).first()
 
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
 
    # Extract steps
    steps = request.get("remediation_steps", [])
    if not steps:
        raise HTTPException(status_code=400, detail="No remediation steps provided")
 
    commands = []
    for step in steps:
        command = step.get("command", "")
        if command:
            commands.append({
                "step_id": step.get("step_id"),
                "command": command,
                "description": step.get("description", ""),
                "action_type": step.get("action_type", ""),
                "cluster_name": step.get("cluster_name", cluster_name)
            })
 
    if not commands:
        raise HTTPException(status_code=400, detail="No commands found in remediation steps")
 
    # Prepare kubectl executor with server_url/token
    kubectl_executor = KubectlExecutor(config={
        "server_url": server_url,
        "token": token,
        "namespace": namespace,
        "use_secure_tls": use_secure_tls
    })
 
    try:
        execution_results = []
 
        for cmd_info in commands:
            try:
                command = cmd_info["command"]
 
                # Use kubectl executor when command starts with kubectl
                if command.strip().startswith("kubectl"):
                    result = await kubectl_executor.execute_command(command)
                    execution_results.append({
                        "step_id": cmd_info["step_id"],
                        "command": cmd_info["command"],
                        "description": cmd_info["description"],
                        "success": result.get("success", False),
                        "output": result.get("stdout", ""),
                        "error": result.get("stderr") or result.get("error"),
                        "return_code": result.get("return_code", 0)
                    })
                    continue
 
                # Non-kubectl commands (unchanged)
                import subprocess
 
                # jq safety wrapping kept as-is
                if 'jq' in command:
                    if '|' in command and 'jq' in command.split('|')[-1]:
                        parts = command.rsplit('|', 1)
                        if len(parts) == 2:
                            base_cmd = parts[0].strip()
                            jq_part = parts[1].strip()
                            safe_jq = f"({jq_part} 2>/dev/null || echo '{{\"error\": \"jq parsing failed\"}}')"
                            command = f"{base_cmd} | {safe_jq}"
                    command = command.replace('jq .', 'jq . 2>/dev/null || echo "{\\"error\\": \\"invalid json\\"}"')
                    command = command.replace("jq '", "jq -r '")
 
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=dict(os.environ, LC_ALL='C', LANG='C')
                )
 
                output = result.stdout
                error = result.stderr
 
                if 'jq: error' in error or 'jq: parse error' in error:
                    if '|' in cmd_info["command"] and 'jq' in cmd_info["command"]:
                        raw_command = cmd_info["command"].split('|')[0].strip()
                        try:
                            raw_result = subprocess.run(
                                raw_command,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=60,
                                env=dict(os.environ, LC_ALL='C')
                            )
                            if raw_result.returncode == 0:
                                output = f"Raw data (jq parsing failed):\n{raw_result.stdout}"
                                error = f"jq parsing failed, showing raw data instead. Original error: {error}"
                        except:
                            pass
 
                execution_results.append({
                    "step_id": cmd_info["step_id"],
                    "command": cmd_info["command"],
                    "description": cmd_info["description"],
                    "success": result.returncode == 0 or (result.returncode != 0 and 'jq: error' in error and output),
                    "output": output,
                    "error": error if result.returncode != 0 and 'jq: error' not in error else None,
                    "return_code": result.returncode
                })
 
            except subprocess.TimeoutExpired:
                execution_results.append({
                    "step_id": cmd_info["step_id"],
                    "command": cmd_info["command"],
                    "description": cmd_info["description"],
                    "success": False,
                    "output": "",
                    "error": "Command timed out after 300 seconds",
                    "return_code": -1
                })
            except Exception as e:
                execution_results.append({
                    "step_id": cmd_info["step_id"],
                    "command": cmd_info["command"],
                    "description": cmd_info["description"],
                    "success": False,
                    "output": "",
                    "error": str(e),
                    "return_code": -1
                })
 
        incident.resolution_attempts += 1
        incident.last_resolution_attempt = datetime.utcnow()
        incident.updated_at = datetime.utcnow()
 
        successful_steps = sum(1 for result in execution_results if result.get("success", False))
        if successful_steps == len(commands):
            incident.is_resolved = True
 
        session.add(incident)
        session.commit()
 
        return JSONResponse(content={
            "message": "Remediation steps executed",
            "results": execution_results,
            "successful_steps": successful_steps,
            "total_steps": len(commands)
        }, status_code=200)
 
    except Exception as e:
        logger.error(f"Error executing remediation steps: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error executing remediation steps: {str(e)}")
 
 
 
 
 
 
 

# Remediation endpoints

@remediation_router.post("/incidents/{incident_id}/remediate",
                        summary="Generate Remediation Solution",
                        description="Generate and optionally execute remediation solution for an incident")
async def remediate_incident(
    incident_id: int,
    request: RemediationRequest,
    background_tasks: BackgroundTasks,
    execute: bool = Query(False, description="Whether to execute the remediation automatically"),
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user) 
):
    """Generate remediation solution for ANY type of incident using LLM."""
    
    if not settings.LLM_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="LLM functionality is disabled. Please enable it in settings to use AI remediation."
        )
    
    user_id = current_user["id"]
    
    incident = session.exec(
        select(Incident).join(WebhookUser).where(
            Incident.id == incident_id,
            WebhookUser.user_id == user_id
        )
    ).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Determine executor to use
    executor_type = request.executor_type
    if not executor_type:
        active_executor = session.exec(
            select(Executor).where(Executor.status == ExecutorStatus.ACTIVE)
        ).first()
        
        if not active_executor:
            raise HTTPException(status_code=400, detail="No active executor found. Please activate an executor first.")
        
        executor_type = active_executor.name
        executor_config = json.loads(active_executor.config) if active_executor.config else {}
    else:
        executor = session.exec(
            select(Executor).where(Executor.name == executor_type)
        ).first()
        
        if not executor:
            raise HTTPException(status_code=404, detail=f"Executor {executor_type.value} not found")
        
        if executor.status != ExecutorStatus.ACTIVE:
            raise HTTPException(status_code=400, detail=f"Executor {executor_type.value} is not active")
        
        executor_config = json.loads(executor.config) if executor.config else {}
    
    try:
        # Initialize LLM service
        llm_service = RemediationLLMService()
        
        logger.info(f"Generating remediation solution for incident {incident_id} using {executor_type.value}")
        
        cluster_context = {
            "executor_type": executor_type.value,
            "namespace": incident.metadata_namespace,
            "cluster_name": "current-cluster",
            "incident_count": incident.count,
            "resolution_attempts": incident.resolution_attempts
        }
        
        # Add await here since the method is now async
        solution_data = await llm_service.generate_remediation_solution(
            incident=incident,
            executor_type=executor_type,
            cluster_context=cluster_context
        )
        
        solution = RemediationSolution(**solution_data)
        
        # Update incident tracking
        incident.resolution_attempts += 1
        incident.last_resolution_attempt = datetime.utcnow()
        incident.executor_id = session.exec(
            select(Executor.id).where(Executor.name == executor_type)
        ).first()
        incident.updated_at = datetime.utcnow()
        
        session.add(incident)
        session.commit()
        
        response = RemediationResponse(
            incident_id=incident_id,
            solution=solution,
            execution_status="generated",
            timestamp=datetime.utcnow()
        )
        
        # Execute remediation if requested
        if execute:
            background_tasks.add_task(
                execute_remediation_background,
                incident_id,
                solution,
                executor_type,
                executor_config
            )
            response.execution_status = "executing"
        
        logger.info(f"Remediation solution generated - Incident: {incident_id}, Executor: {executor_type.value}, Confidence: {solution.confidence_score}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating remediation solution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating remediation solution: {str(e)}")




@remediation_router.post("/incidents/{id}/execute",
                        summary="Execute Remediation Steps",
                        description="Execute specific remediation steps for an incident")
async def execute_remediation_steps(
    id: int,
    request: Dict[str, Any],
    executor_type: Optional[ExecutorType] = Query(None),
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)):

    """Execute specific remediation steps for an incident"""

     # CHANGED: Get user_id from current_user
    user_id = current_user["id"]
    
    # CHANGED: Get incident with webhook_user filter based on current_user
    incident = session.exec(
        select(Incident).join(WebhookUser).where(
            Incident.id == id,
            WebhookUser.user_id == user_id
        )
    ).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Extract steps from request
    steps = request.get("remediation_steps", [])
    if not steps:
        raise HTTPException(status_code=400, detail="No remediation steps provided")
    
    # Process all types of commands (not just kubectl)
    commands = []
    for step in steps:
        command = step.get("command", "")
        if command:  # Accept any command, not just kubectl
            commands.append({
                "step_id": step.get("step_id"),
                "command": command,
                "description": step.get("description", ""),
                "action_type": step.get("action_type", "")
            })
    
    if not commands:
        raise HTTPException(status_code=400, detail="No commands found in remediation steps")
    
    try:
        # Execute all types of commands
        execution_results = []
        
        for cmd_info in commands:
            try:
                # Execute command using shell to support pipes, grep, jq, etc.
                import subprocess
                import shlex
                
                # Handle jq commands with proper shell escaping
                command = cmd_info["command"]
                
                # Better jq command handling with error protection
                if 'jq' in command:
                    # Wrap jq commands with error handling
                    if '|' in command and 'jq' in command.split('|')[-1]:
                        # Split the command at the last pipe to jq
                        parts = command.rsplit('|', 1)
                        if len(parts) == 2:
                            base_cmd = parts[0].strip()
                            jq_part = parts[1].strip()
                            
                            # Create safe jq command with error handling
                            safe_jq = f"({jq_part} 2>/dev/null || echo '{{\"error\": \"jq parsing failed\"}}')"
                            command = f"{base_cmd} | {safe_jq}"
                    
                    # Additional jq safety measures
                    command = command.replace('jq .', 'jq . 2>/dev/null || echo "{\\"error\\": \\"invalid json\\"}"')
                    command = command.replace('jq \'', 'jq -r \'')  # Use raw output when possible
                
                # Execute with better error handling
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=dict(os.environ, LC_ALL='C', LANG='C')  # Set proper locale
                )
                
                # Check if jq failed and provide meaningful output
                output = result.stdout
                error = result.stderr
                
                # If jq failed, try to provide the raw data
                if 'jq: error' in error or 'jq: parse error' in error:
                    # Try to get the raw output without jq
                    if '|' in cmd_info["command"] and 'jq' in cmd_info["command"]:
                        raw_command = cmd_info["command"].split('|')[0].strip()
                        try:
                            raw_result = subprocess.run(
                                raw_command,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=60,
                                env=dict(os.environ, LC_ALL='C')
                            )
                            if raw_result.returncode == 0:
                                output = f"Raw data (jq parsing failed):\n{raw_result.stdout}"
                                error = f"jq parsing failed, showing raw data instead. Original error: {error}"
                        except:
                            pass
                
                execution_results.append({
                    "step_id": cmd_info["step_id"],
                    "command": cmd_info["command"],
                    "description": cmd_info["description"],
                    "success": result.returncode == 0 or (result.returncode != 0 and 'jq: error' in error and output),
                    "output": output,
                    "error": error if result.returncode != 0 and 'jq: error' not in error else None,
                    "return_code": result.returncode
                })
                
            except subprocess.TimeoutExpired:
                execution_results.append({
                    "step_id": cmd_info["step_id"],
                    "command": cmd_info["command"],
                    "description": cmd_info["description"],
                    "success": False,
                    "output": "",
                    "error": "Command timed out after 300 seconds",
                    "return_code": -1
                })
            except Exception as e:
                execution_results.append({
                    "step_id": cmd_info["step_id"],
                    "command": cmd_info["command"],
                    "description": cmd_info["description"],
                    "success": False,
                    "output": "",
                    "error": str(e),
                    "return_code": -1
                })
        
        # Update incident
        incident.resolution_attempts += 1
        incident.last_resolution_attempt = datetime.utcnow()
        incident.updated_at = datetime.utcnow()
        
        # Check if all steps were successful
        successful_steps = sum(1 for result in execution_results if result.get("success", False))
        if successful_steps == len(commands):
            incident.is_resolved = True
        
        session.add(incident)
        session.commit()
        
        return JSONResponse(content={
            "message": "Remediation steps executed",
            "results": execution_results,
            "successful_steps": successful_steps,
            "total_steps": len(commands)
        }, status_code=200)
        
    except Exception as e:
        logger.error(f"Error executing remediation steps: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error executing remediation steps: {str(e)}")



# Initialize default executors
@remediation_router.post("/initialize",
                        summary="Initialize Default Executors",
                        description="Initialize default executors (kubectl, argocd, crossplane)")
async def initialize_default_executors(
    session: Session = Depends(get_session),
):
    """Initialize default executors with kubectl as active"""
    try:
        executors_to_create = [
            {
                "name": ExecutorType.KUBECTL,
                "status": ExecutorStatus.ACTIVE,
                "description": "Kubernetes kubectl executor for direct cluster operations",
                "config": {
                    "kubeconfig_path": "~/.kube/config",
                    "namespace": "default"
                }
            },
            {
                "name": ExecutorType.ARGOCD,
                "status": ExecutorStatus.INACTIVE,
                "description": "ArgoCD executor for GitOps operations",
                "config": {
                    "server": "localhost:8080",
                    "username": "admin",
                    "insecure": True
                }
            },
            {
                "name": ExecutorType.CROSSPLANE,
                "status": ExecutorStatus.INACTIVE,
                "description": "Crossplane executor for infrastructure operations",
                "config": {
                    "kubeconfig_path": "~/.kube/config",
                    "namespace": "crossplane-system"
                }
            }
        ]
        
        created_executors = []
        updated_executors = []
        
        for executor_data in executors_to_create:
            # Check if executor already exists
            existing = session.exec(
                select(Executor).where(Executor.name == executor_data["name"])
            ).first()
            
            if not existing:
                # Create new executor
                executor = Executor(
                    name=executor_data["name"],
                    status=executor_data["status"],
                    description=executor_data["description"],
                    config=json.dumps(executor_data["config"])
                )
                session.add(executor)
                created_executors.append(executor_data["name"].value)
            else:
                # Update existing executor if needed
                existing.description = executor_data["description"]
                existing.config = json.dumps(executor_data["config"])
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                updated_executors.append(executor_data["name"].value)
        
        session.commit()
        
        message_parts = []
        if created_executors:
            message_parts.append(f"Created: {', '.join(created_executors)}")
        if updated_executors:
            message_parts.append(f"Updated: {', '.join(updated_executors)}")
        
        message = "Default executors initialized. " + "; ".join(message_parts) if message_parts else "All executors already exist and are up to date"
        
        logger.info(message)
        return JSONResponse(content={
            "message": message,
            "created": created_executors,
            "updated": updated_executors
        }, status_code=200)
            
    except Exception as e:
        logger.error(f"Error initializing default executors: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error initializing executors: {str(e)}")

# Health check endpoint
@remediation_router.get("/health",
                       summary="Health Check",
                       description="Check service health and component status")
async def health_check(session: Session = Depends(get_session)):
    """Health check endpoint"""
    try:
        # Check database connection
        session.exec(select(Executor).limit(1)).first()
        
        # Check LLM service
        llm_status = "enabled" if settings.LLM_ENABLED else "disabled"
        
        # Get active executor
        active_executor = session.exec(
            select(Executor).where(Executor.status == ExecutorStatus.ACTIVE)
        ).first()
        
        return JSONResponse(content={
            "status": "healthy",
            "database": "connected",
            "llm_service": llm_status,
            "active_executor": active_executor.name.value if active_executor else None,
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=200)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(content={
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=503)                   