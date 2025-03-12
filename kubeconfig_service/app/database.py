from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from app.logger import logger

connect_args = {"check_same_thread": False}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

def create_db_and_tables():
    logger.info("Creating database and tables if they don't exist")
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
