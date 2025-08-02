from fastapi import APIRouter, HTTPException, Query, Path, Depends, Request 
from fastapi.responses import JSONResponse
from typing import Optional
from app.auth import get_current_user
from app.logger import logger
from datetime import datetime
from app.models import PolicyApplicationModel, ApplicationStatus,PolicyModel , PolicyCategoryModel
from app.policy_schemas import PolicyApplicationRequest, PolicyApplicationResponse, PolicyApplicationListRequest,AddPoliciesRequest, AddPoliciesResponse,  DeletePolicyRequest, DeleteCategoryRequest, DeleteResponse



#  ********************************** POLICIE ROUTES **********************************


from fastapi import APIRouter, HTTPException, Query, Path, Depends, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from app.policy_schemas import (
    PolicyResponse, PolicyCreate, PolicyUpdate, PolicyCategoryResponse,
    PolicyListResponse, PolicyApplicationRequest, PolicyApplicationResponse,
    PolicyApplicationListResponse, ClusterPolicyOverview, PolicyEditableResponse
)
from app.policy_service import policy_db_service
from app.database import get_db
from app.auth import get_current_user
from app.logger import logger
from app.policy_schemas import APIResponse
from datetime import datetime
from sqlalchemy import and_

# Create router
policy_router = APIRouter(prefix="/policies", tags=["policies"])


