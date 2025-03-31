from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
import datetime  # Added for timestamp

from app.database import get_session
from app.models import User , UserToken
from app.schemas import UserCreate, UserResponse, UserUpdate, LoginRequest, Token, ChangePasswordRequest
from app.auth import (
    authenticate_user, 
    create_access_token, 
    get_password_hash, 
    get_current_active_user,
    get_current_admin_user,
    verify_password,
    get_current_user
)
from app.config import settings
from app.logger import logger
from datetime import timedelta
from app.queue import publish_message  # Import the queue functionality
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security import OAuth2PasswordBearer

# Auth router
auth_router = APIRouter()

@auth_router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, expires_at = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    # Save UserToken in the database
    user_token = UserToken(
        token=access_token,
        user_id=user.id,
        expires_at=expires_at
    )
    session.add(user_token)
    session.commit()
    session.refresh(user_token)

    print(f"User token is {user_token}, save in the database")
        
    # Publish login event
    publish_message("user_events", {
        "event_type": "user_login",
        "user_id": user.id,
        "username": user.username,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "expires_at": expires_at
    }



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

@auth_router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
    ):
    """
    Logout user by removing their token from the database.
    Optionally can clear all user sessions or just the current one.
    """
    try:
        # Delete the current token
        user_token = session.query(UserToken).filter(
            UserToken.token == token,
            UserToken.user_id == current_user.id
        ).first()
        
        if user_token:
            session.delete(user_token)
            session.commit()
        
        # Option 1: Delete all tokens for this user (complete logout from all devices)
        # session.query(UserToken).filter(UserToken.user_id == current_user.id).delete()
        # session.commit()
        
        # Publish logout event
        publish_message("user_events", {
            "event_type": "user_logout",
            "user_id": current_user.id,
            "username": current_user.username,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during logout"
        )



@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, session: Session = Depends(get_session)):
    print(user_data)
    # Check if username exists
    existing_user = session.exec(select(User).where(User.username == user_data.username)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    existing_email = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
 
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=user_data.is_active,
        is_admin=user_data.is_admin
        # is_admin="true"
    )
    
    try:
        # Add user to the session and commit the transaction
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        logger.info(f"User {db_user.username} registered successfully")
        
        # Publish user registration event
        publish_message("user_events", {
            "event_type": "user_created",
            "user_id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,
            "is_active": db_user.is_active,
            "is_admin": db_user.is_admin,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        return db_user

    except Exception as e:
        # Handle any errors that occur during the commit
        logger.error(f"Error during user registration: {e}")
        session.rollback()  # Rollback the transaction in case of an error
        raise HTTPException(status_code=500, detail="User registration failed")

@auth_router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    session.add(current_user)
    session.commit()
    
    logger.info(f"Password changed for user {current_user.username}")
    
    # Publish password change event
    publish_message("user_events", {
        "event_type": "password_changed",
        "user_id": current_user.id,
        "username": current_user.username,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    return {"detail": "Password updated successfully"}

# User router
user_router = APIRouter()

@user_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@user_router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0, 
    limit: int = 100, 
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return users

@user_router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int, 
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@user_router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields if provided
    user_data = user_update.dict(exclude_unset=True)
    
    # Handle password update separately
    if "password" in user_data:
        password = user_data.pop("password")
        db_user.hashed_password = get_password_hash(password)
    
    # Update other fields
    for key, value in user_data.items():
        setattr(db_user, key, value)
    
    db_user.updated_at = datetime.datetime.now()
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    logger.info(f"User {db_user.username} updated successfully")
    
    # Publish user update event
    publish_message("user_events", {
        "event_type": "user_updated",
        "user_id": db_user.id,
        "username": db_user.username,
        "updated_fields": list(user_data.keys()),
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    return db_user

@user_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Store user info before deletion for event publishing
    user_info = {
        "user_id": db_user.id,
        "username": db_user.username
    }
    
    session.delete(db_user)
    session.commit()
    
    logger.info(f"User {user_info['username']} deleted successfully")
    
    # Publish user deletion event
    publish_message("user_events", {
        "event_type": "user_deleted",
        "user_id": user_info["user_id"],
        "username": user_info["username"],
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    return None