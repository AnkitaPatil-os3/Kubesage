from fastapi import Depends, HTTPException, status
from typing import Callable, Annotated
from sqlmodel import Session
from app.database import get_session
from app.auth import get_current_user
from app.schemas import UserInfo

# Define callable functions that return dependencies
def get_db_session():
    """Return a database session dependency"""
    return Depends(get_session)

def get_current_user_dependency():
    print("check .....")
    """Return a current user dependency"""
    return Depends(get_current_user)

# You can keep these for compatibility, but they won't be used in routes.py
# if you're providing default values there
SessionDep = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
