from sqlmodel import SQLModel, Field, Column, JSON, create_engine, Text
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class AlertModel(SQLModel, table=True):
    """Database model for storing alerts"""
    __tablename__ = "alerts"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Additional tracking fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approval_status: str = Field(default="pending")  # pending, approved, rejected, auto-approved
    action_plan: Optional[str] = None
    remediation_status: Optional[str] = None  # pending, in_progress, completed, failed
    
    # Store complete JSON data without separate fields
    complete_json_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # Store entire incoming JSON data
    generated_report: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # Store generated report
