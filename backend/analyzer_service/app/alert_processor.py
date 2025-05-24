from typing import List
from fastapi import BackgroundTasks
from app.schemas import Alert
from app.llm_client import query_llm
from app.enforcer_client import send_to_enforcer
from app.email_client import send_alert_email_background
from app.logger import logger

async def process_alerts(alerts: List[Alert], background_tasks: BackgroundTasks):
    for alert in alerts:
        print("************************** test 1 ....")

        # Check if the alert is critical
        severity = alert.labels.get('severity', '').lower()
        
        # Send email notification in all cases
        send_alert_email_background(background_tasks, alert)
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
            send_to_enforcer(alert, action_plan)
            
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
        send_to_enforcer(alert, action_plan)
        update_alert_status(alert_id, "approved")
        return True
    else:
        # User rejected, log and skip
        logger.info(f"Alert rejected by user, skipping: {alert.labels.get('alertname')}")
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
