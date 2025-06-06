from sqlmodel import SQLModel, Field
from typing import Optional
import datetime

class Kubeconf(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(index=True)
    original_filename: str = Field(default="")
    user_id: int = Field(index=True)
    active: bool = Field(default=False, index=True)
    path: str = Field()
    cluster_name: Optional[str] = Field(default=None, index=True)
    context_name: Optional[str] = Field(default=None, index=True)
    is_operator_installed: bool = Field(default=False, index=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


class ClusterInfo1(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True)  # <- Make it optional
    api_server_url: str = Field()
    internal_api_server_url: Optional[str] = Field(default=None)
    external_ip: Optional[str] = Field(default=None)
    ca_certificate: str = Field()
    bearer_token: str = Field()
    namespace: str = Field(index=True)
    service_account: str = Field()
    cluster_role: str = Field()
    cluster_name: Optional[str] = Field(default=None, index=True)
    api_access_test: str = Field(default="unknown")
    timestamp: datetime.datetime = Field()
    helm_release: Optional[str] = Field(default=None)
    helm_namespace: Optional[str] = Field(default=None)
    status: bool = Field(default=False)
    source: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)



class ClusterInfo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    api_server_url: str = Field()
    internal_api_server_url: Optional[str] = Field(default=None)
    external_ip: Optional[str] = Field(default=None)
    ca_certificate: str = Field()
    bearer_token: str = Field()
    namespace: str = Field(index=True)
    service_account: str = Field()
    cluster_role: str = Field()
    cluster_name: Optional[str] = Field(default=None, index=True)
    api_access_test: str = Field(default="unknown")
    timestamp: datetime.datetime = Field()
    helm_release: Optional[str] = Field(default=None)
    helm_namespace: Optional[str] = Field(default=None)
    status: bool = Field(default=False)
    source: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)



