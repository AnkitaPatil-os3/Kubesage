from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import settings
from app.schemas import TokenData, UserInfo
from app.logger import logger
import httpx
from typing import Optional




oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"https://10.0.34.171:8001/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInfo:
    print("Authenticating user using token...")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"https://10.0.34.171:8001/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return UserInfo(
                    id=user_data["id"],
                    username=user_data["username"],
                    email=user_data.get("email", "")
                )
            else:
                logger.error(f"Token validation failed: {response.text}")
                raise credentials_exception
    except httpx.RequestError as e:
        logger.error(f"Connection error with user service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User authentication service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in auth: {str(e)}")
        raise credentials_exception


