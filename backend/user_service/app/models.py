from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid

class User(SQLModel, table=True):
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    confirmed: bool = Field(default=False)
    roles: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    password_changed: bool = Field(default=False)  # Add this new field

    
    # Relationships
    tokens: List["UserToken"] = Relationship(back_populates="user")
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="user")
    api_keys: List["ApiKey"] = Relationship(back_populates="user")

class UserToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    user_id: int = Field(foreign_key="user.id")
    session_id: Optional[str] = Field(default=None, index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
    
    # Device information
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    last_used_at: Optional[datetime] = None
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="tokens")

class RefreshToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    user_id: int = Field(foreign_key="user.id")
    session_id: str = Field(index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    is_revoked: bool = Field(default=False)
    
    # Device information
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="refresh_tokens")

class ApiKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key_name: str
    api_key: str = Field(unique=True, index=True)
    user_id: int = Field(foreign_key="user.id")
    is_active: bool = Field(default=True)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="api_keys")

class License(SQLModel, table=True):
    __tablename__ = "licenses"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    license_key: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_active: bool = Field(default=True)
    created_by: Optional[str] = Field(default=None)
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
