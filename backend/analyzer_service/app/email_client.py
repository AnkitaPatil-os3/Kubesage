import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import BackgroundTasks
from pydantic import EmailStr
from app.schemas import Alert
from app.logger import logger
from typing import List, Dict, Any, Optional
import uuid
from app.config import settings

# Log the configuration (without password)
logger.info(f"Email Configuration: Server={settings.MAIL_SERVER}, Port={settings.MAIL_PORT}, User={settings.MAIL_USERNAME}, From={settings.MAIL_FROM}")


# Configure email connection with updated parameter names
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,  # Make sure these match your Settings class
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,    # Make sure these match your Settings class
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# Dictionary to store alert IDs and their details for tracking responses
alert_tracking = {}

# Create a static test alert for testing purposes
def create_test_alert() -> Alert:
    """Create a static test alert for testing email functionality"""
    return Alert(
        status="firing",
        labels={
            "alertname": "TestAlert",
            "severity": "critical",
            "instance": "test-instance"
        },
        annotations={
            "summary": "This is a test alert summary",
            "description": "This is a test alert description for email verification"
        },
        startsAt="2023-05-23T07:55:04Z",
        endsAt="2023-05-23T08:55:04Z"
    )

async def send_alert_email(alert: Optional[Alert] = None, alert_id: Optional[str] = None):
    """Send an email notification for the alert"""
    try:
        # Use the provided alert or create a test alert if none is provided
        if alert is None:
            logger.info("No alert provided, using test alert")
            alert = create_test_alert()
        
        # Create email content
        alert_name = alert.labels.get('alertname', 'Unknown Alert')
        severity = alert.labels.get('severity', 'Unknown')
        summary = alert.annotations.get('summary', 'No summary provided')
        description = alert.annotations.get('description', 'No description provided')
        start_time = alert.startsAt
        
        # Use provided alert_id or generate a new one
        if not alert_id:
            alert_id = str(uuid.uuid4())
            
        alert_tracking[alert_id] = {
            "alert": alert,
            "status": "pending",  # pending, approved, rejected
            "timestamp": start_time
        }
        
        logger.info(f"Preparing email for alert: {alert_name} with tracking ID: {alert_id}")
        
        # Check if severity is critical
        is_critical = severity.lower() == "critical"
        
        # Format the email body - with or without Yes/No buttons based on severity
        if is_critical:
            # Create Yes/No action buttons with links back to our server
            yes_url = f"{settings.SERVER_BASE_URL}/alert-response/{alert_id}/yes"
            no_url = f"{settings.SERVER_BASE_URL}/alert-response/{alert_id}/no"
            
            email_body = f"""
            <h2>KubeSage Alert Notification</h2>
            <p><strong>Alert Triggered:</strong> {alert_name}</p>
            <p><strong>Severity:</strong> {severity}</p>
            <p><strong>Summary:</strong> {summary}</p>
            <p><strong>Description:</strong> {description}</p>
            <p><strong>Start Time:</strong> {start_time}</p>
            
            <p>Do you want to proceed with automatic remediation?</p>
            
            <div style="margin-top: 20px;">
                <a href="{yes_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; margin-right: 10px; border-radius: 4px;">Yes, Proceed</a>
                <a href="{no_url}" style="background-color: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">No, Skip</a>
            </div>
            
            <p style="margin-top: 20px; font-size: 12px; color: #666;">
                If the buttons don't work, you can copy and paste these URLs into your browser:<br>
                Yes: {yes_url}<br>
                No: {no_url}
            </p>
            """
            
            subject = f"KubeSage Alert: {alert_name} - {severity} - Action Required"
        else:
            # For non-critical alerts, just show the information without buttons
            email_body = f"""
            <h2>KubeSage Alert Notification</h2>
            <p><strong>Alert Triggered:</strong> {alert_name}</p>
            <p><strong>Severity:</strong> {severity}</p>
            <p><strong>Summary:</strong> {summary}</p>
            <p><strong>Description:</strong> {description}</p>
            <p><strong>Start Time:</strong> {start_time}</p>
            
            <p>This is an informational alert. Automatic remediation will be performed.</p>
            """
            
            subject = f"KubeSage Alert: {alert_name} - {severity} - Information Only"
            
            # For non-critical alerts, automatically mark as approved
            alert_tracking[alert_id]["status"] = "auto-approved"
        
        # Create message schema - use string directly for recipients
        message = MessageSchema(
            subject=subject,
            recipients=[settings.ALERT_EMAIL_RECIPIENT],  
            body=email_body,
            subtype="html"
        )
        
         # Log SMTP configuration (without password)
        logger.info(f"SMTP Configuration: Server={settings.MAIL_SERVER}, Port={settings.MAIL_PORT}, User={settings.MAIL_USERNAME}")
        
        # Initialize FastMail and send the email
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"Alert email sent to {settings.ALERT_EMAIL_RECIPIENT} for alert: {alert_name}")
        return True, alert_id
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        # More detailed error logging
        if hasattr(e, 'args') and len(e.args) > 0:
            logger.error(f"Error details: {e.args}")
        return False, None

def send_alert_email_background(background_tasks: BackgroundTasks, alert: Optional[Alert] = None, alert_id: Optional[str] = None):
    """Add email sending to background tasks"""
    background_tasks.add_task(send_alert_email, alert, alert_id)
    logger.info("Email task added to background tasks")
    return True

def get_alert_status(alert_id: str) -> Dict:
    """Get the current status of an alert"""
    if alert_id in alert_tracking:
        return alert_tracking[alert_id]
    return None

def update_alert_status(alert_id: str, status: str) -> bool:
    """Update the status of an alert"""
    if alert_id in alert_tracking:
        alert_tracking[alert_id]["status"] = status
        logger.info(f"Alert {alert_id} status updated to: {status}")
        return True
    logger.warning(f"Attempted to update unknown alert ID: {alert_id}")
    return False
