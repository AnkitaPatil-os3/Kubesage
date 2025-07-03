# from sqlmodel import SQLModel, Field
# from typing import Optional
# import datetime
# from datetime import datetime  # Import the datetime class directly, not the module


# class User(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     username: str = Field(unique=True, index=True)
#     email: str = Field(unique=True, index=True)
#     hashed_password: str
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     is_active: bool = Field(default=True)

#     roles: Optional[str] = Field(default="")
#     created_at: datetime = Field(default_factory=datetime.now)
#     updated_at: datetime = Field(default_factory=datetime.now)
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = Field(default=True)
    confirmed: bool = Field(default=False)  # Added confirmed field
    roles: str 
    # roles: Optional[str] = Field(default="")  # Comma-separated roles as a string
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
    expires_at: Optional[datetime] = None  # CHANGE: Remove .datetime
    last_used_at: Optional[datetime] = None  # CHANGE: Remove .datetime
    created_at: datetime = Field(default_factory=datetime.now)  # CHANGE: Remove .datetime
    updated_at: datetime = Field(default_factory=datetime.now)  # CHANGE: Remove .datetime
