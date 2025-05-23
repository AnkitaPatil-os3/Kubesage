from typing import List
from fastapi import BackgroundTasks
from app.schemas import Alert
from app.llm_client import query_llm
from app.enforcer_client import send_to_enforcer
from app.email_client import send_alert_email
from app.email_client import send_alert_email_background
from app.logger import logger

async def process_alerts(alerts: List[Alert], background_tasks: BackgroundTasks):
    for alert in alerts:

        print("************************** test 1 ....")

         # Send email notification in the background
        send_alert_email_background(background_tasks, alert)
        logger.info(f"Email notification queued for alert: {alert.labels.get('alertname')}")
        print("*************************** test 2 ....")

        prompt = build_prompt(alert)
        print('prompt', prompt)
        logger.info(f"Built prompt for alert: {alert.labels.get('alertname')}")
        action_plan = query_llm(prompt)
        logger.info(f"LLM Action Plan: {action_plan}")
        send_to_enforcer(alert, action_plan)


def build_prompt(alert: Alert) -> str:
    return f"""
Alert Triggered: {alert.labels.get('alertname')}
Severity: {alert.labels.get('severity')}
Summary: {alert.annotations.get('summary')}
Description: {alert.annotations.get('description')}
Start Time: {alert.startsAt}

What steps should we take to resolve this issue?
"""



