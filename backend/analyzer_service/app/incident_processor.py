from typing import Dict, Any, List
from app.schemas import KubernetesEvent, FlexibleIncident
from app.models import IncidentModel, ExecutionAttemptModel, SolutionModel
from app.database import engine
from app.logger import logger
from sqlmodel import Session, select
from datetime import datetime

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
    Enhanced to handle Elasticsearch format with _source wrapper
    """
    try:
        # Handle Elasticsearch format with _source wrapper
        if "_source" in raw_data:
            source_data = raw_data["_source"]
            es_id = raw_data.get("_id", str(uuid.uuid4()))
        else:
            source_data = raw_data
            es_id = str(uuid.uuid4())
        
        # Extract metadata
        metadata = source_data.get("metadata", {})
        
        # Extract event info with proper fallbacks
        event_type = source_data.get("type", "Normal")
        reason = source_data.get("reason", "Unknown")
        message = source_data.get("message", "No message provided")
        count = source_data.get("count", 1)
        
        # Extract timestamps with better handling
        first_timestamp = None
        last_timestamp = None
        creation_timestamp = None
        
        # Handle different timestamp formats
        if source_data.get("firstTimestamp"):
            try:
                first_timestamp = datetime.fromisoformat(source_data["firstTimestamp"].replace("Z", "+00:00"))
            except:
                pass
                
        if source_data.get("lastTimestamp"):
            try:
                last_timestamp = datetime.fromisoformat(source_data["lastTimestamp"].replace("Z", "+00:00"))
            except:
                pass
                
        if source_data.get("eventTime"):
            try:
                # Use eventTime as fallback for timestamps
                event_time = datetime.fromisoformat(source_data["eventTime"].replace("Z", "+00:00"))
                if not first_timestamp:
                    first_timestamp = event_time
                if not last_timestamp:
                    last_timestamp = event_time
            except:
                pass
        
        if metadata.get("creationTimestamp"):
            try:
                creation_timestamp = datetime.fromisoformat(metadata["creationTimestamp"].replace("Z", "+00:00"))
            except:
                pass
        
        # Extract source info
        source = source_data.get("source", {})
        
        # Extract involved object info with proper handling
        involved_object = source_data.get("involvedObject", {})
        
        return KubernetesEvent(
            metadata_name=metadata.get("name", f"incident-{es_id}"),
            metadata_namespace=metadata.get("namespace") or involved_object.get("namespace"),
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
            involved_object_owner_references=involved_object.get("ownerReferences", []),
            reporting_component=source_data.get("reportingComponent"),
            reporting_instance=source_data.get("reportingInstance")
        )
        
    except Exception as e:
        logger.error(f"Error converting raw data to KubernetesEvent: {str(e)}")
        logger.error(f"Raw data keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Not a dict'}")
        
        # Return a minimal event with error info but use available data
        fallback_name = "error-incident"
        fallback_message = "Failed to parse incident data"
        
        if isinstance(raw_data, dict):
            if "_source" in raw_data:
                source_data = raw_data["_source"]
                fallback_name = source_data.get("metadata", {}).get("name", fallback_name)
                fallback_message = source_data.get("message", fallback_message)
            else:
                fallback_name = raw_data.get("metadata", {}).get("name", fallback_name)
                fallback_message = raw_data.get("message", fallback_message)
        
        return KubernetesEvent(
            metadata_name=fallback_name,
            type="Warning",
            reason="ConversionError",
            message=f"{fallback_message}: {str(e)}"
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
            
            # Process incident with LLM → Enforcer → Executor chain
            await _process_incident_with_llm_chain(k8s_event, incident_id)
            
        except Exception as e:
            logger.error(f"Error processing incident: {str(e)}")

async def _process_incident_with_llm_chain(k8s_event: KubernetesEvent, incident_id: str):
    """Process incident through LLM → Enforcer → Executor chain"""
    try:
        # Prepare incident data for LLM
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
            "involved_object_labels": _clean_dict_for_llm(k8s_event.involved_object_labels),
            "involved_object_annotations": _clean_dict_for_llm(k8s_event.involved_object_annotations)
        }
        
        logger.info(f"Starting LLM → Enforcer → Executor chain for incident: {incident_id}")

        # Step 1: LLM Analysis
        try:
            solution = analyze_kubernetes_incident_sync(incident_data)
            logger.info(f"✅ LLM analysis completed for incident {incident_id}")
            
            # Step 2: Enforcer Processing
            try:
                from app.enforcer_client import enforce_remediation_plan
                enforcer_result = enforce_remediation_plan(solution, incident_id)
                
                if enforcer_result.get("status") == "max_attempts_reached":
                    logger.warning(f"⚠️ Maximum attempts reached for incident {incident_id}")
                    return
                elif enforcer_result.get("status") == "error":
                    logger.error(f"❌ Enforcer failed for incident {incident_id}")
                    return
                
                logger.info(f"✅ Enforcer processing completed for incident {incident_id}")
                
                # Step 3: Executor Processing
                try:
                    from app.executor_client import execute_remediation_steps
                    execution_result = execute_remediation_steps(enforcer_result)
                    
                    if execution_result.get("overall_success"):
                        logger.info(f"✅ Execution completed successfully for incident {incident_id}")
                    else:
                        logger.warning(f"⚠️ Execution failed for incident {incident_id}, attempt {execution_result.get('attempt_number')}")
                    
                except Exception as executor_error:
                    logger.error(f"❌ Executor failed for incident {incident_id}: {str(executor_error)}")
                    
            except Exception as enforcer_error:
                logger.error(f"❌ Enforcer failed for incident {incident_id}: {str(enforcer_error)}")
                
        except Exception as llm_error:
            logger.error(f"❌ LLM analysis failed for incident {incident_id}: {str(llm_error)}")
            
    except Exception as e:
        logger.error(f"❌ Error in LLM chain processing for incident {incident_id}: {str(e)}")

async def retry_incident_analysis(incident_id: str):
    """Retry incident analysis after execution failure"""
    try:
        logger.info(f"🔄 Retrying analysis for incident {incident_id}")
        
        # Get original incident from database
        with Session(engine) as session:
            incident = session.exec(
                select(IncidentModel).where(IncidentModel.id == incident_id)
            ).first()
            
            if not incident:
                logger.error(f"Incident {incident_id} not found for retry")
                return
            
            # Get previous execution attempts for context
            attempts = session.exec(
                select(ExecutionAttemptModel).where(
                    ExecutionAttemptModel.incident_id == incident_id
                )
            ).all()
            
            # Prepare enhanced incident data with failure context
            incident_data = {
                "id": incident_id,
                "type": incident.type,
                "reason": incident.reason,
                "message": incident.message,
                "metadata_namespace": incident.metadata_namespace,
                "metadata_creation_timestamp": incident.metadata_creation_timestamp.isoformat() if incident.metadata_creation_timestamp else None,
                "involved_object_kind": incident.involved_object_kind,
                "involved_object_name": incident.involved_object_name,
                "source_component": incident.source_component,
                "source_host": incident.source_host,
                "reporting_component": incident.reporting_component,
                "count": incident.count,
                "first_timestamp": incident.first_timestamp.isoformat() if incident.first_timestamp else None,
                "last_timestamp": incident.last_timestamp.isoformat() if incident.last_timestamp else None,
                "involved_object_labels": incident.involved_object_labels or {},
                "involved_object_annotations": incident.involved_object_annotations or {},
                # Add failure context
                "previous_attempts": len(attempts),
                "last_failure_reason": attempts[-1].error_message if attempts else None
            }
            
            # Convert incident model back to KubernetesEvent for processing
            k8s_event = KubernetesEvent(
                metadata_name=incident.metadata_name,
                metadata_namespace=incident.metadata_namespace,
                metadata_creation_timestamp=incident.metadata_creation_timestamp,
                type=incident.type,
                reason=incident.reason,
                message=incident.message,
                count=incident.count,
                first_timestamp=incident.first_timestamp,
                last_timestamp=incident.last_timestamp,
                source_component=incident.source_component,
                source_host=incident.source_host,
                involved_object_kind=incident.involved_object_kind,
                involved_object_name=incident.involved_object_name,
                involved_object_field_path=incident.involved_object_field_path,
                involved_object_labels=incident.involved_object_labels or {},
                involved_object_annotations=incident.involved_object_annotations or {},
                involved_object_owner_references=incident.involved_object_owner_references or {},
                reporting_component=incident.reporting_component,
                reporting_instance=incident.reporting_instance
            )
            
            # Process through LLM chain again
            await _process_incident_with_llm_chain(k8s_event, incident_id)
            
    except Exception as e:
        logger.error(f"Error in retry analysis for incident {incident_id}: {str(e)}")

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



