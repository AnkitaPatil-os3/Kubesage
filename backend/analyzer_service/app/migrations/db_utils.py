from sqlmodel import Session, select
from app.database import engine
from app.models import AlertModel
import logging
from datetime import datetime, timedelta
import random
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_all_data():
    """Clear all data from the database"""
    with Session(engine) as session:
        alerts = session.exec(select(AlertModel)).all()
        for alert in alerts:
            session.delete(alert)
        session.commit()
    logger.info("All data cleared from database")

def create_sample_data(count=10):
    """Create sample alert data for testing"""
    severities = ["critical", "warning", "info"]
    statuses = ["firing", "resolved"]
    approval_statuses = ["pending", "approved", "rejected", "auto-approved"]
    remediation_statuses = ["pending", "in_progress", "completed", "failed"]
    
    with Session(engine) as session:
        for i in range(count):
            # Determine severity and approval status
            severity = random.choice(severities)
            
            # For critical alerts, use manual approval statuses
            if severity == "critical":
                approval_status = random.choice(["pending", "approved", "rejected"])
            else:
                # For non-critical, use auto-approved
                approval_status = "auto-approved"
            
            # Create alert
            alert = AlertModel(
                id=str(uuid.uuid4()),
                status=random.choice(statuses),
                labels={
                    "alertname": f"Test Alert {i+1}",
                    "severity": severity,
                    "instance": f"test-instance-{i+1}"
                },
                annotations={
                    "summary": f"This is test alert {i+1}",
                    "description": f"This is a detailed description for test alert {i+1}"
                },
                startsAt=(datetime.utcnow() - timedelta(hours=random.randint(1, 24))).isoformat(),
                endsAt=(datetime.utcnow() + timedelta(hours=random.randint(1, 24))).isoformat(),
                approval_status=approval_status,
                action_plan="Sample action plan" if approval_status in ["approved", "auto-approved"] else None,
                remediation_status=random.choice(remediation_statuses) if approval_status in ["approved", "auto-approved"] else None,
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                updated_at=datetime.utcnow()
            )
            session.add(alert)
        
        session.commit()
    logger.info(f"Created {count} sample alerts")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "clear":
            clear_all_data()
        elif sys.argv[1] == "sample":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            create_sample_data(count)
        else:
            print("Unknown command. Use 'clear' or 'sample'")
    else:
        print("Please specify a command: 'clear' or 'sample'")