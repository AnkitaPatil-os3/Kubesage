import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import BackgroundTasks
from pydantic import EmailStr
from app.schemas import Alert
from app.logger import logger
from typing import List, Dict, Any, Optional

# Load environment variables directly to ensure they're available
mail_username = os.getenv("MAIL_USERNAME", "nisha30603@gmail.com")
mail_password = os.getenv("MAIL_PASSWORD", "ylqlgjmkppphxlvh")  # Use App Password for Gmail
mail_from = os.getenv("MAIL_FROM", "nisha30603@gmail.com")
mail_port = int(os.getenv("MAIL_PORT", "587"))
mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
mail_from_name = os.getenv("MAIL_FROM_NAME", "KubeSage Alert System")
mail_starttls = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
mail_ssl_tls = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"

# Log the configuration (without password)
logger.info(f"Email Configuration: Server={mail_server}, Port={mail_port}, User={mail_username}, From={mail_from}")

# Configure email connection with updated parameter names
conf = ConnectionConfig(
    MAIL_USERNAME=mail_username,
    MAIL_PASSWORD=mail_password,
    MAIL_FROM=mail_from,
    MAIL_PORT=mail_port,
    MAIL_SERVER=mail_server,
    MAIL_FROM_NAME=mail_from_name,
    MAIL_STARTTLS=mail_starttls,
    MAIL_SSL_TLS=mail_ssl_tls,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

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

async def send_alert_email(alert: Optional[Alert] = None):
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
        
        logger.info(f"Preparing email for alert: {alert_name}")
        
        # Format the email body
        email_body = f"""
        <h2>Kubernetes Alert Notification</h2>
        <p><strong>Alert Triggered:</strong> {alert_name}</p>
        <p><strong>Severity:</strong> {severity}</p>
        <p><strong>Summary:</strong> {summary}</p>
        <p><strong>Description:</strong> {description}</p>
        <p><strong>Start Time:</strong> {start_time}</p>
        """
        
        # Create message schema - use string directly for recipients
        message = MessageSchema(
            subject=f"KubeSage Alert: {alert_name} - {severity}",
            recipients=["nisha16063@gmail.com"],  # Hardcoded for testing
            body=email_body,
            subtype="html"
        )
        
        # Log SMTP configuration (without password)
        logger.info(f"SMTP Configuration: Server={mail_server}, Port={mail_port}, User={mail_username}")
        
        # Initialize FastMail and send the email
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"Alert email sent to nisha16063@gmail.com for alert: {alert_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        # More detailed error logging
        if hasattr(e, 'args') and len(e.args) > 0:
            logger.error(f"Error details: {e.args}")
        return False

def send_alert_email_background(background_tasks: BackgroundTasks, alert: Optional[Alert] = None):
    """Add email sending to background tasks"""
    background_tasks.add_task(send_alert_email, alert)
    logger.info("Email task added to background tasks")
    return True
