from fastapi import Depends, HTTPException, Header
from typing import Dict, Any, Optional
import httpx
from app.config import settings
from app.logger import logger

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Validate JWT token with User Service and return user info"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{settings.USER_SERVICE_URL}/auth/verify",
                headers={"Authorization": authorization}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Invalid or expired token"
                )
            
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to User Service: {str(e)}")
        raise HTTPException(status_code=503, detail="User Service unavailable")        
