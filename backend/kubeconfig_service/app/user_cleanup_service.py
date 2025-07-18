import json
import httpx
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlmodel import Session, select
from app.database import get_session, engine
from app.models import ClusterConfig, UserCleanupOperation
from app.queue import publish_message
from app.logger import logger
from app.config import settings


class KubeconfigUserCleanupService:
    """Service to handle user data cleanup in kubeconfig service"""
    
    def __init__(self):
        self.user_service_url = settings.USER_SERVICE_URL or "https://10.0.32.103:8001"
    
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
            
            logger.info(f"Processing user deletion for user {username} (ID: {user_id}), operation: {operation_id}")
            
            with Session(engine) as session:
                # Check if we already have this operation
                existing_operation = session.exec(
                    select(UserCleanupOperation).where(
                        UserCleanupOperation.operation_id == operation_id
                    )
                ).first()
                
                if existing_operation:
                    logger.info(f"Operation {operation_id} already exists, updating status")
                    cleanup_operation = existing_operation
                else:
                    # Create new cleanup operation record
                    cleanup_operation = UserCleanupOperation(
                        operation_id=operation_id,
                        user_id=user_id,
                        username=username,
                        status="pending"
                    )
                    session.add(cleanup_operation)
                    session.commit()
                    session.refresh(cleanup_operation)
                
                # Start cleanup process
                await self._perform_user_cleanup(cleanup_operation, session, callback_url)
                
        except Exception as e:
            logger.error(f"Error processing user deletion: {str(e)}")
            await self._send_cleanup_failure(event_data, str(e))
    
    async def _process_user_deletion_retry(self, event_data: Dict[str, Any]):
        """Process user deletion retry request"""
        try:
            operation_id = event_data.get("operation_id")
            services_to_retry = event_data.get("services_to_retry", [])
            
            if "kubeconfig_service" not in services_to_retry:
                logger.info(f"Kubeconfig service not in retry list for operation {operation_id}")
                return
            
            logger.info(f"Processing user deletion retry for operation: {operation_id}")
            
            with Session(engine) as session:
                cleanup_operation = session.exec(
                    select(UserCleanupOperation).where(
                        UserCleanupOperation.operation_id == operation_id
                    )
                ).first()
                
                if not cleanup_operation:
                    logger.error(f"Cleanup operation not found for retry: {operation_id}")
                    return
                
                # Reset status and increment retry count
                cleanup_operation.status = "pending"
                cleanup_operation.retry_count += 1
                cleanup_operation.updated_at = datetime.now()
                cleanup_operation.error_message = None
                session.add(cleanup_operation)
                session.commit()
                
                # Retry cleanup
                callback_url = event_data.get("callback_url")
                await self._perform_user_cleanup(cleanup_operation, session, callback_url)
                
        except Exception as e:
            logger.error(f"Error processing user deletion retry: {str(e)}")
    
    async def _perform_user_cleanup(
        self, 
        cleanup_operation: UserCleanupOperation, 
        session: Session,
        callback_url: Optional[str] = None
    ):
        """Perform the actual user data cleanup"""
        try:
            # Update status to in_progress
            cleanup_operation.status = "in_progress"
            cleanup_operation.updated_at = datetime.now()
            session.add(cleanup_operation)
            session.commit()
            
            user_id = cleanup_operation.user_id
            username = cleanup_operation.username
            
            logger.info(f"Starting cleanup for user {username} (ID: {user_id})")
            
            # Find all cluster configurations for this user
            cluster_configs = session.exec(
                select(ClusterConfig).where(ClusterConfig.user_id == user_id)
            ).all()
            
            cluster_ids = [config.id for config in cluster_configs]
            cleanup_operation.clusters_to_cleanup = json.dumps(cluster_ids)
            session.add(cleanup_operation)
            session.commit()
            
            logger.info(f"Found {len(cluster_configs)} cluster configurations to cleanup for user {username}")
            
            # Cleanup details
            cleanup_details = {
                "clusters_deleted": [],
                "total_clusters": len(cluster_configs),
                "cleanup_timestamp": datetime.now().isoformat()
            }
            
            # Delete all cluster configurations
            clusters_cleaned = []
            for config in cluster_configs:
                try:
                    logger.info(f"Deleting cluster config: {config.cluster_name} (ID: {config.id})")
                    session.delete(config)
                    clusters_cleaned.append(config.id)
                    
                    cleanup_details["clusters_deleted"].append({
                        "cluster_id": config.id,
                        "cluster_name": config.cluster_name,
                        "provider_name": config.provider_name,
                        "deleted_at": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Error deleting cluster config {config.id}: {str(e)}")
                    # Continue with other clusters even if one fails
            
            # Commit all deletions
            session.commit()
            
            # Update cleanup operation
            cleanup_operation.status = "completed"
            cleanup_operation.clusters_cleaned = json.dumps(clusters_cleaned)
            cleanup_operation.cleanup_details = json.dumps(cleanup_details)
            cleanup_operation.completed_at = datetime.now()
            cleanup_operation.updated_at = datetime.now()
            session.add(cleanup_operation)
            session.commit()
            
            logger.info(f"Successfully cleaned up {len(clusters_cleaned)} cluster configurations for user {username}")
            
            # Send success acknowledgment
            await self._send_cleanup_success(cleanup_operation, cleanup_details, callback_url)
            
        except Exception as e:
            logger.error(f"Error performing user cleanup: {str(e)}")
            
            # Update cleanup operation with error
            cleanup_operation.status = "failed"
            cleanup_operation.error_message = str(e)
            cleanup_operation.updated_at = datetime.now()
            session.add(cleanup_operation)
            session.commit()
            
            # Send failure acknowledgment
            await self._send_cleanup_failure({
                "operation_id": cleanup_operation.operation_id,
                "user_id": cleanup_operation.user_id,
                "username": cleanup_operation.username
            }, str(e), callback_url)
    
    async def _send_cleanup_success(
        self, 
        cleanup_operation: UserCleanupOperation, 
        cleanup_details: Dict[str, Any],
        callback_url: Optional[str] = None
    ):
        """Send cleanup success acknowledgment to user service"""
        try:
            # Prepare acknowledgment data
            ack_data = {
                "operation_id": cleanup_operation.operation_id,
                "service_name": "kubeconfig_service",
                "user_id": cleanup_operation.user_id,
                "status": "completed",
                "cleanup_details": cleanup_details
            }
            
            # Send via message queue
            success_event = {
                "event_type": "user_cleanup_completed",
                "operation_id": cleanup_operation.operation_id,
                "user_id": cleanup_operation.user_id,
                "username": cleanup_operation.username,
                "service_name": "kubeconfig_service",
                "status": "completed",
                "cleanup_details": cleanup_details,
                "timestamp": datetime.now().isoformat()
            }
            
            publish_message("user_events", success_event)
            logger.info(f"Published cleanup success event for operation {cleanup_operation.operation_id}")
            
            # Also send HTTP callback if URL provided
            if callback_url:
                await self._send_http_callback(callback_url, ack_data)
                
        except Exception as e:
            logger.error(f"Error sending cleanup success acknowledgment: {str(e)}")
    
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
                "service_name": "kubeconfig_service",
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
                "service_name": "kubeconfig_service",
                "status": "failed",
                "error_message": error_message,
                "timestamp": datetime.now().isoformat()
            }
            
            publish_message("user_events", failure_event)
            logger.info(f"Published cleanup failure event for operation {operation_id}")
            
            # Also send HTTP callback if URL provided
            if callback_url:
                await self._send_http_callback(callback_url, ack_data)
                
        except Exception as e:
            logger.error(f"Error sending cleanup failure acknowledgment: {str(e)}")
    
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
                    logger.info(f"Successfully sent HTTP callback for operation {ack_data['operation_id']}")
                else:
                    logger.error(f"HTTP callback failed with status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error sending HTTP callback: {str(e)}")
    
    def get_cleanup_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get cleanup operation status"""
        try:
            with Session(engine) as session:
                cleanup_operation = session.exec(
                    select(UserCleanupOperation).where(
                        UserCleanupOperation.operation_id == operation_id
                    )
                ).first()
                if not cleanup_operation:
                    return None
                
                clusters_to_cleanup = json.loads(cleanup_operation.clusters_to_cleanup) if cleanup_operation.clusters_to_cleanup else []
                clusters_cleaned = json.loads(cleanup_operation.clusters_cleaned) if cleanup_operation.clusters_cleaned else []
                cleanup_details = json.loads(cleanup_operation.cleanup_details) if cleanup_operation.cleanup_details else {}
                
                return {
                    "operation_id": cleanup_operation.operation_id,
                    "user_id": cleanup_operation.user_id,
                    "username": cleanup_operation.username,
                    "status": cleanup_operation.status,
                    "clusters_to_cleanup": clusters_to_cleanup,
                    "clusters_cleaned": clusters_cleaned,
                    "cleanup_details": cleanup_details,
                    "error_message": cleanup_operation.error_message,
                    "retry_count": cleanup_operation.retry_count,
                    "created_at": cleanup_operation.created_at.isoformat(),
                    "updated_at": cleanup_operation.updated_at.isoformat(),
                    "completed_at": cleanup_operation.completed_at.isoformat() if cleanup_operation.completed_at else None
                }
                
        except Exception as e:
            logger.error(f"Error getting cleanup status: {str(e)}")
            return None


# Global instance
kubeconfig_cleanup_service = KubeconfigUserCleanupService()