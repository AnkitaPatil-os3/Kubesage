from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None

class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False

# Chat Request/Response Schemas
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    enable_tool_response: Optional[bool] = False

class ToolInfo(BaseModel):
    name: str
    args: str

class ToolResponse(BaseModel):
    name: str
    response: str

class ChatResponse(BaseModel):
    session_id: str
    response: str
    tools_info: Optional[List[ToolInfo]] = []
    tool_response: Optional[List[ToolResponse]] = []

# Session Schemas
class SessionInfo(BaseModel):
    id: str
    created_at: datetime

class SessionHistory(SessionInfo):
    messages: List[Dict[str, Any]]

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "Kubernetes Chat"

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None

class ChatSessionResponse(BaseModel):
    id: int
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

class ChatSessionList(BaseModel):
    sessions: List[ChatSessionResponse]

# Message Schemas
class MessageCreate(BaseModel):
    content: str
    session_id: Optional[str] = None

class MessageResponse(BaseModel):
    role: str
    content: str
    session_id: str
    created_at: Optional[datetime] = None

class ChatHistoryEntry(BaseModel):
    role: str
    content: str
    created_at: datetime

class ChatHistoryResponse(BaseModel):
    session_id: str
    title: str
    messages: List[ChatHistoryEntry]
    created_at: datetime
    updated_at: datetime

# Health Check Schemas
class HealthResponse(BaseModel):
    status: str
    database: str
    llm: str
    kubernetes: str
    timestamp: str

# Error Response Schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: str

# Streaming Schemas
class StreamingToken(BaseModel):
    token: Optional[str] = Field(None, description="Streaming token")
    done: bool = Field(False, description="Whether streaming is complete")
    session_id: Optional[str] = Field(None, description="Session ID")
    error: Optional[str] = Field(None, description="Error message if any")

# Debug Schemas
class DebugSchemaResponse(BaseModel):
    tables: List[str]
    schema: dict
    timestamp: str

class DebugLLMResponse(BaseModel):
    status: str
    response: str
    timestamp: str