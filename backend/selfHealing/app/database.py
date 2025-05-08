from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from app.models import Plan, Action, RawEvent, Incident, ExecutionResult  # Import all models



# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

def create_db_and_tables():
    """Create database tables if they don't exist"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Get a database session"""
    with Session(engine) as session:
        yield session
