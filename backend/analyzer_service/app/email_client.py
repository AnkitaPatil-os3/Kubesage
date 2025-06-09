import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import BackgroundTasks
from pydantic import EmailStr
from app.schemas import KubernetesEvent
from app.logger import logger
from typing import List, Dict, Any, Optional
import uuid
from app.config import settings

# Log the configuration (without password)
logger.info(f"Email Configuration: Server={settings.MAIL_SERVER}, Port={settings.MAIL_PORT}, User={settings.MAIL_USERNAME}, From={settings.MAIL_FROM}")

# Configure email connection
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# Dictionary to store incident IDs and their details for tracking responses
incident_tracking = {}

def create_test_incident() -> KubernetesEvent:
    """Create a static test incident for testing email functionality"""
    from datetime import datetime
    return KubernetesEvent(
        metadata_name="test-incident.123456789",
        metadata_namespace="default",
        metadata_creation_timestamp=datetime.utcnow(),
        type="Warning",
        reason="TestIncident",
        message="This is a test incident for email verification",
        count=1,
        source_component="kubelet",
        source_host="test-instance",
        involved_object_kind="Pod",
        involved_object_name="test-pod",
        reporting_component="kubelet",
        reporting_instance="test-instance"
    )

async def send_incident_email(incident: KubernetesEvent, incident_id: str):
    """
    Send email notification for Kubernetes incidents using FastMail
    """
    try:
        # Email body
        email_body = f"""
        <h2>Kubernetes Incident Alert</h2>
        
        <p><strong>Incident ID:</strong> {incident_id}</p>
        <p><strong>Type:</strong> {incident.type}</p>
        <p><strong>Reason:</strong> {incident.reason}</p>
        <p><strong>Message:</strong> {incident.message}</p>
        
        <h3>Object Details</h3>
        <p><strong>Kind:</strong> {incident.involved_object_kind}</p>
        <p><strong>Name:</strong> {incident.involved_object_name}</p>
        <p><strong>Namespace:</strong> {incident.metadata_namespace}</p>
        
        <h3>Source Information</h3>
        <p><strong>Component:</strong> {incident.source_component}</p>
        <p><strong>Host:</strong> {incident.source_host}</p>
        
        <h3>Reporter Information</h3>
        <p><strong>Component:</strong> {incident.reporting_component}</p>
        <p><strong>Instance:</strong> {incident.reporting_instance}</p>
        
        <p><strong>Count:</strong> {incident.count}</p>
        <p><strong>Creation Time:</strong> {incident.metadata_creation_timestamp}</p>
        """
        
        subject = f"Kubernetes {incident.type} Incident: {incident.reason}"
        
        # Create message schema
        message = MessageSchema(
            subject=subject,
            recipients=[settings.MAIL_RECIPIENT],  # Use the corrected setting name
            body=email_body,
            subtype="html"
        )
        
        # Initialize FastMail and send the email
        fm = FastMail(conf)
        await fm.send_message(message)
        
        logger.info(f"Incident email sent to {settings.MAIL_RECIPIENT} for incident: {incident.reason}")
        return True, incident_id
        
    except Exception as e:
        logger.error(f"Failed to send incident email: {e}")
        return False, incident_id

def send_incident_email_background(background_tasks: BackgroundTasks, incident: Optional[KubernetesEvent] = None, incident_id: Optional[str] = None):
    """Add email sending to background tasks"""
    background_tasks.add_task(send_incident_email, incident, incident_id)
    logger.info("Email task added to background tasks")
    return True
