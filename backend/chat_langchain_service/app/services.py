from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import re
import html

from app.models import ChatSession, ChatMessage, User
from app.logger import logger
from app.config import settings

class MessageService:
    """Service for handling message operations and validation."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def validate_message_content(self, content: str) -> bool:
        """Validate message content with relaxed rules."""
        if not content or not content.strip():
            return False
        
        if len(content) > settings.MAX_MESSAGE_LENGTH:
            return False
        
        return True
    
    def sanitize_message_content(self, content: str) -> str:
        """Light sanitization preserving kubectl commands and YAML."""
        # Remove excessive whitespace but preserve structure
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Max 2 consecutive newlines
        content = content.strip()
        
        # Limit length
        if len(content) > settings.MAX_MESSAGE_LENGTH:
            content = content[:settings.MAX_MESSAGE_LENGTH] + "... (message truncated)"
        
        return content

class ChatService:
    """Service for handling chat session operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_session(self, user_id: int, title: str = "Kubernetes Chat") -> ChatSession:
        """Create a new chat session."""
        try:
            chat_session = ChatSession(
                user_id=user_id,
                title=title,
                is_active=True
            )
            
            self.session.add(chat_session)
            self.session.commit()
            self.session.refresh(chat_session)
            
            logger.info(f"✅ Created new chat session: {chat_session.session_id}")
            return chat_session
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error creating chat session: {e}")
            raise
    
    def get_session(self, session_id: str, user_id: int) -> Optional[ChatSession]:
        """Get a chat session by ID and user."""
        try:
            statement = select(ChatSession).where(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            )
            return self.session.exec(statement).first()
            
        except Exception as e:
            logger.error(f"❌ Error getting chat session: {e}")
            return None
    
    def list_user_sessions(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 50,
        include_inactive: bool = False
    ) -> List[ChatSession]:
        """List user's chat sessions."""
        try:
            statement = select(ChatSession).where(ChatSession.user_id == user_id)
            
            if not include_inactive:
                statement = statement.where(ChatSession.is_active == True)
            
            statement = statement.order_by(ChatSession.updated_at.desc())
            statement = statement.offset(skip).limit(limit)
            
            sessions = self.session.exec(statement).all()
            logger.info(f"📋 Retrieved {len(sessions)} sessions for user {user_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Error listing user sessions: {e}")
            return []
    
    def update_session(
        self, 
        session_id: str, 
        user_id: int, 
        updates: Dict[str, Any]
    ) -> Optional[ChatSession]:
        """Update a chat session."""
        try:
            chat_session = self.get_session(session_id, user_id)
            if not chat_session:
                return None
            
            for key, value in updates.items():
                if hasattr(chat_session, key):
                    setattr(chat_session, key, value)
            
            chat_session.updated_at = datetime.utcnow()
            
            self.session.add(chat_session)
            self.session.commit()
            self.session.refresh(chat_session)
            
            logger.info(f"✅ Updated chat session: {session_id}")
            return chat_session
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error updating chat session: {e}")
            return None
    
    def delete_session(self, session_id: str, user_id: int) -> bool:
        """Delete a chat session and all its messages."""
        try:
            chat_session = self.get_session(session_id, user_id)
            if not chat_session:
                return False
            
            # Delete all messages first
            messages = self.session.exec(
                select(ChatMessage).where(ChatMessage.session_id == session_id)
            ).all()
            
            for message in messages:
                self.session.delete(message)
            
            # Delete the session
            self.session.delete(chat_session)
            self.session.commit()
            
            logger.info(f"🗑️ Deleted chat session: {session_id}")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error deleting chat session: {e}")
            return False
    
    def add_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        """Add a message to a chat session."""
        try:
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content
            )
            
            self.session.add(message)
            self.session.commit()
            self.session.refresh(message)
            
            # Update session timestamp
            statement = select(ChatSession).where(ChatSession.session_id == session_id)
            chat_session = self.session.exec(statement).first()
            if chat_session:
                chat_session.updated_at = datetime.utcnow()
                self.session.add(chat_session)
                self.session.commit()
            
            logger.info(f"💾 Added {role} message to session {session_id}")
            return message
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error adding message: {e}")
            raise
    
    def get_session_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get messages for a chat session."""
        try:
            statement = select(ChatMessage).where(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at.asc())
            
            if limit:
                statement = statement.limit(limit)
            
            messages = self.session.exec(statement).all()
            logger.info(f"📚 Retrieved {len(messages)} messages for session {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error getting session messages: {e}")
            return []
    
    def clear_session_messages(self, session_id: str, user_id: int) -> bool:
        """Clear all messages in a session."""
        try:
            # Verify session ownership
            chat_session = self.get_session(session_id, user_id)
            if not chat_session:
                return False
            
            # Delete all messages
            messages = self.session.exec(
                select(ChatMessage).where(ChatMessage.session_id == session_id)
            ).all()
            
            for message in messages:
                self.session.delete(message)
            
            self.session.commit()
            
            logger.info(f"🧹 Cleared {len(messages)} messages for session: {session_id}")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error clearing session messages: {e}")
            return False
    
    def get_session_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for user's chat sessions."""
        try:
            # Total sessions
            total_sessions = len(self.list_user_sessions(user_id, include_inactive=True))
            
            # Active sessions
            active_sessions = len(self.list_user_sessions(user_id, include_inactive=False))
            
            # Total messages
            user_sessions = self.list_user_sessions(user_id, include_inactive=True)
            total_messages = 0
            
            for session in user_sessions:
                messages = self.get_session_messages(session.session_id)
                total_messages += len(messages)
            
            # Recent activity (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_sessions = self.session.exec(
                select(ChatSession).where(
                    ChatSession.user_id == user_id,
                    ChatSession.updated_at >= week_ago
                )
            ).all()
            
            stats = {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "recent_sessions": len(recent_sessions),
                "last_activity": max(
                    [s.updated_at for s in user_sessions], 
                    default=None
                )
            }
            
            logger.info(f"📊 Generated stats for user {user_id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting session stats: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "total_messages": 0,
                "recent_sessions": 0,
                "last_activity": None,
                "error": str(e)
            }
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Clean up old inactive sessions."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Find old inactive sessions
            old_sessions = self.session.exec(
                select(ChatSession).where(
                    ChatSession.is_active == False,
                    ChatSession.updated_at < cutoff_date
                )
            ).all()
            
            cleaned_count = 0
            for session in old_sessions:
                # Delete messages first
                messages = self.session.exec(
                    select(ChatMessage).where(ChatMessage.session_id == session.session_id)
                ).all()
                
                for message in messages:
                    self.session.delete(message)
                
                # Delete session
                self.session.delete(session)
                cleaned_count += 1
            
            self.session.commit()
            
            logger.info(f"🧹 Cleaned up {cleaned_count} old sessions")
            return cleaned_count
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error cleaning up old sessions: {e}")
            return 0

