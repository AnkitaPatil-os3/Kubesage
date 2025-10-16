from pydantic import BaseModel, field_validator
from typing import Optional, List, Union
from datetime import datetime
import json

class ClusterConfigRequest(BaseModel):
    cluster_name: str
    context_name: Optional[str] = None
    provider_name: Optional[str] = "kubernetes"
    tags: Optional[Union[str, List[str]]] = None
    use_secure_tls: bool = True
    metadata: Optional[dict] = None  # For storing cluster metadata from agent

    @field_validator('tags', mode='before')
    @classmethod
    def normalize_tags(cls, v):
        if isinstance(v, str):
            return [v]
        return v

class ClusterConfigResponse(BaseModel):
    id: int
    cluster_name: str
    context_name: Optional[str] = None
    provider_name: Optional[str] = None
    tags: Optional[List[str]] = None
    use_secure_tls: bool
    user_id: int
    is_operator_installed: bool
    created_at: datetime
    updated_at: datetime
    message: Optional[str] = None
    metadata: Optional[dict] = None  # For cluster metadata
    tags: Optional[List[str]] = None
    use_secure_tls: bool
    ca_data: Optional[str] = None
    tls_key: Optional[str] = None
    tls_cert: Optional[str] = None
    user_id: int
    is_operator_installed: bool
    created_at: datetime
    updated_at: datetime
    message: Optional[str] = None

    class Config:
        from_attributes = True

class ClusterListResponse(BaseModel):
    clusters: List[ClusterConfigResponse]

class GenerateAgentIdResponse(BaseModel):
    agent_id: str
    cluster_id: Optional[int] = None
    status: str
    message: str

    class Config:
        from_attributes = True
