from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.schemas import AlertRequest, Alert
from app.alert_processor import process_alerts, process_alert_after_approval
from app.logger import logger
from app.email_client import send_alert_email, send_alert_email_background, create_test_alert, get_alert_status
from app.database import create_db_and_tables, get_session, engine
from app.models import AlertModel
from sqlmodel import Session, select
from typing import List, Optional
import datetime
import uuid

# Create FastAPI app with metadata for documentation
app = FastAPI(
    title="KubeSage Analyzer Service",
    description="""
    The Analyzer Service processes Kubernetes alerts, determines their severity,
    and takes appropriate actions. Critical alerts require user approval via email,
    while non-critical alerts are processed automatically.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

@app.on_event("startup")
def on_startup():
    """Initialize database on startup"""
    create_db_and_tables()
    logger.info("Database initialized")

@app.post("/alerts", 
    summary="Process incoming alerts",
    description="Receives a batch of alerts from monitoring systems and processes them based on severity.",
    response_description="Confirmation of alert processing",
    tags=["Alerts"])
async def receive_alerts(request: AlertRequest, background_tasks: BackgroundTasks):
    """
    Process a batch of incoming Kubernetes alerts.
    
    - Sends email notifications for all alerts
    - For critical alerts: Waits for user approval before remediation
    - For non-critical alerts: Automatically proceeds with remediation
    
    The request body should contain a list of alerts with their metadata.
    """
    logger.info("Received alert batch")
    await process_alerts(request.alerts, background_tasks)
    return {"status": "Alerts processed with background tasks"}

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
    summary="Get all alerts",
    description="Retrieves all alerts from the database with optional filtering.",
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
    Get all alerts with optional filtering.
    
    Parameters:
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by alert status (e.g., 'firing')
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
        # This is a bit more complex since severity is in the labels JSON
        # We'll need to filter in Python after fetching
        pass
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    results = session.exec(query).all()
    
    # Apply severity filter if needed (post-processing)
    if severity:
        results = [alert for alert in results if alert.labels.get('severity', '').lower() == severity.lower()]
    
    return results

@app.get("/alerts/{alert_id}", 
    summary="Get alert by ID",
    description="Retrieves a specific alert by its ID.",
    response_model=AlertModel,
    tags=["Alerts"])
async def get_alert(alert_id: str, session: Session = Depends(get_session)):
    """
    Get a specific alert by ID.
    
    Parameters:
    - **alert_id**: Unique identifier for the alert
    """
    alert = session.exec(select(AlertModel).where(AlertModel.id == alert_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

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

