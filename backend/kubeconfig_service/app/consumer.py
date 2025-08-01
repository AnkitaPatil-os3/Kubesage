import threading
from app.queue import setup_consumer, start_consuming
from app.logger import logger
from app.database import get_session
from app.models import ClusterConfig
from sqlmodel import select, Session
import os

def handle_user_event(message):
    """Handle events from user service"""
    event_type = message.get("event_type")
    logger.info(f"Received user event: {event_type}")
    
    if event_type == "user_created":
        # A new user was created - you might want to set up default cluster configurations
        user_id = message.get("user_id")
        username = message.get("username")
        logger.info(f"New user created: {username} (ID: {user_id})")
        
        # You could create default resources or permissions if needed
        # For example, create a default cluster configuration or set up user-specific settings
        
    elif event_type == "user_deleted":
        # A user was deleted - clean up their cluster configurations
        user_id = message.get("user_id")
        
        with Session(engine) as session:
            # Get all cluster configurations for the user
            cluster_configs = session.exec(
                select(ClusterConfig).where(ClusterConfig.user_id == user_id)
            ).all()
            
            # Remove all cluster configurations for the user
            for cluster_config in cluster_configs:
                session.delete(cluster_config)
            
            session.commit()
            logger.info(f"Deleted {len(cluster_configs)} cluster configurations for user {user_id}")

def handle_cluster_event(message):
    """Handle events from cluster operations"""
    event_type = message.get("event_type")
    logger.info(f"Received cluster event: {event_type}")
    
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
    
    logger.info(f"Audit event: {event_type} by user {username} ({user_id}) at {timestamp}")
    
    # You could implement audit logging here, such as:
    # - Store in audit database
    # - Send to external audit systems
    # - Generate compliance reports

def start_consumers():
    """Start background consumers for different event queues"""
    try:
        # Set up consumer for user events
        setup_consumer("user_events", handle_user_event)
        logger.info("Set up consumer for user_events")
        
        # Set up consumer for cluster events
        setup_consumer("cluster_events", handle_cluster_event)
        logger.info("Set up consumer for cluster_events")
        
        # Set up consumer for audit events (optional)
        setup_consumer("audit_events", handle_audit_event)
        logger.info("Set up consumer for audit_events")
        
        # Start consuming in background thread
        consumer_thread = threading.Thread(target=start_consuming, daemon=True)
        consumer_thread.start()
        logger.info("Event consumers started in background thread")
        
    except Exception as e:
        logger.error(f"Failed to start consumers: {str(e)}")
        raise

def stop_consumers():
    """Stop all consumers gracefully"""
    try:
        # This function can be called during application shutdown
        # to gracefully stop all consumers
        logger.info("Stopping event consumers...")
        # Implementation depends on your queue system
        # For example, you might need to call a stop method on your queue consumer
        
    except Exception as e:
        logger.error(f"Error stopping consumers: {str(e)}")

# Import the database engine for session creation
from app.database import engine