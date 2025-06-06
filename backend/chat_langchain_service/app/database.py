from sqlmodel import SQLModel, Session, create_engine
from app.config import settings
from app.logger import logger
 
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
 
 