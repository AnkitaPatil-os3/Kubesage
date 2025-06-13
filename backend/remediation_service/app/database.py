from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

engine = create_engine(settings.DATABASE_URL)

def create_db_and_tables():
    """Create database tables - REMOVE DROP_ALL"""
    # Remove this line if it exists - it drops all tables:
    # SQLModel.metadata.drop_all(engine)  # <-- REMOVE THIS LINE
    
    # Only create tables, don't drop existing ones
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session