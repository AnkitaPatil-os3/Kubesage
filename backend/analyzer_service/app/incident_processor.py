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
        print(f"🔍 PARSING REQUEST DATA: {type(request_data)}")
        print(f"🔍 REQUEST DATA KEYS: {list(request_data.keys()) if isinstance(request_data, dict) else 'Not a dict'}")
        
        # Handle Kubernetes events format
        if "items" in request_data and isinstance(request_data["items"], list):
            print("📋 Processing items array format")
            for item in request_data["items"]:
                incident = FlexibleIncident(raw_data=item)
                incidents.append(incident)
        
        # Handle single incident
        elif "metadata" in request_data and "type" in request_data:
            print("📋 Processing direct Kubernetes event format")
            incident = FlexibleIncident(raw_data=request_data)
            incidents.append(incident)
        
        # Handle array of incidents
        elif isinstance(request_data, list):
            print("📋 Processing array format")
            for item in request_data:
                incident = FlexibleIncident(raw_data=item)
                incidents.append(incident)
        
        # Handle custom format with 'events' key
        elif "events" in request_data:
            print("📋 Processing events array format")
            for event in request_data["events"]:
                incident = FlexibleIncident(raw_data=event)
                incidents.append(incident)
        
        # Handle Elasticsearch format with _source
        elif "_source" in request_data:
            print("📋 Processing Elasticsearch format with _source")
            incident = FlexibleIncident(raw_data=request_data)
            incidents.append(incident)
        
        # Handle single incident in custom format
        else:
            print("📋 Processing generic format")
            incident = FlexibleIncident(raw_data=request_data)
            incidents.append(incident)
            
        print(f"✅ PARSED {len(incidents)} INCIDENTS")
        return incidents
        
    except Exception as e:
        print(f"❌ ERROR PARSING INCIDENT DATA: {str(e)}")
        logger.error(f"Error parsing incident data: {str(e)}")
        return []

