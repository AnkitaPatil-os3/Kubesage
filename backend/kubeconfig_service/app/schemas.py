from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class KubeconfigBase(BaseModel):
    filename: str
    original_filename: str
    cluster_name: Optional[str] = None
    context_name: Optional[str] = None
    active: bool = False
    is_operator_installed: bool = False

class KubeconfigResponse(KubeconfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class KubeconfigList(BaseModel):
    kubeconfigs: List[KubeconfigResponse]

class MessageResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    detail: str

class ClusterNameResponse(BaseModel):
    filename: str
    cluster_name: str
    active: bool
    operator_installed: bool

class ClusterNamesResponse(BaseModel):
    cluster_names: List[ClusterNameResponse]
    errors: Optional[List[dict]] = None


# New schemas for cluster info
class ClusterInfoData(BaseModel):
    api_server_url: str
    internal_api_server_url: Optional[str] = None
    external_ip: Optional[str] = None
    ca_certificate: str
    bearer_token: str
    namespace: str
    service_account: str
    cluster_role: str
    cluster_name: Optional[str] = None
    api_access_test: str = "unknown"
    timestamp: str
    helm_release: Optional[str] = None
    helm_namespace: Optional[str] = None
    status: bool = False

class MetadataInfo(BaseModel):
    source: Optional[str] = None
    version: Optional[str] = None

class ClusterInfoRequest(BaseModel):
    cluster_info: ClusterInfoData
    metadata: MetadataInfo


class ClusterInfoResponse(BaseModel):
    id: int
    api_server_url: str
    cluster_name: Optional[str]
    namespace: str
    status: bool
    created_at: datetime

    class Config:
        orm_mode = True


class ClusterInfoRequest1(BaseModel):
    cluster_info: ClusterInfoData
    metadata: MetadataInfo

class ClusterInfoResponse1(BaseModel):
    id: int
    user_id: Optional[int]  # <- make this optional
    api_server_url: str
    cluster_name: Optional[str]
    namespace: str
    status: bool
    created_at: datetime
    
    class Config:
        orm_mode = True



