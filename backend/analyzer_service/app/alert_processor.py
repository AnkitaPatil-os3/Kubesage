from typing import List, Dict, Any, Union
from fastapi import BackgroundTasks
from app.schemas import Alert, FlexibleAlert
from app.llm_client import query_llm
from app.enforcer_client import send_to_enforcer
from app.email_client import send_alert_email_background
from app.logger import logger
from app.models import AlertModel
from app.database import engine
from sqlmodel import Session, select
import uuid
import json
from datetime import datetime

# New changes: Store original request data separately
def parse_flexible_alert_data(data: Union[List[Dict[str, Any]], Dict[str, Any], str], original_request_data: Any = None) -> List[FlexibleAlert]:
    """Parse various alert data formats into normalized FlexibleAlert objects"""
    alerts = []
    
    try:
        # Handle string data (might be JSON or multiple JSON objects)
        if isinstance(data, str):
            # Try to parse as single JSON
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                # Handle multiple JSON objects separated by newlines or concatenated
                json_objects = []
                lines = data.strip().split('\n')
                for line in lines:
                    if line.strip():
                        try:
                            json_objects.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            # Try to split concatenated JSON objects
                            parts = line.split('}{')
                            for i, part in enumerate(parts):
                                if i > 0:
                                    part = '{' + part
                                if i < len(parts) - 1:
                                    part = part + '}'
                                try:
                                    json_objects.append(json.loads(part))
                                except json.JSONDecodeError:
                                    continue
                data = json_objects
        
        # Ensure data is a list
        if not isinstance(data, list):
            data = [data]
        
        # Process each alert/event
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # New changes: Pass original request data to normalize function
            alert = normalize_alert_data(item, original_request_data)
            alerts.append(alert)
            
    except Exception as e:
        logger.error(f"Error parsing flexible alert data: {e}")
        # Create a fallback alert with the raw data
        alerts.append(FlexibleAlert(
            alert_type="unknown",
            severity="warning",
            status="active",
            raw_data=original_request_data if original_request_data else {"original_data": str(data), "parse_error": str(e)},
            title="Failed to parse alert data",
            description=f"Error parsing alert: {str(e)}"
        ))
    
    return alerts

# New changes: Updated to accept original request data
def normalize_alert_data(item: Dict[str, Any], original_request_data: Any = None) -> FlexibleAlert:
    """Normalize different alert formats into a standard FlexibleAlert"""
    
    # Detect alert type and extract relevant information
    alert_type = "unknown"
    severity = "info"
    status = "active"
    title = "Unknown Alert"
    description = ""
    source = ""
    timestamp = datetime.utcnow().isoformat()
    
    # Handle Kubernetes events (like your Grafana data)
    if "metadata" in item and "involvedObject" in item:
        alert_type = "kubernetes-event"
        
        # Extract information from Kubernetes event
        metadata = item.get("metadata", {})
        involved_object = item.get("involvedObject", {})
        
        title = f"{item.get('reason', 'Unknown')} - {involved_object.get('kind', 'Unknown')} {involved_object.get('name', 'Unknown')}"
        description = item.get("message", "No description available")
        source = f"{involved_object.get('namespace', 'default')}/{involved_object.get('kind', 'Unknown')}"
        timestamp = item.get("firstTimestamp") or item.get("lastTimestamp") or metadata.get("creationTimestamp", timestamp)
        
        # Determine severity based on event type
        event_type = item.get("type", "Normal")
        if event_type == "Warning":
            severity = "warning"
        elif event_type == "Error":
            severity = "critical"
        else:
            severity = "info"
            
        # Determine status
        if item.get("count", 1) > 1:
            status = "recurring"
        else:
            status = "active"
    
    # Handle Prometheus/AlertManager format
    elif "labels" in item and "annotations" in item:
        alert_type = "prometheus"
        
        labels = item.get("labels", {})
        annotations = item.get("annotations", {})
        
        title = labels.get("alertname", "Unknown Alert")
        description = annotations.get("summary") or annotations.get("description", "No description available")
        severity = labels.get("severity", "info").lower()
        status = item.get("status", "active")
        source = labels.get("instance") or labels.get("job", "unknown")
        timestamp = item.get("startsAt", timestamp)
    
    # Handle Grafana alerts
    elif "title" in item or "name" in item:
        alert_type = "grafana"
        
        title = item.get("title") or item.get("name", "Grafana Alert")
        description = item.get("message") or item.get("description", "No description available")
        severity = item.get("severity", "info").lower()
        status = item.get("state", "active").lower()
        source = item.get("datasource") or "grafana"
        timestamp = item.get("time") or item.get("timestamp", timestamp)
    
    # Handle generic alerts
    else:
        # Try to extract common fields
        title = (item.get("title") or item.get("name") or 
                item.get("alertname") or item.get("summary") or "Generic Alert")
        description = (item.get("description") or item.get("message") or 
                      item.get("summary") or "No description available")
        severity = (item.get("severity") or item.get("level") or 
                   item.get("priority", "info")).lower()
        status = (item.get("status") or item.get("state") or "active").lower()
        source = item.get("source") or item.get("origin") or "unknown"
    
    # New changes: Use original request data instead of processed item
    raw_data_to_store = original_request_data if original_request_data else item
    
    return FlexibleAlert(
        alert_type=alert_type,
        severity=severity,
        status=status,
        raw_data=raw_data_to_store,  # Store original request data
        title=title,
        description=description,
        source=source,
        timestamp=timestamp
    )

