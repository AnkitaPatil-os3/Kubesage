from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text, inspect
from .config import settings
from .logger import logger
import time

# Create database engine with better error handling
def create_database_engine():
    """Create database engine with retry logic."""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=10,
                max_overflow=20,
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "k_chat_lang_db"
                }
            )
            
            # Test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info(f"Database connection established successfully on attempt {attempt + 1}")
            return engine
            
        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("All database connection attempts failed")
                raise

# Create the engine
engine = create_database_engine()

def create_db_and_tables():
    """Create database tables with proper error handling."""
    try:
        # Import models to ensure they're registered
        from .models import User, ChatSession, ChatMessage
        
        # Check existing schema
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        logger.info(f"Existing tables: {existing_tables}")
        
        # Create tables (only creates missing ones)
        SQLModel.metadata.create_all(engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()
        logger.info(f"Tables after creation: {new_tables}")
        
        logger.info("Database tables created/verified successfully")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        # Don't raise the exception, just log it
        logger.warning("Continuing with existing schema...")

def get_db():
    """Get database session."""
    try:
        with Session(engine) as session:
            yield session
    except Exception as e:
        logger.error(f"Error getting database session: {e}")
        raise

def test_database_connection():
    """Test database connection for health checks."""
    try:
        with Session(engine) as session:
            session.execute(text("SELECT 1"))
            return {"status": "healthy", "message": "Database connection successful"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

def get_database_stats():
    """Get database statistics."""
    try:
        with Session(engine) as session:
            from .models import User, ChatSession, ChatMessage
            
            users_count = session.query(User).count()
            sessions_count = session.query(ChatSession).count()
            messages_count = session.query(ChatMessage).count()
            
            return {
                "users": users_count,
                "sessions": sessions_count,
                "messages": messages_count,
                "timestamp": time.time()
            }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {"error": str(e)}

def check_table_schema():
    """Check and log table schema for debugging."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        schema_info = {}
        for table in tables:
            columns = inspector.get_columns(table)
            schema_info[table] = [col['name'] for col in columns]
            logger.info(f"Table {table} columns: {schema_info[table]}")
        
        return schema_info
            
    except Exception as e:
        logger.error(f"Error checking table schema: {e}")
        return {"error": str(e)}