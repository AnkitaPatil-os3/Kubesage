from sqlmodel import SQLModel, Session, create_engine
from app.config import settings
from app.logger import logger
from fastapi import Depends
from typing import Annotated
from app.auth import get_current_user
from app.schemas import UserInfo  # Make sure this import exists

# Create database engine
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)

def create_db_and_tables():
    """Create database tables if they don't exist"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

def get_session():
    """Generate a new database session for dependency injection"""
    with Session(engine) as session:
        logger.debug(f"Creating new database session: {id(session)}")
        yield session
        logger.debug(f"Closing database session: {id(session)}")

# Add these functions to fix the import error
def get_db_session():
    """Return a database session dependency"""
    return Depends(get_session)

def get_current_user_dependency():
    """Return a current user dependency"""
    return Depends(get_current_user)

# Define common dependencies
SessionDep = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
