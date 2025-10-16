#!/usr/bin/env python3
"""
Database management script for onboarding service.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from app.config import settings
from app.models import Base
import sys

def reset_database():
    """Reset the database by dropping and recreating it."""
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Drop database if exists
        cursor.execute(f'DROP DATABASE IF EXISTS "{settings.POSTGRES_DB}"')
        print(f"✅ Dropped database: {settings.POSTGRES_DB}")

        # Create fresh database
        cursor.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
        print(f"✅ Created fresh database: {settings.POSTGRES_DB}")
        
        cursor.close()
        conn.close()
        
        # Now create tables
        print("📋 Creating tables...")
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("✅ Created all tables")
        
        return True
        
    except (psycopg2.Error, Exception) as e:
        print(f"❌ Error resetting database: {e}")
        return False

def show_tables():
    """Show all tables in the database."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            
            if tables:
                print("📋 Tables in database:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("📋 No tables found in database")
                
            return True
    except Exception as e:
        print(f"❌ Error showing tables: {e}")
        return False

def show_data():
    """Show data in key tables."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Check if tables exist first
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('agents', 'cluster_configs')
                ORDER BY table_name
            """))
            existing_tables = [row[0] for row in result.fetchall()]
            
            if 'agents' in existing_tables:
                result = conn.execute(text("SELECT COUNT(*) FROM agents"))
                agent_count = result.fetchone()[0]
                print(f"👥 Agents: {agent_count}")
            else:
                print("👥 Agents table: Not found")
            
            if 'cluster_configs' in existing_tables:
                result = conn.execute(text("SELECT COUNT(*) FROM cluster_configs"))
                cluster_count = result.fetchone()[0]
                print(f"🔧 Clusters: {cluster_count}")
            else:
                print("🔧 Cluster_configs table: Not found")
            
            return True
    except Exception as e:
        print(f"❌ Error showing data: {e}")
        return False

def create_tables():
    """Create tables using SQLAlchemy models."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("✅ Created/updated all tables")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage_db.py [reset|tables|data|create-tables]")
        print("  reset         - Drop and recreate database")
        print("  tables        - Show all tables")
        print("  data          - Show data counts")
        print("  create-tables - Create tables from models")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    print(f"🐘 Database: {settings.DATABASE_URL}")
    print("=" * 50)
    
    if command == "reset":
        print("🔄 Resetting database...")
        if reset_database():
            print("✅ Database reset completed")
        else:
            sys.exit(1)
    elif command == "tables":
        show_tables()
    elif command == "data":
        show_data()
    elif command == "create-tables":
        print("📋 Creating tables...")
        if create_tables():
            show_tables()
        else:
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)