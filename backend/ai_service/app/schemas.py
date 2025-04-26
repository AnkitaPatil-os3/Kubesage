from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

# Input schemas
class Query(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language query for kubectl command generation")

class ExecuteRequest(BaseModel):
    execute: str = Field(..., min_length=3,  description="kubectl command to execute")

# Response schemas
class CommandMetadata(BaseModel):
    start_time: str
    end_time: str
    duration_ms: float
    success: bool
    error_type: Optional[str] = None
    error_code: Optional[int] = None

class CommandResponse(BaseModel):
    kubectl_command: List[str]
    execution_result: Optional[str] = None
    execution_error: Optional[str] = None
    from_cache: bool
    metadata: CommandMetadata

class MessageResponse(BaseModel):
    message: str
