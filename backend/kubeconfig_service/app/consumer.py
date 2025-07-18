import threading
import asyncio
from app.queue import setup_consumer, start_consuming
from app.logger import logger
from app.user_cleanup_service import kubeconfig_cleanup_service
import time

def handle_user_event(message):
    """Handle events from user service"""
    try:
        event_type = message.get("event_type")
        logger.info(f"📨 Received user event: {event_type}")
        
        if event_type == "user_created":
            # A new user was created - you might want to set up default cluster configurations
            user_id = message.get("user_id")
            username = message.get("username")
            logger.info(f"👤 New user created: {username} (ID: {user_id})")
            
            # You could create default resources or permissions if needed
            # For example, create a default cluster configuration or set up user-specific settings
            
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
                    loop.run_until_complete(kubeconfig_cleanup_service.handle_user_deletion_event(message))
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

def handle_cluster_event(message):
    """Handle events from cluster operations"""
    event_type = message.get("event_type")
    logger.info(f"🔧 Received cluster event: {event_type}")
    
    if event_type == "cluster_onboarded":
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        cluster_name = message.get("cluster_name")
        logger.info(f"Cluster '{cluster_name}' onboarded for user {user_id} (Cluster ID: {cluster_id})")
        
        # You could perform additional actions here, such as:
        # - Send notifications
        # - Update external systems
        # - Log to audit trail
        
    elif event_type == "cluster_activated":
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        cluster_name = message.get("cluster_name")
        logger.info(f"Cluster '{cluster_name}' activated for user {user_id}")
        
    elif event_type == "cluster_deleted":
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        cluster_name = message.get("cluster_name")
        logger.info(f"Cluster '{cluster_name}' deleted for user {user_id}")
        
    elif event_type == "operator_installed":
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        cluster_name = message.get("cluster_name")
        success = message.get("success", False)
        
        if success:
            logger.info(f"K8sGPT operator successfully installed on cluster '{cluster_name}' for user {user_id}")
        else:
            logger.warning(f"K8sGPT operator installation failed on cluster '{cluster_name}' for user {user_id}")
            
    elif event_type == "operator_uninstalled":
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        cluster_name = message.get("cluster_name")
        success = message.get("success", False)
        
        if success:
            logger.info(f"K8sGPT operator successfully uninstalled from cluster '{cluster_name}' for user {user_id}")
        else:
            logger.warning(f"K8sGPT operator uninstallation failed on cluster '{cluster_name}' for user {user_id}")
            
    elif event_type == "namespaces_retrieved":
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        cluster_name = message.get("cluster_name")
        namespace_count = message.get("namespace_count", 0)
        logger.info(f"Retrieved {namespace_count} namespaces from cluster '{cluster_name}' for user {user_id}")
        
    elif event_type == "k8s_analysis_performed":
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        cluster_name = message.get("cluster_name")
        issue_count = message.get("issue_count", 0)
        resource_types = message.get("resource_types", [])
        namespace = message.get("namespace", "all")
        
        logger.info(f"K8s analysis performed on cluster '{cluster_name}' for user {user_id}: "
                   f"{issue_count} issues found in {len(resource_types)} resource types (namespace: {namespace})")
        
    elif event_type == "k8s_analysis_with_solutions_performed":
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        cluster_name = message.get("cluster_name")
        problem_count = message.get("problem_count", 0)
        resource_types = message.get("resource_types", [])
        namespace = message.get("namespace", "all")
        
        logger.info(f"K8s analysis with AI solutions performed on cluster '{cluster_name}' for user {user_id}: "
                   f"{problem_count} problems analyzed with solutions (namespace: {namespace})")
        
    # Handle error events
    elif event_type in ["operator_installation_failed", "operator_uninstallation_failed", 
                       "namespaces_retrieval_failed"]:
        cluster_id = message.get("cluster_id")
        user_id = message.get("user_id")
        cluster_name = message.get("cluster_name")
        error = message.get("error", "Unknown error")
        
        logger.error(f"Event '{event_type}' for cluster '{cluster_name}' (user {user_id}): {error}")
        
        # You could implement error handling here, such as:
        # - Send error notifications
        # - Update cluster status in database
        # - Trigger retry mechanisms

def handle_audit_event(message):
    """Handle audit events for logging and compliance"""
    event_type = message.get("event_type")
    user_id = message.get("user_id")
    username = message.get("username", "unknown")
    timestamp = message.get("timestamp")
    
    logger.info(f"📋 Audit event: {event_type} by user {username} ({user_id}) at {timestamp}")
    
    # You could implement audit logging here, such as:
    # - Store in audit database
    # - Send to external audit systems
    # - Generate compliance reports

def start_consumers():
    """Start background consumers for different event queues"""
    def consumer_thread_function():
        while True:
            try:
                # Set up consumers for different services
                consumers = [
                    ("user_events", handle_user_event),
                    ("cluster_events", handle_cluster_event),
                    ("audit_events", handle_audit_event),
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

# Import the database engine for session creation
from app.database import engine