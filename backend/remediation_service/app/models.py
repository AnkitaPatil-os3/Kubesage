from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json

class ExecutorType(str, Enum):
    KUBECTL = "kubectl"
    ARGOCD = "argocd"
    CROSSPLANE = "crossplane"

class ExecutorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class IncidentType(str, Enum):
    NORMAL = "Normal"
    WARNING = "Warning"
    ERROR = "Error"


# Make sure your Executor model has proper constraints
class Executor(SQLModel, table=True):
    __tablename__ = "executors"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: ExecutorType = Field(index=True, unique=True)  # Add unique constraint
    status: ExecutorStatus = Field(default=ExecutorStatus.INACTIVE)
    description: Optional[str] = Field(default=None)
    config: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    incidents: list["Incident"] = Relationship(back_populates="executor")



class WebhookUser(SQLModel, table=True):
    __tablename__ = "webhook_users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(unique=True, index=True)  # User ID from user service
    username: str = Field(index=True)
    email: Optional[str] = None
    api_key_hash: str = Field(index=True)  # Store hash of API key for security
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    incidents: list["Incident"] = Relationship(back_populates="webhook_user")



class Incident(SQLModel, table=True):
    __tablename__ = "incidents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    incident_id: str = Field(unique=True, index=True)
    type: IncidentType = Field(index=True)
    reason: str = Field(index=True)
    message: str
    metadata_namespace: Optional[str] = Field(default=None, index=True)
    metadata_creation_timestamp: Optional[datetime] = Field(default=None)
    involved_object_kind: Optional[str] = Field(default=None, index=True)
    involved_object_name: Optional[str] = Field(default=None, index=True)
    source_component: Optional[str] = Field(default=None)
    source_host: Optional[str] = Field(default=None)
    reporting_component: Optional[str] = Field(default=None)
    count: Optional[int] = Field(default=1)
    first_timestamp: Optional[datetime] = Field(default=None)
    last_timestamp: Optional[datetime] = Field(default=None)
    involved_object_labels: Optional[str] = Field(default=None)
    involved_object_annotations: Optional[str] = Field(default=None)
    cluster_name: Optional[str] = Field(default=None, index=True)
    
    # Remediation tracking
    executor_id: Optional[int] = Field(default=None, foreign_key="executors.id")
    is_resolved: bool = Field(default=False)
    resolution_attempts: int = Field(default=0)
    last_resolution_attempt: Optional[datetime] = Field(default=None)
    
    # Only webhook_user_id - NO user_id field
    webhook_user_id: Optional[int] = Field(default=None, foreign_key="webhook_users.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    executor: Optional[Executor] = Relationship(back_populates="incidents")
    webhook_user: Optional[WebhookUser] = Relationship(back_populates="incidents")
    
    def get_labels_dict(self) -> Dict[str, Any]:
        """Convert labels JSON string to dictionary"""
        if self.involved_object_labels:
            try:
                return json.loads(self.involved_object_labels)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_annotations_dict(self) -> Dict[str, Any]:
        """Convert annotations JSON string to dictionary"""
        if self.involved_object_annotations:
            try:
                return json.loads(self.involved_object_annotations)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_labels_dict(self, labels: Dict[str, Any]):
        """Set labels from dictionary"""
        self.involved_object_labels = json.dumps(labels) if labels else None
    
    def set_annotations_dict(self, annotations: Dict[str, Any]):
        """Set annotations from dictionary"""
        self.involved_object_annotations = json.dumps(annotations) if annotations else None