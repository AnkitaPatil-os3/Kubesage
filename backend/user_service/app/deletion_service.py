import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlmodel import Session, select
from app.database import get_session
from app.models import User, UserDeletionOperation, ServiceCleanupAck, UserToken, ApiKey
from app.schemas import UserDeletionRequest, UserDeletionResponse, UserDeletionStatus
from app.queue import publish_message
from app.logger import logger
from app.config import settings


class UserDeletionService:
    """Service to handle user deletion operations across microservices"""
    
    # Define services that need cleanup when a user is deleted
    CLEANUP_SERVICES = [
        "kubeconfig_service",
        "chat_service", 
        "remediation_service",
        "security_service",
        "monitoring_service"
    ]
    
    def __init__(self):
        self.max_retries = 3
        self.cleanup_timeout = 300  # 5 minutes
    
    def initiate_user_deletion(
        self, 
        user_id: int, 
        deletion_request: UserDeletionRequest,
        session: Session
    ) -> UserDeletionResponse:
        """Initiate user deletion process"""
        try:
            # Get user details
            user = session.exec(select(User).where(User.id == user_id)).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            if user.is_deleted:
                raise ValueError(f"User {user.username} is already deleted")
            
            # Generate operation ID
            operation_id = str(uuid.uuid4())
            
            # Determine services to cleanup
            services_to_cleanup = [
                service for service in self.CLEANUP_SERVICES 
                if service not in (deletion_request.services_to_skip or [])
            ]
            
            # Create deletion operation record
            deletion_op = UserDeletionOperation(
                user_id=user_id,
                username=user.username,
                operation_id=operation_id,
                status="initiated",
                services_to_cleanup=json.dumps(services_to_cleanup),
                services_completed=json.dumps([]),
                services_failed=json.dumps([]),
                max_retries=self.max_retries
            )
            
            session.add(deletion_op)
            session.commit()
            session.refresh(deletion_op)
            
            # Create service cleanup acknowledgment records
            for service in services_to_cleanup:
                cleanup_ack = ServiceCleanupAck(
                    operation_id=operation_id,
                    service_name=service,
                    user_id=user_id,
                    status="pending"
                )
                session.add(cleanup_ack)
            
            session.commit()
            
            # Start the deletion process
            self._start_deletion_process(deletion_op, deletion_request, session)
            
            logger.info(f"User deletion initiated for user {user.username} (ID: {user_id}), operation: {operation_id}")
            
            return UserDeletionResponse(
                operation_id=operation_id,
                user_id=user_id,
                username=user.username,
                status="initiated",
                message="User deletion process initiated successfully",
                services_to_cleanup=services_to_cleanup,
                estimated_completion_time=datetime.now() + timedelta(seconds=deletion_request.cleanup_timeout)
            )
            
        except Exception as e:
            logger.error(f"Error initiating user deletion: {str(e)}")
            raise
    
    def _start_deletion_process(
        self, 
        deletion_op: UserDeletionOperation, 
        deletion_request: UserDeletionRequest,
        session: Session
    ):
        """Start the actual deletion process"""
        try:
            # Update status to in_progress
            deletion_op.status = "in_progress"
            deletion_op.updated_at = datetime.now()
            session.add(deletion_op)
            session.commit()
            
            # Step 1: Soft delete user in user service (mark as deleted but keep record)
            user = session.exec(select(User).where(User.id == deletion_op.user_id)).first()
            if user:
                user.is_deleted = True
                user.deleted_at = datetime.now()
                user.is_active = False
                session.add(user)
                session.commit()
                logger.info(f"User {user.username} marked as deleted in user service")
            
            # Step 2: Revoke all user tokens and API keys
            self._cleanup_user_auth_data(deletion_op.user_id, session)
            
            # Step 3: Publish deletion events to other services
            services_to_cleanup = json.loads(deletion_op.services_to_cleanup)
            
            deletion_event = {
                "event_type": "user_deletion_initiated",
                "operation_id": deletion_op.operation_id,
                "user_id": deletion_op.user_id,
                "username": deletion_op.username,
                "force_delete": deletion_request.force_delete,
                "cleanup_timeout": deletion_request.cleanup_timeout,
                "services_to_cleanup": services_to_cleanup,
                "timestamp": datetime.now().isoformat(),
                "callback_url": f"{settings.SERVER_BASE_URL}/users/deletion/callback"
            }
            
            # Publish to each service's specific queue
            for service in services_to_cleanup:
                service_queue = f"{service}_events"
                publish_success = publish_message(service_queue, deletion_event)
                
                if not publish_success:
                    logger.error(f"Failed to publish deletion event to {service}")
                    # Mark service as failed if we can't even send the message
                    self._mark_service_cleanup_failed(
                        deletion_op.operation_id,
                        service,
                        f"Failed to publish deletion event to {service}",
                        session
                    )
                else:
                    logger.info(f"Deletion event published to {service}")
            
            # Publish general user deletion event
            publish_message("user_events", deletion_event)
            
            logger.info(f"Deletion process started for operation {deletion_op.operation_id}")
            
        except Exception as e:
            logger.error(f"Error starting deletion process: {str(e)}")
            deletion_op.status = "failed"
            deletion_op.error_details = str(e)
            deletion_op.updated_at = datetime.now()
            session.add(deletion_op)
            session.commit()
            raise
    
    def _cleanup_user_auth_data(self, user_id: int, session: Session):
        """Clean up user's authentication data (tokens, API keys)"""
        try:
            # Revoke all user tokens
            user_tokens = session.exec(select(UserToken).where(UserToken.user_id == user_id)).all()
            for token in user_tokens:
                token.is_revoked = True
                session.add(token)
            
            # Deactivate all API keys
            api_keys = session.exec(select(ApiKey).where(ApiKey.user_id == user_id)).all()
            for api_key in api_keys:
                api_key.is_active = False
                session.add(api_key)
            
            session.commit()
            logger.info(f"Cleaned up authentication data for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up auth data for user {user_id}: {str(e)}")
            raise
    
    def handle_service_cleanup_ack(
        self, 
        operation_id: str, 
        service_name: str, 
        user_id: int,
        status: str,
        cleanup_details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        session: Session = None
    ) -> bool:
        """Handle cleanup acknowledgment from a service"""
        try:
            if not session:
                with Session(get_session()) as session:
                    return self._process_cleanup_ack(
                        operation_id, service_name, user_id, status, 
                        cleanup_details, error_message, session
                    )
            else:
                return self._process_cleanup_ack(
                    operation_id, service_name, user_id, status, 
                    cleanup_details, error_message, session
                )
                
        except Exception as e:
            logger.error(f"Error handling service cleanup ack: {str(e)}")
            return False
    
    def _process_cleanup_ack(
        self,
        operation_id: str,
        service_name: str,
        user_id: int,
        status: str,
        cleanup_details: Optional[Dict[str, Any]],
        error_message: Optional[str],
        session: Session
    ) -> bool:
        """Process the cleanup acknowledgment"""
        try:
            # Update service cleanup acknowledgment
            cleanup_ack = session.exec(
                select(ServiceCleanupAck).where(
                    ServiceCleanupAck.operation_id == operation_id,
                    ServiceCleanupAck.service_name == service_name
                )
            ).first()
            
            if not cleanup_ack:
                logger.warning(f"Cleanup ack not found for operation {operation_id}, service {service_name}")
                return False
            
            cleanup_ack.status = status
            cleanup_ack.cleanup_details = json.dumps(cleanup_details) if cleanup_details else None
            cleanup_ack.error_message = error_message
            cleanup_ack.updated_at = datetime.now()
            session.add(cleanup_ack)
            
            # Update deletion operation
            deletion_op = session.exec(
                select(UserDeletionOperation).where(
                    UserDeletionOperation.operation_id == operation_id
                )
            ).first()
            
            if not deletion_op:
                logger.error(f"Deletion operation not found: {operation_id}")
                return False
            
            services_completed = json.loads(deletion_op.services_completed)
            services_failed = json.loads(deletion_op.services_failed)
            
            if status == "completed":
                if service_name not in services_completed:
                    services_completed.append(service_name)
                # Remove from failed list if it was there
                if service_name in services_failed:
                    services_failed.remove(service_name)
                    
                logger.info(f"Service {service_name} completed cleanup for operation {operation_id}")
                
            elif status == "failed":
                if service_name not in services_failed:
                    services_failed.append(service_name)
                # Remove from completed list if it was there
                if service_name in services_completed:
                    services_completed.remove(service_name)
                    
                logger.error(f"Service {service_name} failed cleanup for operation {operation_id}: {error_message}")
            
            deletion_op.services_completed = json.dumps(services_completed)
            deletion_op.services_failed = json.dumps(services_failed)
            deletion_op.updated_at = datetime.now()
            session.add(deletion_op)
            
            # Check if all services have responded
            services_to_cleanup = json.loads(deletion_op.services_to_cleanup)
            total_services = len(services_to_cleanup)
            completed_services = len(services_completed)
            failed_services = len(services_failed)
            
            if completed_services + failed_services >= total_services:
                # All services have responded
                self._finalize_deletion_operation(deletion_op, session)
            
            session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error processing cleanup ack: {str(e)}")
            session.rollback()
            return False
    
    def _finalize_deletion_operation(self, deletion_op: UserDeletionOperation, session: Session):
        """Finalize the deletion operation"""
        try:
            services_completed = json.loads(deletion_op.services_completed)
            services_failed = json.loads(deletion_op.services_failed)
            services_to_cleanup = json.loads(deletion_op.services_to_cleanup)
            
            if len(services_failed) == 0:
                # All services completed successfully
                deletion_op.status = "completed"
                deletion_op.completed_at = datetime.now()
                
                # Now we can safely hard delete the user if needed
                # For now, we'll keep the soft delete approach
                logger.info(f"User deletion completed successfully for operation {deletion_op.operation_id}")
                
            elif len(services_completed) > 0:
                # Some services completed, some failed
                deletion_op.status = "partially_completed"
                deletion_op.error_details = f"Failed services: {', '.join(services_failed)}"
                
                logger.warning(f"User deletion partially completed for operation {deletion_op.operation_id}")
                
            else:
                # All services failed
                deletion_op.status = "failed"
                deletion_op.error_details = f"All services failed: {', '.join(services_failed)}"
                
                logger.error(f"User deletion failed for operation {deletion_op.operation_id}")
            
            deletion_op.updated_at = datetime.now()
            session.add(deletion_op)
            
            # Publish completion event
            completion_event = {
                "event_type": "user_deletion_completed",
                "operation_id": deletion_op.operation_id,
                "user_id": deletion_op.user_id,
                "username": deletion_op.username,
                "status": deletion_op.status,
                "services_completed": services_completed,
                "services_failed": services_failed,
                "timestamp": datetime.now().isoformat()
            }
            
            publish_message("user_events", completion_event)
            
        except Exception as e:
            logger.error(f"Error finalizing deletion operation: {str(e)}")
            raise
    
    def _mark_service_cleanup_failed(
        self, 
        operation_id: str, 
        service_name: str, 
        error_message: str, 
        session: Session
    ):
        """Mark a service cleanup as failed"""
        try:
            cleanup_ack = session.exec(
                select(ServiceCleanupAck).where(
                    ServiceCleanupAck.operation_id == operation_id,
                    ServiceCleanupAck.service_name == service_name
                )
            ).first()
            
            if cleanup_ack:
                cleanup_ack.status = "failed"
                cleanup_ack.error_message = error_message
                cleanup_ack.updated_at = datetime.now()
                session.add(cleanup_ack)
                session.commit()
                
        except Exception as e:
            logger.error(f"Error marking service cleanup as failed: {str(e)}")
    
    def get_deletion_status(self, operation_id: str, session: Session) -> Optional[UserDeletionStatus]:
        """Get the status of a deletion operation"""
        try:
            deletion_op = session.exec(
                select(UserDeletionOperation).where(
                    UserDeletionOperation.operation_id == operation_id
                )
            ).first()
            
            if not deletion_op:
                return None
            
            services_to_cleanup = json.loads(deletion_op.services_to_cleanup)
            services_completed = json.loads(deletion_op.services_completed)
            services_failed = json.loads(deletion_op.services_failed)
            
            total_services = len(services_to_cleanup)
            completed_count = len(services_completed) + len(services_failed)
            progress_percentage = (completed_count / total_services * 100) if total_services > 0 else 100
            
            return UserDeletionStatus(
                operation_id=deletion_op.operation_id,
                user_id=deletion_op.user_id,
                username=deletion_op.username,
                status=deletion_op.status,
                services_to_cleanup=services_to_cleanup,
                services_completed=services_completed,
                services_failed=services_failed,
                error_details=deletion_op.error_details,
                retry_count=deletion_op.retry_count,
                max_retries=deletion_op.max_retries,
                created_at=deletion_op.created_at,
                updated_at=deletion_op.updated_at,
                completed_at=deletion_op.completed_at,
                progress_percentage=progress_percentage
            )
            
        except Exception as e:
            logger.error(f"Error getting deletion status: {str(e)}")
            return None
    
    def retry_failed_cleanup(self, operation_id: str, session: Session) -> bool:
        """Retry failed cleanup operations"""
        try:
            deletion_op = session.exec(
                select(UserDeletionOperation).where(
                    UserDeletionOperation.operation_id == operation_id
                )
            ).first()
            
            if not deletion_op:
                logger.error(f"Deletion operation not found: {operation_id}")
                return False
            
            if deletion_op.retry_count >= deletion_op.max_retries:
                logger.error(f"Max retries exceeded for operation {operation_id}")
                return False
            
            services_failed = json.loads(deletion_op.services_failed)
            
            if not services_failed:
                logger.info(f"No failed services to retry for operation {operation_id}")
                return True
            
            # Increment retry count
            deletion_op.retry_count += 1
            deletion_op.updated_at = datetime.now()
            session.add(deletion_op)
            
            # Retry failed services
            retry_event = {
                "event_type": "user_deletion_retry",
                "operation_id": operation_id,
                "user_id": deletion_op.user_id,
                "username": deletion_op.username,
                "services_to_retry": services_failed,
                "retry_count": deletion_op.retry_count,
                "timestamp": datetime.now().isoformat(),
                "callback_url": f"{settings.SERVER_BASE_URL}/users/deletion/callback"
            }
            
            for service in services_failed:
                service_queue = f"{service}_events"
                publish_message(service_queue, retry_event)
                
                # Reset service cleanup ack status
                cleanup_ack = session.exec(
                    select(ServiceCleanupAck).where(
                        ServiceCleanupAck.operation_id == operation_id,
                        ServiceCleanupAck.service_name == service
                    )
                ).first()
                
                if cleanup_ack:
                    cleanup_ack.status = "pending"
                    cleanup_ack.retry_count += 1
                    cleanup_ack.updated_at = datetime.now()
                    session.add(cleanup_ack)
            
            session.commit()
            logger.info(f"Retry initiated for operation {operation_id}, attempt {deletion_op.retry_count}")
            return True
            
        except Exception as e:
            logger.error(f"Error retrying failed cleanup: {str(e)}")
            return False


# Global instance
deletion_service = UserDeletionService()