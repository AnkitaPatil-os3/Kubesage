# hi
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
import datetime
import uuid

class UserRoleLink(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    role_id: Optional[int] = Field(default=None, foreign_key="role.id", primary_key=True)

class RolePermissionLink(SQLModel, table=True):
    role_id: Optional[int] = Field(default=None, foreign_key="role.id", primary_key=True)
    permission_id: Optional[int] = Field(default=None, foreign_key="permission.id", primary_key=True)

class Permission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    roles: List["Role"] = Relationship(back_populates="permissions", link_model=RolePermissionLink)

class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    permissions: List[Permission] = Relationship(back_populates="roles", link_model=RolePermissionLink)
    users: List["User"] = Relationship(back_populates="roles", link_model=UserRoleLink)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

# Permission.roles = Relationship(back_populates="permissions", link_model=RolePermissionLink)

# Role.permissions = Relationship(back_populates="roles", link_model=RolePermissionLink)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    roles: List[Role] = Relationship(back_populates="users", link_model=UserRoleLink)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

class UserToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    expires_at: datetime.datetime
    is_revoked: bool = Field(default=False)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    

class ApiKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key_name: str = Field(index=True)  # Human-readable name for the API key
    api_key: str = Field(unique=True, index=True)  # The actual API key
    user_id: int = Field(foreign_key="user.id", index=True)
    is_active: bool = Field(default=True)
    expires_at: Optional[datetime.datetime] = None  # Optional expiration
    last_used_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
