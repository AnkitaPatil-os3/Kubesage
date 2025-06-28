from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from app.config import settings
from app.logger import logger
import uuid
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio

# Configure email connection
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# Dictionary to store pending user confirmations
# Structure: {confirmation_id: {user_data: dict, expires_at: datetime, status: str}}
pending_confirmations = {}

async def send_confirmation_email(user_data: Dict):
    """
    Send a confirmation email to a new user
    
    Args:
        user_data: Dictionary containing user information
    
    Returns:
        Tuple of (success: bool, confirmation_id: str)
    """
    try:
        # Generate a unique confirmation ID
        confirmation_id = str(uuid.uuid4())
        
        # Store user data with expiration time (1 hour from now)
        expires_at = datetime.now() + timedelta(seconds=settings.USER_CONFIRMATION_TIMEOUT)
        pending_confirmations[confirmation_id] = {
            "user_data": user_data,
            "expires_at": expires_at,
            "status": "pending"
        }
        
        # Create Yes/No action buttons with links back to our server
        yes_url = f"{settings.SERVER_BASE_URL}/auth/confirm/{confirmation_id}/yes"
        no_url = f"{settings.SERVER_BASE_URL}/auth/confirm/{confirmation_id}/no"
        
        # Format the email body with Yes/No buttons
        email_body = f"""
        <h2>KubeSage User Registration Confirmation</h2>
        <p>Hello {user_data.get('first_name', '')} {user_data.get('last_name', '')},</p>
        <p>Admin has registered an account with the username <strong>{user_data.get('username')}</strong> on KubeSage.</p>
        <p>Please confirm , is it you? :</p>
        
        <div style="margin-top: 20px;">
            <a href="{yes_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; margin-right: 10px; border-radius: 4px;">Yes, I am.</a>
            <a href="{no_url}" style="background-color: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">No, I am not.</a>
        </div>
        
        <p style="margin-top: 20px;">This confirmation link will expire in {settings.USER_CONFIRMATION_TIMEOUT // 60} minutes.</p>
        
        <p style="margin-top: 20px; font-size: 12px; color: #666;">
            If the buttons don't work, you can copy and paste these URLs into your browser:<br>
            Yes: {yes_url}<br>
            No: {no_url}
        </p>
        """
        
        # Create message schema
        message = MessageSchema(
            subject="Confirm Your KubeSage Registration",
            recipients=[user_data.get('email')],
            body=email_body,
            subtype="html"
        )
        
        # Initialize FastMail and send the email
        fm = FastMail(conf)
        await fm.send_message(message)
        
        logger.info(f"Confirmation email sent to {user_data.get('email')} with ID: {confirmation_id}")
        
        # Start a background task to expire the confirmation after timeout
        # We'll use a much longer timeout to avoid premature expiration
        asyncio.create_task(expire_confirmation(confirmation_id))
        
        return True, confirmation_id
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")
        return False, None

async def expire_confirmation(confirmation_id: str):
    """
    Expire a confirmation after the timeout period
    
    Args:
        confirmation_id: The ID of the confirmation to expire
    """
    # Wait for the confirmation timeout period
    await asyncio.sleep(settings.USER_CONFIRMATION_TIMEOUT)
    
    # Only expire if it's still pending
    if confirmation_id in pending_confirmations and pending_confirmations[confirmation_id]["status"] == "pending":
        pending_confirmations[confirmation_id]["status"] = "expired"
        logger.info(f"Confirmation {confirmation_id} expired after timeout")

def get_confirmation_status(confirmation_id: str) -> Optional[Dict]:
    """
    Get the status of a confirmation
    
    Args:
        confirmation_id: The ID of the confirmation to check
    
    Returns:
        Dictionary with confirmation data or None if not found
    """
    if confirmation_id in pending_confirmations:
        # Log the current status for debugging
        logger.info(f"Confirmation {confirmation_id} status: {pending_confirmations[confirmation_id]['status']}")
        return pending_confirmations[confirmation_id]
    
    logger.warning(f"Confirmation {confirmation_id} not found in pending_confirmations")
    return None

def update_confirmation_status(confirmation_id: str, status: str) -> bool:
    """
    Update the status of a confirmation
    
    Args:
        confirmation_id: The ID of the confirmation to update
        status: The new status (confirmed, rejected, expired)
    
    Returns:
        True if updated successfully, False otherwise
    """
    if confirmation_id in pending_confirmations:
        old_status = pending_confirmations[confirmation_id]["status"]
        pending_confirmations[confirmation_id]["status"] = status
        logger.info(f"Confirmation {confirmation_id} status updated from {old_status} to {status}")
        return True
    
    logger.warning(f"Attempted to update status for non-existent confirmation {confirmation_id}")
    return False

def clean_expired_confirmations():
    """
    Clean up expired confirmations from memory
    This should be run periodically to prevent memory leaks
    """
    now = datetime.now()
    expired_ids = []
    
    # Log the current state of pending_confirmations
    logger.info(f"Current pending confirmations: {len(pending_confirmations)}")
    
    for confirmation_id, data in pending_confirmations.items():
        # Only clean up if it's been processed or truly expired (with a grace period)
        if data["status"] in ["confirmed", "rejected"]:
            # For processed confirmations, we can clean them up immediately
            expired_ids.append(confirmation_id)
        elif data["status"] == "expired" or (data["expires_at"] + timedelta(hours=1) < now):
            # For expired confirmations or those that expired over an hour ago
            expired_ids.append(confirmation_id)
    
    for confirmation_id in expired_ids:
        if confirmation_id in pending_confirmations:
            status = pending_confirmations[confirmation_id]["status"]
            if status == "pending":
                logger.info(f"Marking confirmation {confirmation_id} as expired during cleanup")
                pending_confirmations[confirmation_id]["status"] = "expired"
            
            logger.info(f"Removing confirmation {confirmation_id} with status {status} during cleanup")
            del pending_confirmations[confirmation_id]
    
    if expired_ids:
        logger.info(f"Cleaned up {len(expired_ids)} expired confirmations")
