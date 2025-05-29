from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse


from app.schemas import AlertRequest, Alert, FlexibleAlertRequest  # New changes: Added FlexibleAlertRequest
from app.alert_processor import process_alerts, process_alert_after_approval, parse_flexible_alert_data, process_flexible_alerts  # New changes: Added flexible processing functions
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

# New changes: Updated to preserve original request data
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

async def receive_alerts(request: Union[AlertRequest, FlexibleAlertRequest, Dict[str, Any], List[Dict[str, Any]]], background_tasks: BackgroundTasks):
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
        
        # New changes: Store original request data
        original_request_data = None
        if hasattr(request, 'dict'):
            original_request_data = request.dict()
        elif isinstance(request, (dict, list)):
            original_request_data = request
        else:
            original_request_data = str(request)
        
        # Handle different input formats and preserve original data
        if isinstance(request, dict):
            # Handle raw dictionary input
            if "alerts" in request:
                # Traditional AlertManager format
                alert_request = AlertRequest(**request)
                await process_alerts(alert_request.alerts, background_tasks, original_request_data)
            else:
                # Flexible format - treat entire dict as alert data
                flexible_alerts = parse_flexible_alert_data(request, original_request_data)
                await process_flexible_alerts(flexible_alerts, background_tasks, original_request_data)
        
        elif isinstance(request, list):
            # Handle direct list of alerts
            flexible_alerts = parse_flexible_alert_data(request, original_request_data)
            await process_flexible_alerts(flexible_alerts, background_tasks, original_request_data)
        
        elif hasattr(request, 'alerts') and request.alerts:
            # Traditional AlertRequest format
            await process_alerts(request.alerts, background_tasks, original_request_data)
        
        elif hasattr(request, 'data') and request.data:
            # FlexibleAlertRequest format
            flexible_alerts = parse_flexible_alert_data(request.data, original_request_data)
            await process_flexible_alerts(flexible_alerts, background_tasks, original_request_data)
        
        else:
            # Try to parse as flexible format
            request_dict = request.dict() if hasattr(request, 'dict') else request
            flexible_alerts = parse_flexible_alert_data(request_dict, original_request_data)
            await process_flexible_alerts(flexible_alerts, background_tasks, original_request_data)
        
        return {"status": "Alerts processed successfully with original data preservation"}
        
    except Exception as e:
        logger.error(f"Error processing alerts: {str(e)}")
        # New changes: Try to handle as raw string data (like your Grafana example)
        try:
            if hasattr(request, 'body'):
                raw_data = request.body
            else:
                raw_data = str(request)
            
            flexible_alerts = parse_flexible_alert_data(raw_data, raw_data)
            await process_flexible_alerts(flexible_alerts, background_tasks, raw_data)
            return {"status": "Alerts processed from raw data format with original data preservation"}
        except Exception as fallback_error:
            logger.error(f"Fallback processing also failed: {str(fallback_error)}")
            raise HTTPException(status_code=400, detail=f"Unable to process alert data: {str(e)}")

# New changes: Updated to preserve original request data
@app.post("/alerts/raw",
    summary="Process raw alert data with original data preservation",
    description="""
    Endpoint specifically designed to handle raw alert data in any format.
    Preserves the complete incoming data exactly as received from the POST API.
    Useful for webhook integrations where the data format is not standardized.
    """,
    tags=["Alerts"])
async def receive_raw_alerts(request: Request, background_tasks: BackgroundTasks):
    """
    Process raw alert data from webhooks or custom integrations with original data preservation.
    
    This endpoint accepts any content type and tries to parse the data
    as alerts regardless of the format while preserving the original data exactly as received.
    """
    try:
        # Get raw body data
        body = await request.body()
        content_type = request.headers.get("content-type", "")
        
        logger.info(f"Received raw alert data, content-type: {content_type}")
        
        # Try to decode the body
        if body:
            try:
                # Try UTF-8 decoding first
                raw_data = body.decode('utf-8')
            except UnicodeDecodeError:
                # Fallback to latin-1 if UTF-8 fails
                raw_data = body.decode('latin-1')
            
            # New changes: Store original raw data
            original_request_data = raw_data
            
            # Parse and process the data
            flexible_alerts = parse_flexible_alert_data(raw_data, original_request_data)
            await process_flexible_alerts(flexible_alerts, background_tasks, original_request_data)
            
            return {
                "status": "Raw alert data processed successfully with original data preservation",
                "alerts_processed": len(flexible_alerts),
                "content_type": content_type
            }
        else:
            raise HTTPException(status_code=400, detail="No data received")
            
    except Exception as e:
        logger.error(f"Error processing raw alert data: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Unable to process raw alert data: {str(e)}")

@app.get("/alert-response/{alert_id}/{response}", 
    response_class=HTMLResponse,
    summary="Handle user response to alert",
    description="Processes user's approval or rejection of a critical alert remediation.",
    tags=["Alerts"])
