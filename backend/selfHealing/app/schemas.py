from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Request and response schemas

class MessageResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    detail: str

class RawEventCreate(BaseModel):
    event_data: Dict[str, Any] = Field(..., description="The raw event payload")

class RawEventResponse(BaseModel):
    id: int
    event_data: Dict[str, Any]
    received_at: datetime

class IncidentCreate(BaseModel):
    affected_resource: Dict[str, str]
    failure_type: str
    description: str
    severity: Optional[str] = "medium"

class IncidentResponse(BaseModel):
    incident_id: str
    affected_resource: Dict[str, str]
    failure_type: str
    description: str
    severity: str
    created_at: datetime
    updated_at: datetime
    status: str

class IncidentList(BaseModel):
    incidents: List[IncidentResponse]

class ActionCreate(BaseModel):
    executor: str
    command: str
    parameters: Optional[Dict[str, Any]] = {}
    description: Optional[str] = None

class ActionResponse(BaseModel):
    action_id: str
    executor: str
    command: str
    parameters: Dict[str, Any]
    description: Optional[str]
    order: int
    created_at: datetime

class PlanCreate(BaseModel):
    incident_id: str
    actions: List[ActionCreate]

class PlanResponse(BaseModel):
    plan_id: str
    incident_id: str
    actions: List[ActionResponse]
    created_at: datetime
    status: str

class PlanList(BaseModel):
    plans: List[PlanResponse]

class ExecutionResultCreate(BaseModel):
    plan_id: Optional[str] = None
    action_id: Optional[str] = None
    status: str
    output: Optional[str] = None
    error: Optional[str] = None

class ExecutionResultResponse(BaseModel):
    execution_id: str
    plan_id: Optional[str]
    action_id: Optional[str]
    status: str
    output: Optional[str]
    error: Optional[str]