@policy_router.post("/initialize")
async def initialize_policies(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Initialize database with predefined policies"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} initializing policy database")
        policy_db_service.initialize_database(db)
        return APIResponse(
            success=True,
            message="Policy database initialized successfully",
            data={"initialized": True},
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error initializing policy database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@policy_router.get("/categories", response_model=APIResponse)
async def get_policy_categories(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all policy categories with policy counts"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested policy categories")
        categories = policy_db_service.get_categories(db)
        return APIResponse(
            success=True,
            message=f"Retrieved {len(categories)} policy categories",
            data=categories,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting policy categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@policy_router.get("/categories/{category_name}", response_model=APIResponse)
async def get_policies_by_category(
    category_name: str = Path(..., description="Policy category name"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get policies by category with pagination"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested policies for category: {category_name}")
        result = policy_db_service.get_policies_by_category(db, category_name, page, size)
        return APIResponse(
            success=True,
            message=f"Retrieved {len(result['policies'])} policies for category '{category_name}'",
            data=result,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting policies by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@policy_router.get("/{policy_id}", response_model=APIResponse)
async def get_policy_by_id(
    policy_id: str = Path(..., description="Policy ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific policy by ID"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested policy: {policy_id}")
        policy = policy_db_service.get_policy_by_id(db, policy_id)
        
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        return APIResponse(
            success=True,
            message=f"Retrieved policy '{policy_id}'",
            data=policy,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@policy_router.get("/categories/{category_name}/stats", response_model=APIResponse)
async def get_category_stats(
    category_name: str = Path(..., description="Policy category name"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get statistics for a specific policy category"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} requested stats for category: {category_name}")
        result = policy_db_service.get_policies_by_category(db, category_name, 1, 1000)  # Get all policies
        
        # Calculate stats
        policies = result['policies']
        severity_counts = {}
        active_count = 0
        
        for policy in policies:
            severity = policy.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            if policy.is_active:
                active_count += 1
        
        stats = {
            "total_policies": len(policies),
            "active_policies": active_count,
            "inactive_policies": len(policies) - active_count,
            "severity_breakdown": severity_counts,
            "category": category_name
        }
        
        return APIResponse(
            success=True,
            message=f"Retrieved statistics for category '{category_name}'",
            data=stats,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ***************************** APPLY POLICIES IN CLUSTER *****************************

def get_user_token(request: Request) -> str:
    """Extract token from request headers"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    raise HTTPException(
        status_code=401,
        detail="User token not available"
    )



''' You can apply policies at cluster level because:

1. Your YAML policies already use ClusterPolicy kind - which applies cluster-wide by default
2. Kyverno ClusterPolicy automatically applies to all namespaces in the cluster
3. The kubernetes_namespace field set to "cluster-wide" is just for tracking/display purposes
4. The actual cluster-wide application happens through the YAML content (kind: ClusterPolicy) which makes it apply cluster-wide. 

So removing the is_cluster_wide database field won't affect the cluster-level policy application functionality - it will still work because the policy YAML itself contains kind: ClusterPolicy which makes it apply cluster-wide. '''




''' Note:

1. The kubernetes_namespace field is only for tracking purposes in the database
2. Since your policies use kind: ClusterPolicy in the YAML, they will automatically apply cluster-wide regardless of the namespace value
3. Setting kubernetes_namespace: "cluster-wide" just helps you identify in the database that this was intended as a cluster-wide application '''




#  ---------------------------------------- Cluster-wide application: ------------------------------

# {
#   "cluster_name": "kubesage-demo",
#   "policy_id": "disallow-latest-tag",
#   "kubernetes_namespace": "cluster-wide"
# }



# ------------------------ Alternative (using default namespace but still applies cluster-wide): ------------------------------

# {
#   "cluster_name": "kubesage-demo", 
#   "policy_id": "disallow-latest-tag",
#   "kubernetes_namespace": "default"
# }


# ------------------------ Or without namespace (will default to "default"): ------------------------------

# {
#   "cluster_name": "kubesage-demo",
#   "policy_id": "disallow-latest-tag"
# }




@policy_router.post("/apply", response_model=APIResponse)
async def apply_policy_to_cluster(
    policy_request: PolicyApplicationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Apply a policy to a specific cluster"""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 1))
        user_token = get_user_token(request)
        
        # Log whether edited YAML is being used
        yaml_type = "edited" if policy_request.edited_yaml else "original"
        save_status = " and saved" if policy_request.save_edited_policy else ""
        
        logger.info(f"User {current_user.get('username', 'unknown')} applying {yaml_type} policy {policy_request.policy_id} to cluster {policy_request.cluster_name}{save_status}")

        application = await policy_db_service.apply_policy_to_cluster(db, policy_request, user_id, user_token)
        
        # Print the applied YAML data (edited or original)
        print(f"Applied {yaml_type.upper()} YAML data for policy {policy_request.policy_id}:")
        print("=" * 50)
        print(application.applied_yaml)
        print("=" * 50)
        
        return APIResponse(
            success=True,
            message=f"Policy '{policy_request.policy_id}' ({yaml_type}) applied successfully to cluster '{policy_request.cluster_name}'{save_status}",
            data=application,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error applying policy to cluster: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@policy_router.post("/applications/list", response_model=APIResponse)
async def get_policy_applications(
    request_data: PolicyApplicationListRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get policy applications for the current user with cluster filtering"""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 1))
        
        logger.info(f"User {current_user.get('username', 'unknown')} requested policy applications for cluster: {request_data.cluster_name}")
        
        result = policy_db_service.get_policy_applications(
            db, user_id, request_data.cluster_name, request_data.status, request_data.page, request_data.size
        )
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(result.applications)} policy applications",
            data=result.dict(),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting policy applications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@policy_router.get("/applications/{application_id}", response_model=APIResponse)
async def get_policy_application_details(
    application_id: int = Path(..., description="Policy application ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get details of a specific policy application"""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 1))
        
        application = db.query(PolicyApplicationModel).filter(
            and_(
                PolicyApplicationModel.id == application_id,
                PolicyApplicationModel.user_id == user_id
            )
        ).first()
        
        if not application:
            raise HTTPException(status_code=404, detail="Policy application not found")
        
        response = policy_db_service._convert_application_to_response(db, application)
        
        return APIResponse(
            success=True,
            message=f"Retrieved policy application details",
            data=response,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy application details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@policy_router.delete("/applications/{application_id}", response_model=APIResponse)
async def remove_policy_from_cluster(
    application_id: int = Path(..., description="Policy application ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    """Remove a policy from cluster and database"""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 1))
        user_token = get_user_token(request)
        
        logger.info(f"User {current_user.get('username', 'unknown')} removing policy application {application_id}")
        
        application = await policy_db_service.remove_policy_from_cluster(db, application_id, user_id, user_token)
        
        return APIResponse(
            success=True,
            message=f"Policy removed from cluster and database successfully",
            data=application,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error removing policy from cluster and database: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@policy_router.get("/clusters/overview", response_model=APIResponse)
async def get_cluster_policy_overview(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get overview of policy applications across all clusters"""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 1))
        user_token = get_user_token(request)
        
        logger.info(f"User {current_user.get('username', 'unknown')} requested cluster policy overview")
        
        overview = await policy_db_service.get_cluster_policy_overview(db, user_id, user_token)
        
        return APIResponse(
            success=True,
            message=f"Retrieved policy overview for {len(overview)} clusters",
            data=overview,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting cluster policy overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@policy_router.get("/clusters/{cluster_name}/available-policies", response_model=APIResponse)
async def get_available_policies_for_cluster(
    cluster_name: str = Path(..., description="Cluster name"),
    category: Optional[str] = Query(None, description="Filter by policy category"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get available policies that can be applied to a cluster"""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 1))
        
        # Get already applied policies for this cluster
        applied_policies = db.query(PolicyApplicationModel.policy_id).filter(
            and_(
                PolicyApplicationModel.cluster_name == cluster_name,
                PolicyApplicationModel.user_id == user_id,
                PolicyApplicationModel.status.in_([ApplicationStatus.APPLIED, ApplicationStatus.PENDING, ApplicationStatus.APPLYING])
            )
        ).subquery()
        
        # Get available policies (not already applied)
        query = db.query(PolicyModel).filter(
            and_(
                PolicyModel.is_active == True,
                ~PolicyModel.id.in_(db.query(applied_policies))

            )
        )
        
        # Filter by category if specified
        if category:
            category_obj = db.query(PolicyCategoryModel).filter(
                PolicyCategoryModel.name == category
            ).first()
            if category_obj:
                query = query.filter(PolicyModel.category_id == category_obj.id)
        
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
                "policy_metadata": policy.policy_metadata,
                "tags": policy.tags,
                "is_active": policy.is_active,
                "category_id": policy.category_id,
                "created_at": policy.created_at,
                "updated_at": policy.updated_at or policy.created_at
            }
            policy_responses.append(PolicyResponse(**policy_dict))
        
        total_pages = (total + size - 1) // size
        
        result = {
            "policies": policy_responses,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "cluster_name": cluster_name
        }
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(policy_responses)} available policies for cluster '{cluster_name}'",
            data=result,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting available policies for cluster: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@policy_router.get("/clusters/{cluster_name}/applied-policies", response_model=APIResponse)
async def get_applied_policies_for_cluster(
    cluster_name: str = Path(..., description="Cluster name"),
    status: Optional[str] = Query(None, description="Filter by application status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get policies applied to a specific cluster"""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 1))
        
        query = db.query(PolicyApplicationModel).filter(
            and_(
                PolicyApplicationModel.cluster_name == cluster_name,
                PolicyApplicationModel.user_id == user_id
            )
        )
        
        if status:
            query = query.filter(PolicyApplicationModel.status == status)
        
        total = query.count()
        applications = query.offset((page - 1) * size).limit(size).all()
        
        application_responses = [
            policy_db_service._convert_application_to_response(db, app) for app in applications
        ]
        
        total_pages = (total + size - 1) // size
        
        result = {
            "applications": application_responses,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "cluster_name": cluster_name
        }
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(application_responses)} applied policies for cluster '{cluster_name}'",
            data=result,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting applied policies for cluster: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@policy_router.delete("/applications/failed/{application_id}", response_model=APIResponse)
async def remove_failed_policy_by_id(
    application_id: int = Path(..., description="Failed policy application ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a specific failed policy application from database"""
    try:
        user_id = current_user.get('user_id', current_user.get('id', 1))
        
        logger.info(f"User {current_user.get('username', 'unknown')} removing failed policy application {application_id}")
        
        result = policy_db_service.remove_failed_policy_by_id(db, application_id, user_id)
        
        return APIResponse(
            success=True,
            message=result["message"],
            data={
                "removed_count": result["removed_count"],
                "removed_policy": result.get("removed_policy")
            },
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error removing failed policy by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ------------------ Policy Management Endpoints for Super Admin ------------------

@policy_router.delete("/policy/{policy_id}", response_model=APIResponse)
async def delete_policy(
    policy_id: str = Path(..., description="Policy ID to delete"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a specific policy (Super Admin only)"""
    try:
        # Check if user is Super Admin
        user_roles = current_user.get('roles', [])
        if 'Super Admin' not in user_roles:
            raise HTTPException(status_code=403, detail="Only Super Admin can delete policies")
        
        logger.info(f"Super Admin {current_user.get('username', 'unknown')} deleting policy: {policy_id}")
        
        result = policy_db_service.delete_policy_by_id(db, policy_id)
        
        return APIResponse(
            success=True,
            message=result.message,
            data=result.dict(),
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@policy_router.delete("/category/{category_name}", response_model=APIResponse)
async def delete_category(
    category_name: str = Path(..., description="Category name to delete"),
    force_delete: bool = Query(False, description="Force delete category with all policies"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a category and optionally its policies (Super Admin only)"""
    try:
        # Check if user is Super Admin
        user_roles = current_user.get('roles', [])
        if 'Super Admin' not in user_roles:
            raise HTTPException(status_code=403, detail="Only Super Admin can delete categories")
        
        logger.info(f"Super Admin {current_user.get('username', 'unknown')} deleting category: {category_name} (force: {force_delete})")
        
        result = policy_db_service.delete_category_with_policies(db, category_name, force_delete)
        
        return APIResponse(
            success=True,
            message=result.message,
            data=result.dict(),
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@policy_router.post("/add-policies", response_model=APIResponse)
async def add_policies_and_categories(
    request: AddPoliciesRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add policies to existing category or create new category with policies"""
    try:
        logger.info(f"User {current_user.get('username', 'unknown')} adding policies")
        
        result = policy_db_service.add_policies_and_categories(db, request)
        
        return APIResponse(
            success=True,
            message=result.message,
            data=result.dict(),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error adding policies and categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- 1. Create new category with policies: ----------------

"""
{
  "new_category": {
    "category_name": "custom_security",
    "category_display_name": "Custom Security Policies",
    "category_description": "Custom security policies for specific use cases",
    "category_icon": "shield-alert",
    "policies": [
      {
        "policy_id": "custom-policy-1",
        "name": "Custom Policy 1",
        "description": "Custom security policy",
        "purpose": "Enforce custom security rules",
        "severity": "high",
        "yaml_content": "apiVersion: kyverno.io/v1\nkind: ClusterPolicy\n...",
        "tags": ["custom", "security"]
      }
    ]
  }
}

"""


# ---------------- 2. Add policies to existing category: ----------------

"""

{
  "existing_category_name": "validation",
  "policies": [
    {
      "policy_id": "new-validation-policy",
      "name": "New Validation Policy",
      "description": "Additional validation policy",
      "purpose": "Validate additional resources",
      "severity": "medium",
      "yaml_content": "apiVersion: kyverno.io/v1\nkind: ClusterPolicy\n...",
      "tags": ["validation", "custom"]
    }
  ]
}
"""