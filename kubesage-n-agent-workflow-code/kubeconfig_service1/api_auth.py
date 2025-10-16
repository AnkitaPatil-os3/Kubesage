from fastapi import HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from app.config import settings
from app.logger import logger

# API Key authentication for cluster onboarding
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Depends(api_key_header)):
    """
    Validate API key for cluster onboarding endpoints
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required. Please provide X-API-Key header."
        )
    
    if api_key != settings.CLUSTER_ONBOARD_API_KEY:
        logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    return api_key
