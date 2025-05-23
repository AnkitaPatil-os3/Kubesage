import requests
from app.config import settings
from app.logger import logger
from app.schemas import Alert

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
    except Exception as e:
        logger.error(f"Failed to notify enforcer: {e}")
