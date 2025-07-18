import threading
from app.queue import setup_consumer, start_consuming
from app.logger import logger
from app.deletion_service import deletion_service
from app.database import get_session
from sqlmodel import Session
import time

def handle_kubeconfig_event(message):
    """Handle events from kubeconfig service"""
    try:
        event_type = message.get("event_type")
        logger.info(f"Received kubeconfig event: {event_type}")
        
        if event_type == "kubeconfig_created":
            # Process new kubeconfig creation
            user_id = message.get("user_id")
            cluster_name = message.get("cluster_name")
            logger.info(f"New kubeconfig created for user {user_id}, cluster: {cluster_name}")
            
        elif event_type == "kubeconfig_deleted":
            # Handle kubeconfig deletion
            user_id = message.get("user_id")
            cluster_name = message.get("cluster_name")
            logger.info(f"Kubeconfig deleted for user {user_id}, cluster: {cluster_name}")
            
        elif event_type == "user_cleanup_completed":
            # Handle cleanup completion acknowledgment from kubeconfig service
            operation_id = message.get("operation_id")
            user_id = message.get("user_id")
            status = message.get("status", "completed")
            cleanup_details = message.get("cleanup_details")
            error_message = message.get("error_message")
            
            logger.info(f"Received cleanup completion from kubeconfig service: {operation_id}")
            
            with Session(next(get_session())) as session:
                deletion_service.handle_service_cleanup_ack(
                    operation_id=operation_id,
                    service_name="kubeconfig_service",
                    user_id=user_id,
                    status=status,
                    cleanup_details=cleanup_details,
                    error_message=error_message,
                    session=session
                )
                
    except Exception as e:
        logger.error(f"Error processing kubeconfig event: {str(e)}")

def handle_chat_service_event(message):
    """Handle events from chat service"""
    try:
        event_type = message.get("event_type")
        logger.info(f"Received chat service event: {event_type}")
        
        if event_type == "user_cleanup_completed":
            # Handle cleanup completion acknowledgment from chat service
            operation_id = message.get("operation_id")
            user_id = message.get("user_id")
            status = message.get("status", "completed")
            cleanup_details = message.get("cleanup_details")
            error_message = message.get("error_message")
            
            logger.info(f"Received cleanup completion from chat service: {operation_id}")
            
            with Session(next(get_session())) as session:
                deletion_service.handle_service_cleanup_ack(
                    operation_id=operation_id,
                    service_name="chat_service",
                    user_id=user_id,
                    status=status,
                    cleanup_details=cleanup_details,
                    error_message=error_message,
                    session=session
                )
                
    except Exception as e:
        logger.error(f"Error processing chat service event: {str(e)}")

def handle_remediation_service_event(message):
    """Handle events from remediation service"""
    try:
        event_type = message.get("event_type")
        logger.info(f"Received remediation service event: {event_type}")
        
        if event_type == "user_cleanup_completed":
            # Handle cleanup completion acknowledgment from remediation service
            operation_id = message.get("operation_id")
            user_id = message.get("user_id")
            status = message.get("status", "completed")
            cleanup_details = message.get("cleanup_details")
            error_message = message.get("error_message")
            
            logger.info(f"Received cleanup completion from remediation service: {operation_id}")
            
            with Session(next(get_session())) as session:
                deletion_service.handle_service_cleanup_ack(
                    operation_id=operation_id,
                    service_name="remediation_service",
                    user_id=user_id,
                    status=status,
                    cleanup_details=cleanup_details,
                    error_message=error_message,
                    session=session
                )
                
    except Exception as e:
        logger.error(f"Error processing remediation service event: {str(e)}")

def handle_security_service_event(message):
    """Handle events from security service"""
    try:
        event_type = message.get("event_type")
        logger.info(f"Received security service event: {event_type}")
        
        if event_type == "user_cleanup_completed":
            # Handle cleanup completion acknowledgment from security service
            operation_id = message.get("operation_id")
            user_id = message.get("user_id")
            status = message.get("status", "completed")
            cleanup_details = message.get("cleanup_details")
            error_message = message.get("error_message")
            
            logger.info(f"Received cleanup completion from security service: {operation_id}")
            
            with Session(next(get_session())) as session:
                deletion_service.handle_service_cleanup_ack(
                    operation_id=operation_id,
                    service_name="security_service",
                    user_id=user_id,
                    status=status,
                    cleanup_details=cleanup_details,
                    error_message=error_message,
                    session=session
                )
                
    except Exception as e:
        logger.error(f"Error processing security service event: {str(e)}")

def start_consumers():
    """Start background consumers with restart capability"""
    def consumer_thread_function():
        while True:
            try:
                # Set up consumers for different services
                consumers = [
                    ("kubeconfig_events", handle_kubeconfig_event),
                    ("chat_service_events", handle_chat_service_event),
                    ("remediation_service_events", handle_remediation_service_event),
                    ("security_service_events", handle_security_service_event),
                ]
                
                for queue_name, handler in consumers:
                    if setup_consumer(queue_name, handler):
                        logger.info(f"Set up consumer for {queue_name}")
                    else:
                        logger.warning(f"Failed to set up consumer for {queue_name}")
                
                # Start consuming if at least one consumer was set up successfully
                start_consuming()
                
            except Exception as e:
                logger.error(f"Consumer thread error: {str(e)}")
                time.sleep(5)  # Wait before trying to reconnect
    
    # Start consuming in background thread
    consumer_thread = threading.Thread(target=consumer_thread_function)
    consumer_thread.daemon = True
    consumer_thread.start()
    logger.info("Event consumers started in background")