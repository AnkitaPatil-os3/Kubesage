from datetime import datetime, timedelta , UTC
from typing import Optional

from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User
from app.schemas import TokenData
from app.logger import logger

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

router = APIRouter()

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta

    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, expire

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
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError as e:
        logger.error(f"JWT error: {str(e)}")
        raise credentials_exception
    
    user = session.exec(select(User).where(User.id == token_data.user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions"
    )
    return current_user

@router.post("/auth/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, expire = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires": expire.isoformat()
    }




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
