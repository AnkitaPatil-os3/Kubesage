#!/usr/bin/env python3
"""
Initialize database with all required tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import SQLModel, create_engine, text
from app.config import settings
from app.models import User, UserToken, RefreshToken, ApiKey
from app.logger import logger

def init_database():
    """Initialize database with all required tables"""
    
    print("🔄 Initializing database...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        print("🔨 Creating all tables...")
        SQLModel.metadata.create_all(engine)
        
        print("✅ Database initialized successfully!")
        
        # List created tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Created tables: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        logger.error(f"Database initialization error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
