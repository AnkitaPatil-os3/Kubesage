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
    is_operator_installed: bool = Field(default=False, index=True)
    
    # Timestamps
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

# New model for tracking user cleanup operations
class UserCleanupOperation(SQLModel, table=True):
    """Track user cleanup operations in kubeconfig service"""
    id: Optional[int] = Field(default=None, primary_key=True)
    operation_id: str = Field(unique=True, index=True)  # From user service
    user_id: int = Field(index=True)
    username: str = Field(index=True)
    status: str = Field(default="pending", index=True)  # pending, in_progress, completed, failed
    clusters_to_cleanup: str = Field(default="")  # JSON list of cluster IDs
    clusters_cleaned: str = Field(default="")  # JSON list of cleaned cluster IDs
    cleanup_details: Optional[str] = Field(default=None)  # JSON details of cleanup
    error_message: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    completed_at: Optional[datetime.datetime] = Field(default=None)
