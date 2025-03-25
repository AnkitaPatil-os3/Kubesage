from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import settings
from app.logger import logger
from fastapi import FastAPI, HTTPException


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
    print("Engine data ...... ", engine)
    try:
        with Session(engine) as session:
            yield session
    except Exception as e:
        logger.error(f"Error with database session: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

