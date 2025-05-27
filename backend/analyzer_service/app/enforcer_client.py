import requests
from app.config import settings
from app.logger import logger
from app.schemas import Alert
from app.models import AlertModel
from app.database import engine
from sqlmodel import Session, select

def send_to_enforcer(alert: Alert, plan: str):
    try:
        payload = {
            "alertname": alert.labels.get("alertname"),
            "plan": plan,
            "severity": alert.labels.get("severity")
        }
        response = requests.post(f"{settings.ENFORCER_URL}/execute", json=payload)
        response.raise_for_status()
        logger.info("Successfully forwarded to enforcer")
        
        # Update alert in database with remediation status
        update_remediation_status(alert, "in_progress")
        
        return True
    except Exception as e:
        logger.error(f"Failed to notify enforcer: {e}")
        
        # Update alert in database with failed status
        update_remediation_status(alert, "failed")
        
        return False

def update_remediation_status(alert: Alert, status: str):
    """Update the remediation status of an alert in the database"""
    try:
        # Find the alert by its fingerprint or other unique identifier
        with Session(engine) as session:
            # Try to find by fingerprint first if available
            if alert.fingerprint:
                db_alert = session.exec(
                    select(AlertModel).where(AlertModel.fingerprint == alert.fingerprint)
                ).first()
            else:
                # Otherwise try to match by other fields
                db_alert = session.exec(
                    select(AlertModel).where(
                        (AlertModel.startsAt == alert.startsAt) &
                        (AlertModel.labels["alertname"].as_string() == alert.labels.get("alertname"))
                    )
                ).first()
            
            if db_alert:
                db_alert.remediation_status = status
                session.add(db_alert)
                session.commit()
                logger.info(f"Updated remediation status to {status} for alert: {alert.labels.get('alertname')}")
            else:
                logger.warning(f"Could not find alert in database to update remediation status: {alert.labels.get('alertname')}")
    except Exception as e:
        logger.error(f"Error updating remediation status in database: {e}")
