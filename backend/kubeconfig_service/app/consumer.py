import threading
from app.queue import setup_consumer, start_consuming
from app.logger import logger
from app.database import get_session
from app.models import Kubeconf
from sqlmodel import select, Session
import os

def handle_user_event(message):
    """Handle events from user service"""
    event_type = message.get("event_type")
    logger.info(f"Received user event: {event_type}")
    
    if event_type == "user_created":
        # A new user was created - you might want to set up default kubeconfigs
        user_id = message.get("user_id")
        username = message.get("username")
        logger.info(f"New user created: {username} (ID: {user_id})")
        
        # You could create default resources or permissions if needed
        
    elif event_type == "user_deleted":
        # A user was deleted - clean up their kubeconfigs
        user_id = message.get("user_id")
        
        with Session() as session:
            kubeconfigs = session.exec(
                select(Kubeconf).where(Kubeconf.user_id == user_id)
            ).all()
            
            for kubeconf in kubeconfigs:
                # Remove the file from disk if it exists
                if os.path.exists(kubeconf.path):
                    try:
                        os.remove(kubeconf.path)
                    except Exception as e:
                        logger.error(f"Error removing kubeconfig file {kubeconf.path}: {str(e)}")
                
                # Remove from database
                session.delete(kubeconf)
            
            session.commit()
            logger.info(f"Deleted {len(kubeconfigs)} kubeconfigs for user {user_id}")

def start_consumers():
    """Start background consumers for different event queues"""
    # Set up consumer for user events
    setup_consumer("user_events", handle_user_event)
    
    # Start consuming in background thread
    consumer_thread = threading.Thread(target=start_consuming)
    consumer_thread.daemon = True
    consumer_thread.start()
    logger.info("Event consumers started in background")