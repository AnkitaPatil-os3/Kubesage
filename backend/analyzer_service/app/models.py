from sqlmodel import SQLModel, Field, Column, JSON, create_engine
from typing import Optional, Dict
from datetime import datetime
import uuid

class AlertModel(SQLModel, table=True):
    """Database model for storing alerts"""
    __tablename__ = "alerts"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    status: str
    labels: Dict = Field(sa_column=Column(JSON))
    annotations: Dict = Field(sa_column=Column(JSON))
    startsAt: str
    endsAt: str
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None
    
    # Additional tracking fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approval_status: str = Field(default="pending")  # pending, approved, rejected, auto-approved
    action_plan: Optional[str] = None
    remediation_status: Optional[str] = None  # pending, in_progress, completed, failed
