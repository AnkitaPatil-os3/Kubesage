#!/usr/bin/env python3
"""
PostgreSQL database setup script for onboarding service.
This script creates the database and tables.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from app.config import settings
from app.models import Base
import sys

def create_database():
    """Create the PostgreSQL database if it doesn't exist."""
    try:
        # Connect to PostgreSQL server (not to specific database)
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{settings.POSTGRES_DB}'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
            print(f"✅ Created database: {settings.POSTGRES_DB}")
        else:
            print(f"✅ Database already exists: {settings.POSTGRES_DB}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Error creating database: {e}")
        return False

def create_tables():
    """Create all tables using SQLAlchemy."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("✅ Created all database tables")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def test_connection():
    """Test database connection."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Database connection successful")
            print(f"PostgreSQL version: {version}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def show_tables():
    """Show created tables."""
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
                print("📋 Created tables:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("📋 No tables found")
            
        return True
    except Exception as e:
        print(f"❌ Error showing tables: {e}")
        return False

if __name__ == "__main__":
    print("🐘 PostgreSQL Database Setup for Onboarding Service")
    print("=" * 55)
    print(f"Host: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    print(f"Database: {settings.POSTGRES_DB}")
    print(f"User: {settings.POSTGRES_USER}")
    print()

    # Step 1: Create database
    print("1️⃣ Creating database...")
    if not create_database():
        sys.exit(1)

    # Step 2: Test connection
    print("\n2️⃣ Testing connection...")
    if not test_connection():
        sys.exit(1)

    # Step 3: Create tables
    print("\n3️⃣ Creating tables...")
    if not create_tables():
        sys.exit(1)

    # Step 4: Show created tables
    print("\n4️⃣ Verifying tables...")
    show_tables()

    print("\n🎉 Database setup completed successfully!")
    print("\nYou can now start the onboarding service:")
    print("  uvicorn app.main:app --host 0.0.0.0 --port 8007 --reload")