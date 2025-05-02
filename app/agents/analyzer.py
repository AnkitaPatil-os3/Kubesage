from app.models import RawEvent, Incident
from typing import Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AnalyzerAgent:
    """
    Analyzes raw events and transforms them into structured Incidents.
    """

    def process_event(self, raw_event: RawEvent) -> Incident:
        """
        Processes a single RawEvent and attempts to create an Incident.

        Args:
            raw_event: The raw event data received.

        Returns:
            An Incident object representing the structured information.
            Raises ValueError if essential information is missing.
        """
        logger.info(f"Processing raw event received at: {raw_event.received_at}")

        event_data = raw_event.event_data

        # --- Basic Enrichment Logic ---
        # This is a placeholder. Real-world implementation would involve
        # more sophisticated parsing based on the event source (e.g., K8s API).
        try:
            # Attempt to extract common Kubernetes event fields
            affected_resource = {
                "kind": event_data.get("involvedObject", {}).get("kind", "Unknown"),
                "name": event_data.get("involvedObject", {}).get("name", "Unknown"),
                "namespace": event_data.get("involvedObject", {}).get("namespace", "default"),
            }
            failure_type = event_data.get("reason", "UnknownFailure")
            description = event_data.get("message", "No description provided.")
            severity = self._determine_severity(failure_type) # Basic severity mapping

            incident = Incident(
                affected_resource=affected_resource,
                failure_type=failure_type,
                description=description,
                severity=severity,
                raw_events=[raw_event], # Include the source event
                created_at=datetime.utcnow(),
                status="open"
            )
            logger.info(f"Created Incident {incident.incident_id} for resource {affected_resource['kind']}/{affected_resource['name']}")
            return incident

        except Exception as e:
            logger.error(f"Failed to process raw event: {e}", exc_info=True)
            # Depending on requirements, might return None or raise a specific exception
            raise ValueError(f"Could not parse essential information from raw event: {event_data}") from e

    def _determine_severity(self, failure_type: str) -> str:
        """
        Maps failure types to severity levels (basic example).
        """
        failure_type_lower = failure_type.lower()
        if "crashloop" in failure_type_lower:
            return "critical"
        elif "failed" in failure_type_lower or "error" in failure_type_lower:
            return "high"
        elif "unhealthy" in failure_type_lower or "pressure" in failure_type_lower:
            return "medium"
        else:
            return "low"

# Example Usage (for testing purposes)
if __name__ == '__main__':
    # Configure basic logging for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Example Kubernetes Event (simplified)
    sample_k8s_event_data = {
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

    raw = RawEvent(event_data=sample_k8s_event_data)
    analyzer = AnalyzerAgent()

    try:
        incident_obj = analyzer.process_event(raw)
        print("\n--- Generated Incident ---")
        print(incident_obj.model_dump_json(indent=2))
    except ValueError as e:
        print(f"\nError creating incident: {e}")

    # Example of an event that might cause an error (missing key fields)
    bad_event_data = {"some_other_key": "value"}
    bad_raw = RawEvent(event_data=bad_event_data)
    try:
        incident_obj = analyzer.process_event(bad_raw)
        print("\n--- Generated Incident (Bad Event) ---")
        print(incident_obj.model_dump_json(indent=2))
    except ValueError as e:
        print(f"\nError creating incident from bad event: {e}")
