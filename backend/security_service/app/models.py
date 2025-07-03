from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class ApplicationStatus(enum.Enum):
    PENDING = "pending"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    REMOVED = "removed"

class PolicyCategoryModel(Base):
    __tablename__ = "policy_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    policies = relationship("PolicyModel", back_populates="category")

class PolicyModel(Base):
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(String(200), unique=True, index=True, nullable=False)
    name = Column(String(300), nullable=False)
    description = Column(Text)
    purpose = Column(Text)
    severity = Column(String(20), default="medium")
    yaml_content = Column(Text, nullable=False)
    policy_metadata = Column(JSON)
    tags = Column(JSON)
    is_active = Column(Boolean, default=True)
    category_id = Column(Integer, ForeignKey("policy_categories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    category = relationship("PolicyCategoryModel", back_populates="policies")
    applications = relationship("PolicyApplicationModel", back_populates="policy")

# NEW MODEL: Policy Applications
class PolicyApplicationModel(Base):
    __tablename__ = "policy_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    cluster_id = Column(Integer, nullable=False, index=True)
    cluster_name = Column(String(200), nullable=False)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    
    # Application details
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING)
    applied_yaml = Column(Text)
    application_log = Column(Text)
    error_message = Column(Text)
    
    # Kubernetes details
    kubernetes_name = Column(String(200))
    kubernetes_namespace = Column(String(100), default="cluster-wide")
    # is_cluster_wide = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    policy = relationship("PolicyModel", back_populates="applications")