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

def handle_api_key_validation_request(message):
    """Handle API key validation requests from onboarding service"""
    try:
        from app.database import get_session
        from app.models import ApiKey
        from sqlmodel import select
        from app.queue import publish_message

        agent_id = message.get("agent_id")
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        api_key = message.get("api_key")

        logger.info(f"Processing API key validation request for agent {agent_id}")

        # Validate API key
        with get_session() as session:
            db_api_key = session.exec(
                select(ApiKey).where(
                    ApiKey.api_key == api_key,
                    ApiKey.is_active == True
                )
            ).first()

            if db_api_key and db_api_key.user_id == user_id:
                # API key is valid
                result = {
                    "agent_id": agent_id,
                    "cluster_id": cluster_id,
                    "user_id": user_id,
                    "valid": True,
                    "message": "API key validated successfully"
                }
                logger.info(f"API key validation successful for agent {agent_id}")
            else:
                # API key is invalid
                result = {
                    "agent_id": agent_id,
                    "cluster_id": cluster_id,
                    "user_id": user_id,
                    "valid": False,
                    "error": "Invalid API key"
                }
                logger.warning(f"API key validation failed for agent {agent_id}")

        # Publish result back to onboarding service
        publish_message("api_key_validation_results", result)

    except Exception as e:
        logger.error(f"Error processing API key validation request: {str(e)}")

        # Publish error result
        error_result = {
            "agent_id": message.get("agent_id"),
            "error": f"Validation error: {str(e)}"
        }
        from app.queue import publish_message
        publish_message("api_key_validation_results", error_result)

def start_consumers():
    """Start background consumers with restart capability"""
    def consumer_thread_function():
        while True:
            try:
                # Set up consumers for different queues
                consumers_setup = True

                # Set up consumer for kubeconfig events
                if not setup_consumer("kubeconfig_events", handle_kubeconfig_event):
                    consumers_setup = False

                # Set up consumer for API key validation requests
                if not setup_consumer("api_key_validation_requests", handle_api_key_validation_request):
                    consumers_setup = False

                if consumers_setup:
                    # Start consuming if setup was successful
                    start_consuming()
                else:
                    logger.warning("Failed to set up consumers, retrying in 5 seconds...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Consumer thread error: {str(e)}")
                time.sleep(5)  # Wait before trying to reconnect

    # Start consuming in background thread
    consumer_thread = threading.Thread(target=consumer_thread_function)
    consumer_thread.daemon = True
    consumer_thread.start()
    logger.info("Event consumers started in background")
