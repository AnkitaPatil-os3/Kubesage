from fastapi import Depends, HTTPException, status
from app.auth import get_current_user
from app.permissions import role_permissions

def require_permission(required_permission: str):
    async def permission_checker(current_user = Depends(get_current_user)):
        # Allow all access for Super Admin
        if current_user.get("roles") and "Super Admin" in current_user.get("roles"):
            print(f"Access granted: User is Super Admin")
            return current_user
        
        user_roles = current_user.get("roles", "").split(",") if current_user.get("roles") else []
        print(f"User roles: {user_roles}")
        print(f"Required permission: {required_permission}")
        # Check if any of the user's roles have the required permission
        for role in user_roles:
            role = role.strip()
            permissions = role_permissions.get(role, [])
            print(f"Checking role '{role}' with permissions {permissions}")
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
