import threading
from app.queue import setup_consumer, start_consuming
from app.logger import logger
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
    except Exception as e:
        logger.error(f"Error processing kubeconfig event: {str(e)}")

def start_consumers():
    """Start background consumers with restart capability"""
    def consumer_thread_function():
        while True:
            try:
                # Set up consumer for kubeconfig events
                if setup_consumer("kubeconfig_events", handle_kubeconfig_event):
                    # Start consuming if setup was successful
                    start_consuming()
                else:
                    logger.warning("Failed to set up consumer, retrying in 5 seconds...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Consumer thread error: {str(e)}")
                time.sleep(5)  # Wait before trying to reconnect
    
    # Start consuming in background thread
    consumer_thread = threading.Thread(target=consumer_thread_function)
    consumer_thread.daemon = True
    consumer_thread.start()
    logger.info("Event consumers started in background")