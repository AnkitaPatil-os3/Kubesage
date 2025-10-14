import httpx
from fastapi import HTTPException
from app.config import settings
from app.logger import logger
from app.rabbitmq import authenticate_via_rabbitmq
from typing import Dict, Any

async def authenticate_request(api_key: str) -> Dict[str, Any]:
    """
    Authenticate the incoming request token via UserService through RabbitMQ.
    Falls back to direct HTTP call if RabbitMQ is unavailable.
    """
    try:
        # Try RabbitMQ authentication first
        user_data = await authenticate_via_rabbitmq(api_key)
        if user_data.get('valid'):
            return user_data.get('user_data', {})
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    except Exception as rabbitmq_error:
        logger.warning(f"RabbitMQ authentication failed: {str(rabbitmq_error)}, falling back to HTTP")
        
        # Fallback to direct HTTP authentication
        return await authenticate_request_http(api_key)

async def authenticate_request_http(api_key: str) -> Dict[str, Any]:
    """
    Fallback authentication method using direct HTTP call to UserService.
    """
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(
                f"{settings.USER_SERVICE_URL}/api/v1.0/users/me/api-key",
                headers={"X-API-Key": api_key},
                timeout=5.0
            )
            response.raise_for_status()
            user_data = response.json()
            return user_data
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP authentication failed: {e.response.status_code} {e.response.text}")
            raise HTTPException(status_code=401, detail="Authentication failed")
        except Exception as e:
            logger.error(f"Error during HTTP authentication: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
