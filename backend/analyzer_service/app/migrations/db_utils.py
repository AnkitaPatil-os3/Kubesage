from sqlmodel import Session, select, text
from app.database import engine
from app.models import AlertModel
import logging
from datetime import datetime, timedelta
import random
import uuid
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Run database migrations"""
    try:
        with Session(engine) as session:
            # Check if column exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='alerts' AND column_name='complete_json_data';
            """)
            
            result = session.exec(check_column_query).first()
            
            if not result:
                # Add the new column
                alter_query = text("""
                    ALTER TABLE alerts 
                    ADD COLUMN complete_json_data JSON DEFAULT '{}';
                """)
                
                session.exec(alter_query)
                session.commit()
                logger.info("Successfully added 'complete_json_data' column")
            else:
                logger.info("Column 'complete_json_data' already exists")
                
    except Exception as e:
        logger.error(f"Error during database migration: {e}")
        raise

def clear_all_data():
    """Clear all data from the database"""
    with Session(engine) as session:
        alerts = session.exec(select(AlertModel)).all()
        for alert in alerts:
            session.delete(alert)
        session.commit()
    logger.info("All data cleared from database")

def create_sample_data(count=10):
    """Create sample alert data for testing with complete JSON storage"""
    # First ensure the column exists
    migrate_database()
    
    severities = ["critical", "warning", "info"]
    statuses = ["firing", "resolved"]
    approval_statuses = ["pending", "approved", "rejected", "auto-approved"]
    remediation_statuses = ["pending", "in_progress", "completed", "failed"]
    alert_types = ["prometheus", "grafana", "kubernetes-event"]
    
    with Session(engine) as session:
        for i in range(count):
            # Determine severity and approval status
            severity = random.choice(severities)
            alert_type = random.choice(alert_types)
            
            # For critical alerts, use manual approval statuses
            if severity == "critical":
                approval_status = random.choice(["pending", "approved", "rejected"])
            else:
                # For non-critical, use auto-approved
                approval_status = "auto-approved"
            
            # Create complete JSON data based on alert type
            if alert_type == "kubernetes-event":
                complete_json_data = {
                    "metadata": {
                        "name": f"test-event-{i+1}",
                        "namespace": "default",
                        "creationTimestamp": (datetime.utcnow() - timedelta(hours=random.randint(1, 24))).isoformat()
                    },
                    "involvedObject": {
                        "kind": "Pod",
                        "name": f"test-pod-{i+1}",
                        "namespace": "default"
                    },
                    "reason": "FailedScheduling",
                    "message": f"Test Kubernetes event message {i+1}",
                    "type": "Warning" if severity in ["critical", "warning"] else "Normal",
                    "count": random.randint(1, 5),
                    "firstTimestamp": (datetime.utcnow() - timedelta(hours=random.randint(1, 24))).isoformat(),
                    "lastTimestamp": datetime.utcnow().isoformat(),
                    "alert_type": alert_type,
                    "processed_at": datetime.utcnow().isoformat()
                }
            elif alert_type == "grafana":
                complete_json_data = {
                    "title": f"Grafana Alert {i+1}",
                    "message": f"This is a test Grafana alert {i+1}",
                    "severity": severity,
                    "state": random.choice(statuses),
                    "datasource": "prometheus",
                    "time": datetime.utcnow().isoformat(),
                    "tags": {
                        "team": "devops",
                        "environment": "production"
                    },
                    "alert_type": alert_type,
                    "processed_at": datetime.utcnow().isoformat()
                }
            else:  # prometheus
                complete_json_data = {
                    "status": random.choice(statuses),
                    "labels": {
                        "alertname": f"Test Alert {i+1}",
                        "severity": severity,
                        "instance": f"test-instance-{i+1}",
                        "job": "test-job"
                    },
                    "annotations": {
                        "summary": f"This is test alert {i+1}",
                        "description": f"This is a detailed description for test alert {i+1}"
                    },
                    "startsAt": (datetime.utcnow() - timedelta(hours=random.randint(1, 24))).isoformat(),
                    "endsAt": (datetime.utcnow() + timedelta(hours=random.randint(1, 24))).isoformat(),
                    "generatorURL": f"http://prometheus:9090/graph?g0.expr=test_metric_{i+1}",
                    "fingerprint": f"test_fingerprint_{i+1}",
                    "alert_type": alert_type,
                    "processed_at": datetime.utcnow().isoformat()
                }
            
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
                updated_at=datetime.utcnow(),
                complete_json_data=complete_json_data
            )
            session.add(alert)
        
        session.commit()
    logger.info(f"Created {count} sample alerts with complete JSON data")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "migrate":
            migrate_database()
        elif sys.argv[1] == "clear":
            clear_all_data()
        elif sys.argv[1] == "sample":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            create_sample_data(count)
        else:
            print("Unknown command. Use 'migrate', 'clear', or 'sample'")
    else:
        print("Please specify a command:")
        print("  migrate - Run database migration")
        print("  clear - Clear all data")
        print("  sample [count] - Create sample data")