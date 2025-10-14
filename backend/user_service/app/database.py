from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.logger import logger
from fastapi import HTTPException
from slowapi.errors import RateLimitExceeded

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

# Create SessionLocal
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session
)

def get_session():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        if isinstance(e, RateLimitExceeded):
            raise
        logger.error(f"Database session error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
    finally:
        db.close()
