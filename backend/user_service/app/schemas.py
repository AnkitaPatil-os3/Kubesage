from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
 
# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    roles: str
 
class UserCreate(UserBase):
    password: str
 
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[str] = None
    password: Optional[str] = None
 
from pydantic import model_validator
 
class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]= None
    confirmed: Optional[bool] = False
    model_config = ConfigDict(from_attributes=True)
 
    @model_validator(mode='before')
    def convert_roles_to_string(cls, values):
        roles = values.get('roles')
        if isinstance(roles, list):
            values['roles'] = ",".join(roles)
        return values
 
# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
 
class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    roles: Optional[str] = None
 
class LoginRequest(BaseModel):
    username: str
    password: str
 
class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)
 
    @model_validator(mode='before')
    def check_password_match(cls, data):
        if data.get('new_password') != data.get('confirm_password'):
            raise ValueError('Passwords do not match')
        return data
 
# API Key Schemas
class ApiKeyCreate(BaseModel):
    key_name: str = Field(..., min_length=1, max_length=100)
    expires_at: Optional[datetime] = None
 
class ApiKeyResponse(BaseModel):
    id: int
    key_name: str
    api_key: str  # Only shown once during creation
    user_id: int
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
 
    model_config = ConfigDict(from_attributes=True)
 
class ApiKeyListResponse(BaseModel):
    id: int
    key_name: str
    api_key_preview: str  # Only show first 8 characters for security
    user_id: int
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
 
    model_config = ConfigDict(from_attributes=True)
 
class ApiKeyUpdate(BaseModel):
    key_name: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None
 
class UsersListResponse(BaseModel):
    users: List[UserResponse]
    roles_options: List[str]

# New schemas for user deletion operations
class UserDeletionRequest(BaseModel):
    """Request to delete a user with optional cleanup options"""
    force_delete: bool = Field(default=False, description="Force delete even if some services fail")
    cleanup_timeout: int = Field(default=300, description="Timeout in seconds for cleanup operations")
    services_to_skip: Optional[List[str]] = Field(default=None, description="Services to skip during cleanup")

class UserDeletionResponse(BaseModel):
    """Response for user deletion operation"""
    operation_id: str
    user_id: int
    username: str
    status: str
    message: str
    services_to_cleanup: List[str]
    estimated_completion_time: Optional[datetime] = None

class UserDeletionStatus(BaseModel):
    """Status of user deletion operation"""
    operation_id: str
    user_id: int
    username: str
    status: str
    services_to_cleanup: List[str]
    services_completed: List[str]
    services_failed: List[str]
    error_details: Optional[str] = None
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    progress_percentage: float

class ServiceCleanupAckRequest(BaseModel):
    """Acknowledgment from service about cleanup completion"""
    operation_id: str
    service_name: str
    user_id: int
    status: str  # completed, failed
    cleanup_details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class ServiceCleanupAckResponse(BaseModel):
    """Response to cleanup acknowledgment"""
    success: bool
    message: str
    operation_status: str