async def process_alerts(alerts: List[Alert], background_tasks: BackgroundTasks, original_request_data: Any = None):
    for alert in alerts:
        print("************************** test 1 ....")

        # Check if the alert is critical
        severity = alert.labels.get('severity', '').lower()
        
        # Save alert to database with original request data
        alert_id = save_alert_to_db(alert, original_request_data)
        
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

# New changes: Updated to accept original request data
async def process_flexible_alerts(alerts: List[FlexibleAlert], background_tasks: BackgroundTasks, original_request_data: Any = None):
    """Process flexible alerts from various sources"""
    for alert in alerts:
        print("************************** Processing flexible alert ....")

        # Check if the alert is critical
        severity = alert.severity.lower() if alert.severity else 'info'
        
        # Save alert to database with original request data
        alert_id = save_flexible_alert_to_db(alert, original_request_data)
        
        # Convert to legacy Alert format for email compatibility
        legacy_alert = convert_to_legacy_alert(alert)
        
        # Send email notification in all cases
        send_alert_email_background(background_tasks, legacy_alert, alert_id)
        logger.info(f"Email notification queued for flexible alert: {alert.title}")
        
        if severity == 'critical':
            # For critical alerts, wait for user response
            logger.info(f"Waiting for user response before processing critical alert: {alert.title}")
        else:
            # For non-critical alerts, process immediately
            prompt = build_flexible_prompt(alert)
            logger.info(f"Built prompt for non-critical alert: {alert.title}")
            action_plan = query_llm(prompt)
            logger.info(f"LLM Action Plan: {action_plan}")
            
            # Update database with action plan
            update_alert_action_plan(alert_id, action_plan, "auto-approved")
            
            # Send to enforcer
            send_to_enforcer(legacy_alert, action_plan)
            
            # Update remediation status
            update_alert_remediation_status(alert_id, "completed")
            
        print("*************************** Flexible alert processed ....")

# Convert FlexibleAlert to legacy Alert format for backward compatibility
def convert_to_legacy_alert(flexible_alert: FlexibleAlert) -> Alert:
    """Convert FlexibleAlert to legacy Alert format for email and other legacy functions"""
    
    # Create labels from flexible alert data
    labels = {
        "alertname": flexible_alert.title or "Unknown Alert",
        "severity": flexible_alert.severity or "info",
        "alert_type": flexible_alert.alert_type or "unknown",
        "source": flexible_alert.source or "unknown"
    }
    
    # Extract additional labels from raw_data if available
    if flexible_alert.raw_data:
        # For Kubernetes events
        if flexible_alert.alert_type == "kubernetes-event":
            involved_object = flexible_alert.raw_data.get("involvedObject", {})
            labels.update({
                "namespace": involved_object.get("namespace", "default"),
                "kind": involved_object.get("kind", "Unknown"),
                "name": involved_object.get("name", "Unknown"),
                "reason": flexible_alert.raw_data.get("reason", "Unknown")
            })
        
        # For Prometheus alerts
        elif flexible_alert.alert_type == "prometheus" and "labels" in flexible_alert.raw_data:
            labels.update(flexible_alert.raw_data["labels"])
    
    # Create annotations
    annotations = {
        "summary": flexible_alert.title or "No summary available",
        "description": flexible_alert.description or "No description available",
        "alert_type": flexible_alert.alert_type or "unknown"
    }
    
    # Extract additional annotations from raw_data if available
    if flexible_alert.raw_data:
        if flexible_alert.alert_type == "prometheus" and "annotations" in flexible_alert.raw_data:
            annotations.update(flexible_alert.raw_data["annotations"])
        elif flexible_alert.alert_type == "kubernetes-event":
            annotations.update({
                "message": flexible_alert.raw_data.get("message", ""),
                "reason": flexible_alert.raw_data.get("reason", ""),
                "type": flexible_alert.raw_data.get("type", "Normal"),
                "count": str(flexible_alert.raw_data.get("count", 1))
            })
    
    # Create timestamps
    start_time = flexible_alert.timestamp or datetime.utcnow().isoformat()
    end_time = start_time  # For active alerts, end time is same as start time
    
    return Alert(
        status=flexible_alert.status or "active",
        labels=labels,
        annotations=annotations,
        startsAt=start_time,
        endsAt=end_time,
        generatorURL=flexible_alert.raw_data.get("generatorURL"),
        fingerprint=flexible_alert.raw_data.get("fingerprint")
    )

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