def convert_to_kubernetes_event(raw_data: Dict[str, Any]) -> KubernetesEvent:
    """
    Convert raw incident data to KubernetesEvent format - FIXED VERSION
    """
    print("\n" + "="*80)
    print("🔄 STARTING CONVERSION TO KUBERNETES EVENT")
    print("="*80)
    
    try:
        # Handle Elasticsearch format with _source wrapper
        if "_source" in raw_data:
            source_data = raw_data["_source"]
            es_id = raw_data.get("_id", str(uuid.uuid4()))
            print(f"📦 ELASTICSEARCH FORMAT DETECTED - ID: {es_id}")
        else:
            source_data = raw_data
            es_id = str(uuid.uuid4())
            print(f"📦 DIRECT FORMAT DETECTED - ID: {es_id}")
        
        print(f"📋 SOURCE DATA KEYS: {list(source_data.keys())}")
        
        # FIXED: Check if data is already in flattened format (direct from API)
        if "metadata_namespace" in source_data or "involved_object_kind" in source_data:
            print("🔧 DETECTED FLATTENED FORMAT - USING DIRECT MAPPING")
            
            # Direct mapping for flattened format
            metadata_name = source_data.get("metadata_name") or f"incident-{es_id}"
            metadata_namespace = source_data.get("metadata_namespace")
            metadata_creation_timestamp = None
            
            # Parse creation timestamp if provided
            if source_data.get("metadata_creation_timestamp"):
                try:
                    metadata_creation_timestamp = datetime.fromisoformat(
                        source_data["metadata_creation_timestamp"].replace("Z", "+00:00")
                    )
                except Exception as ts_error:
                    print(f"⚠️  TIMESTAMP PARSE ERROR: {ts_error}")
            
            # Parse other timestamps
            first_timestamp = None
            last_timestamp = None
            
            if source_data.get("first_timestamp"):
                try:
                    first_timestamp = datetime.fromisoformat(
                        source_data["first_timestamp"].replace("Z", "+00:00")
                    )
                except:
                    pass
                    
            if source_data.get("last_timestamp"):
                try:
                    last_timestamp = datetime.fromisoformat(
                        source_data["last_timestamp"].replace("Z", "+00:00")
                    )
                except:
                    pass
            
            # Create KubernetesEvent with direct mapping
            k8s_event = KubernetesEvent(
                metadata_name=metadata_name,
                metadata_namespace=metadata_namespace,
                metadata_creation_timestamp=metadata_creation_timestamp,
                type=source_data.get("type", "Normal"),
                reason=source_data.get("reason", "Unknown"),
                message=source_data.get("message", "No message provided"),
                count=source_data.get("count", 1),
                first_timestamp=first_timestamp,
                last_timestamp=last_timestamp,
                source_component=source_data.get("source_component"),
                source_host=source_data.get("source_host"),
                involved_object_kind=source_data.get("involved_object_kind"),
                involved_object_name=source_data.get("involved_object_name"),
                involved_object_field_path=source_data.get("involved_object_field_path"),
                involved_object_labels=source_data.get("involved_object_labels", {}),
                involved_object_annotations=source_data.get("involved_object_annotations", {}),
                involved_object_owner_references=source_data.get("involved_object_owner_references", {}),
                reporting_component=source_data.get("reporting_component"),
                reporting_instance=source_data.get("reporting_instance")
            )
            
        else:
            print("🔧 DETECTED NESTED FORMAT - USING NESTED MAPPING")
            
            # Original nested format handling (for Elasticsearch _source format)
            metadata = source_data.get("metadata", {})
            print(f"🏷️  METADATA: {metadata}")
            
            # Extract event info with proper fallbacks
            event_type = source_data.get("type", "Normal")
            reason = source_data.get("reason", "Unknown")
            message = source_data.get("message", "No message provided")
            count = source_data.get("count", 1)
            
            print(f"📊 EVENT INFO:")
            print(f"   Type: {event_type}")
            print(f"   Reason: {reason}")
            print(f"   Message: {message[:100]}...")
            print(f"   Count: {count}")
            
            # Extract timestamps with better handling
            first_timestamp = None
            last_timestamp = None
            creation_timestamp = None
            
            # Handle different timestamp formats
            timestamp_fields = ["firstTimestamp", "lastTimestamp", "eventTime"]
            for field in timestamp_fields:
                if source_data.get(field):
                    try:
                        ts_value = source_data[field]
                        if ts_value and ts_value != "null":
                            parsed_ts = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
                            if field == "firstTimestamp":
                                first_timestamp = parsed_ts
                            elif field == "lastTimestamp":
                                last_timestamp = parsed_ts
                            elif field == "eventTime":
                                if not first_timestamp:
                                    first_timestamp = parsed_ts
                                if not last_timestamp:
                                    last_timestamp = parsed_ts
                            print(f"⏰ PARSED {field}: {parsed_ts}")
                    except Exception as ts_error:
                        print(f"⚠️  TIMESTAMP PARSE ERROR {field}: {ts_error}")
                        
            if metadata.get("creationTimestamp"):
                try:
                    creation_timestamp = datetime.fromisoformat(metadata["creationTimestamp"].replace("Z", "+00:00"))
                    print(f"⏰ CREATION TIMESTAMP: {creation_timestamp}")
                except Exception as ts_error:
                    print(f"⚠️  CREATION TIMESTAMP ERROR: {ts_error}")
            
            # Extract source info
            source = source_data.get("source", {})
            print(f"🔧 SOURCE: {source}")
            
            # Extract involved object info
            involved_object = source_data.get("involvedObject", {})
            print(f"🎯 INVOLVED OBJECT: {involved_object}")
            
            # Handle owner references by converting to simple dict
            owner_references_raw = involved_object.get("ownerReferences", [])
            print(f"👑 RAW OWNER REFERENCES: {owner_references_raw}")
            
            # Convert to simple dict format to avoid validation issues
            owner_references_dict = {}
            if owner_references_raw:
                if isinstance(owner_references_raw, list) and len(owner_references_raw) > 0:
                    # Take first owner reference and flatten it
                    first_owner = owner_references_raw[0]
                    if isinstance(first_owner, dict):
                        owner_references_dict = {
                            "apiVersion": str(first_owner.get("apiVersion", "")),
                            "kind": str(first_owner.get("kind", "")),
                            "name": str(first_owner.get("name", "")),
                            "uid": str(first_owner.get("uid", "")),
                            "controller": bool(first_owner.get("controller", False)),
                            "blockOwnerDeletion": bool(first_owner.get("blockOwnerDeletion", False))
                        }
                elif isinstance(owner_references_raw, dict):
                    owner_references_dict = owner_references_raw
            
            print(f"👑 PROCESSED OWNER REFERENCES: {owner_references_dict}")
            
            # Extract all the fields we need
            metadata_name = metadata.get("name", f"incident-{es_id}")
            metadata_namespace = metadata.get("namespace") or involved_object.get("namespace")
            source_component = source.get("component")
            source_host = source.get("host")
            involved_object_kind = involved_object.get("kind")
            involved_object_name = involved_object.get("name")
            involved_object_field_path = involved_object.get("fieldPath")
            involved_object_labels = involved_object.get("labels", {})
            involved_object_annotations = involved_object.get("annotations", {})
            reporting_component = source_data.get("reportingComponent")
            reporting_instance = source_data.get("reportingInstance")
            
            # Create the KubernetesEvent object
            k8s_event = KubernetesEvent(
                metadata_name=metadata_name,
                metadata_namespace=metadata_namespace,
                metadata_creation_timestamp=creation_timestamp,
                type=event_type,
                reason=reason,
                message=message,
                count=count,
                first_timestamp=first_timestamp,
                last_timestamp=last_timestamp,
                source_component=source_component,
                source_host=source_host,
                involved_object_kind=involved_object_kind,
                involved_object_name=involved_object_name,
                involved_object_field_path=involved_object_field_path,
                involved_object_labels=involved_object_labels or {},
                involved_object_annotations=involved_object_annotations or {},
                involved_object_owner_references=owner_references_dict,
                reporting_component=reporting_component,
                reporting_instance=reporting_instance
            )
        
        print(f"✅ KUBERNETES EVENT CREATED SUCCESSFULLY!")
        print(f"   Event Name: {k8s_event.metadata_name}")
        print(f"   Event Type: {k8s_event.type}")
        print(f"   Event Reason: {k8s_event.reason}")
        print(f"   Namespace: {k8s_event.metadata_namespace}")
        print(f"   Object Kind: {k8s_event.involved_object_kind}")
        print(f"   Object Name: {k8s_event.involved_object_name}")
        print("="*80 + "\n")
        
        return k8s_event
        
    except Exception as e:
        print(f"❌ CONVERSION ERROR: {str(e)}")
        print(f"❌ ERROR TYPE: {type(e)}")
        logger.error(f"Error converting raw data to KubernetesEvent: {str(e)}")
        
        # Create a minimal fallback event that will definitely work
        print(f"🔄 CREATING FALLBACK EVENT...")
        
        try:
            # Extract basic info for fallback
            if "_source" in raw_data:
                source_data = raw_data["_source"]
                es_id = raw_data.get("_id", str(uuid.uuid4()))
            else:
                source_data = raw_data
                es_id = str(uuid.uuid4())
            
            fallback_name = source_data.get("metadata", {}).get("name", f"fallback-{es_id}")
            fallback_message = source_data.get("message", f"Original conversion failed: {str(e)}")
            fallback_namespace = source_data.get("metadata", {}).get("namespace") or source_data.get("metadata_namespace")
            fallback_type = source_data.get("type", "Warning")
            fallback_reason = "ConversionError"
            
            fallback_event = KubernetesEvent(
                metadata_name=fallback_name,
                metadata_namespace=fallback_namespace,
                type=fallback_type,
                reason=fallback_reason,
                message=fallback_message,
                involved_object_kind=source_data.get("involvedObject", {}).get("kind") or source_data.get("involved_object_kind"),
                involved_object_name=source_data.get("involvedObject", {}).get("name") or source_data.get("involved_object_name"),
                reporting_component=source_data.get("reportingComponent") or source_data.get("reporting_component")
            )
            
            print(f"✅ FALLBACK EVENT CREATED: {fallback_event.metadata_name}")
            return fallback_event
            
        except Exception as fallback_error:
            print(f"❌ EVEN FALLBACK FAILED: {fallback_error}")
            # Last resort - absolute minimal event
            return KubernetesEvent(
                metadata_name=f"critical-error-{uuid.uuid4()}",
                type="Warning",
                reason="CriticalConversionError",
                message=f"Complete conversion failure: {str(e)}"
            )

