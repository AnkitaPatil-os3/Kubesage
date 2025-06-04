from typing import Dict, Any, List
from app.schemas import KubernetesEvent, FlexibleIncident
from app.models import IncidentModel
from app.database import engine
from app.logger import logger
from sqlmodel import Session
from datetime import datetime
# Replace the old import
# from app.llm_client import query_llm
from app.llm_client import analyze_kubernetes_incident_sync
import uuid

def parse_flexible_incident_data(request_data: Dict[str, Any]) -> List[FlexibleIncident]:
    """
    Parse incoming incident data from various formats
    """
    incidents = []
    
    try:
        # Handle Kubernetes events format
        if "items" in request_data and isinstance(request_data["items"], list):
            for item in request_data["items"]:
                incident = FlexibleIncident(raw_data=item)
                incidents.append(incident)
        
        # Handle single incident
        elif "metadata" in request_data and "type" in request_data:
            incident = FlexibleIncident(raw_data=request_data)
            incidents.append(incident)
        
        # Handle array of incidents
        elif isinstance(request_data, list):
            for item in request_data:
                incident = FlexibleIncident(raw_data=item)
                incidents.append(incident)
        
        # Handle custom format with 'events' key
        elif "events" in request_data:
            for event in request_data["events"]:
                incident = FlexibleIncident(raw_data=event)
                incidents.append(incident)
        
        # Handle single incident in custom format
        else:
            incident = FlexibleIncident(raw_data=request_data)
            incidents.append(incident)
            
        logger.info(f"Parsed {len(incidents)} incidents from request data")
        return incidents
        
    except Exception as e:
        logger.error(f"Error parsing incident data: {str(e)}")
        return []

def convert_to_kubernetes_event(raw_data: Dict[str, Any]) -> KubernetesEvent:
    """
    Convert raw incident data to KubernetesEvent format
    """
    try:
        # Extract metadata
        metadata = raw_data.get("metadata", {})
        
        # Extract event info
        event_type = raw_data.get("type", "Normal")
        reason = raw_data.get("reason", "Unknown")
        message = raw_data.get("message", "No message provided")
        count = raw_data.get("count", 1)
        
        # Extract timestamps
        first_timestamp = None
        last_timestamp = None
        creation_timestamp = None
        
        if "firstTimestamp" in raw_data:
            first_timestamp = datetime.fromisoformat(raw_data["firstTimestamp"].replace("Z", "+00:00"))
        if "lastTimestamp" in raw_data:
            last_timestamp = datetime.fromisoformat(raw_data["lastTimestamp"].replace("Z", "+00:00"))
        if "creationTimestamp" in metadata:
            creation_timestamp = datetime.fromisoformat(metadata["creationTimestamp"].replace("Z", "+00:00"))
        
        # Extract source info
        source = raw_data.get("source", {})
        
        # Extract involved object info
        involved_object = raw_data.get("involvedObject", {})
        
        return KubernetesEvent(
            metadata_name=metadata.get("name", f"incident-{uuid.uuid4()}"),
            metadata_namespace=metadata.get("namespace"),
            metadata_creation_timestamp=creation_timestamp,
            type=event_type,
            reason=reason,
            message=message,
            count=count,
            first_timestamp=first_timestamp,
            last_timestamp=last_timestamp,
            source_component=source.get("component"),
            source_host=source.get("host"),
            involved_object_kind=involved_object.get("kind"),
            involved_object_name=involved_object.get("name"),
            involved_object_field_path=involved_object.get("fieldPath"),
            involved_object_labels=involved_object.get("labels", {}),
            involved_object_annotations=involved_object.get("annotations", {}),
            involved_object_owner_references=involved_object.get("ownerReferences", {}),
            reporting_component=raw_data.get("reportingComponent"),
            reporting_instance=raw_data.get("reportingInstance")
        )
        
    except Exception as e:
        logger.error(f"Error converting raw data to KubernetesEvent: {str(e)}")
        # Return a minimal event with error info
        return KubernetesEvent(
            metadata_name=f"error-incident-{uuid.uuid4()}",
            type="Warning",
            reason="ConversionError",
            message=f"Failed to parse incident data: {str(e)}"
        )


