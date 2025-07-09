from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import uuid

# Database Models
class User(SQLModel, table=True):
    """User model - should match the user service model."""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str = Field(default="")
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
    title: str = Field(default="Kubernetes Chat", max_length=200)
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

# API Request/Response Models
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: Optional[str] = None
    enable_tool_response: bool = False
    format: Optional[str] = "markdown"  # ADD: Default to markdown

class ToolInfo(BaseModel):
    """Tool information model."""
    name: str
    args: str

class ToolResponse(BaseModel):
    """Tool response model."""
    name: str
    response: str

class ChatResponse(BaseModel):
    """Chat response model."""
    session_id: str
    response: str
    tools_info: Optional[List[ToolInfo]] = []
    tool_response: Optional[List[ToolResponse]] = []

class SessionInfo(BaseModel):
    """Session information model."""
    id: str
    created_at: datetime

class SessionHistory(SessionInfo):
    """Session history model."""
    messages: List[Dict[str, Any]]

class MessageCreate(BaseModel):
    """Message creation model."""
    content: str
    session_id: Optional[str] = None

class MessageResponse(BaseModel):
    """Message response model."""
    role: str
    content: str
    session_id: str
    created_at: Optional[datetime] = None

class ChatHistoryEntry(BaseModel):
    """Chat history entry model."""
    role: str
    content: str
    created_at: datetime

class ChatHistoryResponse(BaseModel):
    """Chat history response model."""
    session_id: str
    title: str
    messages: List[ChatHistoryEntry]
    created_at: datetime
    updated_at: datetime

class ChatSessionCreate(BaseModel):
    """Chat session creation model."""
    title: Optional[str] = "Kubernetes Chat"

class ChatSessionUpdate(BaseModel):
    """Chat session update model."""
    title: Optional[str] = None
    is_active: Optional[bool] = None

class ChatSessionResponse(BaseModel):
    """Chat session response model."""
    id: int
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

class ChatSessionList(BaseModel):
    """Chat session list model."""
    sessions: List[ChatSessionResponse]

class HealthResponse(BaseModel):
    """Health response model."""
    status: str
    database: str
    llm: str
    kubernetes: str
    timestamp: str

class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    error_code: Optional[str] = None
    timestamp: str

class UserInfo(BaseModel):
    """User information model."""
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_admin: bool

class Token(BaseModel):
    """Token model."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Token data model."""
    user_id: Optional[int] = None
    username: Optional[str] = None

# Streaming Models
class StreamingToken(BaseModel):
    """Streaming token model."""
    token: Optional[str] = Field(None, description="Streaming token")
    done: bool = Field(False, description="Whether streaming is complete")
    session_id: Optional[str] = Field(None, description="Session ID")
    error: Optional[str] = Field(None, description="Error message if any")

# Analytics Models
class UsageStats(BaseModel):
    """Usage statistics model."""
    total_sessions: int
    active_sessions: int
    total_messages: int
    recent_sessions_24h: int
    average_messages_per_session: float
    timestamp: str
    user_id: Optional[int] = None

class InteractionMetrics(BaseModel):
    """Interaction metrics model."""
    user_id: int
    session_id: str
    message_length: int
    response_time: float
    tools_used: List[str]
    timestamp: str

# Debug Models (only used in debug mode)
class DebugInfo(BaseModel):
    """Debug information model."""
    database_url: str
    config: Dict[str, Any]
    stats: Dict[str, Any]
    timestamp: str

class DebugLLMResponse(BaseModel):
    """Debug LLM response model."""
    status: str
    request: str
    response: str
    timestamp: str

class DatabaseStats(BaseModel):
    """Database statistics model."""
    users: int
    sessions: int
    messages: int
    integrity: Dict[str, Any]
    timestamp: str