async def process_flexible_incidents(incidents: List[FlexibleIncident], background_tasks):
    """ 
    Process a list of flexible incidents
    """
    print(f"\n🚀 PROCESSING {len(incidents)} FLEXIBLE INCIDENTS")
    
    for i, incident in enumerate(incidents, 1):
        try:
            print(f"\n📋 PROCESSING INCIDENT {i}/{len(incidents)}")
            
            # Convert to standard format
            k8s_event = convert_to_kubernetes_event(incident.raw_data)
            print(f"✅ CONVERTED TO KUBERNETES EVENT: {k8s_event.metadata_name}")
            
            # Save to database
            incident_id = await save_incident_to_db(k8s_event)
            print(f"✅ SAVED TO DATABASE WITH ID: {incident_id}")
            
            # Send email notification IMMEDIATELY before LLM analysis
            from app.email_client import send_incident_email
            try:
                await send_incident_email(k8s_event, incident_id)
                print(f"✅ EMAIL SENT FOR INCIDENT: {incident_id}")
            except Exception as email_error:
                print(f"⚠️  EMAIL FAILED FOR INCIDENT {incident_id}: {str(email_error)}")
                # Continue processing even if email fails
            
            # Process incident with LLM → Enforcer → Executor chain
            await _process_incident_with_llm_chain(k8s_event, incident_id)
            
        except Exception as e:
            print(f"❌ ERROR PROCESSING INCIDENT {i}: {str(e)}")
            logger.error(f"Error processing incident: {str(e)}")

