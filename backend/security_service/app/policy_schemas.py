from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from fastapi import Request
import re

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    REMOVED = "removed"

class PolicyCategoryEnum(str, Enum):
    VALIDATION = "validation"
    MUTATION = "mutation"
    GENERATION = "generation"
    CLEANUP = "cleanup"
    IMAGE_VERIFICATION = "image_verification"
    MISCELLANEOUS = "miscellaneous"
    # NEW CATEGORIES
    FILE_BASED = "file_based"
    PROCESS_BASED = "process_based"
    NETWORK_BASED = "network_based"
    CAPABILITIES_PERMISSIONS = "capabilities_permissions"

class PolicyCategoryBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = None

class PolicyCategoryCreate(PolicyCategoryBase):
    pass

class PolicyCategoryResponse(PolicyCategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    policy_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# Add this new schema for editable fields
class EditableField(BaseModel):
    line_number: int
    field_name: str
    current_value: str
    field_type: str = "string"  # string, boolean, array, etc.

class PolicyEditableResponse(BaseModel):
    policy_id: str
    name: str
    yaml_content: str
    editable_fields: List[EditableField]

class UserEditedPolicyResponse(BaseModel):
    id: int
    user_id: int
    original_policy_id: int
    edited_yaml_content: str
    edited_name: Optional[str] = None
    edited_description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class PolicyBase(BaseModel):
    policy_id: str
    name: str
    description: Optional[str] = None
    purpose: Optional[str] = None
    severity: str = "medium"
    yaml_content: str
    policy_metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: bool = True

class PolicyCreate(PolicyBase):
    category_id: int

class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    severity: Optional[str] = None
    yaml_content: Optional[str] = None
    policy_metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class PolicyResponse(PolicyBase):
    id: int
    category_id: int
    category: Optional[PolicyCategoryResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_edited: Optional[bool] = False
    user_edited_policy: Optional[UserEditedPolicyResponse] = None
    
    class Config:
        from_attributes = True

class PolicyListResponse(BaseModel):
    policies: List[PolicyResponse]
    total: int
    page: int
    size: int
    total_pages: int

class PolicyApplicationRequest(BaseModel):
    cluster_name: str
    policy_id: str  # The policy's policy_id (not database id)
    kubernetes_namespace: Optional[str] = None  # Make it optional for cluster-level policies
    edited_yaml: Optional[str] = None  # Add this field for edited YAML content
    save_edited_policy: Optional[bool] = False  # Add this field to save edited policy
    force_apply: Optional[bool] = False  # Add this field to force apply even if exists

class PolicyApplicationResponse(BaseModel):
    id: int
    user_id: int
    cluster_id: int
    cluster_name: str
    policy_id: int
    policy: Optional[PolicyResponse] = None  # Make this optional
    user_edited_policy_id: Optional[int] = None
    user_edited_policy: Optional[UserEditedPolicyResponse] = None
    status: ApplicationStatus
    applied_yaml: Optional[str] = None
    application_log: Optional[str] = None
    error_message: Optional[str] = None
    kubernetes_name: Optional[str] = None
    kubernetes_namespace: str
    is_edited_policy: Optional[bool] = False
    created_at: datetime
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Add these fields for when policy is missing
    policy_name: Optional[str] = None
    policy_severity: Optional[str] = None
    
    class Config:
        from_attributes = True

class PolicyApplicationListResponse(BaseModel):
    applications: List[PolicyApplicationResponse]
    total: int
    page: int
    size: int
    total_pages: int

class ClusterInfo(BaseModel):
    id: int
    cluster_name: str
    server_url: str
    provider_name: Optional[str] = None
    is_accessible: bool = True

class ClusterPolicyOverview(BaseModel):
    cluster: ClusterInfo
    total_applications: int
    applied_count: int
    failed_count: int
    pending_count: int
    categories_applied: List[str]

class PolicyApplicationListRequest(BaseModel):
    cluster_name: Optional[str] = None
    status: Optional[str] = None
    page: int = 1
    size: int = 10

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str

class PolicyCreateRequest(BaseModel):
    policy_id: str
    name: str
    description: Optional[str] = None
    purpose: Optional[str] = None
    severity: str = "medium"
    yaml_content: str
    policy_metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: bool = True

class CategoryWithPoliciesRequest(BaseModel):
    category_name: str
    category_display_name: str
    category_description: Optional[str] = None
    category_icon: Optional[str] = "shield"
    policies: List[PolicyCreateRequest]

class AddPoliciesRequest(BaseModel):
    # For adding to existing category
    existing_category_name: Optional[str] = None
    
    # For creating new category with policies
    new_category: Optional[CategoryWithPoliciesRequest] = None
    
    # For adding policies to existing category without category info
    policies: Optional[List[PolicyCreateRequest]] = None

class AddPoliciesResponse(BaseModel):
    success: bool
    message: str
    category_created: Optional[bool] = False
    category_name: str
    policies_added: int
    policies_failed: int
    added_policies: List[PolicyResponse]
    failed_policies: List[Dict[str, str]]  # {"policy_id": str, "error": str}

class DeletePolicyRequest(BaseModel):
    policy_id: str

class DeleteCategoryRequest(BaseModel):
    category_name: str
    force_delete: Optional[bool] = False  # If true, deletes category even if it has policies

class DeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_count: int
    deleted_items: List[str]
    warnings: Optional[List[str]] = None
