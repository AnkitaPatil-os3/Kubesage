from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.schemas import Alert, FlexibleAlertRequest
from app.alert_processor import process_alerts, process_alert_after_approval, parse_flexible_alert_data, process_flexible_alerts
from app.logger import logger
from app.email_client import send_alert_email, send_alert_email_background, create_test_alert, get_alert_status
from app.database import create_db_and_tables, get_session, engine
from app.models import AlertModel
from sqlmodel import Session, select

from typing import List, Optional, Dict, Any, Union
import datetime
import uuid
import json

# Create FastAPI app with metadata for documentation
app = FastAPI(
    title="KubeSage Analyzer Service",
    description="""
    The Analyzer Service processes Kubernetes alerts, determines their severity,
    and takes appropriate actions. Critical alerts require user approval via email,
    while non-critical alerts are processed automatically.
    
    NEW: Now supports flexible alert formats from various sources including Grafana, 
    Kubernetes events, and custom alert systems with original data preservation.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

@app.on_event("startup")
def on_startup():
    """Initialize database on startup"""
    try:
        # Step 1: Create database and tables first
        logger.info("Creating database tables...")
        create_db_and_tables()
        logger.info("Database tables created successfully")
        
        # Step 2: Run migration to add missing columns (if any)
        logger.info("Running database migration...")
        from app.migrations.db_utils import migrate_database
        migrate_database()
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    logger.info("Database initialization completed")

@app.post("/alerts", 
    summary="Process incoming alerts (Enhanced with Original Data Preservation)",
    description="""
    Receives and processes alerts from various monitoring systems with flexible format support.
    Preserves the original incoming JSON data exactly as received from the POST API.
    
    Supported formats:
    - Traditional Prometheus AlertManager format
    - Grafana alerts
    - Kubernetes events
    - Custom alert formats
    - Raw JSON data
    
    The API automatically detects the format and processes accordingly while preserving original data.
    """,
    response_description="Confirmation of alert processing",
    tags=["Alerts"])
async def receive_alerts(
    background_tasks: BackgroundTasks,
    request_data: Dict[str, Any] = Body(..., 
        description="Alert data in any format",
        
    )
):
    """
    Process incoming alerts with flexible format support and original data preservation.
    
    - Automatically detects alert format (Prometheus, Grafana, Kubernetes events, etc.)
    - Preserves original incoming JSON data exactly as received
    - Sends email notifications for all alerts
    - For critical alerts: Waits for user approval before remediation
    - For non-critical alerts: Automatically proceeds with remediation
    
    The request body can contain:
    - Traditional AlertManager format with 'alerts' array
    - Flexible format with 'data' field containing any alert structure
    - Direct JSON array of alerts
    - Raw alert data in various formats
    """
    try:
        logger.info("Received alert batch - processing with flexible format support and original data preservation")
        
        # Store original request data
        original_request_data = request_data
        
        # Handle different input formats and preserve original data
        if isinstance(request_data, dict):
            # Check if it's a traditional AlertManager format
            if "alerts" in request_data and request_data["alerts"]:
                # Traditional AlertManager format
                alerts_data = []
                for alert_dict in request_data["alerts"]:
                    alert = Alert(**alert_dict)
                    alerts_data.append(alert)
                await process_alerts(alerts_data, background_tasks, original_request_data)
            else:
                # Flexible format - treat entire dict as alert data
                flexible_alerts = parse_flexible_alert_data(request_data, original_request_data)
                await process_flexible_alerts(flexible_alerts, background_tasks, original_request_data)
        
        elif isinstance(request_data, list):
            # Handle direct list of alerts
            flexible_alerts = parse_flexible_alert_data(request_data, original_request_data)
            await process_flexible_alerts(flexible_alerts, background_tasks, original_request_data)
        
        else:
            # Try to parse as flexible format
            flexible_alerts = parse_flexible_alert_data(request_data, original_request_data)
            await process_flexible_alerts(flexible_alerts, background_tasks, original_request_data)
        
        return {"status": "Alerts processed successfully with original data preservation"}
        
    except Exception as e:
        logger.error(f"Error processing alerts: {str(e)}")
        # Try to handle as raw string data
        try:
            if isinstance(request_data, str):
                flexible_alerts = parse_flexible_alert_data(request_data, request_data)
                await process_flexible_alerts(flexible_alerts, background_tasks, request_data)
                return {"status": "Alerts processed from raw data format with original data preservation"}
        except Exception as fallback_error:
            logger.error(f"Fallback processing also failed: {str(fallback_error)}")
            raise HTTPException(status_code=400, detail=f"Unable to process alert data: {str(e)}")


@app.get("/alerts", 
    summary="Get all alerts with complete JSON data",
    description="Retrieves all alerts from the database with optional filtering and complete JSON data.",
    response_model=List[AlertModel],
    tags=["Alerts"])
async def get_alerts(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    approval_status: Optional[str] = None
):
    """
    Get all alerts with optional filtering and complete JSON data.
    
    Parameters:
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by alert status (e.g., 'firing', 'active')
    - **severity**: Filter by severity (e.g., 'critical', 'warning')
    - **approval_status**: Filter by approval status (e.g., 'pending', 'approved', 'rejected')
    """
    query = select(AlertModel)
    
    # Apply filters if provided
    if status:
        query = query.where(AlertModel.status == status)
    
    if approval_status:
        query = query.where(AlertModel.approval_status == approval_status)
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    results = session.exec(query).all()
    
    return results

@app.get("/alerts/{alert_id}", 
    summary="Get alert by ID with complete JSON data",
    description="Retrieves a specific alert by its ID with complete JSON data.",
    response_model=AlertModel,
    tags=["Alerts"])
async def get_alert(alert_id: str, session: Session = Depends(get_session)):
    """
    Get a specific alert by ID with complete JSON data.
    
    Parameters:
    - **alert_id**: Unique identifier for the alert
    """
    alert = session.exec(select(AlertModel).where(AlertModel.id == alert_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@app.get("/alerts/{alert_id}/raw-data",
    summary="Get complete JSON data for an alert",
    description="Get the complete original JSON data that was received for this alert.",
    tags=["Alerts"])
async def get_alert_complete_data(alert_id: str, session: Session = Depends(get_session)):
    """
    Get the complete original JSON data for a specific alert.
    
    Parameters:
    - **alert_id**: Unique identifier for the alert
    """
    alert = session.exec(select(AlertModel).where(AlertModel.id == alert_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "alert_id": alert_id,
        "complete_json_data": alert.complete_json_data,
        "created_at": alert.created_at,
        "updated_at": alert.updated_at
    }

@app.get("/alerts/{alert_id}/generated-report",
    summary="Get generated report for an alert",
    description="Get the generated report that was created for this alert.",
    tags=["Alerts"])
async def get_alert_generated_report(alert_id: str, session: Session = Depends(get_session)):
    """
    Get the generated report for a specific alert.
    
    Parameters:
    - **alert_id**: Unique identifier for the alert
    """
    alert = session.exec(select(AlertModel).where(AlertModel.id == alert_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "alert_id": alert_id,
        "generated_report": alert.generated_report,
        "created_at": alert.created_at,
        "updated_at": alert.updated_at
    }



@app.get("/test-email-sync", 
    summary="Test email sending (synchronous)",
    description="Tests the email notification system by sending a test alert email synchronously.",
    tags=["Testing"])
async def test_email_sync():
    """
    Test endpoint to verify email sending functionality synchronously.
    
    - Creates a test alert
    - Sends an email synchronously (waits for completion)
    - Returns the status and alert ID
    
    This is useful for testing the email configuration and getting immediate results.
    """
    try:
        # Create a test alert
        test_alert = create_test_alert()
        
        # Generate test report
        test_alert_dict = {
            "status": test_alert.status,
            "labels": test_alert.labels,
            "annotations": test_alert.annotations,
            "startsAt": test_alert.startsAt,
            "endsAt": test_alert.endsAt
        }
        from app.alert_processor import generate_report
        generated_report = generate_report(test_alert_dict, "prometheus")
        
        # Save test alert to database
        with Session(engine) as session:
            alert_id = str(uuid.uuid4())
            alert_model = AlertModel(
                id=alert_id,
                approval_status="pending",
                complete_json_data={
                    "labels": test_alert.labels,
                    "annotations": test_alert.annotations,
                    "status": test_alert.status,
                    "startsAt": test_alert.startsAt,
                    "endsAt": test_alert.endsAt,
                    "alert_type": "test"
                },
                generated_report=generated_report
            )
            session.add(alert_model)
            session.commit()
        
        # Send test email synchronously
        result, alert_id = await send_alert_email(test_alert, alert_id)
        
        if result:
            return {
                "status": "Email test successful", 
                "message": "Test email sent successfully",
                "alert_id": alert_id,
                "generated_report": generated_report
            }
        else:
            return {"status": "Email test failed", "message": "Failed to send test email"}
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return {"status": "Error", "message": f"Exception occurred: {str(e)}"}

@app.get("/test-non-critical", 
    summary="Test non-critical alert email",
    description="Tests the email notification system with a non-critical alert.",
    tags=["Testing"])
async def test_non_critical_email():
    """
    Test endpoint to verify non-critical alert email.
    
    - Creates a test alert with 'warning' severity
    - Sends an email synchronously
    - Returns the status and alert ID
    
    This is useful for testing how non-critical alerts are handled differently
    from critical alerts (no approval buttons, automatic remediation).
    """
    try:
        # Create a test alert with non-critical severity
        test_alert = Alert(
            status="firing",
            labels={
                "alertname": "NonCriticalAlert",
                "severity": "warning",  # Non-critical severity
                "instance": "test-instance"
            },
            annotations={
                "summary": "This is a test warning alert",
                "description": "This is a test warning alert that should be auto-remediated"
            },
            startsAt="2023-05-23T07:55:04Z",
            endsAt="2023-05-23T08:55:04Z"
        )
        
        # Generate test report
        test_alert_dict = {
            "status": test_alert.status,
            "labels": test_alert.labels,
            "annotations": test_alert.annotations,
            "startsAt": test_alert.startsAt,
            "endsAt": test_alert.endsAt
        }
        from app.alert_processor import generate_report
        generated_report = generate_report(test_alert_dict, "prometheus")
        
        # Save test alert to database
        with Session(engine) as session:
            alert_id = str(uuid.uuid4())
            alert_model = AlertModel(
                id=alert_id,
                approval_status="auto-approved",
                complete_json_data={
                    "labels": test_alert.labels,
                    "annotations": test_alert.annotations,
                    "status": test_alert.status,
                    "startsAt": test_alert.startsAt,
                    "endsAt": test_alert.endsAt,
                    "alert_type": "test"
                },
                generated_report=generated_report
            )
            session.add(alert_model)
            session.commit()
        
        # Send test email synchronously
        result, alert_id = await send_alert_email(test_alert, alert_id)
        
        if result:
            return {
                "status": "Non-critical email test successful", 
                "message": "Test email sent successfully without approval buttons",
                "alert_id": alert_id,
                "generated_report": generated_report
            }
        else:
            return {"status": "Email test failed", "message": "Failed to send test email"}
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return {"status": "Error", "message": f"Exception occurred: {str(e)}"}
