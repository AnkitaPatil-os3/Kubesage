from sqlmodel import SQLModel, create_engine, Session
from app.models import IncidentModel  # Import the new model
import os

def get_database_url():
    """Get database URL from environment variables"""
    user = os.getenv("POSTGRES_USER", "nisha")
    password = os.getenv("POSTGRES_PASSWORD", "linux")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "n_analyzer_db")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

engine = create_engine(get_database_url())

def create_db_and_tables():
    """Create database and tables"""
    try:
        # Drop and recreate tables to ensure schema is correct
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        raise

def get_session():
    """Get database session"""
    with Session(engine) as session:
        yield session
