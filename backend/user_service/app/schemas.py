from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict
from typing import Optional
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    is_admin: Optional[bool] = None

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

