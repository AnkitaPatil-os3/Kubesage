from sqlmodel import SQLModel, Field, Column, JSON, create_engine, Text
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid


class IncidentModel(SQLModel, table=True):
    """Database model for storing Kubernetes incidents/events"""
    __tablename__ = "incidents"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Metadata fields
    metadata_name: str = Field(description="Unique name of the event")
    metadata_namespace: Optional[str] = Field(default=None, description="Namespace of the involved object")
    metadata_creation_timestamp: Optional[datetime] = Field(default=None, description="Timestamp when the event was created")
    
    # Event Info fields
    type: str = Field(description="Event type: Normal or Warning")
    reason: str = Field(description="Reason for the event")
    message: str = Field(description="Message describing what happened")
    count: Optional[int] = Field(default=1, description="Number of times the event occurred")
    first_timestamp: Optional[datetime] = Field(default=None, description="First occurrence timestamp")
    last_timestamp: Optional[datetime] = Field(default=None, description="Last occurrence timestamp")
    
    # Source Info fields
    source_component: Optional[str] = Field(default=None, description="Component that generated the event")
    source_host: Optional[str] = Field(default=None, description="Node where the event originated")
    
    # Involved Object fields
    involved_object_kind: Optional[str] = Field(default=None, description="Type of resource involved")
    involved_object_name: Optional[str] = Field(default=None, description="Name of the involved object")
    involved_object_field_path: Optional[str] = Field(default=None, description="Specific container involved")
    involved_object_labels: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Labels for correlation")
    involved_object_annotations: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Network or checksum-related metadata")
    involved_object_owner_references: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Owner controller information")
    
    # Reporter Info fields
    reporting_component: Optional[str] = Field(default=None, description="Component that reported the event")
    reporting_instance: Optional[str] = Field(default=None, description="Host instance reporting the event")

class ExecutionAttemptModel(SQLModel, table=True):
    """Track execution attempts for incidents"""
    __tablename__ = "execution_attempts"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    incident_id: str = Field(description="Related incident ID")
    solution_id: str = Field(description="Solution ID from LLM")
    attempt_number: int = Field(description="Attempt number (1, 2, 3)")
    executor_name: str = Field(description="Name of executor used")
    status: str = Field(description="success, failed, in_progress")
    execution_result: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    
class SolutionModel(SQLModel, table=True):
    """Store LLM solutions"""
    __tablename__ = "solutions"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    solution_id: str = Field(description="Solution ID from LLM")
    incident_id: str = Field(description="Related incident ID")
    summary: str = Field(description="Solution summary")
    analysis: str = Field(sa_column=Column(Text), description="Detailed analysis")
    steps: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))
    confidence_score: Optional[float] = Field(default=None)
    estimated_time_mins: Optional[int] = Field(default=None)
    severity_level: str = Field(description="LOW, MEDIUM, HIGH, CRITICAL")
    recommendations: List[str] = Field(default=[], sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ExecutorStatusModel(SQLModel, table=True):
    """Track executor status"""
    __tablename__ = "executor_status"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    executor_name: str = Field(index=True, unique=True)  # kubectl, crossplane, argocd
    status: int = Field(default=0)  # 0 = Active, 1 = Inactive
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
