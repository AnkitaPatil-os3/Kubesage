from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

engine = create_engine(settings.DATABASE_URL)

# Make sure your create_db_and_tables function includes the new model
# from app.models import WebhookUser  # ADD THIS IMPORT

def create_db_and_tables():
    """Create database tables - REMOVE DROP_ALL"""
    # Remove this line if it exists - it drops all tables:
    # SQLModel.metadata.drop_all(engine)  # <-- REMOVE THIS LINE
    
    # Only create tables, don't drop existing ones
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session





# psql -h your_host -U your_user -d your_database -c "
# ALTER TABLE incidents ADD COLUMN IF NOT EXISTS webhook_user_id INTEGER;
# ALTER TABLE incidents ADD CONSTRAINT IF NOT EXISTS fk_incidents_webhook_user 
# FOREIGN KEY (webhook_user_id) REFERENCES webhook_users(id);"

