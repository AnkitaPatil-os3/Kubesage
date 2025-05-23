from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from app.logger import logger
from fastapi import HTTPException
from slowapi.errors import RateLimitExceeded

# Modified to use PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

def create_db_and_tables():
    logger.info("Creating database and tables if they don't exist")
    SQLModel.metadata.create_all(engine)


def get_session():
    try:
        with Session(engine) as session:
            yield session
    except Exception as e:
        # Propagate rate limit exceptions
        if isinstance(e, RateLimitExceeded) or "429" in str(e):
            logger.warning(f"Rate limit exceeded: {e}")
            raise
        # Handle authentication errors
        if "401" in str(e) or "authentication" in str(e).lower() or "credentials" in str(e).lower():
            logger.warning(f"Authentication error: {e}")
            raise HTTPException(
                status_code=401, 
                detail="Authentication failed. Please check your token or login again."
            )
        # Log other errors
        logger.error(f"Error with database session: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
