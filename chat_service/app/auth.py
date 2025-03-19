from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import settings
from app.schemas import TokenData, UserInfo
from app.logger import logger
import httpx
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.USER_SERVICE_URL}/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInfo:
    """Validate JWT token and get current user information"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        token_data = TokenData(user_id=int(user_id))
    except JWTError:
        raise credentials_exception
    
    # Get user info from user service
    user = await get_user_from_service(token_data.user_id, token)
    if user is None:
        raise credentials_exception
    
    return user

async def get_user_from_service(user_id: int, token: str) -> Optional[UserInfo]:
    """Get user information from user service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.USER_SERVICE_URL}/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return UserInfo(
                    id=user_data["id"],
                    username=user_data["username"],
                    email=user_data["email"]
                )
            else:
                logger.error(f"Failed to get user from service: {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error getting user from service: {str(e)}")
        return None
