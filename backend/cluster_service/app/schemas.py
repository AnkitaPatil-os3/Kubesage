from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Request Schemas
class NamespacesRequest(BaseModel):
    """Request schema for getting namespaces"""
    agent_id: str
    cluster_id: Optional[int] = None

# Response Schemas
class NamespaceInfo(BaseModel):
    """Schema for namespace information"""
    name: str
    status: str
    created_at: Optional[str] = None
    labels: Optional[Dict[str, str]] = {}
    annotations: Optional[Dict[str, str]] = {}

class NamespacesResponse(BaseModel):
    """Response schema for namespaces list"""
    success: bool
    agent_id: str
    cluster_id: Optional[int] = None
    namespaces: List[NamespaceInfo] = []
    total_count: int = 0
    message: Optional[str] = None
    timestamp: str

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: str

class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str
    service: str
    timestamp: str
    version: str = "1.0.0"
