import httpx
import yaml
import asyncio
from kubernetes import client
from kubernetes.client import Configuration, ApiClient
from kubernetes.client.rest import ApiException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import base64
import os
import re
from fastapi import Request

from app.models import (
    PolicyCategoryModel, PolicyModel, PolicyApplicationModel, 
    ApplicationStatus
)
from app.policy_schemas import (
    PolicyApplicationRequest, PolicyApplicationResponse, 
    PolicyApplicationListResponse, ClusterInfo, ClusterPolicyOverview,
    ApplicationStatus as SchemaApplicationStatus,
    PolicyCategoryResponse, PolicyResponse, PolicyCreate, PolicyUpdate,
    PolicyEditableResponse, EditableField,UserEditedPolicyResponse , AddPoliciesRequest, AddPoliciesResponse,DeletePolicyRequest, DeleteCategoryRequest, DeleteResponse


)
from app.logger import logger

class PolicyDatabaseService:
    
 

    def extract_editable_fields(self, yaml_content: str) -> List[EditableField]:
        """Extract editable fields from YAML content marked with ##editable"""
        editable_fields = []
        lines = yaml_content.split('\n')
        
        for i, line in enumerate(lines):
            if '##editable' in line:
                # Remove the ##editable comment to get the actual line
                clean_line = line.split('##editable')[0].strip()
                
                # Extract field name and value
                if ':' in clean_line:
                    parts = clean_line.split(':', 1)
                    field_name = parts[0].strip()
                    current_value = parts[1].strip().strip('"\'')
                    
                    # Determine field type
                    field_type = "string"
                    if current_value.lower() in ['true', 'false']:
                        field_type = "boolean"
                    elif current_value.startswith('[') and current_value.endswith(']'):
                        field_type = "array"
                    elif current_value.isdigit():
                        field_type = "number"
                    
                    editable_fields.append(EditableField(
                        line_number=i + 1,
                        field_name=field_name,
                        current_value=current_value,
                        field_type=field_type
                    ))
        
        return editable_fields
    
    def get_categories(self, db: Session) -> List[PolicyCategoryResponse]:
        """Get all policy categories with policy counts"""
        categories = db.query(PolicyCategoryModel).all()
        result = []
        
        for category in categories:
            policy_count = db.query(PolicyModel).filter(
                PolicyModel.category_id == category.id
            ).count()
            
            cat_dict = {
                "id": category.id,
                "name": category.name,
                "display_name": category.display_name,
                "description": category.description,
                "icon": category.icon,
                "created_at": category.created_at,
                "updated_at": category.updated_at or category.created_at,
                "policy_count": policy_count
            }
            result.append(PolicyCategoryResponse(**cat_dict))
        
        return result

    def get_policy_applications(
        self, 
        db: Session, 
        user_id: int, 
        cluster_name: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1, 
        size: int = 10
    ) -> PolicyApplicationListResponse:
        """Get policy applications for a user with cluster filtering"""
        
        try:
            query = db.query(PolicyApplicationModel).filter(
                PolicyApplicationModel.user_id == user_id
            )
            
            if cluster_name:
                query = query.filter(PolicyApplicationModel.cluster_name == cluster_name)
            
            if status:
                try:
                    status_enum = ApplicationStatus(status.lower())
                    query = query.filter(PolicyApplicationModel.status == status_enum)
                except ValueError:
                    pass
            
            total = query.count()
            applications = query.offset((page - 1) * size).limit(size).all()
            
            application_responses = []
            for app in applications:
                try:
                    response = self._convert_application_to_response(db, app)
                    application_responses.append(response)
                except Exception as e:
                    logger.error(f"Error converting application {app.id}: {e}")
                    continue
            
            total_pages = (total + size - 1) // size if total > 0 else 0
            
            return PolicyApplicationListResponse(
                applications=application_responses,
                total=len(application_responses),
                page=page,
                size=size,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"Error in get_policy_applications: {e}")
            return PolicyApplicationListResponse(
                applications=[],
                total=0,
                page=page,
                size=size,
                total_pages=0
            )

    async def get_cluster_policy_overview(
        self, 
        db: Session, 
        user_id: int,
        user_token: str
    ) -> List[ClusterPolicyOverview]:
        """Get overview of policy applications across all clusters"""
        
        applications = db.query(PolicyApplicationModel).filter(
            PolicyApplicationModel.user_id == user_id
        ).all()
        
        cluster_data = {}
        for app in applications:
            cluster_name = app.cluster_name
            if cluster_name not in cluster_data:
                cluster_data[cluster_name] = {
                    'cluster_id': app.cluster_id,
                    'applications': [],
                    'categories': set()
                }
            
            cluster_data[cluster_name]['applications'].append(app)
            
            policy = db.query(PolicyModel).filter(PolicyModel.id == app.policy_id).first()
            if policy and policy.category:
                cluster_data[cluster_name]['categories'].add(policy.category.name)
        
        overviews = []
        for cluster_name, data in cluster_data.items():
            apps = data['applications']
            
            cluster_info = await self.get_cluster_info(cluster_name, user_token)
            
            cluster_overview = ClusterPolicyOverview(
                cluster=ClusterInfo(
                    id=data['cluster_id'],
                    cluster_name=cluster_name,
                    server_url=cluster_info.get('server_url', '') if cluster_info else '',
                    provider_name=cluster_info.get('provider_name', '') if cluster_info else '',
                    is_accessible=cluster_info is not None
                ),
                total_applications=len(apps),
                applied_count=len([a for a in apps if a.status == ApplicationStatus.APPLIED]),
                failed_count=len([a for a in apps if a.status == ApplicationStatus.FAILED]),
                pending_count=len([a for a in apps if a.status == ApplicationStatus.PENDING]),
                categories_applied=list(data['categories'])
            )
            
            overviews.append(cluster_overview)
        
        return overviews

    def initialize_database(self, db: Session):
        """Initialize database with predefined policies"""
        if not hasattr(self, 'policy_data') or not self.policy_data:
          logger.error("Policy data not available, reinitializing...")
          self.policy_data = self._get_all_policy_data()
        try:
            # Create categories first
            categories = [
                {
                    "name": "validation",
                    "display_name": "Validation Policies",  # editing - removed icon
                    "description": "Ensure resources conform to best practices and standards",
                    "icon": "shield-check"
                },
                {
                    "name": "mutation",
                    "display_name": "Mutation Policies",  # editing - removed icon
                    "description": "Automatically modify resources to apply standards",
                    "icon": "edit"
                },
                {
                    "name": "generation",
                    "display_name": "Generation Policies",  # editing - removed icon
                    "description": "Automatically create new resources when others are created",
                    "icon": "plus-circle"
                },
                {
                    "name": "cleanup",
                    "display_name": "Cleanup Policies",  # editing - removed icon
                    "description": "Automatically delete dependent or temporary resources",
                    "icon": "trash"
                },
                {
                    "name": "image_verification",
                    "display_name": "Image Verification Policies",  # editing - removed icon
                    "description": "Verify image signatures to ensure only trusted images are used",
                    "icon": "verified"
                },
                {
                    "name": "miscellaneous",
                    "display_name": "Miscellaneous Policies",  # editing - removed icon
                    "description": "Helpful or unique policies not falling into other categories",
                    "icon": "puzzle"
                },
                # NEW CATEGORIES
                {
                    "name": "file_based",
                    "display_name": "File-Based Security Policies",
                    "description": "Protect against unauthorized file changes and access",
                    "icon": "folder-lock"
                },
                {
                    "name": "process_based",
                    "display_name": "Process-Based Security Policies",
                    "description": "Control process execution and behavior",
                    "icon": "activity"
                },
                {
                    "name": "network_based",
                    "display_name": "Network-Based Security Policies",
                    "description": "Control network access and communications",
                    "icon": "wifi"
                },
                {
                    "name": "capabilities_permissions",
                    "display_name": "Capabilities & Permissions",
                    "description": "Manage service account tokens and permissions",
                    "icon": "lock-keyhole"
                }
            ]
            
            category_map = {}
            for cat_data in categories:
                category = db.query(PolicyCategoryModel).filter(
                    PolicyCategoryModel.name == cat_data["name"]
                ).first()
                
                if not category:
                    category = PolicyCategoryModel(**cat_data)
                    db.add(category)
                    db.commit()
                    db.refresh(category)
                
                category_map[cat_data["name"]] = category.id
            
            # Add policies for each category
            for category_name, policies in (self.policy_data or {}).items():

                category_id = category_map[category_name]
                
                for policy_data in policies:
                    existing_policy = db.query(PolicyModel).filter(
                        PolicyModel.policy_id == policy_data["policy_id"]
                    ).first()
                    
                    if not existing_policy:
                        policy = PolicyModel(
                            category_id=category_id,
                            **policy_data
                        )
                        db.add(policy)
            
            db.commit()
            logger.info("Database initialized with predefined policies")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            db.rollback()
            raise

    def get_policies_by_category(self, db: Session, category_name: str, 
                               page: int = 1, size: int = 10) -> Dict[str, Any]:
        """Get policies by category with pagination"""
        category = db.query(PolicyCategoryModel).filter(
            PolicyCategoryModel.name == category_name
        ).first()
        
        if not category:
            return {"policies": [], "total": 0, "page": page, "size": size, "total_pages": 0}
        
        query = db.query(PolicyModel).filter(PolicyModel.category_id == category.id)
        total = query.count()
        
        policies = query.offset((page - 1) * size).limit(size).all()
        
        policy_responses = []
        for policy in policies:
            policy_dict = {
                "id": policy.id,
                "policy_id": policy.policy_id,
                "name": policy.name,
                "description": policy.description,
                "purpose": policy.purpose,
                "severity": policy.severity,
                "yaml_content": policy.yaml_content,
                "metadata": policy.metadata,
                "tags": policy.tags,
                "is_active": policy.is_active,
                "category_id": policy.category_id,
                "created_at": policy.created_at,
                "updated_at": policy.updated_at or policy.created_at
            }
            policy_responses.append(PolicyResponse(**policy_dict))
        
        total_pages = (total + size - 1) // size
        
        return {
            "policies": policy_responses,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages
        }
    
    def get_policy_by_id(self, db: Session, policy_id: str) -> Optional[PolicyResponse]:
        """Get a specific policy by ID"""
        policy = db.query(PolicyModel).filter(PolicyModel.policy_id == policy_id).first()
        
        if not policy:
            return None
        
        policy_dict = {
            "id": policy.id,
            "policy_id": policy.policy_id,
            "name": policy.name,
            "description": policy.description,
            "purpose": policy.purpose,
            "severity": policy.severity,
            "yaml_content": policy.yaml_content,
            "policy_metadata": policy.policy_metadata,
            "tags": policy.tags,
            "is_active": policy.is_active,
            "category_id": policy.category_id,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at or policy.created_at
        }
        
        return PolicyResponse(**policy_dict)
    
    def search_policies(self, db: Session, query: str, category: Optional[str] = None,
                       severity: Optional[str] = None, page: int = 1, size: int = 10) -> Dict[str, Any]:
        """Search policies with filters"""
        db_query = db.query(PolicyModel)
        
        # Text search
        if query:
            db_query = db_query.filter(
                or_(
                    PolicyModel.name.ilike(f"%{query}%"),
                    PolicyModel.description.ilike(f"%{query}%"),
                    PolicyModel.purpose.ilike(f"%{query}%")
                )
            )
        
        # Category filter
        if category:
            category_obj = db.query(PolicyCategoryModel).filter(
                PolicyCategoryModel.name == category
            ).first()
            if category_obj:
                db_query = db_query.filter(PolicyModel.category_id == category_obj.id)
        
        # Severity filter
        if severity:
            db_query = db_query.filter(PolicyModel.severity == severity)
        
        total = db_query.count()
        policies = db_query.offset((page - 1) * size).limit(size).all()
        
        policy_responses = []
        for policy in policies:
            policy_dict = {
                "id": policy.id,
                "policy_id": policy.policy_id,
                "name": policy.name,
                "description": policy.description,
                "purpose": policy.purpose,
                "severity": policy.severity,
                "yaml_content": policy.yaml_content,
                "metadata": policy.metadata,
                "tags": policy.tags,
                "is_active": policy.is_active,
                "category_id": policy.category_id,
                "created_at": policy.created_at,
                "updated_at": policy.updated_at or policy.created_at
            }
            policy_responses.append(PolicyResponse(**policy_dict))
        
        total_pages = (total + size - 1) // size
        
        return {
            "policies": policy_responses,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages
        }
    
    def create_policy(self, db: Session, policy_data: PolicyCreate) -> PolicyResponse:
        """Create a new policy"""
        policy = PolicyModel(**policy_data.dict())
        db.add(policy)
        db.commit()
        db.refresh(policy)
        
        policy_dict = {
            "id": policy.id,
            "policy_id": policy.policy_id,
            "name": policy.name,
            "description": policy.description,
            "purpose": policy.purpose,
            "severity": policy.severity,
            "yaml_content": policy.yaml_content,
            "metadata": policy.metadata,
            "tags": policy.tags,
            "is_active": policy.is_active,
            "category_id": policy.category_id,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at or policy.created_at
        }
        
        return PolicyResponse(**policy_dict)
    
    def update_policy(self, db: Session, policy_id: str, policy_data: PolicyUpdate) -> Optional[PolicyResponse]:
        """Update an existing policy"""
        policy = db.query(PolicyModel).filter(PolicyModel.policy_id == policy_id).first()
        
        if not policy:
            return None
        
        update_data = policy_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(policy, field, value)
        
        db.commit()
        db.refresh(policy)
        
        policy_dict = {
            "id": policy.id,
            "policy_id": policy.policy_id,
            "name": policy.name,
            "description": policy.description,
            "purpose": policy.purpose,
            "severity": policy.severity,
            "yaml_content": policy.yaml_content,
            "metadata": policy.metadata,
            "tags": policy.tags,
            "is_active": policy.is_active,
            "category_id": policy.category_id,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at
        }
        
        return PolicyResponse(**policy_dict)
    
    def delete_policy(self, db: Session, policy_id: str) -> bool:
        """Delete a policy"""
        policy = db.query(PolicyModel).filter(PolicyModel.policy_id == policy_id).first()
        
        if not policy:
            return False
        
        db.delete(policy)
        db.commit()
        return True

    def _get_all_policy_data(self) -> Dict[str, List[Dict]]:
      """Get all predefined policy data organized by category"""
      return {
          "validation": self._get_validation_policies(),
          "mutation": self._get_mutation_policies(),
          "generation": self._get_generation_policies(),
          "cleanup": self._get_cleanup_policies(),
          "image_verification": self._get_image_verification_policies(),
          "miscellaneous": self._get_miscellaneous_policies(),
          # NEW CATEGORIES
          "file_based": self._get_file_based_policies(),
          "process_based": self._get_process_based_policies(),
          "network_based": self._get_network_based_policies(),
          "capabilities_permissions": self._get_capabilities_permissions_policies()
        } 


    # Add method to get policy for editing with editable fields
    def get_policy_for_editing(self, db: Session, policy_id: str) -> Optional[PolicyEditableResponse]:
        """Get policy with editable fields highlighted for editing"""
        policy = db.query(PolicyModel).filter(PolicyModel.policy_id == policy_id).first()
        
        if not policy:
            return None
        
        # Find editable fields in YAML content
        editable_fields = self._extract_editable_fields(policy.yaml_content)
        
        return PolicyEditableResponse(
            policy_id=policy.policy_id,
            name=policy.name,
            yaml_content=policy.yaml_content,
            editable_fields=editable_fields
        )

    def _extract_editable_fields(self, yaml_content: str) -> List[EditableField]:
        """Extract editable fields from YAML content based on ##editable comments"""
        editable_fields = []
        lines = yaml_content.split('\n')
        
        for i, line in enumerate(lines):
            if '##editable' in line:
                # Remove the comment and extract the field
                clean_line = line.replace('##editable', '').strip()
                
                # Extract field name and value
                if ':' in clean_line:
                    parts = clean_line.split(':', 1)
                    field_name = parts[0].strip()
                    current_value = parts[1].strip() if len(parts) > 1 else ""
                    
                    # Determine field type
                    field_type = "string"
                    if current_value.lower() in ['true', 'false']:
                        field_type = "boolean"
                    elif current_value.startswith('[') and current_value.endswith(']'):
                        field_type = "array"
                    elif current_value.isdigit():
                        field_type = "number"
                    
                    editable_fields.append(EditableField(
                        line_number=i + 1,
                        field_name=field_name,
                        current_value=current_value,
                        field_type=field_type
                    ))
        
        return editable_fields

    # Add method to save user edited policy
    def save_user_edited_policy(
        self, 
        db: Session, 
        user_id: int, 
        original_policy_id: int, 
        edited_yaml: str,
        edited_name: Optional[str] = None,
        edited_description: Optional[str] = None
    ) -> UserEditedPolicyResponse:
        """Save user's edited policy"""
        
        # Check if user already has an edited version of this policy
        existing_edited = db.query(UserEditedPolicyModel).filter(
            UserEditedPolicyModel.user_id == user_id,
            UserEditedPolicyModel.original_policy_id == original_policy_id,
            UserEditedPolicyModel.is_active == True
        ).first()
        
        if existing_edited:
            # Update existing edited policy
            existing_edited.edited_yaml_content = edited_yaml
            existing_edited.edited_name = edited_name
            existing_edited.edited_description = edited_description
            existing_edited.updated_at = datetime.now()
            db.commit()
            db.refresh(existing_edited)
            
            return UserEditedPolicyResponse(
                id=existing_edited.id,
                user_id=existing_edited.user_id,
                original_policy_id=existing_edited.original_policy_id,
                edited_yaml_content=existing_edited.edited_yaml_content,
                edited_name=existing_edited.edited_name,
                edited_description=existing_edited.edited_description,
                is_active=existing_edited.is_active,
                created_at=existing_edited.created_at,
                updated_at=existing_edited.updated_at
            )
        else:
            # Create new edited policy
            new_edited = UserEditedPolicyModel(
                user_id=user_id,
                original_policy_id=original_policy_id,
                edited_yaml_content=edited_yaml,
                edited_name=edited_name,
                edited_description=edited_description,
                is_active=True
            )
            
            db.add(new_edited)
            db.commit()
            db.refresh(new_edited)
            
            return UserEditedPolicyResponse(
                id=new_edited.id,
                user_id=new_edited.user_id,
                original_policy_id=new_edited.original_policy_id,
                edited_yaml_content=new_edited.edited_yaml_content,
                edited_name=new_edited.edited_name,
                edited_description=new_edited.edited_description,
                is_active=new_edited.is_active,
                created_at=new_edited.created_at,
                updated_at=new_edited.updated_at
            ) 

    def get_categories(self, db: Session) -> List[PolicyCategoryResponse]:
        """Get all policy categories with policy counts"""
        categories = db.query(PolicyCategoryModel).all()
        result = []
        
        for category in categories:
            policy_count = db.query(PolicyModel).filter(
                PolicyModel.category_id == category.id
            ).count()
            
            cat_dict = {
                "id": category.id,
                "name": category.name,
                "display_name": category.display_name,
                "description": category.description,
                "icon": category.icon,
                "created_at": category.created_at,
                "updated_at": category.updated_at or category.created_at,
                "policy_count": policy_count
            }
            result.append(PolicyCategoryResponse(**cat_dict))
        
        return result
    
    
    def _get_validation_policies(self) -> List[Dict]:
        """Get all validation policies data"""
        return [
            {
                "policy_id": "disallow-image",  # editing - updated policy_id
                "name": "Disallow any image",  # editing - updated name
                "description": "Prevent using any image",  # editing - updated description
                "purpose": "Prevent using any image",  # editing - updated purpose
                "severity": "high",
                "tags": ["security", "best-practices", "images"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-image
spec:
  validationFailureAction: Enforce
  rules:
    - name: validate-image
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Using the 'latest' tag for images is not allowed."  ##editable
        pattern:
          spec:
            containers:
              - image: "!*:latest" """,  # editing - updated YAML
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "restrict-hostpath",
                "name": "Restrict hostPath volumes",  # editing - updated name
                "description": "Disallow or restrict hostPath usage",  # editing - updated description
                "purpose": "Disallow or restrict hostPath usage",
                "severity": "high",
                "tags": ["security", "volumes"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-hostpath
spec:
  validationFailureAction: Enforce
  rules:
    - name: disallow-hostpath
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "hostPath volumes are not allowed."
        pattern:
          spec:
            volumes:
              - =(hostPath): "null" """,
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "disallow-privileged",
                "name": "Disallow privileged containers",  # editing - updated name
                "description": "Block pods running with privileged: true",
                "purpose": "Block pods running with privileged: true",
                "severity": "critical",
                "tags": ["security", "privileged"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-privileged
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Privileged mode is not allowed."
        pattern:
          spec:
            containers:
              - securityContext:
                  privileged: false""",
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "enforce-readonly-rootfs",
                "name": "Enforce read-only root filesystem",  # editing - updated name
                "description": "Enforce readOnlyRootFilesystem: true",  # editing - updated description
                "purpose": "Enforce readOnlyRootFilesystem: true",
                "severity": "medium",
                "tags": ["security", "filesystem"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: enforce-readonly-rootfs
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-readonly-rootfs
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Containers must run with readOnlyRootFilesystem set to true."
        pattern:
          spec:
            containers:
              - securityContext:
                  readOnlyRootFilesystem: true""",
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "restrict-capabilities",
                "name": "Restrict capabilities",  # editing - updated name
                "description": "Prevent containers from running with certain Linux capabilities",
                "purpose": "Prevent containers from running with certain Linux capabilities",
                "severity": "high",
                "tags": ["security", "capabilities"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-capabilities
spec:
  validationFailureAction: Enforce
  rules:
    - name: disallow-dangerous-capabilities
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Dangerous Linux capabilities are not allowed."
        pattern:
          spec:
            containers:
              - securityContext:
                  capabilities:
                    drop:
                      - ALL""",
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "enforce-non-root-user",
                "name": "Disallow root user",  # editing - updated name
                "description": "Prevent containers from running as root",  # editing - updated description
                "purpose": "Prevent containers from running as root",
                "severity": "high",
                "tags": ["security", "user"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: enforce-non-root-user
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-non-root-user
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Containers must not run as root."
        pattern:
          spec:
            containers:
              - securityContext:
                  runAsNonRoot: true""",
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "restrict-image-registries",
                "name": "Restrict image registries",  # editing - updated name
                "description": "Allow only approved registries",  # editing - updated description
                "purpose": "Allow only approved registries",
                "severity": "high",
                "tags": ["security", "images", "registries"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-image-registries
spec:
  validationFailureAction: Enforce
  rules:
    - name: only-allow-approved-registries
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Only approved image registries are allowed." ##editable
        anyPattern:
          - spec:
              containers:
                - image: "registry.mycorp.com/*"  ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "block-namespace",  # editing - updated policy_id
                "name": "Block any namespace",  # editing - updated name
                "description": "Prevent deployments to the any selected namespace",  # editing - updated description
                "purpose": "Prevent deployments to the any selected namespace",  # editing - updated purpose
                "severity": "medium",
                "tags": ["best-practices", "namespaces"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: block-namespace
spec:
  validationFailureAction: Enforce
  rules:
    - name: prevent-namespace
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Resources cannot be created in the default namespace."  ##editable
        pattern:
          metadata:
            namespace: "!default"  ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "enforce-resource-requests-limits",
                "name": "Enforce resource requests/limits",  # editing - updated name
                "description": "Require resources.requests and resources.limits",
                "purpose": "Require resources.requests and resources.limits",
                "severity": "medium",
                "tags": ["resources", "best-practices"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: enforce-resource-requests-limits
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-requests-and-limits
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "CPU and memory requests and limits are required."
        pattern:
          spec:
            containers:
              - resources:
                  requests:
                    memory: "*"  ##editable
                    cpu: "*"  ##editable
                  limits:
                    memory: "*"  ##editable
                    cpu: "*"  ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "validate-labels-annotations",
                "name": "Validate labels/annotations",  # editing - updated name
                "description": "Enforce presence/format of labels/annotations",  # editing - updated description
                "purpose": "Enforce presence/format of labels/annotations",
                "severity": "low",
                "tags": ["labels", "governance"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: validate-labels-annotations
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-org-labels
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Labels 'app' and 'team' must be set."  ##editable
        pattern:
          metadata:
            labels:
              app: "*"  ##editable
              team: "*"  ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "validation", "kubernetes_resources": ["Pod"]}
            }
        ]

    def _get_mutation_policies(self) -> List[Dict]:
        """Get all mutation policies data"""
        return [
            {
                "policy_id": "add-default-resource-limits",
                "name": "Add default resource limits",  # editing - updated name
                "description": "Inject CPU/memory limits if missing",
                "purpose": "Inject CPU/memory limits if missing",
                "severity": "medium",
                "tags": ["resources", "defaults"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-resource-limits
spec:
  rules:
    - name: set-default-limits
      match:
        resources:
          kinds:
            - Pod
      mutate:
        patchStrategicMerge:
          spec:
            containers:
              - name: "*" ##editable
                resources:
                  requests:
                    memory: "256Mi"  ##editable
                    cpu: "250m" ##editable
                  limits:
                    memory: "512Mi"  ##editable
                    cpu: "500m"  ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "mutation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "add-security-context",
                "name": "Add security context",  # editing - updated name
                "description": "Inject standard securityContext",  # editing - updated description
                "purpose": "Inject standard securityContext",
                "severity": "high",
                "tags": ["security", "defaults"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-security-context
spec:
  rules:
    - name: inject-security-context
      match:
        resources:
          kinds:
            - Pod
      mutate:
        patchStrategicMerge:
          spec:
            containers:
              - name: "*"
                securityContext:
                  runAsNonRoot: true
                  readOnlyRootFilesystem: true
                  allowPrivilegeEscalation: false""",
                "policy_metadata": {"type": "mutation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "add-labels-annotations",
                "name": "Add labels or annotations",  # editing - updated name
                "description": "Add organization-required metadata",
                "purpose": "Add organization-required metadata",
                "severity": "low",
                "tags": ["labels", "governance"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-labels-annotations
spec:
  rules:
    - name: inject-default-labels
      match:
        resources:
          kinds:
            - Pod
      mutate:
        patchStrategicMerge:
          metadata:
            labels:
              organization: "kubesage" ##editable
              environment: "production" ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "mutation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "enforce-image-pull-policy",
                "name": "Enforce imagePullPolicy",  # editing - updated name
                "description": "Set Always or IfNotPresent automatically",
                "purpose": "Set Always or IfNotPresent automatically",
                "severity": "low",
                "tags": ["images", "defaults"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: enforce-image-pull-policy
spec:
  rules:
    - name: set-image-pull-policy
      match:
        resources:
          kinds:
            - Pod
      mutate:
        patchStrategicMerge:
          spec:
            containers:
              - name: "*" ##editable
                imagePullPolicy: Always ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "mutation", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "add-default-network-policy",
                "name": "Add network policy",  # editing - updated name
                "description": "Automatically apply a default NetworkPolicy",
                "purpose": "Automatically apply a default NetworkPolicy",
                "severity": "medium",
                "tags": ["network", "security"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-network-policy
spec:
  generateExistingOnPolicyUpdate: true
  rules:
    - name: generate-network-policy
      match:
        resources:
          kinds:
            - Namespace
      generate:
        kind: NetworkPolicy
        name: default-deny
        namespace: "{{request.object.metadata.name}}"
        synchronize: true
        data:
          apiVersion: networking.k8s.io/v1
          kind: NetworkPolicy
          metadata:
            name: default-deny
          spec:
            podSelector: {}
            policyTypes:
              - Ingress
              - Egress""",
                "policy_metadata": {"type": "mutation", "kubernetes_resources": ["Namespace"]}
            },
            {
                "policy_id": "set-default-namespace",
                "name": "Set default namespace",  # editing - updated name
                "description": "Default to a specific namespace if none provided",
                "purpose": "Default to a specific namespace if none provided",
                "severity": "low",
                "tags": ["namespaces", "defaults"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: set-default-namespace
spec:
  rules:
    - name: set-namespace-if-undefined
      match:
        resources:
          kinds:
            - Pod
      preconditions:
        all:
          - key: "{{request.object.metadata.namespace}}"
            operator: Equals
            value: ""
      mutate:
        overlay:
          metadata:
            namespace: default""",
                "policy_metadata": {"type": "mutation", "kubernetes_resources": ["Pod"]}
            }
        ]

    def _get_generation_policies(self) -> List[Dict]:
        """Get all generation policies data"""
        return [
            {
                "policy_id": "generate-configmap-example",  # editing - updated policy_id
                "name": "Create ConfigMap/Secret",  # editing - updated name
                "description": "Generate a ConfigMap when a resource is created",
                "purpose": "Generate a ConfigMap when a resource is created",
                "severity": "low",
                "tags": ["generation", "configmap"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-configmap-example
spec:
  rules:
    - name: create-configmap
      match:
        resources:
          kinds:
            - Namespace
      generate:
        kind: ConfigMap
        name: default-config
        namespace: "{{request.object.metadata.name}}"
        data:
          data:
            key: "value"  ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "generation", "kubernetes_resources": ["Namespace"]}  # editing - updated metadata key
            },
            {
                "policy_id": "generate-rolebinding",
                "name": "Create RBAC RoleBinding",  # editing - updated name
                "description": "Auto-create RBAC bindings with namespace",
                "purpose": "Auto-create RBAC bindings with namespace",
                "severity": "medium",
                "tags": ["rbac", "security"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-rolebinding
spec:
  rules:
    - name: create-rolebinding
      match:
        resources:
          kinds:
            - Namespace
      generate:
        kind: RoleBinding
        name: view-binding
        namespace: "{{request.object.metadata.name}}"
        data:
          metadata:
            labels:
              generated-by: kyverno
          roleRef:
            kind: ClusterRole
            name: view
            apiGroup: rbac.authorization.k8s.io
          subjects:
            - kind: User
              name: dev-user ##editable
              apiGroup: rbac.authorization.k8s.io""",  # editing - updated YAML
                "policy_metadata": {"type": "generation", "kubernetes_resources": ["Namespace"]}  # editing - updated metadata key
            },
            {
                "policy_id": "generate-network-policy",
                "name": "Generate NetworkPolicy",  # editing - updated name
                "description": "Ensure every namespace has a default NetworkPolicy",
                "purpose": "Ensure every namespace has a default NetworkPolicy",
                "severity": "high",
                "tags": ["network", "security"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-network-policy
spec:
  rules:
    - name: default-deny-all
      match:
        resources:
          kinds:
            - Namespace
      generate:
        kind: NetworkPolicy
        name: default-deny
        namespace: "{{request.object.metadata.name}}"
        data:
          spec:
            podSelector: {}
            policyTypes:
              - Ingress
              - Egress""",
                "policy_metadata": {"type": "generation", "kubernetes_resources": ["Namespace"]}  # editing - updated metadata key
            }
        ]

    def _get_cleanup_policies(self) -> List[Dict]:
        """Get all cleanup policies data"""
        return [
            {
                "policy_id": "cleanup-resources",  # editing - updated policy_id
                "name": "Cleanup test resources",  # editing - updated name
                "description": "Auto-delete test pods or temporary resources",
                "purpose": "Auto-delete test pods or temporary resources",
                "severity": "medium",
                "tags": ["cleanup", "testing"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: cleanup-resources
spec:
  rules:
    - name: cleanup-pods
      match:
        any:
          - resources:
              kinds:
                - Pod
              labels:
                app: test ##editable
      preconditions:
        all:
          - key: "{{request.operation}}"
            operator: Equals
            value: CREATE
      mutate:
        patchStrategicMerge:
          metadata:
            annotations:
              cleanup.kyverno.io/ttl: "1h" """,  # editing - updated YAML
                "policy_metadata": {"type": "cleanup", "kubernetes_resources": ["Pod"]}  # editing - updated metadata key
            },
            {
                "policy_id": "cleanup-orphaned-pvcs",
                "name": "Remove orphaned resources",  # editing - updated name
                "description": "Clean up resources no longer in use",
                "purpose": "Clean up resources no longer in use",
                "severity": "medium",
                "tags": ["cleanup", "storage"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: cleanup-orphaned-pvcs
spec:
  rules:
    - name: mark-unused-pvcs
      match:
        resources:
          kinds:
            - PersistentVolumeClaim
      preconditions:
        all:
          - key: "{{request.operation}}"
            operator: Equals
            value: CREATE
      mutate:
        patchStrategicMerge:
          metadata:
            annotations:
              cleanup.kyverno.io/ttl: "24h" """,
                "policy_metadata": {"type": "cleanup", "kubernetes_resources": ["PersistentVolumeClaim"]}  # editing - updated metadata key
            },
            {
                "policy_id": "cleanup-expired-secrets",
                "name": "Auto-delete expired Secrets",  # editing - updated name
                "description": "Clean up secrets after a TTL",
                "purpose": "Clean up secrets after a TTL",
                "severity": "low",
                "tags": ["cleanup", "secrets"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: cleanup-expired-secrets
spec:
  rules:
    - name: mark-short-lived-secrets
      match:
        any:
          - resources:
              kinds:
                - Secret
              annotations:
                type: ephemeral
      mutate:
        patchStrategicMerge:
          metadata:
            annotations:
              cleanup.kyverno.io/ttl: "6h" """,
                "policy_metadata": {"type": "cleanup", "kubernetes_resources": ["Secret"]}  # editing - updated metadata key
            }
        ]

    def _get_image_verification_policies(self) -> List[Dict]:
        """Get all image verification policies data"""
        return [
            {
                "policy_id": "verify-image-signature-cosign",
                "name": "Verify image signature (cosign)",  # editing - updated name
                "description": "Only allow signed images",
                "purpose": "Only allow signed images",
                "severity": "critical",
                "tags": ["security", "images", "cosign"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature-cosign
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: require-signed-images-cosign
      match:
        resources:
          kinds:
            - Pod
      verifyImages:
        - image: "registry.mycorp.com/*" ##editable
          key: https://mykeyserver.com/cosign.pub  ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "image_verification", "kubernetes_resources": ["Pod"]}  # editing - updated metadata key
            },
            {
                "policy_id": "enforce-keyless-signing",
                "name": "Enforce keyless signing",  # editing - updated name
                "description": "Use keyless verification (Sigstore)",
                "purpose": "Use keyless verification (Sigstore)",
                "severity": "critical",
                "tags": ["security", "images", "sigstore"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: enforce-keyless-signing
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: require-keyless-signed-images
      match:
        resources:
          kinds:
            - Pod
      verifyImages:
        - image: "ghcr.io/myorg/*" ##editable
          issuer: https://token.actions.githubusercontent.com  ##editable
          subject: "myorg/*" ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "image_verification", "kubernetes_resources": ["Pod"]}  # editing - updated metadata key
            },
            {
                "policy_id": "disallow-unsigned-images",
                "name": "Disallow unsigned images",  # editing - updated name
                "description": "Block any unsigned container image",
                "purpose": "Block any unsigned container image",
                "severity": "critical",
                "tags": ["security", "images"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-unsigned-images
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: block-unsigned-images
      match:
        resources:
          kinds:
            - Pod
      verifyImages:
        - image: "docker.io/myorg/*" ##editable
          key: https://mykeyserver.com/cosign.pub  ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "image_verification", "kubernetes_resources": ["Pod"]}  # editing - updated metadata key
            }
        ]

    def _get_miscellaneous_policies(self) -> List[Dict]:
        """Get all miscellaneous policies data"""
        return [
            {
                "policy_id": "block-any-deployments",  # editing - updated policy_id
                "name": "Block deployment in any namespace",  # editing - updated name
                "description": "Protect critical namespaces",
                "purpose": "Protect critical namespaces",
                "severity": "high",
                "tags": ["security", "namespaces"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: block-any-deployments
spec:
  validationFailureAction: Enforce
  rules:
    - name: deny-deployment  ##editable
      match:
        resources:
          kinds:
            - Pod
      validate:
        message: "Deployments in  namespace are not allowed."
        pattern:
          metadata:
            namespace: "!kube-system" ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "miscellaneous", "kubernetes_resources": ["Pod"]}  # editing - updated metadata key
            },
            {
                "policy_id": "require-pdb",
                "name": "Require PodDisruptionBudget",  # editing - updated name
                "description": "Enforce application availability rules",
                "purpose": "Enforce application availability rules",
                "severity": "medium",
                "tags": ["availability", "best-practices"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-pdb
spec:
  validationFailureAction: Audit
  rules:
    - name: require-pdb-for-deployments
      match:
        resources:
          kinds:
            - Deployment
      validate:
        message: "A PodDisruptionBudget must be defined for this deployment."
        deny:
          conditions:
            all:
              - key: "{{ request.object.metadata.name }}"
                operator: NotIn
                value: "{{ kube.pdb[*].metadata.ownerReferences[?(@.name==request.object.metadata.name)] }}" """,
                "policy_metadata": {"type": "miscellaneous", "kubernetes_resources": ["Deployment"]}  # editing - updated metadata key
            },
            {
                "policy_id": "ingress-name-format",
                "name": "Enforce ingress naming conventions",  # editing - updated name
                "description": "Require ingress names follow format",
                "purpose": "Require ingress names follow format",
                "severity": "low",
                "tags": ["naming", "best-practices"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: ingress-name-format
spec:
  validationFailureAction: Enforce
  rules:
    - name: enforce-ingress-name-format
      match:
        resources:
          kinds:
            - Ingress
      validate:
        message: "Ingress name must start with 'ing-' and follow naming convention." ##editable
        pattern:
          metadata:
            name: "ing-*" ##editable""",  # editing - updated YAML
                "policy_metadata": {"type": "miscellaneous", "kubernetes_resources": ["Ingress"]}  # editing - updated metadata key
            },
            {
                "policy_id": "validate-crd-k8s-version",
                "name": "Validate Kubernetes version in CRDs",  # editing - updated name
                "description": "Ensure CRDs target supported API versions",
                "purpose": "Ensure CRDs target supported API versions",
                "severity": "medium",
                "tags": ["crd", "api-version"],
                "yaml_content": """apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: validate-crd-k8s-version
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-crd-api-version
      match:
        resources:
          kinds:
            - CustomResourceDefinition
      validate:
        message: "Only apiextensions.k8s.io/v1 CRDs are supported."
        pattern:
          apiVersion: "apiextensions.k8s.io/v1" """,
                "policy_metadata": {"type": "miscellaneous", "kubernetes_resources": ["CustomResourceDefinition"]}  # editing - updated metadata key
            }
        ]

    # Add new policy category methods
    def _get_file_based_policies(self) -> List[Dict]:
        """Get all file-based security policies"""
        return [
            {
                "policy_id": "fim-file-integrity-monitoring",
                "name": "FIM (File Integrity Monitoring)",
                "description": "Protect against unauthorized file changes",
                "purpose": "Detect and prevent compromise to file integrity",
                "severity": "critical",
                "tags": ["security", "file-integrity", "monitoring", "NIST", "MITRE"],
                "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: harden-mysql-file-integrity-monitoring
  namespace: default
spec:
  action: Block ##editable
  file:
    matchDirectories:
    - dir: /sbin/
      readOnly: true
      recursive: true
    - dir: /usr/bin/
      readOnly: true
      recursive: true
    - dir: /usr/lib/
      readOnly: true
      recursive: true
    - dir: /usr/sbin/
      readOnly: true
      recursive: true
    - dir: /bin/
      readOnly: true
      recursive: true
    - dir: /boot/
      readOnly: true
      recursive: true
  message: Detected and prevented compromise to File integrity
  selector:
    matchLabels:
      app: nginx ##editable
  severity: 1
  tags:
  - NIST
  - NIST_800-53_AU-2
  - NIST_800-53_SI-4
  - MITRE
  - MITRE_T1036_masquerading
  - MITRE_T1565_data_manipulation""",
            "policy_metadata": {"type": "file_based", "kubernetes_resources": ["Pod"]}
        },
        {
            "policy_id": "trusted-certs-bundle",
            "name": "Trusted certs bundle",
            "description": "Protect write access to system root certificates",
            "purpose": "Protect write access to the trusted root certificates bundle",
            "severity": "critical",
            "tags": ["security", "certificates", "MITRE", "credentials"],
            "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: harden-mysql-trusted-cert-mod
  namespace: default ##editable
spec:
  action: Block ##editable
  file:
    matchDirectories:
    - dir: /etc/ssl/
      readOnly: true
      recursive: true
    - dir: /etc/pki/
      readOnly: true
      recursive: true
    - dir: /usr/local/share/ca-certificates/
      readOnly: true
      recursive: true
  message: Credentials modification denied
  selector:
    matchLabels:
      app: mysql ##editable
  severity: 1
  tags:
  - MITRE
  - MITRE_T1552_unsecured_credentials
  - FGT1555
  - FIGHT""",
            "policy_metadata": {"type": "file_based", "kubernetes_resources": ["Pod"]}
        },
        {
            "policy_id": "file-copy-prevention",
            "name": "File Copy",
            "description": "Prevent file copying using cp, rsync, etc.",
            "purpose": "Prevent file copy using standard utilities",
            "severity": "high",
            "tags": ["security", "file-copy", "MITRE", "lateral-movement"],
            "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: harden-wordpress-remote-file-copy
  namespace: default ##editable
spec:
  action: Block ##editable
  message: Alert! remote file copy tools execution prevented.
  process:
    matchPaths:
    - path: /usr/bin/rsync
    - path: /bin/rsync
    - path: /usr/bin/scp
    - path: /bin/scp
    - path: /usr/bin/cp ##editable
    - path: /bin/cp ##editable
  selector:
    matchLabels:
      app: wordpress ##editable
  severity: 5
  tags:
  - MITRE
  - MITRE_TA0008_lateral_movement
  - MITRE_TA0010_exfiltration
  - MITRE_TA0006_credential_access
  - MITRE_T1552_unsecured_credentials
  - NIST_800-53_SI-4(18)
  - NIST
  - NIST_800-53
  - NIST_800-53_SC-4""",
            "policy_metadata": {"type": "file_based", "kubernetes_resources": ["Pod"]}
        },
        {
            "policy_id": "audit-etc-access",
            "name": "Audit access",
            "description": "Monitor configuration /etc changes",
            "purpose": "Audit access to CONFIG FILE /etc",
            "severity": "medium",
            "tags": ["security", "audit", "configuration"],
            "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: audit-etc-nginx-access
  namespace: default ##editable
spec:
  selector:
    matchLabels:
     app: nginx ##editable
  file:
    matchDirectories:
    - dir: /etc/
      recursive: true
  action: Audit ##editable""",
            "policy_metadata": {"type": "file_based", "kubernetes_resources": ["Pod"]}
        }
    ]


    def _get_process_based_policies(self) -> List[Dict]:
        """Get all process-based security policies"""
        return [
            {
                "policy_id": "deny-package-mgmt-tools",
                "name": "Packaging tools",
                "description": "Deny execution of apt, yum, apk, etc.",
                "purpose": "Deny execution of package management tools (apt/apt-get)",
                "severity": "high",
                "tags": ["security", "package-management", "process-control"],
                "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: block-pkg-mgmt-tools-exec
  namespace: default ##editable
spec:
  selector:
    matchLabels:
      app: nginx ##editable
  process:
    matchPaths:
    - path: /usr/bin/apt
    - path: /usr/bin/apt-get
    - path: /usr/bin/yum ##editable
    - path: /usr/bin/apk ##editable
  action: Block ##editable""",
                "policy_metadata": {"type": "process_based", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "tmp-noexec",
                "name": "/tmp/ noexec",
                "description": "Block execution of binaries/scripts from /tmp",
                "purpose": "Do not allow execution of binaries from /tmp/ folder",
                "severity": "high",
                "tags": ["security", "tmp-execution", "CIS"],
                "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: ksp-block-exec-inside-tmp
  namespace: default ##editable
spec:
  tags:
  - CIS
  - CIS-control-1.1.5
  message: Alert! Execution attempted inside tmp folder
  selector:
    matchLabels:
      app: wordpress ##editable
  process:
    matchDirectories:
    - dir: /tmp/
      recursive: true
  action: Block ##editable""",
                "policy_metadata": {"type": "process_based", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "zero-trust-least-permissive",
                "name": "Zero Trust",
                "description": "Least Permissive Policy",
                "purpose": "Zero Trust Least Permissive Policy",
                "severity": "critical",
                "tags": ["security", "zero-trust", "least-privilege"],
                "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: only-allow-nginx-exec
  namespace: default ##editable
spec:
  selector:
    matchLabels:
      app: nginx ##editable
  file:
    matchDirectories:
    - dir: /
      recursive: true
  process:
    matchPaths:
    - path: /usr/sbin/nginx ##editable
    - path: /bin/bash ##editable
  action: Allow ##editable""",
                "policy_metadata": {"type": "process_based", "kubernetes_resources": ["Pod"]}
            }
        ]

    def _get_network_based_policies(self) -> List[Dict]:
        """Get all network-based security policies"""
        return [
            {
                "policy_id": "network-access-control",
                "name": "Network Access",
                "description": "Restrict which processes can initiate network connections",
                "purpose": "Process based network access control",
                "severity": "high",
                "tags": ["security", "network", "access-control"],
                "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: restrict-proccess
  namespace: default ##editable
spec:
  severity: 4
  selector:
    matchLabels:
      app: nginx ##editable
  network:
    matchProtocols:
    - protocol: tcp
      fromSource:
      - path: /usr/bin/wget
    - protocol: udp
      fromSource:
      - path: /usr/bin/wget
  action: Allow ##editable""",
                "policy_metadata": {"type": "network_based", "kubernetes_resources": ["Pod"]}
            },
            {
                "policy_id": "icmp-control",
                "name": "ICMP control",
                "description": "Block usage of ping, traceroute for scanning/discovery",
                "purpose": "Restrict scanning tools",
                "severity": "medium",
                "tags": ["security", "network", "icmp", "scanning"],
                "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: restrict-scanning-tools
  namespace: default ##editable
spec:
  severity: 4
  selector:
    matchLabels:
      app: nginx ##editable
  network:
    matchProtocols:
    - protocol: icmp
      fromSource:
      - path: /usr/bin/ping
    - protocol: udp
      fromSource:
      - path: /usr/bin/ping
  action: Allow ##editable
  message: Scanning tool has been detected""",
                "policy_metadata": {"type": "network_based", "kubernetes_resources": ["Pod"]}
            }
        ]

    def _get_capabilities_permissions_policies(self) -> List[Dict]:
        """Get all capabilities and permissions policies"""
        return [
            {
                "policy_id": "service-account-token-access",
                "name": "Service Account token",
                "description": "Prevent pods/processes from accessing the mounted service account token",
                "purpose": "Deny access to service account token",
                "severity": "high",
                "tags": ["security", "service-account", "token", "permissions"],
                "yaml_content": """apiVersion: security.kubearmor.com/v1
kind: KubeArmorPolicy
metadata:
  name: block-service-access-token-access
  namespace: default ##editable
spec:
  selector:
    matchLabels:
      app: nginx ##editable
  file:
    matchDirectories:
    - dir: /run/secrets/kubernetes.io/serviceaccount/
      recursive: true
  action: Block ##editable""",
                "policy_metadata": {"type": "capabilities_permissions", "kubernetes_resources": ["Pod"]}
            }
        ]



    def __init__(self):
      try:
          self.policy_data = self._get_all_policy_data()
      except Exception as e:
          logger.error(f"Failed to initialize policy data: {e}")
          self.policy_data = {}
      
      # Get kubeconfig service URL from environment or use default
      self.kubeconfig_service_url = os.getenv("KUBECONFIG_SERVICE_URL", "https://10.0.2.29:8002")
        

    async def get_cluster_info(self, cluster_name: str, user_token: str) -> Optional[Dict]:
        """Get cluster information from kubeconfig service"""
        try:
            # Call kubeconfig service to get cluster credentials
            async with httpx.AsyncClient(verify=False) as client:  # Disable SSL verification
                response = await client.get(
                    f"{self.kubeconfig_service_url}/kubeconfig/cluster/{cluster_name}/credentials",
                    headers={"Authorization": f"Bearer {user_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("cluster"):
                        return data["cluster"]
                    
                logger.error(f"Failed to get cluster info: {data}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting cluster info: {e}")
            return None

    def apply_kyverno_policy(self, api_server_url: str, token: str, policy_yaml: str, namespace: str = "default"):
        """
        Apply a Kyverno policy to a remote Kubernetes cluster using its API URL and Bearer Token.
        """
        # Step 1: Set up dynamic Kubernetes API client
        configuration = client.Configuration()
        configuration.host = api_server_url
        configuration.verify_ssl = False  # Set to True if using valid HTTPS
        configuration.api_key = {"authorization": f"Bearer {token}"}
        api_client = client.ApiClient(configuration)
        custom_api = client.CustomObjectsApi(api_client)
        
        # Step 2: Parse YAML into Python dict
        try:
            policy = yaml.safe_load(policy_yaml)
        except yaml.YAMLError as e:
            raise Exception(f"Invalid YAML: {e}")
        
        # Step 3: Extract kind and apply accordingly
        kind = policy.get("kind")
        if not kind:
            raise Exception("Policy YAML must contain a 'kind' field")
        
        group = "kyverno.io"
        version = "v1"
        
        # Apply based on policy kind
        if kind == "ClusterPolicy":
            # Remove namespace from metadata if present
            if "namespace" in policy.get("metadata", {}):
                del policy["metadata"]["namespace"]
        
            plural = "clusterpolicies"
            return custom_api.create_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
                body=policy
            )
        elif kind == "Policy":
            plural = "policies"
            # Use the namespace from policy metadata or the provided namespace
            policy_namespace = policy.get("metadata", {}).get("namespace", namespace)
            return custom_api.create_namespaced_custom_object(
                group=group,
                version=version,
                namespace=policy_namespace,
                plural=plural,
                body=policy
            )
        else:
            raise Exception(f"Unsupported policy kind: {kind}")

    async def apply_policy_to_cluster(
        self, 
        db: Session, 
        request: PolicyApplicationRequest, 
        user_id: int,
        user_token: str
    ) -> PolicyApplicationResponse:
        """Apply a policy to a specific cluster"""
        
        # 1. Get cluster information using user token
        cluster_info = await self.get_cluster_info(request.cluster_name, user_token)
        if not cluster_info:
            raise Exception(f"Cluster '{request.cluster_name}' not found or not accessible")
        
        # 2. Get policy from database
        policy = db.query(PolicyModel).filter(
            PolicyModel.policy_id == request.policy_id
        ).first()
        
        if not policy:
            raise Exception(f"Policy '{request.policy_id}' not found")
        
        # 3. Check if policy already exists (only for non-edited policies)
        yaml_to_apply = policy.yaml_content
        is_edited_policy = False
        
        if request.edited_yaml and request.edited_yaml.strip() != policy.yaml_content.strip():
            yaml_to_apply = request.edited_yaml
            is_edited_policy = True
        else:
            # Check if same policy already applied (only for non-edited policies)
            existing_application = db.query(PolicyApplicationModel).filter(
                PolicyApplicationModel.user_id == user_id,
                PolicyApplicationModel.cluster_name == request.cluster_name,
                PolicyApplicationModel.policy_id == policy.id,
                PolicyApplicationModel.status == ApplicationStatus.APPLIED,
                PolicyApplicationModel.is_edited_policy == False
            ).first()
            
            if existing_application:
                raise Exception(f"Policy '{policy.name}' is already applied to cluster '{request.cluster_name}'. Please edit the policy to apply a modified version.")
        
        # Parse YAML to get the actual namespace
        parsed_policy = yaml.safe_load(yaml_to_apply)
        actual_namespace = parsed_policy.get("metadata", {}).get("namespace", "default")

        # 4. Handle edited policy saving
        user_edited_policy_id = None
        if is_edited_policy and request.save_edited_policy:
            try:
                edited_policy = self.save_user_edited_policy(
                    db=db,
                    user_id=user_id,
                    original_policy_id=policy.id,
                    edited_yaml=request.edited_yaml
                )
                user_edited_policy_id = edited_policy.id
                logger.info(f"Saved edited policy for user {user_id}, policy {request.policy_id}")
            except Exception as e:
                logger.warning(f"Failed to save edited policy: {e}")

        # 5. Create application record
        application = PolicyApplicationModel(
            user_id=user_id,
            cluster_id=cluster_info["cluster_id"],
            cluster_name=request.cluster_name,
            policy_id=policy.id,
            user_edited_policy_id=user_edited_policy_id,
            is_edited_policy=is_edited_policy,
            status=ApplicationStatus.PENDING,
            kubernetes_namespace=actual_namespace,
            applied_yaml=yaml_to_apply,
            original_yaml=policy.yaml_content
        )
        
        db.add(application)
        db.commit()
        db.refresh(application)
        
        try:
            # 6. Update status to applying
            application.status = ApplicationStatus.APPLYING
            db.commit()
            
            # 7. Determine policy type and apply accordingly
            parsed_policy = yaml.safe_load(yaml_to_apply)
            policy_kind = parsed_policy.get("kind", "")

            if policy_kind == "KubeArmorPolicy":
                result = self.apply_kubearmor_policy(
                    api_server_url=cluster_info["server_url"],
                    token=cluster_info["token"],
                    policy_yaml=yaml_to_apply,
                    namespace=request.kubernetes_namespace or "default"
                )
            elif policy_kind in ["ClusterPolicy", "Policy"]:
                result = self.apply_kyverno_policy(
                    api_server_url=cluster_info["server_url"],
                    token=cluster_info["token"],
                    policy_yaml=yaml_to_apply,
                    namespace=request.kubernetes_namespace or "default"
                )
            else:
                raise Exception(f"Unsupported policy kind: {policy_kind}")

            # 8. Extract resource name from result
            resource_name = result.get("metadata", {}).get("name", "unknown")
            
            # 9. Update application record with success
            application.status = ApplicationStatus.APPLIED
            application.applied_at = datetime.now()
            application.kubernetes_name = resource_name
            
            if is_edited_policy:
                application.application_log = f"Successfully applied edited policy to cluster {request.cluster_name}"
            else:
                application.application_log = f"Successfully applied policy to cluster {request.cluster_name}"
            
            db.commit()
            
            logger.info(f"Successfully applied {'edited ' if is_edited_policy else ''}policy {request.policy_id} to cluster {request.cluster_name}")
            
        except Exception as e:
            # 10. Update application record with failure
            application.status = ApplicationStatus.FAILED
            application.error_message = str(e)
            application.application_log = f"Failed to apply policy: {str(e)}"
            
            db.commit()
            
            logger.error(f"Failed to apply policy {request.policy_id} to cluster {request.cluster_name}: {e}")
            raise
        
        # 11. Return response
        return self._convert_application_to_response(db, application)

    # Add method to apply KubeArmor policies (similar to Kyverno but for KubeArmor)
    def apply_kubearmor_policy(self, api_server_url: str, token: str, policy_yaml: str, namespace: str = "default"):
        """
        Apply a KubeArmor policy to a remote Kubernetes cluster using its API URL and Bearer Token.
        """
        # Step 1: Set up dynamic Kubernetes API client
        configuration = client.Configuration()
        configuration.host = api_server_url
        configuration.verify_ssl = False  # Set to True if using valid HTTPS
        configuration.api_key = {"authorization": f"Bearer {token}"}
        api_client = client.ApiClient(configuration)
        custom_api = client.CustomObjectsApi(api_client)
        
        # Step 2: Parse YAML into Python dict
        try:
            policy = yaml.safe_load(policy_yaml)
        except yaml.YAMLError as e:
            raise Exception(f"Invalid YAML: {e}")
        
        # Step 3: Extract kind and apply accordingly
        kind = policy.get("kind")
        if not kind:
            raise Exception("Policy YAML must contain a 'kind' field")
        
        group = "security.kubearmor.com"
        version = "v1"
        
        # Apply KubeArmor policy
        if kind == "KubeArmorPolicy":
            plural = "kubearmorpolicies"
            # Use the namespace from policy metadata or the provided namespace
            policy_namespace = policy.get("metadata", {}).get("namespace", namespace)
            return custom_api.create_namespaced_custom_object(
                group=group,
                version=version,
                namespace=policy_namespace,
                plural=plural,
                body=policy
            )
        else:
            raise Exception(f"Unsupported policy kind: {kind}")



        
        def get_policy_applications(
            self, 
            db: Session, 
            user_id: int, 
            cluster_name: Optional[str] = None,
            status: Optional[str] = None,
            page: int = 1, 
            size: int = 10
        ) -> PolicyApplicationListResponse:
            """Get policy applications for a user with cluster filtering"""
            
            try:
                # Build query with proper joins
                query = db.query(PolicyApplicationModel).outerjoin(
                    PolicyModel, PolicyApplicationModel.policy_id == PolicyModel.id
                ).filter(
                    PolicyApplicationModel.user_id == user_id
                )
                
                # Apply cluster filter if provided
                if cluster_name:
                    query = query.filter(PolicyApplicationModel.cluster_name == cluster_name)
                    logger.info(f"Filtering applications for cluster: {cluster_name}")
                
                # Apply status filter if provided
                if status:
                    try:
                        status_enum = ApplicationStatus(status.lower())
                        query = query.filter(PolicyApplicationModel.status == status_enum)
                        logger.info(f"Filtering applications by status: {status}")
                    except ValueError:
                        logger.warning(f"Invalid status filter: {status}")
                        return PolicyApplicationListResponse(
                            applications=[],
                            total=0,
                            page=page,
                            size=size,
                            total_pages=0
                        )
                
                total = query.count()
                applications = query.offset((page - 1) * size).limit(size).all()
                
                logger.info(f"Found {total} total applications, returning {len(applications)} for page {page}")
                
                application_responses = []
                for app in applications:
                    try:
                        response = self._convert_application_to_response(db, app)
                        application_responses.append(response)
                    except Exception as e:
                        logger.error(f"Error converting application {app.id} to response: {e}")
                        continue
                
                total_pages = (total + size - 1) // size if total > 0 else 0
                
                return PolicyApplicationListResponse(
                    applications=application_responses,
                    total=len(application_responses),
                    page=page,
                    size=size,
                    total_pages=total_pages
                )
                
            except Exception as e:
                logger.error(f"Error in get_policy_applications: {e}")
                return PolicyApplicationListResponse(
                    applications=[],
                    total=0,
                    page=page,
                    size=size,
                    total_pages=0
                )

    async def remove_policy_from_cluster(
        self,
        db: Session,
        application_id: int,
        user_id: int,
        user_token: str
    ) -> PolicyApplicationResponse:
        """Remove a policy from cluster and database"""
        
        application = db.query(PolicyApplicationModel).filter(
            and_(
                PolicyApplicationModel.id == application_id,
                PolicyApplicationModel.user_id == user_id
            )
        ).first()
        
        if not application:
            raise Exception("Policy application not found")
        
        if application.status != ApplicationStatus.APPLIED:
            raise Exception("Policy is not currently applied")
        
        try:
            # Get cluster information
            cluster_info = await self.get_cluster_info(application.cluster_name, user_token)
            if not cluster_info:
                raise Exception(f"Cluster '{application.cluster_name}' not found")
            
            # Set up Kubernetes client
            configuration = client.Configuration()
            configuration.host = cluster_info["server_url"]
            configuration.verify_ssl = False
            configuration.api_key = {"authorization": f"Bearer {cluster_info['token']}"}
            api_client = client.ApiClient(configuration)
            custom_api = client.CustomObjectsApi(api_client)
            
            # Parse YAML to get resource details
            policy = yaml.safe_load(application.applied_yaml)
            kind = policy.get("kind")
            resource_name = policy.get("metadata", {}).get("name", "")

            # Get the actual namespace from the YAML metadata, not from the database field
            yaml_namespace = policy.get("metadata", {}).get("namespace", "default")
            
            # Remove the resource based on policy type
            if kind == "ClusterPolicy":
                custom_api.delete_cluster_custom_object(
                    group="kyverno.io",
                    version="v1",
                    plural="clusterpolicies",
                    name=resource_name
                )
                logger.info(f"Removing Kyverno ClusterPolicy: {resource_name}")
            elif kind == "Policy":
                # Use the namespace from YAML or fallback to database field
                namespace_to_use = yaml_namespace if yaml_namespace != "default" else application.kubernetes_namespace
                custom_api.delete_namespaced_custom_object(
                    group="kyverno.io",
                    version="v1",
                    namespace=namespace_to_use,
                    plural="policies",
                    name=resource_name
                )
                logger.info(f"Removing Kyverno Policy: {resource_name} from namespace: {namespace_to_use}")
                
            elif kind == "KubeArmorPolicy":
                # For KubeArmor policies, always use the namespace from the YAML metadata
                namespace_to_use = yaml_namespace
                logger.info(f"Attempting to remove KubeArmorPolicy: {resource_name} from namespace: {namespace_to_use}")
                
                custom_api.delete_namespaced_custom_object(
                    group="security.kubearmor.com",
                    version="v1",
                    namespace=namespace_to_use,
                    plural="kubearmorpolicies",
                    name=resource_name
                )
                logger.info(f"Successfully removed KubeArmorPolicy: {resource_name} from namespace: {namespace_to_use}")
            else:
                raise Exception(f"Unsupported policy kind for removal: {kind}")
            
            # Remove the application record from database
            db.delete(application)
            db.commit()
            
            logger.info(f"Successfully removed {kind} policy from cluster {application.cluster_name} and database")
            
            # Return a success response since the record is deleted
            return PolicyApplicationResponse(
                id=application.id,
                user_id=application.user_id,
                cluster_id=application.cluster_id,
                cluster_name=application.cluster_name,
                policy_id=application.policy_id,
                policy=None,
                status=ApplicationStatus.REMOVED,
                applied_yaml=application.applied_yaml,
                application_log=f"Removed {kind} policy from cluster {application.cluster_name} and database",
                error_message=None,
                kubernetes_name=application.kubernetes_name,
                kubernetes_namespace=application.kubernetes_namespace,
                is_edited_policy=application.is_edited_policy,
                created_at=application.created_at,
                applied_at=application.applied_at,
                updated_at=datetime.now()
            )
            
        except Exception as e:
            # Update application status to failed removal
            application.status = ApplicationStatus.FAILED
            application.error_message = f"Failed to remove policy: {str(e)}"
            application.application_log += f"\nFailed to remove {kind} policy from cluster {application.cluster_name}"
            application.updated_at = datetime.now()
            db.commit()
            
            logger.error(f"Failed to remove policy from cluster: {e}")
            raise


    def remove_failed_policy_by_id(self, db: Session, application_id: int, user_id: int) -> Dict[str, Any]:
        """Remove a specific failed policy application from database"""
        try:
            # Get the specific failed policy application
            failed_application = db.query(PolicyApplicationModel).filter(
                and_(
                    PolicyApplicationModel.id == application_id,
                    PolicyApplicationModel.user_id == user_id,
                    PolicyApplicationModel.status == ApplicationStatus.FAILED
                )
            ).first()
            
            if not failed_application:
                raise Exception("Failed policy application not found")
            
            # Get policy information for response
            policy = db.query(PolicyModel).filter(PolicyModel.id == failed_application.policy_id).first()
            
            removed_policy_info = {
                "id": failed_application.id,
                "policy_name": policy.name if policy else "Unknown Policy",
                "cluster_name": failed_application.cluster_name,
                "failed_at": failed_application.updated_at,
                "error_message": failed_application.error_message
            }
            
            # Delete the failed application
            db.delete(failed_application)
            db.commit()
            
            logger.info(f"Removed failed policy application {application_id} for user {user_id}")
            
            return {
                "removed_count": 1,
                "message": f"Successfully removed failed policy application",
                "removed_policy": removed_policy_info
            }
            
        except Exception as e:
            logger.error(f"Error removing failed policy by ID: {e}")
            db.rollback()
            raise Exception(f"Failed to remove failed policy: {str(e)}")



    async def get_cluster_policy_overview(
        self,
        db: Session,
        user_id: int,
        user_token: str  # Add user token parameter
    ) -> List[ClusterPolicyOverview]:
        """Get overview of policy applications across all clusters"""
        
        # Get all applications for user
        applications = db.query(PolicyApplicationModel).filter(
            PolicyApplicationModel.user_id == user_id
        ).all()
        
        # Group by cluster
        cluster_data = {}
        for app in applications:
            cluster_name = app.cluster_name
            if cluster_name not in cluster_data:
                cluster_data[cluster_name] = {
                    'cluster_id': app.cluster_id,
                    'applications': [],
                    'categories': set()
                }
            
            cluster_data[cluster_name]['applications'].append(app)
            
            # Get policy category
            policy = db.query(PolicyModel).filter(PolicyModel.id == app.policy_id).first()
            if policy and policy.category:
                cluster_data[cluster_name]['categories'].add(policy.category.name)
        
        # Build overview response
        overviews = []
        for cluster_name, data in cluster_data.items():
            apps = data['applications']
            
            # Get cluster info
            cluster_info = await self.get_cluster_info(cluster_name, user_token)
            
            cluster_overview = ClusterPolicyOverview(
                cluster=ClusterInfo(
                    id=data['cluster_id'],
                    cluster_name=cluster_name,
                    server_url=cluster_info.get('server_url', '') if cluster_info else '',
                    provider_name=cluster_info.get('provider_name', '') if cluster_info else '',
                    is_accessible=cluster_info is not None
                ),
                total_applications=len(apps),
                applied_count=len([a for a in apps if a.status == ApplicationStatus.APPLIED]),
                failed_count=len([a for a in apps if a.status == ApplicationStatus.FAILED]),
                pending_count=len([a for a in apps if a.status == ApplicationStatus.PENDING]),
                categories_applied=list(data['categories'])
            )
            
            overviews.append(cluster_overview)
        
        return overviews


    def _convert_application_to_response(
            self, 
            db: Session, 
            application: PolicyApplicationModel
        ) -> PolicyApplicationResponse:
            """Convert database model to response schema with proper error handling"""
            
            try:
                # Get policy details
                policy = db.query(PolicyModel).filter(PolicyModel.id == application.policy_id).first()
                policy_response = None
                
                if policy:
                    # Get category safely
                    category = None
                    if hasattr(policy, 'category') and policy.category:
                        category = PolicyCategoryResponse(
                            id=policy.category.id,
                            name=policy.category.name,
                            display_name=policy.category.display_name,
                            description=policy.category.description,
                            icon=policy.category.icon,
                            created_at=policy.category.created_at,
                            updated_at=policy.category.updated_at,
                            policy_count=0
                        )
                    
                    policy_response = PolicyResponse(
                        id=policy.id,
                        policy_id=policy.policy_id,
                        name=policy.name,
                        description=policy.description,
                        purpose=policy.purpose,
                        severity=policy.severity,
                        yaml_content=policy.yaml_content,
                        policy_metadata=policy.policy_metadata,
                        tags=policy.tags,
                        is_active=policy.is_active,
                        category_id=policy.category_id,
                        category=category,
                        created_at=policy.created_at,
                        updated_at=policy.updated_at
                    )
                
                # Convert enum status safely
                status_value = application.status.value if hasattr(application.status, 'value') else str(application.status)
                
                return PolicyApplicationResponse(
                    id=application.id,
                    user_id=application.user_id,
                    cluster_id=application.cluster_id,
                    cluster_name=application.cluster_name,
                    policy_id=application.policy_id,
                    policy=policy_response,
                    status=SchemaApplicationStatus(status_value),
                    applied_yaml=application.applied_yaml,
                    application_log=application.application_log,
                    error_message=application.error_message,
                    kubernetes_name=application.kubernetes_name,
                    kubernetes_namespace=application.kubernetes_namespace,
                    created_at=application.created_at,
                    applied_at=application.applied_at,
                    updated_at=application.updated_at
                )
                
            except Exception as e:
                logger.error(f"Error converting application {application.id}: {str(e)}")
                raise Exception(f"Policy not found for application {application.id}")

    def add_policies_and_categories(
        self, 
        db: Session, 
        request: AddPoliciesRequest
    ) -> AddPoliciesResponse:
        """Add policies to existing category or create new category with policies"""
        
        try:
            category_created = False
            category_name = ""
            added_policies = []
            failed_policies = []
            
            # Determine target category
            if request.new_category:
                # Create new category
                category_name = request.new_category.category_name
                
                # Check if category already exists
                existing_category = db.query(PolicyCategoryModel).filter(
                    PolicyCategoryModel.name == category_name
                ).first()
                
                if existing_category:
                    raise Exception(f"Category '{category_name}' already exists")
                
                # Create new category
                new_category = PolicyCategoryModel(
                    name=request.new_category.category_name,
                    display_name=request.new_category.category_display_name,
                    description=request.new_category.category_description,
                    icon=request.new_category.category_icon
                )
                db.add(new_category)
                db.commit()
                db.refresh(new_category)
                
                category_created = True
                target_category_id = new_category.id
                policies_to_add = request.new_category.policies
                
            elif request.existing_category_name:
                # Use existing category
                category_name = request.existing_category_name
                existing_category = db.query(PolicyCategoryModel).filter(
                    PolicyCategoryModel.name == request.existing_category_name
                ).first()
                
                if not existing_category:
                    raise Exception(f"Category '{request.existing_category_name}' not found")
                
                target_category_id = existing_category.id
                policies_to_add = request.policies or []
                
            else:
                raise Exception("Either new_category or existing_category_name must be provided")
            
            # Add policies to the category
            for policy_data in policies_to_add:
                try:
                    # Check if policy already exists
                    existing_policy = db.query(PolicyModel).filter(
                        PolicyModel.policy_id == policy_data.policy_id
                    ).first()
                    
                    if existing_policy:
                        failed_policies.append({
                            "policy_id": policy_data.policy_id,
                            "error": f"Policy '{policy_data.policy_id}' already exists"
                        })
                        continue
                    
                    # Create new policy
                    new_policy = PolicyModel(
                        category_id=target_category_id,
                        policy_id=policy_data.policy_id,
                        name=policy_data.name,
                        description=policy_data.description,
                        purpose=policy_data.purpose,
                        severity=policy_data.severity,
                        yaml_content=policy_data.yaml_content,
                        policy_metadata=policy_data.policy_metadata,
                        tags=policy_data.tags,
                        is_active=policy_data.is_active
                    )
                    
                    db.add(new_policy)
                    db.commit()
                    db.refresh(new_policy)
                    
                    # Convert to response format
                    policy_response = PolicyResponse(
                        id=new_policy.id,
                        policy_id=new_policy.policy_id,
                        name=new_policy.name,
                        description=new_policy.description,
                        purpose=new_policy.purpose,
                        severity=new_policy.severity,
                        yaml_content=new_policy.yaml_content,
                        policy_metadata=new_policy.policy_metadata,
                        tags=new_policy.tags,
                        is_active=new_policy.is_active,
                        category_id=new_policy.category_id,
                        created_at=new_policy.created_at,
                        updated_at=new_policy.updated_at
                    )
                    
                    added_policies.append(policy_response)
                    
                except Exception as e:
                    failed_policies.append({
                        "policy_id": policy_data.policy_id,
                        "error": str(e)
                    })
                    continue
            
            return AddPoliciesResponse(
                success=True,
                message=f"Successfully processed policies for category '{category_name}'",
                category_created=category_created,
                category_name=category_name,
                policies_added=len(added_policies),
                policies_failed=len(failed_policies),
                added_policies=added_policies,
                failed_policies=failed_policies
            )
            
        except Exception as e:
            logger.error(f"Error adding policies and categories: {e}")
            db.rollback()
            raise Exception(f"Failed to add policies: {str(e)}")

    def delete_policy_by_id(self, db: Session, policy_id: str) -> DeleteResponse:
        """Delete a specific policy by policy_id"""
        try:
            # Find the policy
            policy = db.query(PolicyModel).filter(PolicyModel.policy_id == policy_id).first()
            
            if not policy:
                raise Exception(f"Policy '{policy_id}' not found")
            
            # Check if policy is currently applied to any cluster
            active_applications = db.query(PolicyApplicationModel).filter(
                and_(
                    PolicyApplicationModel.policy_id == policy.id,
                    PolicyApplicationModel.status == ApplicationStatus.APPLIED
                )
            ).all()
            
            warnings = []
            if active_applications:
                cluster_names = [app.cluster_name for app in active_applications]
                warnings.append(f"Policy is currently applied to clusters: {', '.join(set(cluster_names))}")
            
            # Delete the policy
            policy_name = policy.name
            db.delete(policy)
            db.commit()
            
            logger.info(f"Successfully deleted policy: {policy_id}")
            
            return DeleteResponse(
                success=True,
                message=f"Policy '{policy_name}' deleted successfully",
                deleted_count=1,
                deleted_items=[policy_id],
                warnings=warnings if warnings else None
            )
            
        except Exception as e:
            logger.error(f"Error deleting policy: {e}")
            db.rollback()
            raise Exception(f"Failed to delete policy: {str(e)}")

    def delete_category_with_policies(self, db: Session, category_name: str, force_delete: bool = False) -> DeleteResponse:
        """Delete a category and optionally its associated policies"""
        try:
            # Find the category
            category = db.query(PolicyCategoryModel).filter(
                PolicyCategoryModel.name == category_name
            ).first()
            
            if not category:
                raise Exception(f"Category '{category_name}' not found")
            
            # Get all policies in this category
            policies = db.query(PolicyModel).filter(PolicyModel.category_id == category.id).all()
            
            warnings = []
            deleted_items = []
            
            if policies and not force_delete:
                raise Exception(f"Category '{category_name}' contains {len(policies)} policies. Use force_delete=true to delete category with all its policies.")
            
            # Check for active applications
            if policies:
                for policy in policies:
                    active_applications = db.query(PolicyApplicationModel).filter(
                        and_(
                            PolicyApplicationModel.policy_id == policy.id,
                            PolicyApplicationModel.status == ApplicationStatus.APPLIED
                        )
                    ).all()
                    
                    if active_applications:
                        cluster_names = [app.cluster_name for app in active_applications]
                        warnings.append(f"Policy '{policy.policy_id}' is applied to clusters: {', '.join(set(cluster_names))}")
            
            # Delete all policies in the category first
            deleted_count = 0
            if policies:
                for policy in policies:
                    deleted_items.append(f"policy:{policy.policy_id}")
                    db.delete(policy)
                    deleted_count += 1
            
            # Delete the category
            deleted_items.append(f"category:{category_name}")
            db.delete(category)
            deleted_count += 1
            
            db.commit()
            
            logger.info(f"Successfully deleted category '{category_name}' with {len(policies)} policies")
            
            return DeleteResponse(
                success=True,
                message=f"Category '{category.display_name}' and {len(policies)} associated policies deleted successfully",
                deleted_count=deleted_count,
                deleted_items=deleted_items,
                warnings=warnings if warnings else None
            )
            
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            db.rollback()
            raise Exception(f"Failed to delete category: {str(e)}")
              


# Global policy service instance
policy_db_service = PolicyDatabaseService()

       
   
