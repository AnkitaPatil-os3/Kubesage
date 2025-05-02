from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from app.logger import logger

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

def create_db_and_tables():
    logger.info("Creating database and tables if they don't exist")
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
