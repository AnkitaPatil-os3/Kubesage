import httpx
from fastapi import HTTPException
from app.config import settings
from app.logger import logger

async def authenticate_request(token: str):
    """Authenticate the incoming request token via UserService"""
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(
                f"{settings.USER_SERVICE_URL}/api/v1.0/users/me/api-key",
                headers={"X-API-Key": token},
                timeout=5.0
            )
            response.raise_for_status()
            user_data = response.json()
            return user_data
        except httpx.HTTPStatusError as e:
            logger.warning(f"Authentication failed: {e.response.status_code} {e.response.text}")
            raise HTTPException(status_code=401, detail="Authentication failed")
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
