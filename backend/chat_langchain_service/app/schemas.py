from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

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

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"

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
 
# New schema for streaming chat
class ChatRequest(BaseModel):
    message: str
    stream: bool = True
    session_id: Optional[str] = None

class StreamingToken(BaseModel):
    token: Optional[str] = Field(None, description="Streaming token")
    done: bool = Field(False, description="Whether streaming is complete")
    session_id: Optional[str] = Field(None, description="Session ID")
    error: Optional[str] = Field(None, description="Error message if any")

class HealthResponse(BaseModel):
    status: str
    database: str
    llm: str
    timestamp: str

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: str

class DebugSchemaResponse(BaseModel):
    tables: List[str]
    schema: dict
    timestamp: str

class DebugLLMResponse(BaseModel):
    status: str
    response: str
    timestamp: str