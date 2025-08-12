from fastapi import Depends, HTTPException, status
from app.auth import get_current_user_from_token
from app.permissions import role_permissions

def require_permission(required_permission: str):
    async def permission_checker(current_user = Depends(get_current_user_from_token)):
        # Allow all access for Super Admin
        roles = current_user.get("roles")
        if roles:
            if isinstance(roles, str):
                # Convert comma-separated string to list
                user_roles = [role.strip() for role in roles.split(",") if role.strip()]
            elif isinstance(roles, list):
                user_roles = roles
            else:
                user_roles = []
        else:
            user_roles = []
        
        if "Super Admin" in user_roles:
            print(f"Access granted: User is Super Admin")
            return current_user
        
        print(f"User roles: {user_roles}")
        print(f"Required permission: {required_permission}")
        # Check if any of the user's roles have the required permission
        for role in user_roles:
            role = role.strip()
            # Normalize role name to lowercase and replace spaces with underscores
            normalized_role = role.lower().replace(" ", "_")
            permissions = role_permissions.get(normalized_role, [])
            print(f"Checking role '{role}' (normalized: '{normalized_role}') with permissions {permissions}")
            if "all" in permissions or required_permission in permissions:
                print(f"Access granted: Role '{role}' has permission '{required_permission}'")
                return current_user
        
        print(f"Access denied: No roles have permission '{required_permission}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "You do not have permission to perform this action."
                }
            }
        )
    return permission_checker