async def handle_alert_response(alert_id: str, response: str):
    """
    Handle user response to an alert email.
    
    - Validates the response (must be 'yes' or 'no')
    - Checks if the alert exists
    - Processes the alert based on the user's response
    - Returns an HTML page confirming the action
    
    Parameters:
    - **alert_id**: Unique identifier for the alert
    - **response**: User's response ('yes' to approve, 'no' to reject)
    """
    # Validate the response
    if response not in ["yes", "no"]:
        raise HTTPException(status_code=400, detail="Invalid response. Must be 'yes' or 'no'.")
    
    # Check if the alert exists
    alert_data = get_alert_status(alert_id)
    if not alert_data:
        return HTMLResponse(content="""
        <html>
            <head><title>Invalid Alert</title></head>
            <body>
                <h1>Invalid Alert ID</h1>
                <p>The alert you're responding to doesn't exist or has expired.</p>
            </body>
        </html>
        """)
    
    # Process the alert based on the response
    approved = (response == "yes")
    result = await process_alert_after_approval(alert_id, approved)
    
    # Return a nice HTML response
    action = "approved" if approved else "rejected"
    return HTMLResponse(content=f"""
    <html>
        <head>
            <title>Alert {action.capitalize()}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                h1 {{ color: {'#4CAF50' if approved else '#f44336'}; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Alert {action.capitalize()}</h1>
                <p>You have {action} the alert: <strong>{alert_data['alert'].labels.get('alertname', 'Unknown Alert')}</strong></p>
                <p>{'The system will now proceed with automatic remediation.' if approved else 'No automatic remediation will be performed.'}</p>
                <p>Thank you for your response.</p>
            </div>
        </body>
    </html>
    """)

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
    
    if severity:
        # New changes: Filter by severity from complete_json_data
        query = query.where(AlertModel.labels['severity'].astext == severity)
    
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

# New changes: Added endpoint to get complete JSON data for an alert
@app.get("/alerts/{alert_id}/complete-data",
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

# New changes: Added endpoint to get alert statistics by type
@app.get("/alerts/stats/by-type",
    summary="Get alert statistics by type",
    description="Get statistics of alerts grouped by alert type.",
    tags=["Alerts", "Statistics"])
async def get_alert_stats_by_type(session: Session = Depends(get_session)):
    """
    Get alert statistics grouped by alert type.
    
    Returns counts for each alert type (prometheus, grafana, kubernetes-event, etc.)
    """
    try:
        # Get all alerts and group by type
        alerts = session.exec(select(AlertModel)).all()
        
        stats = {}
        for alert in alerts:
            alert_type = alert.alert_type or "unknown"
            if alert_type not in stats:
                stats[alert_type] = {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0,
                    "pending": 0,
                    "approved": 0,
                    "rejected": 0,
                    "auto_approved": 0
                }
            
            stats[alert_type]["total"] += 1
            
            # Count by severity
            severity = alert.severity or "info"
            if severity in stats[alert_type]:
                stats[alert_type][severity] += 1
            
            # Count by approval status
            approval = alert.approval_status or "pending"
            if approval in stats[alert_type]:
                stats[alert_type][approval] += 1
        
        return {"alert_type_statistics": stats}
        
    except Exception as e:
        logger.error(f"Error getting alert statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")

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
        
        # Save test alert to database
        with Session(engine) as session:
            alert_id = str(uuid.uuid4())
            alert_model = AlertModel(
                id=alert_id,
                status=test_alert.status,
                labels=test_alert.labels,
                annotations=test_alert.annotations,
                startsAt=test_alert.startsAt,
                endsAt=test_alert.endsAt,
                approval_status="pending"
            )
            session.add(alert_model)
            session.commit()
        
        # Send test email synchronously
        result, alert_id = await send_alert_email(test_alert, alert_id)
        
        if result:
            return {
                "status": "Email test successful", 
                "message": "Test email sent successfully",
                "alert_id": alert_id
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
        
        # Save test alert to database
        with Session(engine) as session:
            alert_id = str(uuid.uuid4())
            alert_model = AlertModel(
                id=alert_id,
                status=test_alert.status,
                labels=test_alert.labels,
                annotations=test_alert.annotations,
                startsAt=test_alert.startsAt,
                endsAt=test_alert.endsAt,
                approval_status="auto-approved"
            )
            session.add(alert_model)
            session.commit()
        
        # Send test email synchronously
        result, alert_id = await send_alert_email(test_alert, alert_id)
        
        if result:
            return {
                "status": "Non-critical email test successful", 
                "message": "Test email sent successfully without approval buttons",
                "alert_id": alert_id
            }
        else:
            return {"status": "Email test failed", "message": "Failed to send test email"}
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return {"status": "Error", "message": f"Exception occurred: {str(e)}"}

