from sqlmodel import SQLModel, Field
from typing import Optional
import datetime
 
class ClusterConfig(SQLModel, table=True):
    """Unified model for cluster configuration - without active concept"""
    id: Optional[int] = Field(default=None, primary_key=True)
    cluster_name: str = Field(index=True)
    server_url: str = Field()
    token: str = Field()
    context_name: Optional[str] = Field(default=None, index=True)
    provider_name: Optional[str] = Field(default=None, index=True)
    tags: Optional[str] = Field(default=None)  # JSON string for tags
    
    # TLS Configuration fields
    use_secure_tls: bool = Field(default=False)
    ca_data: Optional[str] = Field(default=None)  # Certificate Authority Data
    tls_key: Optional[str] = Field(default=None)  # TLS Key
    tls_cert: Optional[str] = Field(default=None)  # TLS Certificate
    
    # User and status fields
    user_id: int = Field(index=True)
    # REMOVED: active field completely
    is_operator_installed: bool = Field(default=False, index=True)
    
    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
 
 