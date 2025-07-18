import json
import httpx
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlmodel import Session, select
from app.database import get_session, engine
from app.models import ChatSession, ChatMessage, User
from app.queue import publish_message
from app.logger import logger
from app.config import settings


class ChatUserCleanupService:
    """Service to handle user data cleanup in chat service"""
    
    def __init__(self):
        self.user_service_url = getattr(settings, 'USER_SERVICE_URL', "https://10.0.32.103:8001")
    
    async def handle_user_deletion_event(self, event_data: Dict[str, Any]):
        """Handle user deletion event from user service"""
        try:
            event_type = event_data.get("event_type")
            
            if event_type == "user_deletion_initiated":
                await self._process_user_deletion(event_data)
            elif event_type == "user_deletion_retry":
                await self._process_user_deletion_retry(event_data)
            else:
                logger.info(f"Ignoring event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling user deletion event: {str(e)}")
    
    async def _process_user_deletion(self, event_data: Dict[str, Any]):
        """Process user deletion request"""
        try:
            operation_id = event_data.get("operation_id")
            user_id = event_data.get("user_id")
            username = event_data.get("username")
            callback_url = event_data.get("callback_url")
            
            logger.info(f"🗑️ Processing user deletion for user {username} (ID: {user_id}), operation: {operation_id}")
            
            # Perform cleanup
            await self._perform_user_cleanup(operation_id, user_id, username, callback_url)
                
        except Exception as e:
            logger.error(f"❌ Error processing user deletion: {str(e)}")
            await self._send_cleanup_failure(event_data, str(e))
    
    async def _process_user_deletion_retry(self, event_data: Dict[str, Any]):
        """Process user deletion retry request"""
        try:
            operation_id = event_data.get("operation_id")
            services_to_retry = event_data.get("services_to_retry", [])
            
            if "chat_service" not in services_to_retry:
                logger.info(f"Chat service not in retry list for operation {operation_id}")
                return
            
            logger.info(f"🔄 Processing user deletion retry for operation: {operation_id}")
            
            user_id = event_data.get("user_id")
            username = event_data.get("username")
            callback_url = event_data.get("callback_url")
            
            # Retry cleanup
            await self._perform_user_cleanup(operation_id, user_id, username, callback_url)
                
        except Exception as e:
            logger.error(f"❌ Error processing user deletion retry: {str(e)}")
    
    async def _perform_user_cleanup(
        self, 
        operation_id: str,
        user_id: int,
        username: str,
        callback_url: Optional[str] = None
    ):
        """Perform the actual user data cleanup"""
        try:
            logger.info(f"🧹 Starting cleanup for user {username} (ID: {user_id})")
            
            with Session(engine) as session:
                # Find all chat sessions for this user
                chat_sessions = session.exec(
                    select(ChatSession).where(ChatSession.user_id == user_id)
                ).all()
                
                logger.info(f"📊 Found {len(chat_sessions)} chat sessions to cleanup for user {username}")
                
                # Cleanup details
                cleanup_details = {
                    "sessions_deleted": [],
                    "messages_deleted": 0,
                    "total_sessions": len(chat_sessions),
                    "cleanup_timestamp": datetime.utcnow().isoformat()
                }
                
                total_messages_deleted = 0
                
                # Delete all chat sessions and their messages
                for chat_session in chat_sessions:
                    try:
                        session_id = chat_session.session_id
                        logger.info(f"🗑️ Deleting chat session: {session_id}")
                        
                        # Find and delete all messages for this session
                        messages = session.exec(
                            select(ChatMessage).where(ChatMessage.session_id == session_id)
                        ).all()
                        
                        message_count = len(messages)
                        for message in messages:
                            session.delete(message)
                        
                        # Delete the session
                        session.delete(chat_session)
                        
                        total_messages_deleted += message_count
                        
                        cleanup_details["sessions_deleted"].append({
                            "session_id": session_id,
                            "title": chat_session.title,
                            "messages_count": message_count,
                            "created_at": chat_session.created_at.isoformat() if chat_session.created_at else None,
                            "deleted_at": datetime.utcnow().isoformat()
                        })
                        
                    except Exception as e:
                        logger.error(f"❌ Error deleting chat session {chat_session.session_id}: {str(e)}")
                        # Continue with other sessions even if one fails
                
                cleanup_details["messages_deleted"] = total_messages_deleted
                
                # Also clean up the user record if it exists in our local database
                local_user = session.exec(
                    select(User).where(User.id == user_id)
                ).first()
                
                if local_user:
                    logger.info(f"🗑️ Deleting local user record for {username}")
                    session.delete(local_user)
                    cleanup_details["local_user_deleted"] = True
                else:
                    cleanup_details["local_user_deleted"] = False
                
                # Commit all deletions
                session.commit()
                
                logger.info(f"✅ Successfully cleaned up {len(chat_sessions)} chat sessions and {total_messages_deleted} messages for user {username}")
                
                # Send success acknowledgment
                await self._send_cleanup_success(operation_id, user_id, username, cleanup_details, callback_url)
            
        except Exception as e:
            logger.error(f"❌ Error performing user cleanup: {str(e)}")
            
            # Send failure acknowledgment
            await self._send_cleanup_failure({
                "operation_id": operation_id,
                "user_id": user_id,
                "username": username
            }, str(e), callback_url)
    
    async def _send_cleanup_success(
        self, 
        operation_id: str,
        user_id: int,
        username: str,
        cleanup_details: Dict[str, Any],
        callback_url: Optional[str] = None
    ):
        """Send cleanup success acknowledgment to user service"""
        try:
            # Prepare acknowledgment data
            ack_data = {
                "operation_id": operation_id,
                "service_name": "chat_service",
                "user_id": user_id,
                "status": "completed",
                "cleanup_details": cleanup_details
            }
            
            # Send via message queue
            success_event = {
                "event_type": "user_cleanup_completed",
                "operation_id": operation_id,
                "user_id": user_id,
                "username": username,
                "service_name": "chat_service",
                "status": "completed",
                "cleanup_details": cleanup_details,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            publish_message("user_events", success_event)
            logger.info(f"📤 Published cleanup success event for operation {operation_id}")
            
            # Also send HTTP callback if URL provided
            if callback_url:
                await self._send_http_callback(callback_url, ack_data)
                
        except Exception as e:
            logger.error(f"❌ Error sending cleanup success acknowledgment: {str(e)}")
    
    async def _send_cleanup_failure(
        self, 
        event_data: Dict[str, Any], 
        error_message: str,
        callback_url: Optional[str] = None
    ):
        """Send cleanup failure acknowledgment to user service"""
        try:
            operation_id = event_data.get("operation_id")
            user_id = event_data.get("user_id")
            username = event_data.get("username")
            
            # Prepare acknowledgment data
            ack_data = {
                "operation_id": operation_id,
                "service_name": "chat_service",
                "user_id": user_id,
                "status": "failed",
                "error_message": error_message
            }
            
            # Send via message queue
            failure_event = {
                "event_type": "user_cleanup_completed",
                "operation_id": operation_id,
                "user_id": user_id,
                "username": username,
                "service_name": "chat_service",
                "status": "failed",
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            publish_message("user_events", failure_event)
            logger.info(f"📤 Published cleanup failure event for operation {operation_id}")
            
            # Also send HTTP callback if URL provided
            if callback_url:
                await self._send_http_callback(callback_url, ack_data)
                
        except Exception as e:
            logger.error(f"❌ Error sending cleanup failure acknowledgment: {str(e)}")
    
    async def _send_http_callback(self, callback_url: str, ack_data: Dict[str, Any]):
        """Send HTTP callback to user service"""
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    callback_url,
                    json=ack_data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Successfully sent HTTP callback for operation {ack_data['operation_id']}")
                else:
                    logger.error(f"❌ HTTP callback failed with status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"❌ Error sending HTTP callback: {str(e)}")


# Global instance
chat_cleanup_service = ChatUserCleanupService()