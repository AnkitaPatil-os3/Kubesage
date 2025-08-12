from fastapi import Depends, HTTPException, status
from app.auth import get_current_user_from_token
from app.permissions import role_permissions

def require_permission(required_permission: str):
    async def permission_checker(current_user = Depends(get_current_user_from_token)):
        # Allow all access for Super Admin
        if current_user.get("roles") and "Super Admin" in current_user.get("roles"):
            return current_user
        
        user_roles = current_user.get("roles") if current_user.get("roles") else []
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
