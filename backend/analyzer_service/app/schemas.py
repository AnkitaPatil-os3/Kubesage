from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional, Any, Union
from datetime import datetime


# Simplified flexible alert schema
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

# Add this new model for flexible request body
class FlexibleAlertRequest(BaseModel):
    """Flexible request model that accepts any JSON structure"""
    
    class Config:
        extra = "allow"  # Allow any additional fields
        
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
class AlertResponse(BaseModel):
    """Schema for alert response data with complete JSON storage"""
    id: str
    approval_status: str
    action_plan: Optional[str] = None
    remediation_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    complete_json_data: Dict[str, Any] = {}  # Include complete JSON data
    generated_report: Dict[str, Any] = {}  # Include generated report

class AlertStats(BaseModel):
    """Schema for alert statistics"""
    total_alerts: int
    critical_alerts: int
    pending_approval: int
    approved: int
    rejected: int
    auto_approved: int
