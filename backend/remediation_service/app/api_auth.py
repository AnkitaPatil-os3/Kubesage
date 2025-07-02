from fastapi import HTTPException, status, Header
from sqlmodel import Session, select
from typing import Optional
import requests
import hashlib
from datetime import datetime
from app.logger import logger
from app.models import WebhookUser
from app.database import get_session

# Configuration
USER_SERVICE_URL = "https://10.0.32.108:8001"

def hash_api_key(api_key: str) -> str:
    """Create a hash of the API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

async def verify_api_key_with_user_service(api_key: str) -> dict:
    """
    Verify API key with the user service.
    """
    try:
        logger.info(f"Attempting to verify API key: {api_key[:10]}...")
        
        # CHANGE THIS ENDPOINT
        response = requests.get(
            f"{USER_SERVICE_URL}/users/me/api-key",  # CHANGED FROM /users/me
            headers={"X-API-Key": api_key},
            timeout=10,
            verify=False
        )
        
        logger.info(f"User service response status: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"API key verified for user: {user_data.get('username')}")
            return user_data
        else:
            try:
                error_detail = response.json()
                logger.error(f"User service error response: {error_detail}")
            except:
                logger.error(f"User service error response (text): {response.text}")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid API key - User service returned {response.status_code}"
            )
            
    except requests.RequestException as e:
        logger.error(f"Error connecting to user service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service unavailable: {str(e)}"
        )

async def get_or_create_webhook_user(user_data: dict, api_key: str, session: Session) -> WebhookUser:
    """
    Get existing webhook user or create new one.
    """
    api_key_hash = hash_api_key(api_key)
    
    # Try to find existing user
    webhook_user = session.exec(
        select(WebhookUser).where(WebhookUser.user_id == user_data.get('id'))
    ).first()
    
    if webhook_user:
        # Update existing user info
        webhook_user.username = user_data.get('username')
        webhook_user.email = user_data.get('email')
        webhook_user.api_key_hash = api_key_hash
        webhook_user.updated_at = datetime.utcnow()
        session.add(webhook_user)
        session.commit()
        session.refresh(webhook_user)
        logger.info(f"Updated webhook user: {webhook_user.username}")
    else:
        # Create new webhook user
        webhook_user = WebhookUser(
            user_id=user_data.get('id'),
            username=user_data.get('username'),
            email=user_data.get('email'),
            api_key_hash=api_key_hash
        )
        session.add(webhook_user)
        session.commit()
        session.refresh(webhook_user)
        logger.info(f"Created new webhook user: {webhook_user.username}")
    
    return webhook_user

# NEW: Header-based authentication function
async def authenticate_api_key_from_header(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    session: Session = None
) -> WebhookUser:
    """
    Authenticate API key from request header and return webhook user.
    """
    if not x_api_key or not x_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required in X-API-Key header"
        )
    
    # Verify API key with user service
    user_data = await verify_api_key_with_user_service(x_api_key.strip())
    
    # Get or create webhook user in local database
    webhook_user = await get_or_create_webhook_user(user_data, x_api_key, session)
    
    return webhook_user

# Keep the existing body-based function for backward compatibility if needed
async def authenticate_api_key_from_body(api_key: str, session: Session) -> WebhookUser:
    """
    Authenticate API key from request body and return webhook user.
    """
    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required and cannot be empty"
        )
    
    # Verify API key with user service
    user_data = await verify_api_key_with_user_service(api_key.strip())
    
    # Get or create webhook user in local database
    webhook_user = await get_or_create_webhook_user(user_data, api_key, session)
    
    return webhook_user