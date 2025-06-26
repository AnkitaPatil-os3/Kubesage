from app.database import engine
from app.models import SQLModel
from app.logger import logger

def recreate_tables():
    logger.info("Dropping and recreating all tables...")
    # This will drop all existing tables and recreate them
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    logger.info("Tables recreated successfully!")

if __name__ == "__main__":
    recreate_tables()

