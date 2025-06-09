from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import re
import html

from app.models import ChatSession, ChatMessage, User
from app.logger import logger

class MessageService:
    """Service for handling message operations and validation."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def validate_message_content(self, content: str) -> bool:
        """Validate message content."""
        if not content or not content.strip():
            return False
        
        if len(content) > 10000:  # Max message length
            return False
        
        # Check for potentially harmful content
        harmful_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
        for pattern in harmful_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False
        
        return True
    
    def sanitize_message_content(self, content: str) -> str:
        """Sanitize message content."""
        # HTML escape
        content = html.escape(content)
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Limit length
        if len(content) > 10000:
            content = content[:10000] + "..."
        
        return content
    
    def should_save_message(self, role: str, content: str, success: bool = True) -> bool:
        """Determine if a message should be saved to database."""
        # Don't save failed AI responses
        if role == "assistant" and not success:
            return False
        
        # Don't save empty messages
        if not content or not content.strip():
            return False
        
        # Don't save error messages
        if "error" in content.lower() and role == "assistant":
            return False
        
        return True

class ChatService:
    """Service for handling chat session operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_session(self, user_id: int, title: str = "New Chat") -> ChatSession:
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
            
            logger.info(f"Created new chat session: {chat_session.session_id}")
            return chat_session
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating chat session: {e}")
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
            logger.error(f"Error getting chat session: {e}")
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
            
            return self.session.exec(statement).all()
            
        except Exception as e:
            logger.error(f"Error listing user sessions: {e}")
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
            
            logger.info(f"Updated chat session: {session_id}")
            return chat_session
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating chat session: {e}")
            return None
    
    def delete_session(self, session_id: str, user_id: int) -> bool:
        """Delete a chat session and all its messages."""
        try:
            chat_session = self.get_session(session_id, user_id)
            if not chat_session:
                return False
            
            # Delete all messages first
            self.session.exec(
                select(ChatMessage).where(ChatMessage.session_id == session_id)
            ).all()
            
            for message in self.session.exec(
                select(ChatMessage).where(ChatMessage.session_id == session_id)
            ).all():
                self.session.delete(message)
            
            # Delete the session
            self.session.delete(chat_session)
            self.session.commit()
            
            logger.info(f"Deleted chat session: {session_id}")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting chat session: {e}")
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
            
            logger.info(f"Added message to session {session_id}: {role}")
            return message
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding message: {e}")
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
            
            return self.session.exec(statement).all()
            
        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
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
            
            logger.info(f"Cleared messages for session: {session_id}")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error clearing session messages: {e}")
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
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "recent_sessions": len(recent_sessions),
                "last_activity": max(
                    [s.updated_at for s in user_sessions], 
                    default=None
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "total_messages": 0,
                "recent_sessions": 0,
                "last_activity": None
            }

class AnalyticsService:
    """Service for handling analytics and usage tracking."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def track_message(self, user_id: int, session_id: str, role: str, content_length: int):
        """Track message for analytics."""
        try:
            # This could be expanded to store detailed analytics
            logger.info(f"Message tracked: user={user_id}, session={session_id}, role={role}, length={content_length}")
            
        except Exception as e:
            logger.error(f"Error tracking message: {e}")
    
    def get_usage_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get usage statistics."""
        try:
            # Basic stats - can be expanded
            if user_id:
                sessions = self.session.exec(
                    select(ChatSession).where(ChatSession.user_id == user_id)
                ).all()
            else:
                sessions = self.session.exec(select(ChatSession)).all()
            
            total_sessions = len(sessions)
            active_sessions = len([s for s in sessions if s.is_active])
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "timestamp": datetime.utcnow().isoformat()
            }