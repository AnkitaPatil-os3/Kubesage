from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from app.logger import logger

# Create database URL from settings
DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Function to create all tables
def create_db_and_tables():
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

# Function to get a database session
def get_session():
    with Session(engine) as session:
        yield session