async def _process_incident_with_llm_chain(k8s_event: KubernetesEvent, incident_id: str):
    """Process incident through LLM → Enforcer → Executor chain"""
    try:
        print(f"\n🤖 STARTING LLM CHAIN FOR INCIDENT: {incident_id}")
        
        # Get active executors first
        from app.executor_client import get_active_executors
        active_executors = get_active_executors()
        print(f"🔧 ACTIVE EXECUTORS: {active_executors}")
        
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
        
        print(f"📊 INCIDENT DATA FOR LLM: {incident_data}")
        
        logger.info(f"Starting LLM → Enforcer → Executor chain for incident: {incident_id}")

        # Step 1: LLM Analysis
        try:
            print(f"🧠 STARTING LLM ANALYSIS...")
            solution = analyze_kubernetes_incident_sync(incident_data, active_executors)
            print(f"✅ LLM ANALYSIS COMPLETED FOR INCIDENT {incident_id}")
            
            # Step 2: Enforcer Processing
            try:
                print(f"⚖️  STARTING ENFORCER PROCESSING...")
                from app.enforcer_client import enforce_remediation_plan
                enforcer_result = enforce_remediation_plan(solution, incident_id)
                
                if enforcer_result.get("status") == "max_attempts_reached":
                    print(f"⚠️  MAXIMUM ATTEMPTS REACHED FOR INCIDENT {incident_id}")
                    return
                elif enforcer_result.get("status") == "error":
                    print(f"❌ ENFORCER FAILED FOR INCIDENT {incident_id}")
                    return
                
                print(f"✅ ENFORCER PROCESSING COMPLETED FOR INCIDENT {incident_id}")
                
                # Step 3: Executor Processing
                try:
                    print(f"🔧 STARTING EXECUTOR PROCESSING...")
                    from app.executor_client import execute_remediation_steps
                    execution_result = execute_remediation_steps(enforcer_result)
                    
                    if execution_result.get("overall_success"):
                        print(f"✅ EXECUTION COMPLETED SUCCESSFULLY FOR INCIDENT {incident_id}")
                    else:
                        print(f"⚠️  EXECUTION FAILED FOR INCIDENT {incident_id}, ATTEMPT {execution_result.get('attempt_number')}")
                    
                except Exception as executor_error:
                    print(f"❌ EXECUTOR FAILED FOR INCIDENT {incident_id}: {str(executor_error)}")
                    
            except Exception as enforcer_error:
                print(f"❌ ENFORCER FAILED FOR INCIDENT {incident_id}: {str(enforcer_error)}")
                
        except Exception as llm_error:
            print(f"❌ LLM ANALYSIS FAILED FOR INCIDENT {incident_id}: {str(llm_error)}")
            
    except Exception as e:
        print(f"❌ ERROR IN LLM CHAIN PROCESSING FOR INCIDENT {incident_id}: {str(e)}")
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
            
            # Get active executors
            from app.executor_client import get_active_executors
            active_executors = get_active_executors()
            
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
    Save incident to database with enhanced error handling and detailed logging
    """
    print(f"\n💾 SAVING INCIDENT TO DATABASE")
    print("="*60)
    
    try:
        with Session(engine) as session:
            incident_id = str(uuid.uuid4())
            
            print(f"🆔 GENERATED INCIDENT ID: {incident_id}")
            print(f"📝 INCIDENT DATA TO SAVE:")
            print(f"   metadata_name: {k8s_event.metadata_name}")
            print(f"   metadata_namespace: {k8s_event.metadata_namespace}")
            print(f"   metadata_creation_timestamp: {k8s_event.metadata_creation_timestamp}")
            print(f"   type: {k8s_event.type}")
            print(f"   reason: {k8s_event.reason}")
            print(f"   message: {k8s_event.message[:100]}...")
            print(f"   count: {k8s_event.count}")
            print(f"   first_timestamp: {k8s_event.first_timestamp}")
            print(f"   last_timestamp: {k8s_event.last_timestamp}")
            print(f"   source_component: {k8s_event.source_component}")
            print(f"   source_host: {k8s_event.source_host}")
            print(f"   involved_object_kind: {k8s_event.involved_object_kind}")
            print(f"   involved_object_name: {k8s_event.involved_object_name}")
            print(f"   involved_object_field_path: {k8s_event.involved_object_field_path}")
            print(f"   involved_object_labels: {k8s_event.involved_object_labels}")
            print(f"   involved_object_annotations: {k8s_event.involved_object_annotations}")
            print(f"   involved_object_owner_references: {k8s_event.involved_object_owner_references}")
            print(f"   reporting_component: {k8s_event.reporting_component}")
            print(f"   reporting_instance: {k8s_event.reporting_instance}")
            
            print(f"\n🏗️  CREATING INCIDENT MODEL...")
            
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
            
            print(f"✅ INCIDENT MODEL CREATED SUCCESSFULLY")
            print(f"💾 ADDING TO SESSION...")
            
            session.add(incident_model)
            
            print(f"💾 COMMITTING TO DATABASE...")
            session.commit()
            
            print(f"🔄 REFRESHING MODEL...")
            session.refresh(incident_model)
            
            print(f"✅ SUCCESSFULLY SAVED INCIDENT TO DATABASE!")
            print(f"🆔 FINAL INCIDENT ID: {incident_id}")
            print(f"📝 SAVED METADATA NAME: {incident_model.metadata_name}")
            print(f"📝 SAVED TYPE: {incident_model.type}")
            print(f"📝 SAVED REASON: {incident_model.reason}")
            print("="*60)
            
            logger.info(f"Successfully saved incident to database with ID: {incident_id}")
            return incident_id
            
    except Exception as e:
        print(f"❌ ERROR SAVING INCIDENT TO DATABASE: {str(e)}")
        print(f"❌ ERROR TYPE: {type(e)}")
        print(f"❌ EVENT DATA THAT FAILED: {k8s_event}")
        logger.error(f"Error saving incident to database: {str(e)}")
        raise e

async def save_solution_to_db(solution, incident_id: str):
    """
    Save LLM solution to database (optional)
    """
    try:
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
