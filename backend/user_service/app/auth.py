from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple
import secrets
import hashlib

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User, UserToken, RefreshToken
from app.schemas import TokenData, DeviceFingerprint
from app.logger import logger

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1.0/auth/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# NEW: Generate secure refresh token
def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token"""
    return secrets.token_urlsafe(64)

# NEW: Create device fingerprint hash
def create_device_fingerprint(device_info: DeviceFingerprint) -> str:
    """Create a hash from device information for session identification"""
    fingerprint_data = f"{device_info.user_agent or ''}{device_info.ip_address or ''}{device_info.device_info or ''}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]

# UPDATED: Enhanced token creation with session support
def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None,
    session_id: Optional[str] = None
) -> Tuple[str, datetime]:
    """Create access token with session information"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "session_id": session_id  # NEW: Include session ID in token
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, expire

# NEW: Create refresh token with session tracking
def create_refresh_token(
    user_id: int,
    session_id: str,
    device_fingerprint: DeviceFingerprint,
    session: Session
) -> Tuple[str, datetime]:
    """Create and store refresh token"""
    refresh_token = generate_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Store refresh token in database
    db_refresh_token = RefreshToken(
        token=refresh_token,
        user_id=user_id,
        session_id=session_id,
        expires_at=expires_at,
        device_info=device_fingerprint.device_info,
        ip_address=device_fingerprint.ip_address
    )
    
    session.add(db_refresh_token)
    session.commit()
    
    return refresh_token, expires_at

# NEW: Validate refresh token
def validate_refresh_token(refresh_token: str, session: Session) -> Optional[RefreshToken]:
    """Validate refresh token and return token record if valid"""
    db_token = session.exec(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.now(UTC)
        )
    ).first()
    
    return db_token

# UPDATED: Enhanced current user function with session validation
async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    session: Session = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        session_id: str = payload.get("session_id")  # NEW: Extract session ID
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError as e:
        logger.error(f"JWT error: {str(e)}")
        raise credentials_exception
    
    # NEW: Validate session is still active
    user_token = session.exec(
        select(UserToken).where(
            UserToken.user_id == user_id,
            UserToken.session_id == session_id,
            UserToken.is_active == True,
            UserToken.expires_at > datetime.now(UTC)
        )
    ).first()
    
    if not user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )
    
    # Update last used timestamp
    user_token.last_used_at = datetime.now(UTC)
    session.add(user_token)
    session.commit()
    
    # Get user
    user = session.exec(select(User).where(User.id == user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Check if user has admin privileges - supports both old and new role systems"""
    
    # Check new role-based system first
    if current_user.roles and "Super Admin" in current_user.roles:
        return current_user
    
    # Fallback to old is_admin field
    if hasattr(current_user, 'is_admin') and current_user.is_admin:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions"
    )

# NEW: Refresh access token using refresh token
async def refresh_access_token(
    refresh_token: str,
    device_fingerprint: DeviceFingerprint,
    session: Session
) -> Tuple[str, str, datetime]:
    """Refresh access token using refresh token"""
    
    # Validate refresh token
    db_refresh_token = validate_refresh_token(refresh_token, session)
    if not db_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user
    user = session.exec(select(User).where(User.id == db_refresh_token.user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, expires_at = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
        session_id=db_refresh_token.session_id
    )
    
    # Update existing user token or create new one
    user_token = session.exec(
        select(UserToken).where(
            UserToken.user_id == user.id,
            UserToken.session_id == db_refresh_token.session_id
        )
    ).first()
    
    if user_token:
        user_token.token = access_token
        user_token.expires_at = expires_at
        user_token.last_used_at = datetime.now(UTC)
    else:
        user_token = UserToken(
            token=access_token,
            user_id=user.id,
            session_id=db_refresh_token.session_id,
            expires_at=expires_at,
            device_info=device_fingerprint.device_info,
            ip_address=device_fingerprint.ip_address,
            user_agent=device_fingerprint.user_agent
        )
    
    session.add(user_token)
    session.commit()
    
    return access_token, db_refresh_token.session_id, expires_at

# NEW: Revoke refresh token
def revoke_refresh_token(refresh_token: str, session: Session) -> bool:
    """Revoke a refresh token"""
    db_token = session.exec(
        select(RefreshToken).where(RefreshToken.token == refresh_token)
    ).first()
    
    if db_token:
        db_token.is_revoked = True
        session.add(db_token)
        session.commit()
        return True
    
    return False

# NEW: Clean up expired tokens
def cleanup_expired_tokens(session: Session):
    """Remove expired tokens from database"""
    now = datetime.now(UTC)
    
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
    
    session.commit()
    logger.info(f"Cleaned up {len(expired_access_tokens)} access tokens and {len(expired_refresh_tokens)} refresh tokens")

#  api key auth implementation **********************

# Add these imports to your existing auth.py file
from app.models import ApiKey
from app.api_key_utils import is_api_key_expired
from datetime import datetime
from fastapi import Header


# Add this function to your existing auth.py file
async def get_user_from_api_key(api_key: str, session: Session) -> Optional[User]:
    """
    Get user from API key.
    
    Args:
        api_key: The API key to verify
        session: Database session
    
    Returns:
        User: The user if API key is valid, None otherwise
    """
    if not api_key:
        return None
    
    # Find the API key in database
    api_key_record = session.exec(
        select(ApiKey).where(
            ApiKey.api_key == api_key,
            ApiKey.is_active == True
        )
    ).first()
    
    if not api_key_record:
        return None
    
    # Check if API key is expired
    if api_key_record.expires_at and api_key_record.expires_at < datetime.now():
        return None
    
    # Get the user
    user = session.exec(select(User).where(User.id == api_key_record.user_id)).first()
    
    if not user or not user.is_active:
        return None
    
    # Update last used timestamp
    api_key_record.last_used_at = datetime.now()
    session.add(api_key_record)
    session.commit()
    
    return user

async def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None),
    session: Session = Depends(get_session)
) -> User:
    """
    Get current user from API key header.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required in X-API-Key header"
        )
    
    user = await get_user_from_api_key(x_api_key, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    
    return user
