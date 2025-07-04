from sqlmodel import Session
from fastapi import Depends
from typing import Annotated
from .database import get_db
from .auth import get_current_user
from .models import UserInfo

def get_db_session():
    """Return a database session dependency"""
    return Depends(get_db)

def get_current_user_dependency():
    """Return a current user dependency"""
    return Depends(get_current_user)

# Define common dependencies
SessionDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