async def process_flexible_incidents(incidents: List[FlexibleIncident], background_tasks):
    """ 
    Process a list of flexible incidents
    """
    for incident in incidents:
        try:
            # Convert to standard format
            k8s_event = convert_to_kubernetes_event(incident.raw_data)
            
            # Save to database
            incident_id = await save_incident_to_db(k8s_event)
            
            # Send email notification IMMEDIATELY before LLM analysis
            from app.email_client import send_incident_email
            try:
                await send_incident_email(k8s_event, incident_id)
                logger.info(f"Email sent successfully for incident: {incident_id}")
            except Exception as email_error:
                logger.error(f"Failed to send email for incident {incident_id}: {str(email_error)}")
                # Continue processing even if email fails
            
            # Prepare incident data for LLM (only required and important info)
            incident_data = {
                "id": incident_id,
                "type": k8s_event.type,
                "reason": k8s_event.reason,
                "message": k8s_event.message,
                "metadata_namespace": k8s_event.metadata_namespace,
                "metadata_creation_timestamp": k8s_event.metadata_creation_timestamp.isoformat() if k8s_event.metadata_creation_timestamp else None,
                "involved_object_kind": k8s_event.involved_object_kind,
                "involved_object_name": k8s_event.involved_object_name,
                "source_component": k8s_event.source_component,
                "source_host": k8s_event.source_host,
                "reporting_component": k8s_event.reporting_component,
                "count": k8s_event.count,
                "first_timestamp": k8s_event.first_timestamp.isoformat() if k8s_event.first_timestamp else None,
                "last_timestamp": k8s_event.last_timestamp.isoformat() if k8s_event.last_timestamp else None,
                # Clean labels and annotations to avoid JSON issues
                "involved_object_labels": _clean_dict_for_llm(k8s_event.involved_object_labels),
                "involved_object_annotations": _clean_dict_for_llm(k8s_event.involved_object_annotations)
            }
            
            logger.info(f"Prepared incident data for LLM analysis: {incident_data['id']}")

            # Analyze incident using LLM to get structured solution (AFTER email is sent)
            try:
                # Use the synchronous function directly
                solution = analyze_kubernetes_incident_sync(incident_data)

                
                logger.info(f"Generated structured solution for incident {incident_id}")
                logger.info(f"Solution summary: {solution.summary}")
                logger.info(f"Number of steps: {len(solution.steps)}")
                logger.info(f"Confidence score: {solution.confidence_score}")
                logger.info(f"Estimated resolution time: {solution.estimated_time_to_resolve_mins} minutes")
                
                # ---- NEW LOGIC: Enforcer ----
                try:
                    from app.enforcer_client import enforce_remediation_plan
                    enforcer_instructions = enforce_remediation_plan(solution)
                    logger.info(f"Enforcer processed solution for incident {incident_id}")
                    
                    # ---- NEW LOGIC: Executor ----
                    from app.executor_client import execute_remediation_steps
                    execution_result = execute_remediation_steps(enforcer_instructions)
                    logger.info(f"Executor completed steps for incident {incident_id}: {execution_result}")
                
                except Exception as enforcement_error:
                    logger.error(f"Enforcer/Executor failed for incident {incident_id}: {str(enforcement_error)}")
                            
            except Exception as llm_error:
                logger.error(f"LLM analysis failed for incident {incident_id}: {str(llm_error)}")
                # Continue processing even if LLM fails
            
        except Exception as e:
            logger.error(f"Error processing incident: {str(e)}")


def _clean_dict_for_llm(data_dict):
    """Clean dictionary data to avoid LLM parsing issues"""
    if not data_dict or not isinstance(data_dict, dict):
        return {}
    
    cleaned = {}
    for key, value in data_dict.items():
        # Convert all values to strings and limit length
        if isinstance(value, str) and len(value) > 200:
            cleaned[key] = value[:200] + "..."
        else:
            cleaned[key] = str(value) if value is not None else ""
    
    return cleaned


async def save_incident_to_db(k8s_event: KubernetesEvent) -> str:
    """
    Save incident to database
    """
    try:
        with Session(engine) as session:
            incident_id = str(uuid.uuid4())
            
            incident_model = IncidentModel(
                id=incident_id,
                metadata_name=k8s_event.metadata_name,
                metadata_namespace=k8s_event.metadata_namespace,
                metadata_creation_timestamp=k8s_event.metadata_creation_timestamp,
                type=k8s_event.type,
                reason=k8s_event.reason,
                message=k8s_event.message,
                count=k8s_event.count,
                first_timestamp=k8s_event.first_timestamp,
                last_timestamp=k8s_event.last_timestamp,
                source_component=k8s_event.source_component,
                source_host=k8s_event.source_host,
                involved_object_kind=k8s_event.involved_object_kind,
                involved_object_name=k8s_event.involved_object_name,
                involved_object_field_path=k8s_event.involved_object_field_path,
                involved_object_labels=k8s_event.involved_object_labels,
                involved_object_annotations=k8s_event.involved_object_annotations,
                involved_object_owner_references=k8s_event.involved_object_owner_references,
                reporting_component=k8s_event.reporting_component,
                reporting_instance=k8s_event.reporting_instance
            )
            
            session.add(incident_model)
            session.commit()
            session.refresh(incident_model)
            
            logger.info(f"Saved incident to database with ID: {incident_id}")
            return incident_id
            
    except Exception as e:
        logger.error(f"Error saving incident to database: {str(e)}")
        raise e

async def save_solution_to_db(solution, incident_id: str):
    """
    Save LLM solution to database (optional)
    """
    try:
        # You would need to create a SolutionModel in your models.py
        # This is just an example of how you might store it
        solution_data = {
            "incident_id": incident_id,
            "solution_id": solution.solution_id,
            "summary": solution.summary,
            "analysis": solution.analysis,
            "steps": solution.steps,
            "confidence_score": solution.confidence_score,
            "estimated_time_to_resolve_mins": solution.estimated_time_to_resolve_mins,
            "severity_level": solution.severity_level,
            "recommendations": solution.recommendations,
            "created_at": datetime.utcnow()
        }
        
        logger.info(f"Solution saved for incident: {incident_id}")
        return solution_data
        
    except Exception as e:
        logger.error(f"Error saving solution to database: {str(e)}")
        raise e



