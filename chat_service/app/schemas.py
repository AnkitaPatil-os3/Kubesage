from pydantic import BaseModel
from typing import List, Optional
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
