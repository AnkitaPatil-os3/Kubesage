from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional, Any, Union
from datetime import datetime


# Simplified flexible alert schema
class FlexibleIncident(BaseModel):
    """Flexible incident schema that can handle any type of event data from different sources"""
    # Flexible data storage - can contain any structure
    raw_data: Dict[str, Any]  # Store the complete original data
    
    class Config:
        extra = "allow"  # Allow additional fields

class KubernetesEvent(BaseModel):
    """Schema for Kubernetes event data"""
    # Metadata
    metadata_name: str
    metadata_namespace: Optional[str] = None
    metadata_creation_timestamp: Optional[datetime] = None
    
    # Event Info
    type: str
    reason: str
    message: str
    count: Optional[int] = 1
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    
    # Source Info
    source_component: Optional[str] = None
    source_host: Optional[str] = None
    
    # Involved Object
    involved_object_kind: Optional[str] = None
    involved_object_name: Optional[str] = None
    involved_object_field_path: Optional[str] = None
    involved_object_labels: Dict[str, Any] = {}
    involved_object_annotations: Dict[str, Any] = {}
    involved_object_owner_references: Dict[str, Any] = {}
    
    # Reporter Info
    reporting_component: Optional[str] = None
    reporting_instance: Optional[str] = None


        
class EmailSettings(BaseModel):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    MAIL_STARTTLS: bool = True  # Updated from MAIL_TLS
    MAIL_SSL_TLS: bool = False  # Updated from MAIL_SSL
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

# Simplified alert response schema
class IncidentResponse(BaseModel):
    """Schema for incident response data"""
    id: str
    metadata_name: str
    metadata_namespace: Optional[str] = None
    metadata_creation_timestamp: Optional[datetime] = None
    type: str
    reason: str
    message: str
    count: Optional[int] = 1
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    source_component: Optional[str] = None
    source_host: Optional[str] = None
    involved_object_kind: Optional[str] = None
    involved_object_name: Optional[str] = None
    involved_object_field_path: Optional[str] = None
    involved_object_labels: Dict[str, Any] = {}
    involved_object_annotations: Dict[str, Any] = {}
    involved_object_owner_references: Dict[str, Any] = {}
    reporting_component: Optional[str] = None
    reporting_instance: Optional[str] = None

class IncidentStats(BaseModel):
    """Schema for incident statistics"""
    total_incidents: int
    warning_incidents: int
    normal_incidents: int
    recent_incidents: int

class ExecutorStatusResponse(BaseModel):
    """Schema for executor status response"""
    name: str
    status: int
    status_text: str
    updated_at: datetime

class ExecutorStatusUpdate(BaseModel):
    """Schema for updating executor status"""
    status: int