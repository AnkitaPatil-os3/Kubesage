from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
import uuid
 
class ChatSession(SQLModel, table=True):
    """Chat session model to group related messages"""
    __tablename__ = "chat_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True, unique=True)
    user_id: int = Field(index=True)
    title: str = Field(default="New Chat")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # Virtual field for relationship
    messages: List["ChatMessage"] = Relationship(back_populates="session")
    
class ChatMessage(SQLModel, table=True):
    """Individual chat message model"""
    __tablename__ = "chat_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chat_sessions.session_id", index=True)
    role: str = Field(index=True)  # 'user', 'assistant', or 'system'
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Virtual field for relationship
    session: Optional[ChatSession] = Relationship(back_populates="messages")
 
class K8sAnalysisReference(SQLModel, table=True):
    """Reference to K8s analysis results to link with chat sessions"""
    __tablename__ = "k8s_analysis_references"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chat_sessions.session_id", index=True)
    analysis_id: int = Field(index=True)  # Reference to analysis in k8sgpt service
    created_at: datetime = Field(default_factory=datetime.utcnow)
 
 