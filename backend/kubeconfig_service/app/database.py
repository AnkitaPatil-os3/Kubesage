from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from app.logger import logger

# Modified to use PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

def create_db_and_tables():
    logger.info("Creating database and tables if they don't exist")
    # Drop all tables and recreate them (WARNING: This will delete all data)
    # SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
