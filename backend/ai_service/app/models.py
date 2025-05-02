from sqlmodel import SQLModel, Field, Column, DateTime
from typing import Optional
from datetime import datetime
import uuid

class QueryHistory(SQLModel, table=True):
    """Model to store query history"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    query: str
    generated_commands: str
    execution_result: Optional[str] = None
    execution_error: Optional[str] = None
    execution_success: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    
    class Config:
        arbitrary_types_allowed = True
