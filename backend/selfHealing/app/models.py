from sqlmodel import SQLModel, Field, Relationship, JSON
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Define the Plan model first
class Plan(SQLModel, table=True):
    __tablename__ = "plan"  # Explicitly define the table name
    
    plan_id: str = Field(primary_key=True)
    incident_id: str = Field(index=True)  # Add foreign key to incident if needed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending")
    
    # Define relationship to Action model
    actions: List["Action"] = Relationship(back_populates="plan")

# Then define the Action model that references Plan
class Action(SQLModel, table=True):
    __tablename__ = "action"  # Explicitly define the table name
    
    action_id: str = Field(primary_key=True)
    plan_id: str = Field(foreign_key="plan.plan_id", index=True)
    executor: str
    command: str
    parameters: Dict[str, Any] = Field(default={}, sa_type=JSON)
    description: Optional[str] = None
    order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Define relationship to Plan model
    plan: Plan = Relationship(back_populates="actions")

# Define other models like RawEvent, Incident, ExecutionResult
class RawEvent(SQLModel, table=True):
    __tablename__ = "raw_event"
    
    id: int = Field(default=None, primary_key=True)
    event_data: Dict[str, Any] = Field(sa_type=JSON)
    user_id: Optional[str] = None
    received_at: datetime = Field(default_factory=datetime.utcnow)

class Incident(SQLModel, table=True):
    __tablename__ = "incident"
    
    incident_id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    affected_resource: Dict[str, str] = Field(sa_type=JSON)
    failure_type: str
    description: str
    severity: str = Field(default="medium")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="detected")
    user_id: Optional[str] = None


class ExecutionResult(SQLModel, table=True):
    __tablename__ = "execution_result"
    
    execution_id: str = Field(primary_key=True)
    plan_id: Optional[str] = Field(default=None, foreign_key="plan.plan_id", index=True)
    action_id: Optional[str] = Field(default=None, foreign_key="action.action_id", index=True)
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
