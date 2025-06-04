from sqlmodel import SQLModel, Field, Column, JSON, create_engine, Text
from typing import Optional, Dict, Any, List
from datetime import datetime
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
