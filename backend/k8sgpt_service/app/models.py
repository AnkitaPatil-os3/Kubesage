from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class AIBackend(SQLModel, table=True):
    __tablename__ = "ai_backends"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    backend_type: str = Field(index=True)  # openai, azureopenai, etc.
    is_default: bool = Field(default=False)
    name: str
    api_key: str
    organization_id: Optional[str] = None
    model: str = Field(default="gpt-3.5-turbo")
    base_url: Optional[str] = None
    engine: Optional[str] = None  # for Azure
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2048)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AnalysisResult(SQLModel, table=True):
    __tablename__ = "analysis_results"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    file_path: str
    namespace: Optional[str] = Field(default=None, index=True)
    summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)