class AnalyticsService:
    """Service for handling analytics and usage tracking."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def track_chat_interaction(
        self, 
        user_id: int, 
        session_id: str, 
        message_length: int,
        response_time: float,
        errors_included: bool = False
    ):
        """Track chat interaction for analytics."""
        try:
            interaction_data = {
                "user_id": user_id,
                "session_id": session_id,
                "message_length": message_length,
                "response_time": response_time,
                "errors_included": errors_included,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"📈 Tracked interaction: {interaction_data}")
            
        except Exception as e:
            logger.error(f"❌ Error tracking interaction: {e}")
    
    def get_usage_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get usage statistics."""
        try:
            base_query = select(ChatSession)
            if user_id:
                base_query = base_query.where(ChatSession.user_id == user_id)
            
            sessions = self.session.exec(base_query).all()
            
            # Calculate stats
            total_sessions = len(sessions)
            active_sessions = len([s for s in sessions if s.is_active])
            
            # Get message counts
            total_messages = 0
            for session in sessions:
                messages = self.session.exec(
                    select(ChatMessage).where(ChatMessage.session_id == session.session_id)
                ).all()
                total_messages += len(messages)
            
            # Recent activity (last 24 hours)
            day_ago = datetime.utcnow() - timedelta(days=1)
            recent_sessions = [s for s in sessions if s.updated_at >= day_ago]
            
            stats = {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "recent_sessions_24h": len(recent_sessions),
                "average_messages_per_session": total_messages / max(total_sessions, 1),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if user_id:
                stats["user_id"] = user_id
            
            logger.info(f"📊 Generated usage stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting usage stats: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "total_messages": 0,
                "recent_sessions_24h": 0,
                "average_messages_per_session": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def get_error_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about error collection usage."""
        try:
            # This would be enhanced with actual tracking data
            # For now, return basic info
            stats = {
                "error_collection_enabled": settings.COLLECT_ERRORS_ON_NEW_CHAT,
                "max_errors_per_type": settings.MAX_ERRORS_PER_TYPE,
                "collection_timeout": settings.ERROR_COLLECTION_TIMEOUT,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting error collection stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

class HealthService:
    """Service for health checks and monitoring."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start_time = datetime.utcnow()
            
            # Test basic query
            result = self.session.exec(select(ChatSession).limit(1)).first()
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time_seconds": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get basic service metrics."""
        try:
            # Count total sessions and messages
            total_sessions = len(self.session.exec(select(ChatSession)).all())
            total_messages = len(self.session.exec(select(ChatMessage)).all())
            
            # Count active sessions (updated in last 24 hours)
            day_ago = datetime.utcnow() - timedelta(days=1)
            active_sessions = len(self.session.exec(
                select(ChatSession).where(ChatSession.updated_at >= day_ago)
            ).all())
            
            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "active_sessions_24h": active_sessions,
                "average_messages_per_session": total_messages / max(total_sessions, 1),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting service metrics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
