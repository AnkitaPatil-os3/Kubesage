from sqlmodel import SQLModel, Field
from typing import Optional
import datetime
from datetime import datetime  # Import the datetime class directly
import uuid


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    confirmed: bool = Field(default=False)
    roles: Optional[str] = Field(default="")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    # Add soft delete support
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    is_deleted: bool = Field(default=False, index=True)

class UserToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    expires_at: datetime
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)


class ApiKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key_name: str = Field(index=True)  # Human-readable name for the API key
    api_key: str = Field(unique=True, index=True)  # The actual API key
    user_id: int = Field(foreign_key="user.id", index=True)
    is_active: bool = Field(default=True)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# New model for tracking user deletion operations
class UserDeletionOperation(SQLModel, table=True):
    """Track user deletion operations and their status across services"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    username: str = Field(index=True)
    operation_id: str = Field(unique=True, index=True)  # UUID for tracking
    status: str = Field(default="initiated", index=True)  # initiated, in_progress, completed, failed
    services_to_cleanup: str = Field(default="")  # JSON list of services
    services_completed: str = Field(default="")  # JSON list of completed services
    services_failed: str = Field(default="")  # JSON list of failed services
    error_details: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)


# New model for service cleanup acknowledgments
class ServiceCleanupAck(SQLModel, table=True):
    """Track cleanup acknowledgments from individual services"""
    id: Optional[int] = Field(default=None, primary_key=True)
    operation_id: str = Field(index=True)
    service_name: str = Field(index=True)
    user_id: int = Field(index=True)
    status: str = Field(default="pending", index=True)  # pending, completed, failed
    cleanup_details: Optional[str] = Field(default=None)  # JSON details of what was cleaned
    error_message: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
