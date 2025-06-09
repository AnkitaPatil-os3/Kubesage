from sqlmodel import Session, text
from app.database import engine
from app.logger import logger

def add_complete_json_data_column():
    """Add complete_json_data column to alerts table"""
    try:
        with Session(engine) as session:
            # Check if column already exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='alerts' AND column_name='complete_json_data';
            """)
            
            result = session.exec(check_column_query).first()
            
            if result:
                logger.info("Column 'complete_json_data' already exists")
                return True
            
            # Add the new column
            alter_query = text("""
                ALTER TABLE alerts 
                ADD COLUMN complete_json_data JSON DEFAULT '{}';
            """)
            
            session.exec(alter_query)
            session.commit()
            
            logger.info("Successfully added 'complete_json_data' column to alerts table")
            return True
            
    except Exception as e:
        logger.error(f"Error adding complete_json_data column: {e}")
        return False

if __name__ == "__main__":
    add_complete_json_data_column()