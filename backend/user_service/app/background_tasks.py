import asyncio
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import get_session
from app.models import UserToken, RefreshToken
from app.config import settings
from app.logger import logger

async def cleanup_expired_tokens_task():
    """
    Background task to periodically clean up expired tokens.
    Runs every hour by default.
    """
    while True:
        try:
            with next(get_session()) as session:
                now = datetime.now()
                
                # Remove expired access tokens
                expired_access_tokens = session.exec(
                    select(UserToken).where(UserToken.expires_at <= now)
                ).all()
                
                for token in expired_access_tokens:
                    session.delete(token)
                
                # Remove expired refresh tokens
                expired_refresh_tokens = session.exec(
                    select(RefreshToken).where(RefreshToken.expires_at <= now)
                ).all()
                
                for token in expired_refresh_tokens:
                    session.delete(token)
                
                # Remove revoked refresh tokens older than 30 days
                old_revoked_tokens = session.exec(
                    select(RefreshToken).where(
                        RefreshToken.is_revoked == True,
                        RefreshToken.created_at <= now - timedelta(days=30)
                    )
                ).all()
                
                for token in old_revoked_tokens:
                    session.delete(token)
                
                session.commit()
                
                total_cleaned = len(expired_access_tokens) + len(expired_refresh_tokens) + len(old_revoked_tokens)
                if total_cleaned > 0:
                    logger.info(f"Cleaned up {total_cleaned} expired/old tokens")
                
        except Exception as e:
            logger.error(f"Error in token cleanup task: {str(e)}")
        
        # Wait for next cleanup cycle
        await asyncio.sleep(settings.SESSION_CLEANUP_INTERVAL)

async def cleanup_inactive_sessions_task():
    """
    Background task to clean up sessions that haven't been used for a long time.
    """
    while True:
        try:
            with next(get_session()) as session:
                # Mark sessions as inactive if not used for 30 days
                inactive_threshold = datetime.now() - timedelta(days=30)
                
                inactive_tokens = session.exec(
                    select(UserToken).where(
                        UserToken.last_used_at <= inactive_threshold,
                        UserToken.is_active == True
                    )
                ).all()
                
                for token in inactive_tokens:
                    token.is_active = False
                    session.add(token)
                
                # Revoke associated refresh tokens
                for token in inactive_tokens:
                    refresh_token = session.exec(
                        select(RefreshToken).where(
                            RefreshToken.session_id == token.session_id,
                            RefreshToken.is_revoked == False
                        )
                    ).first()
                    
                    if refresh_token:
                        refresh_token.is_revoked = True
                        session.add(refresh_token)
                
                session.commit()
                
                if inactive_tokens:
                    logger.info(f"Marked {len(inactive_tokens)} inactive sessions as expired")
                
        except Exception as e:
            logger.error(f"Error in inactive session cleanup: {str(e)}")
        
        # Run daily
        await asyncio.sleep(24 * 60 * 60)
