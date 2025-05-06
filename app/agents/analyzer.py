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
        logger.debug(f"Raw event data received for analysis: {event_data}")

        # --- Enrichment Logic ---
        try:
            kind = "Unknown"
            name = "Unknown"
            namespace = "default"
            failure_type = "UnknownFailure"
            description = "No description provided."

            # Try extracting from direct fields first (based on feedback example)
            if "kind" in event_data and "name" in event_data:
                kind = event_data.get("kind", "Unknown")
                raw_name = event_data.get("name", "Unknown")
                if "/" in raw_name:
                    namespace, name = raw_name.split("/", 1)
                else:
                    name = raw_name
                    # Keep default namespace if not specified in name
                logger.info(f"Parsed resource from direct fields: Kind={kind}, Name={name}, Namespace={namespace}")
                # Try to get failure details from other fields if available
                failure_type = event_data.get("reason", failure_type) # Use 'reason' if present
                if "error" in event_data and isinstance(event_data["error"], list) and len(event_data["error"]) > 0:
                     # Try to get a more specific description from the 'error' field if 'message' isn't there
                     error_text = event_data["error"][0].get("Text", "") if isinstance(event_data["error"][0], dict) else str(event_data["error"][0])
                     description = event_data.get("message", error_text or description)
                else:
                     description = event_data.get("message", description)

            # Fallback to involvedObject structure (original logic)
            elif "involvedObject" in event_data:
                involved_obj = event_data.get("involvedObject", {})
                kind = involved_obj.get("kind", kind)
                name = involved_obj.get("name", name)
                namespace = involved_obj.get("namespace", namespace)
                failure_type = event_data.get("reason", failure_type)
                description = event_data.get("message", description)
                logger.info(f"Parsed resource from involvedObject: Kind={kind}, Name={name}, Namespace={namespace}")
            else:
                 logger.warning("Could not determine affected resource from event_data structure.")
                 # Keep defaults: Unknown/default

            affected_resource = {
                "kind": kind,
                "name": name,
                "namespace": namespace,
            }
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

# End of AnalyzerAgent class
