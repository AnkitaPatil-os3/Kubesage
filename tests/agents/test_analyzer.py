import pytest
from datetime import datetime

from app.models import RawEvent, Incident
from app.agents.analyzer import AnalyzerAgent

# Sample Kubernetes Event Data (from analyzer.py example)
SAMPLE_K8S_EVENT_DATA_OK = {
    "metadata": {"name": "pod-xyz-crash-1", "namespace": "production"},
    "involvedObject": {
        "kind": "Pod",
        "name": "my-app-pod-12345",
        "namespace": "production",
        "uid": "abc-123"
    },
    "reason": "CrashLoopBackOff",
    "message": "Back-off restarting failed container",
    "type": "Warning",
    "firstTimestamp": "2024-01-01T10:00:00Z",
    "lastTimestamp": "2024-01-01T10:05:00Z",
    "count": 5
}

SAMPLE_K8S_EVENT_DATA_INFO = {
    "metadata": {"name": "deployment-update-1", "namespace": "staging"},
    "involvedObject": {
        "kind": "Deployment",
        "name": "frontend-app",
        "namespace": "staging",
    },
    "reason": "ScalingReplicaSet",
    "message": "Scaled up replica set frontend-app-5fgh7 to 3",
    "type": "Normal",
}

BAD_EVENT_DATA = {"some_other_key": "value"} # Missing essential fields

@pytest.fixture
def analyzer():
    """Provides an instance of the AnalyzerAgent for tests."""
    return AnalyzerAgent()

def test_analyzer_process_valid_event(analyzer: AnalyzerAgent):
    """Tests processing a typical valid Kubernetes Warning event."""
    raw_event = RawEvent(event_data=SAMPLE_K8S_EVENT_DATA_OK)
    incident = analyzer.process_event(raw_event)

    assert isinstance(incident, Incident)
    assert incident.incident_id is not None
    assert incident.affected_resource["kind"] == "Pod"
    assert incident.affected_resource["name"] == "my-app-pod-12345"
    assert incident.affected_resource["namespace"] == "production"
    assert incident.failure_type == "CrashLoopBackOff"
    assert incident.description == "Back-off restarting failed container"
    assert incident.severity == "critical" # Based on _determine_severity logic
    assert incident.status == "open"
    assert len(incident.raw_events) == 1
    assert incident.raw_events[0] == raw_event
    assert isinstance(incident.created_at, datetime)

def test_analyzer_process_info_event(analyzer: AnalyzerAgent):
    """Tests processing a typical Kubernetes Normal event."""
    raw_event = RawEvent(event_data=SAMPLE_K8S_EVENT_DATA_INFO)
    incident = analyzer.process_event(raw_event)

    assert isinstance(incident, Incident)
    assert incident.affected_resource["kind"] == "Deployment"
    assert incident.affected_resource["name"] == "frontend-app"
    assert incident.failure_type == "ScalingReplicaSet"
    assert incident.severity == "low" # Based on _determine_severity logic

def test_analyzer_process_invalid_event_raises_valueerror(analyzer: AnalyzerAgent):
    """Tests that processing an event missing key fields raises ValueError."""
    raw_event = RawEvent(event_data=BAD_EVENT_DATA)

    with pytest.raises(ValueError, match="Could not parse essential information"):
        analyzer.process_event(raw_event)

def test_determine_severity(analyzer: AnalyzerAgent):
    """Tests the internal _determine_severity logic."""
    assert analyzer._determine_severity("CrashLoopBackOff") == "critical"
    assert analyzer._determine_severity("FailedCreate") == "high"
    assert analyzer._determine_severity("SomeError") == "high"
    assert analyzer._determine_severity("Unhealthy") == "medium"
    assert analyzer._determine_severity("NodePressure") == "medium"
    assert analyzer._determine_severity("SuccessfulCreate") == "low"
    assert analyzer._determine_severity("UnknownReason") == "low"