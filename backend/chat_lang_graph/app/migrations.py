"""
Database migration utilities for handling user creation and foreign key constraints.
"""

from sqlmodel import Session, select
from app.database import engine
from app.models import User, ChatSession, ChatMessage
from app.logger import logger
from datetime import datetime
from typing import Dict, Any

def ensure_user_exists(session: Session, user_data: Dict[str, Any]) -> User:
    """
    Ensure a user exists in the database, creating if necessary.
    This handles the foreign key constraint issue.
    """
    try:
        user_id = user_data.get("id")
        if not user_id:
            raise ValueError("User ID is required")
        
        # Try to get existing user
        user = session.get(User, user_id)
        if user:
            logger.info(f"✅ User {user_id} already exists")
            return user
        
        # Create new user
        user = User(
            id=user_id,
            username=user_data.get("username", f"user_{user_id}"),
            email=user_data.get("email", f"user_{user_id}@example.com"),
            hashed_password="",  # Managed by user service
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name", ""),
            is_active=user_data.get("is_active", True),
            is_admin=user_data.get("is_admin", False),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        logger.info(f"✅ Created new user: {user.username} (ID: {user.id})")
        return user
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error ensuring user exists: {e}")
        raise

def create_default_users():
    """Create default users for the system."""
    try:
        with Session(engine) as session:
            # Default users to create
            default_users = [
                {
                    "id": 1,
                    "username": "legacy_user",
                    "email": "legacy@example.com",
                    "first_name": "Legacy",
                    "last_name": "User",
                    "is_active": True,
                    "is_admin": False
                },
                {
                    "id": 2,
                    "username": "api_user",
                    "email": "api@example.com",
                    "first_name": "API",
                    "last_name": "User",
                    "is_active": True,
                    "is_admin": True
                }
            ]
            
            for user_data in default_users:
                ensure_user_exists(session, user_data)
                
            logger.info("✅ Default users created/verified successfully")
            
    except Exception as e:
        logger.error(f"❌ Error creating default users: {e}")
        raise

def migrate_orphaned_sessions():
    """
    Migrate any orphaned chat sessions to the default user.
    This fixes existing sessions that might have invalid user_ids.
    """
    try:
        with Session(engine) as session:
            # Find sessions with non-existent users
            orphaned_sessions = session.exec(
                select(ChatSession).where(
                    ~ChatSession.user_id.in_(
                        select(User.id)
                    )
                )
            ).all()
            
            if orphaned_sessions:
                logger.info(f"🔧 Found {len(orphaned_sessions)} orphaned sessions")
                
                # Ensure default user exists
                default_user_data = {
                    "id": 1,
                    "username": "legacy_user",
                    "email": "legacy@example.com",
                    "is_active": True,
                    "is_admin": False
                }
                default_user = ensure_user_exists(session, default_user_data)
                
                # Reassign orphaned sessions to default user
                for session_obj in orphaned_sessions:
                    session_obj.user_id = default_user.id
                    session.add(session_obj)
                
                session.commit()
                logger.info(f"✅ Migrated {len(orphaned_sessions)} orphaned sessions to default user")
            else:
                logger.info("✅ No orphaned sessions found")
                
    except Exception as e:
        logger.error(f"❌ Error migrating orphaned sessions: {e}")
        raise

def run_migrations():
    """Run all necessary migrations."""
    try:
        logger.info("🚀 Starting database migrations...")
        
        # Create default users
        create_default_users()
        
        # Migrate orphaned sessions
        migrate_orphaned_sessions()
        
        logger.info("🎉 Database migrations completed successfully")
        
    except Exception as e:
        logger.error(f"💥 Database migrations failed: {e}")
        raise

def check_database_integrity():
    """Check database integrity and report issues."""
    try:
        with Session(engine) as session:
            # Check for orphaned sessions
            orphaned_count = len(session.exec(
                select(ChatSession).where(
                    ~ChatSession.user_id.in_(
                        select(User.id)
                    )
                )
            ).all())
            
            # Check for orphaned messages
            orphaned_messages_count = len(session.exec(
                select(ChatMessage).where(
                    ~ChatMessage.session_id.in_(
                        select(ChatSession.session_id)
                    )
                )
            ).all())
            
            # Get total counts
            total_users = len(session.exec(select(User)).all())
            total_sessions = len(session.exec(select(ChatSession)).all())
            total_messages = len(session.exec(select(ChatMessage)).all())
            
            integrity_report = {
                "total_users": total_users,
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "orphaned_sessions": orphaned_count,
                "orphaned_messages": orphaned_messages_count,
                "integrity_ok": orphaned_count == 0 and orphaned_messages_count == 0
            }
            
            logger.info(f"📊 Database integrity report: {integrity_report}")
            return integrity_report
            
    except Exception as e:
        logger.error(f"❌ Error checking database integrity: {e}")
        return {"error": str(e), "integrity_ok": False}