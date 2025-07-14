from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict
from typing import Optional, List  # ← Add List to this import
from datetime import datetime

# OR if you're using Python 3.9+, you can use the built-in list type:
# from typing import Optional
# from datetime import datetime

# Rest of your existing code...

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

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
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
    refresh_token: str  # NEW: Add refresh token
    token_type: str = "bearer"
    expires_at: datetime
    session_id: str  # NEW: Session identifier

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

# NEW: Token refresh request
class TokenRefreshRequest(BaseModel):
    refresh_token: str

# NEW: Device fingerprinting
class DeviceFingerprint(BaseModel):
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None

# NEW: Session management schemas
class SessionInfo(BaseModel):
    session_id: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    is_current: bool = False

class UserSessionsResponse(BaseModel):
    sessions: List[SessionInfo]  # ← This should now work
    total_sessions: int

# NEW: Session termination
class TerminateSessionRequest(BaseModel):
    session_id: str

class TerminateAllSessionsRequest(BaseModel):
    except_current: bool = True

# API Key Schemas
class ApiKeyCreate(BaseModel):
    key_name: str = Field(..., min_length=1, max_length=100)
    expires_at: Optional[datetime] = None

class ApiKeyResponse(BaseModel):
    id: int
    key_name: str
    api_key: str
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
    api_key_preview: str
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
    users: List[UserResponse]  # ← This should also work now
    roles_options: List[str]   # ← And this one too
