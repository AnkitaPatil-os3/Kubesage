from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid


class User(SQLModel, table=True):
    """User model - should match the user service model."""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    chat_sessions: List["ChatSession"] = Relationship(back_populates="user")


class ChatSession(SQLModel, table=True):
    """Chat session model for managing conversation contexts."""
    __tablename__ = "chat_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True, default_factory=lambda: str(uuid.uuid4()))
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(default="New Chat", max_length=200)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="chat_sessions")
    messages: List["ChatMessage"] = Relationship(back_populates="session", cascade_delete=True)

class ChatMessage(SQLModel, table=True):
    """Chat message model for storing conversation history."""
    __tablename__ = "chat_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chat_sessions.session_id", index=True)
    role: str = Field(index=True)  # "user" or "assistant"
    content: str = Field(max_length=50000)  # Large text field for long responses
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    session: Optional[ChatSession] = Relationship(back_populates="messages")

class ChatAnalytics(SQLModel, table=True):
    """Analytics model for tracking chat usage and performance."""
    __tablename__ = "chat_analytics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime = Field(index=True)
    total_sessions: int = Field(default=0)
    total_messages: int = Field(default=0)
    active_users: int = Field(default=0)
    avg_session_length: Optional[float] = None
    avg_response_time_ms: Optional[float] = None
    error_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserToken(SQLModel, table=True):
    """User token model for authentication - should match user service."""
    __tablename__ = "user_tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    user_id: int = Field(foreign_key="users.id")
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)