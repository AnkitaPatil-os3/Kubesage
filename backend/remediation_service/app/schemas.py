from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models import ExecutorType, ExecutorStatus, IncidentType






class WebhookUserResponse(BaseModel):
    id: int
    user_id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Executor Schemas
class ExecutorBase(BaseModel):
    name: ExecutorType
    status: ExecutorStatus = ExecutorStatus.INACTIVE
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

class ExecutorCreate(ExecutorBase):
    pass

class ExecutorUpdate(BaseModel):
    status: Optional[ExecutorStatus] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

class ExecutorResponse(ExecutorBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Incident Schemas
class IncidentWebhookPayload(BaseModel):
    """Schema for incoming incident webhook data"""
    metadata: Dict[str, Any]
    reason: str
    message: str
    source: Optional[Dict[str, Any]] = None
    firstTimestamp: Optional[str] = None
    lastTimestamp: Optional[str] = None
    count: Optional[int] = 1
    type: str
    eventTime: Optional[str] = None
    reportingComponent: Optional[str] = None
    reportingInstance: Optional[str] = None
    clusterName: Optional[str] = None
    involvedObject: Dict[str, Any]

class IncidentCreate(BaseModel):
    incident_id: str
    type: IncidentType
    reason: str
    message: str
    metadata_namespace: Optional[str] = None
    metadata_creation_timestamp: Optional[datetime] = None
    involved_object_kind: Optional[str] = None
    involved_object_name: Optional[str] = None
    source_component: Optional[str] = None
    source_host: Optional[str] = None
    reporting_component: Optional[str] = None
    count: Optional[int] = 1
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    involved_object_labels: Optional[Dict[str, Any]] = None
    involved_object_annotations: Optional[Dict[str, Any]] = None

class IncidentResponse(BaseModel):
    id: int
    incident_id: str
    type: IncidentType
    reason: str
    message: str
    metadata_namespace: Optional[str] = None
    metadata_creation_timestamp: Optional[datetime] = None
    involved_object_kind: Optional[str] = None
    involved_object_name: Optional[str] = None
    source_component: Optional[str] = None
    source_host: Optional[str] = None
    reporting_component: Optional[str] = None
    count: Optional[int] = None
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    involved_object_labels: Optional[Dict[str, Any]] = None
    involved_object_annotations: Optional[Dict[str, Any]] = None
    is_resolved: bool
    resolution_attempts: int
    last_resolution_attempt: Optional[datetime] = None
    executor_id: Optional[int] = None
    webhook_user_id: Optional[int] = None  # Keep this field
    webhook_user: Optional[WebhookUserResponse] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Remediation Schemas
class RemediationRequest(BaseModel):
    incident_id: int
    executor_type: Optional[ExecutorType] = None  # If not provided, uses active executor

class RemediationSolution(BaseModel):
    solution_summary: str
    detailed_solution: str
    remediation_steps: List[Dict[str, Any]]
    confidence_score: float
    estimated_time_mins: int
    additional_notes: str
    executor_type: ExecutorType
    commands: List[str] = []

class RemediationResponse(BaseModel):
    incident_id: int
    solution: RemediationSolution
    execution_status: str
    execution_results: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime

# List Schemas
class IncidentList(BaseModel):
    incidents: List[IncidentResponse]
    total: int
    page: int
    per_page: int

class ExecutorList(BaseModel):
    executors: List[ExecutorResponse]