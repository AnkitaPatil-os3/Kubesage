from fastapi import Depends, HTTPException, status
from app.auth import get_current_active_user
from app.permissions import role_permissions

def require_permission(required_permission: str):
    async def permission_checker(current_user = Depends(get_current_active_user)):
        # Allow all access for Super Admin
        if current_user.roles and "Super Admin" in current_user.roles:
            return current_user
        
        user_roles = current_user.roles.split(",") if current_user.roles else []
        # Check if any of the user's roles have the required permission
        for role in user_roles:
            role = role.strip()
            permissions = role_permissions.get(role, [])
            if "all" in permissions or required_permission in permissions:
                return current_user
        
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
