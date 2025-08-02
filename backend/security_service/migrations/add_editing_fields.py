"""
Database migration to add editing fields to policy_applications table
"""

from sqlalchemy import text
from app.database import engine

def upgrade():
    """Add new columns for editing functionality"""
    with engine.connect() as connection:
        # Add original_yaml column
        connection.execute(text("""
            ALTER TABLE policy_applications 
            ADD COLUMN IF NOT EXISTS original_yaml TEXT;
        """))
        
        # Add is_edited column
        connection.execute(text("""
            ALTER TABLE policy_applications 
            ADD COLUMN IF NOT EXISTS is_edited BOOLEAN DEFAULT FALSE;
        """))
        
        # Update existing records to set is_edited = FALSE
        connection.execute(text("""
            UPDATE policy_applications 
            SET is_edited = FALSE 
            WHERE is_edited IS NULL;
        """))
        
        connection.commit()
        print("✅ Migration completed: Added original_yaml and is_edited columns")

def downgrade():
    """Remove the added columns"""
    with engine.connect() as connection:
        connection.execute(text("""
            ALTER TABLE policy_applications 
            DROP COLUMN IF EXISTS original_yaml;
        """))
        
        connection.execute(text("""
            ALTER TABLE policy_applications 
            DROP COLUMN IF EXISTS is_edited;
        """))
        
        connection.commit()
        print("✅ Migration rolled back: Removed original_yaml and is_edited columns")

if __name__ == "__main__":
    upgrade()