from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class ClusterConfig(Base):
    __tablename__ = "cluster_configs"

    id = Column(Integer, primary_key=True, index=True)
    cluster_name = Column(String, index=True)
    server_url = Column(String)  # Keep for backward compatibility, will be "in-cluster" for agents
    token = Column(String)  # Keep for backward compatibility, will be "in-cluster-token" for agents
    context_name = Column(String, nullable=True, index=True)
    provider_name = Column(String, nullable=True, index=True)
    tags = Column(Text, nullable=True)
    use_secure_tls = Column(Boolean, default=False)
    ca_data = Column(Text, nullable=True)
    tls_key = Column(Text, nullable=True)
    tls_cert = Column(Text, nullable=True)
    user_id = Column(Integer, index=True)
    is_operator_installed = Column(Boolean, default=False, index=True)
    cluster_metadata = Column(Text, nullable=True)  # Store agent metadata as JSON (renamed from metadata)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with agents
    agents = relationship("Agent", back_populates="cluster")

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, unique=True, index=True)
    cluster_id = Column(Integer, ForeignKey("cluster_configs.id"), index=True, nullable=True)
    user_id = Column(Integer, index=True)
    status = Column(String, default="pending")  # pending, connected, disconnected, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)

    # Relationship with cluster
    cluster = relationship("ClusterConfig", back_populates="agents")