def build_flexible_prompt(alert: FlexibleAlert) -> str:
    """Build LLM prompt for flexible alerts"""
    prompt = f"""
Alert Type: {alert.alert_type}
Title: {alert.title}
Severity: {alert.severity}
Status: {alert.status}
Source: {alert.source}
Description: {alert.description}
Timestamp: {alert.timestamp}

"""
    
    # Add specific information based on alert type
    if alert.alert_type == "kubernetes-event" and alert.raw_data:
        involved_object = alert.raw_data.get("involvedObject", {})
        prompt += f"""
Kubernetes Event Details:
- Namespace: {involved_object.get('namespace', 'Unknown')}
- Resource Kind: {involved_object.get('kind', 'Unknown')}
- Resource Name: {involved_object.get('name', 'Unknown')}
- Event Reason: {alert.raw_data.get('reason', 'Unknown')}
- Event Type: {alert.raw_data.get('type', 'Normal')}
- Count: {alert.raw_data.get('count', 1)}
- Message: {alert.raw_data.get('message', 'No message')}
"""
    
    prompt += "\nWhat steps should we take to resolve this issue?"
    return prompt

# New changes: Updated to accept original request data
def save_alert_to_db(alert: Alert, original_request_data: Any = None) -> str:
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
                approval_status="pending",
                complete_json_data=original_request_data if original_request_data else {}  # Store original request data
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

# New changes: Updated to accept original request data
def save_flexible_alert_to_db(alert: FlexibleAlert, original_request_data: Any = None) -> str:
    """Save flexible alert to database and return the alert ID"""
    try:
        with Session(engine) as session:
            # Create a unique ID for the alert
            alert_id = str(uuid.uuid4())
            
            # Extract additional fields for Kubernetes events
            namespace = None
            resource_kind = None
            resource_name = None
            
            # Extract from the original raw data (not processed data)
            raw_data_for_extraction = alert.raw_data
            if alert.alert_type == "kubernetes-event" and raw_data_for_extraction:
                involved_object = raw_data_for_extraction.get("involvedObject", {})
                namespace = involved_object.get("namespace")
                resource_kind = involved_object.get("kind")
                resource_name = involved_object.get("name")
            
            # Create labels and annotations for compatibility
            labels = {
                "alertname": alert.title or "Unknown Alert",
                "severity": alert.severity or "info",
                "alert_type": alert.alert_type or "unknown",
                "source": alert.source or "unknown"
            }
            
            annotations = {
                "summary": alert.title or "No summary available",
                "description": alert.description or "No description available",
                "alert_type": alert.alert_type or "unknown"
            }
            
            # Create database model from flexible alert
            alert_model = AlertModel(
                id=alert_id,
                status=alert.status or "active",
                labels=labels,
                annotations=annotations,
                startsAt=alert.timestamp or datetime.utcnow().isoformat(),
                endsAt=alert.timestamp or datetime.utcnow().isoformat(),
                approval_status="pending",
                # New flexible fields
                alert_type=alert.alert_type or "unknown",
                source_system=alert.source,
                raw_data=alert.raw_data,
                severity=alert.severity or "info",
                title=alert.title,
                description=alert.description,
                namespace=namespace,
                resource_kind=resource_kind,
                resource_name=resource_name,
                complete_json_data=original_request_data if original_request_data else alert.raw_data  # Store original request data
            )
            
            # Add to database
            session.add(alert_model)
            session.commit()
            
            logger.info(f"Flexible alert saved to database with ID: {alert_id}")
            return alert_id
    except Exception as e:
        logger.error(f"Error saving flexible alert to database: {e}")
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
