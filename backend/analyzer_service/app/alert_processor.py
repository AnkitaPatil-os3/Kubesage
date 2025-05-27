from typing import List
from fastapi import BackgroundTasks
from app.schemas import Alert
from app.llm_client import query_llm
from app.enforcer_client import send_to_enforcer
from app.email_client import send_alert_email_background
from app.logger import logger
from app.models import AlertModel
from app.database import engine
from sqlmodel import Session, select
import uuid

async def process_alerts(alerts: List[Alert], background_tasks: BackgroundTasks):
    for alert in alerts:
        print("************************** test 1 ....")

        # Check if the alert is critical
        severity = alert.labels.get('severity', '').lower()
        
        # Save alert to database
        alert_id = save_alert_to_db(alert)
        
        # Send email notification in all cases
        send_alert_email_background(background_tasks, alert, alert_id)
        logger.info(f"Email notification queued for alert: {alert.labels.get('alertname')}")
        
        if severity == 'critical':
            # For critical alerts, wait for user response
            logger.info(f"Waiting for user response before processing critical alert: {alert.labels.get('alertname')}")
        else:
            # For non-critical alerts, process immediately
            prompt = build_prompt(alert)
            logger.info(f"Built prompt for non-critical alert: {alert.labels.get('alertname')}")
            action_plan = query_llm(prompt)
            logger.info(f"LLM Action Plan: {action_plan}")
            
            # Update database with action plan
            update_alert_action_plan(alert_id, action_plan, "auto-approved")
            
            # Send to enforcer
            send_to_enforcer(alert, action_plan)
            
            # Update remediation status
            update_alert_remediation_status(alert_id, "completed")
            
        print("*************************** test 2 ....")

async def process_alert_after_approval(alert_id: str, approved: bool):
    """Process an alert after receiving user response"""
    from app.email_client import get_alert_status, update_alert_status
    
    # Get the alert details
    alert_data = get_alert_status(alert_id)
    if not alert_data:
        logger.error(f"Alert ID not found: {alert_id}")
        return False
    
    alert = alert_data["alert"]
    
    if approved:
        # User approved, process the alert
        logger.info(f"Processing approved alert: {alert.labels.get('alertname')}")
        prompt = build_prompt(alert)
        logger.info(f"Built prompt for approved alert: {alert.labels.get('alertname')}")
        action_plan = query_llm(prompt)
        logger.info(f"LLM Action Plan: {action_plan}")
        
        # Update database with action plan and status
        update_alert_action_plan(alert_id, action_plan, "approved")
        
        # Send to enforcer
        send_to_enforcer(alert, action_plan)
        
        # Update remediation status
        update_alert_remediation_status(alert_id, "completed")
        
        # Update in-memory status
        update_alert_status(alert_id, "approved")
        return True
    else:
        # User rejected, log and skip
        logger.info(f"Alert rejected by user, skipping: {alert.labels.get('alertname')}")
        
        # Update database status
        update_alert_approval_status(alert_id, "rejected")
        
        # Update in-memory status
        update_alert_status(alert_id, "rejected")
        return True

def build_prompt(alert: Alert) -> str:
    return f"""
Alert Triggered: {alert.labels.get('alertname')}
Severity: {alert.labels.get('severity')}
Summary: {alert.annotations.get('summary')}
Description: {alert.annotations.get('description')}
Start Time: {alert.startsAt}

What steps should we take to resolve this issue?
"""

def save_alert_to_db(alert: Alert) -> str:
    """Save alert to database and return the alert ID"""
    try:
        with Session(engine) as session:
            # Create a unique ID for the alert
            alert_id = str(uuid.uuid4())
            
            # Create database model from schema
            alert_model = AlertModel(
                id=alert_id,
                status=alert.status,
                labels=alert.labels,
                annotations=alert.annotations,
                startsAt=alert.startsAt,
                endsAt=alert.endsAt,
                generatorURL=alert.generatorURL,
                fingerprint=alert.fingerprint,
                approval_status="pending"
            )
            
            # Add to database
            session.add(alert_model)
            session.commit()
            
            logger.info(f"Alert saved to database with ID: {alert_id}")
            return alert_id
    except Exception as e:
        logger.error(f"Error saving alert to database: {e}")
        # Return a generated ID even if save fails to allow processing to continue
        return str(uuid.uuid4())

def update_alert_approval_status(alert_id: str, status: str):
    """Update the approval status of an alert in the database"""
    try:
        with Session(engine) as session:
            # Find the alert
            statement = select(AlertModel).where(AlertModel.id == alert_id)
            alert = session.exec(statement).first()
            
            if alert:
                # Update status
                alert.approval_status = status
                session.add(alert)
                session.commit()
                logger.info(f"Alert {alert_id} approval status updated to: {status}")
            else:
                logger.warning(f"Alert {alert_id} not found in database for status update")
    except Exception as e:
        logger.error(f"Error updating alert status in database: {e}")

def update_alert_action_plan(alert_id: str, action_plan: str, status: str):
    """Update the action plan and approval status of an alert in the database"""
    try:
        with Session(engine) as session:
            # Find the alert
            statement = select(AlertModel).where(AlertModel.id == alert_id)
            alert = session.exec(statement).first()
            
            if alert:
                # Update action plan and status
                alert.action_plan = action_plan
                alert.approval_status = status
                session.add(alert)
                session.commit()
                logger.info(f"Alert {alert_id} action plan and status updated")
            else:
                logger.warning(f"Alert {alert_id} not found in database for action plan update")
    except Exception as e:
        logger.error(f"Error updating alert action plan in database: {e}")

def update_alert_remediation_status(alert_id: str, status: str):
    """Update the remediation status of an alert in the database"""
    try:
        with Session(engine) as session:
            # Find the alert
            statement = select(AlertModel).where(AlertModel.id == alert_id)
            alert = session.exec(statement).first()
            
            if alert:
                # Update remediation status
                alert.remediation_status = status
                session.add(alert)
                session.commit()
                logger.info(f"Alert {alert_id} remediation status updated to: {status}")
            else:
                logger.warning(f"Alert {alert_id} not found in database for remediation status update")
    except Exception as e:
        logger.error(f"Error updating alert remediation status in database: {e}")
