import threading
import asyncio
from app.queue import setup_consumer, start_consuming
from app.logger import logger
from app.user_cleanup_service import chat_cleanup_service
import time

def handle_user_event(message):
    """Handle events from user service"""
    try:
        event_type = message.get("event_type")
        logger.info(f"📨 Received user event: {event_type}")
        
        if event_type == "user_created":
            # A new user was created
            user_id = message.get("user_id")
            username = message.get("username")
            logger.info(f"👤 New user created: {username} (ID: {user_id})")
            
            # You could create default chat settings or welcome messages here
            
        elif event_type == "user_deleted":
            # Legacy user deletion event - redirect to new deletion system
            user_id = message.get("user_id")
            username = message.get("username")
            
            logger.warning(f"⚠️ Received legacy user_deleted event for user {username} (ID: {user_id})")
            logger.info("This should now be handled by the new user_deletion_initiated event")
            
        elif event_type in ["user_deletion_initiated", "user_deletion_retry"]:
            # New user deletion events
            logger.info(f"🗑️ Processing {event_type} event")
            
            # Run async cleanup in a new event loop
            def run_cleanup():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(chat_cleanup_service.handle_user_deletion_event(message))
                    loop.close()
                except Exception as e:
                    logger.error(f"❌ Error in cleanup thread: {str(e)}")
            
            # Run in separate thread to avoid blocking the consumer
            cleanup_thread = threading.Thread(target=run_cleanup)
            cleanup_thread.daemon = True
            cleanup_thread.start()
            
        elif event_type == "user_deletion_completed":
            # User deletion process completed
            operation_id = message.get("operation_id")
            user_id = message.get("user_id")
            username = message.get("username")
            status = message.get("status")
            
            logger.info(f"✅ User deletion completed for {username} (ID: {user_id}), operation: {operation_id}, status: {status}")
            
        else:
            logger.info(f"ℹ️ Ignoring user event type: {event_type}")
            
    except Exception as e:
        logger.error(f"❌ Error processing user event: {str(e)}")

def handle_chat_event(message):
    """Handle internal chat service events"""
    try:
        event_type = message.get("event_type")
        logger.info(f"💬 Received chat event: {event_type}")
        
        # Handle chat-specific events here
        if event_type == "session_created":
            session_id = message.get("session_id")
            user_id = message.get("user_id")
            logger.info(f"New chat session created: {session_id} for user {user_id}")
            
        elif event_type == "session_deleted":
            session_id = message.get("session_id")
            user_id = message.get("user_id")
            logger.info(f"Chat session deleted: {session_id} for user {user_id}")
            
    except Exception as e:
        logger.error(f"❌ Error processing chat event: {str(e)}")

def start_consumers():
    """Start background consumers for different event queues"""
    def consumer_thread_function():
        while True:
            try:
                # Set up consumers for different services
                consumers = [
                    ("user_events", handle_user_event),
                    ("chat_service_events", handle_chat_event),
                ]
                
                for queue_name, handler in consumers:
                    if setup_consumer(queue_name, handler):
                        logger.info(f"✅ Set up consumer for {queue_name}")
                    else:
                        logger.warning(f"⚠️ Failed to set up consumer for {queue_name}")
                
                # Start consuming if at least one consumer was set up successfully
                start_consuming()
                
            except Exception as e:
                logger.error(f"❌ Consumer thread error: {str(e)}")
                time.sleep(5)  # Wait before trying to reconnect
    
    try:
        # Start consuming in background thread
        consumer_thread = threading.Thread(target=consumer_thread_function, daemon=True)
        consumer_thread.start()
        logger.info("🚀 Event consumers started in background thread")
        
    except Exception as e:
        logger.error(f"❌ Failed to start consumers: {str(e)}")
        raise

def stop_consumers():
    """Stop all consumers gracefully"""
    try:
        logger.info("🛑 Stopping event consumers...")
        # Implementation depends on your queue system
        
    except Exception as e:
        logger.error(f"❌ Error stopping consumers: {str(e)}")