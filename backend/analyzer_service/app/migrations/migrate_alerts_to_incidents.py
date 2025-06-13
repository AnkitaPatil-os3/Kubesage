from sqlmodel import create_engine, text
from app.database import get_database_url
from app.logger import logger

def migrate_alerts_to_incidents():
    """Migrate from alerts table to incidents table"""
    engine = create_engine(get_database_url())
    
    try:
        with engine.connect() as connection:
            # Drop the old alerts table if it exists
            connection.execute(text("DROP TABLE IF EXISTS alerts CASCADE;"))
            logger.info("Dropped old alerts table")
            
            # Create the new incidents table
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id VARCHAR PRIMARY KEY,
                    metadata_name VARCHAR NOT NULL,
                    metadata_namespace VARCHAR,
                    metadata_creation_timestamp TIMESTAMP,
                    type VARCHAR NOT NULL,
                    reason VARCHAR NOT NULL,
                    message VARCHAR NOT NULL,
                    count INTEGER DEFAULT 1,
                    first_timestamp TIMESTAMP,
                    last_timestamp TIMESTAMP,
                    source_component VARCHAR,
                    source_host VARCHAR,
                    involved_object_kind VARCHAR,
                    involved_object_name VARCHAR,
                    involved_object_field_path VARCHAR,
                    involved_object_labels JSON DEFAULT '{}',
                    involved_object_annotations JSON DEFAULT '{}',
                    involved_object_owner_references JSON DEFAULT '{}',
                    reporting_component VARCHAR,
                    reporting_instance VARCHAR
                );
            """))
            
            # Create indexes for better query performance
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_incidents_type ON incidents(type);"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_incidents_namespace ON incidents(metadata_namespace);"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_incidents_kind ON incidents(involved_object_kind);"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_incidents_creation_time ON incidents(metadata_creation_timestamp);"))
            
            connection.commit()
            logger.info("Successfully created incidents table with indexes")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise e

if __name__ == "__main__":
    migrate_alerts_to_incidents()