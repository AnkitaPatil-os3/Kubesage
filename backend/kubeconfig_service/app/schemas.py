from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class KubeconfigBase(BaseModel):
    filename: str
    original_filename: str
    cluster_name: Optional[str] = None
    context_name: Optional[str] = None
    provider_name: Optional[str] = None
    is_operator_installed: bool = False

class KubeconfigResponse(KubeconfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Updated for Pydantic v2

class KubeconfigList(BaseModel):
    kubeconfigs: List[KubeconfigResponse]

class MessageResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    detail: str

class ClusterNameResponse(BaseModel):
    filename: str
    cluster_name: str
    operator_installed: bool

class ClusterNamesResponse(BaseModel):
    cluster_names: List[ClusterNameResponse]
    errors: Optional[List[dict]] = None

# New schemas for cluster configuration
class ClusterConfigRequest(BaseModel):
    cluster_name: str
    server_url: str
    token: str
    context_name: Optional[str] = None
    provider_name: Optional[str] = "Standard"
    tags: Optional[str] = None
    use_secure_tls: bool = False
    ca_data: Optional[str] = None
    tls_key: Optional[str] = None
    tls_cert: Optional[str] = None

class ClusterConfigResponse(BaseModel):
    id: int
    cluster_name: str
    server_url: str
    context_name: Optional[str] = None
    provider_name: Optional[str] = None
    tags: Optional[str] = None
    use_secure_tls: bool
    ca_data: Optional[str] = None
    tls_key: Optional[str] = None
    tls_cert: Optional[str] = None
    user_id: int
    is_operator_installed: bool
    created_at: datetime
    updated_at: datetime
    message: Optional[str] = None  # For success messages

    class Config:
        from_attributes = True  # Updated for Pydantic v2

class ClusterConfigList(BaseModel):
    clusters: List[ClusterConfigResponse]

# Backward compatibility schemas
class ClusterOnboardRequest(BaseModel):
    cluster_name: str
    server_url: str
    token: str
    provider_name: Optional[str] = "Standard"

class ClusterOnboardResponse(BaseModel):
    id: int
    cluster_name: str
    server_url: str
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Updated for Pydantic v2
