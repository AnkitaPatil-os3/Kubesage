from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional, Any, Union
from datetime import datetime


# New changes: Added flexible schemas to handle any type of alert data with complete JSON storage
class FlexibleAlert(BaseModel):
    """Flexible alert schema that can handle any type of alert data from different sources"""
    # Core fields that we'll try to extract or generate
    alert_type: Optional[str] = "unknown"  # prometheus, grafana, kubernetes-event, etc.
    severity: Optional[str] = "info"  # Default severity
    status: Optional[str] = "active"  # Default status
    
    # Flexible data storage - can contain any structure
    raw_data: Dict[str, Any]  # Store the complete original data
    
    # Extracted/normalized fields for easier processing
    title: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional fields

class Alert(BaseModel):
    status: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: str
    endsAt: str
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None


# New changes: Flexible alert request that can handle both old and new formats with complete JSON storage
class FlexibleAlertRequest(BaseModel):

    """Flexible request schema that can handle various alert formats and store complete JSON"""
    # For handling raw data of any format
    data: Optional[Union[List[Dict[str, Any]], Dict[str, Any], str]] = None
    
    # Legacy support for existing AlertManager format
    alerts: Optional[List[Alert]] = None
    receiver: Optional[str] = None
    status: Optional[str] = None
    groupLabels: Optional[Dict[str, str]] = None
    commonLabels: Optional[Dict[str, str]] = None
    commonAnnotations: Optional[Dict[str, str]] = None
    externalURL: Optional[str] = None
    version: Optional[str] = None
    groupKey: Optional[str] = None
    truncatedAlerts: Optional[int] = 0
    

    # New changes: Source identification and complete data storage
    source_type: Optional[str] = None  # grafana, prometheus, kubernetes, etc.
    
    class Config:
        extra = "allow"  # Allow any additional fields

class AlertRequest(BaseModel):
    alerts: List[Alert]
    receiver: Optional[str] = None
    status: Optional[str] = None
    groupLabels: Optional[Dict[str, str]] = None
    commonLabels: Optional[Dict[str, str]] = None
    commonAnnotations: Optional[Dict[str, str]] = None
    externalURL: Optional[str] = None
    version: Optional[str] = None
    groupKey: Optional[str] = None
    truncatedAlerts: Optional[int] = 0

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

# New changes: Updated AlertResponse to include complete JSON data
class AlertResponse(BaseModel):

    """Schema for alert response data with complete JSON storage"""
    id: str
    status: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: str
    endsAt: str
    approval_status: str
    action_plan: Optional[str] = None
    remediation_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    complete_json_data: Dict[str, Any] = {}  # New changes: Include complete JSON data

class AlertStats(BaseModel):
    """Schema for alert statistics"""
    total_alerts: int
    critical_alerts: int
    pending_approval: int
    approved: int
    rejected: int
    auto_approved: int
