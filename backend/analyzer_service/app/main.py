from fastapi import FastAPI, Request , BackgroundTasks
from app.schemas import AlertRequest, Alert
from app.alert_processor import process_alerts
from app.logger import logger
from app.email_client import send_alert_email, send_alert_email_background, create_test_alert


app = FastAPI()

@app.post("/alerts")
async def receive_alerts(request: AlertRequest, background_tasks: BackgroundTasks):
    logger.info("Received alert batch")
    await process_alerts(request.alerts , background_tasks) # add background_tasks here
    return {"status": "Alerts processed with background tasks"}





@app.get("/test-email")
async def test_email(background_tasks: BackgroundTasks):
    """Test endpoint to verify email sending functionality"""
    try:
        # Create a test alert
        test_alert = create_test_alert()
        
        # Send test email in the background
        send_alert_email_background(background_tasks, test_alert)
        
        return {
            "status": "Email test initiated", 
            "message": "Test email sending has been queued in background tasks. Check logs for results."
        }
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return {"status": "Error", "message": f"Exception occurred: {str(e)}"}

@app.get("/test-email-sync")
async def test_email_sync():
    """Test endpoint to verify email sending functionality synchronously"""
    try:
        # Create a test alert
        test_alert = create_test_alert()
        
        # Send test email synchronously
        result = await send_alert_email(test_alert)
        
        if result:
            return {"status": "Email test successful", "message": "Test email sent successfully"}
        else:
            return {"status": "Email test failed", "message": "Failed to send test email"}
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return {"status": "Error", "message": f"Exception occurred: {str(e)}"}

    """Test endpoint to verify email sending functionality"""
    try:
        # Create a test alert
        test_alert = Alert(
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
        
        # Send test email
        result = await send_alert_email(test_alert)
        
        if result:
            return {"status": "Email test successful", "message": "Test email sent successfully"}
        else:
            return {"status": "Email test failed", "message": "Failed to send test email"}
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return {"status": "Error", "message": f"Exception occurred: {str(e)}"}