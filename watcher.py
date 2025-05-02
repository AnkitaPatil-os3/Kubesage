import logging
import os
import time
import json
from datetime import datetime

import httpx
from kubernetes import client, config, watch

# --- Configuration ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("K8sEventWatcher")

# Get API endpoint from environment variable, default to service name in the same namespace
SELF_HEAL_API_ENDPOINT = os.getenv("SELF_HEAL_API_ENDPOINT", "http://self-healing-service.default.svc.cluster.local:8000/self-heal")
# Namespace to watch, default to 'default'. Use "" for all namespaces (requires cluster-level permissions)
WATCH_NAMESPACE = os.getenv("WATCH_NAMESPACE", "default")
# Event types to watch (e.g., 'Warning', 'Normal'). None means all types.
WATCH_EVENT_TYPES = os.getenv("WATCH_EVENT_TYPES", "Warning") # Focus on warnings by default
# Kinds of objects to watch events for (e.g., 'Pod', 'Deployment'). None means all kinds.
WATCH_OBJECT_KINDS = os.getenv("WATCH_OBJECT_KINDS", "Pod,Deployment,ReplicaSet,StatefulSet,DaemonSet") # Common workload types

# --- Kubernetes Client Setup ---

def load_kube_config():
    """Loads Kubernetes configuration (in-cluster or local kubeconfig)."""
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config.")
    except config.ConfigException:
        try:
            config.load_kube_config()
            logger.info("Loaded local Kubernetes config (kubeconfig file).")
        except config.ConfigException as e:
            logger.error(f"Could not load any Kubernetes config: {e}", exc_info=True)
            raise RuntimeError("Failed to configure Kubernetes client") from e

# --- Event Processing ---

def should_process_event(event_obj: dict) -> bool:
    """Determines if an event should be processed based on configured filters."""
    event_type = event_obj.get("type")
    involved_object_kind = event_obj.get("involvedObject", {}).get("kind")

    # Filter by type
    if WATCH_EVENT_TYPES and event_type not in WATCH_EVENT_TYPES.split(','):
        logger.debug(f"Skipping event: Type '{event_type}' not in watched types '{WATCH_EVENT_TYPES}'.")
        return False

    # Filter by kind
    if WATCH_OBJECT_KINDS and involved_object_kind not in WATCH_OBJECT_KINDS.split(','):
         logger.debug(f"Skipping event: Kind '{involved_object_kind}' not in watched kinds '{WATCH_OBJECT_KINDS}'.")
         return False

    # Add more filtering logic here if needed (e.g., based on reason, specific messages)
    # Example: Ignore specific reasons
    # ignore_reasons = ["SuccessfulCreate", "SuccessfulDelete"]
    # if event_obj.get("reason") in ignore_reasons:
    #     logger.debug(f"Skipping event: Reason '{event_obj.get('reason')}' is ignored.")
    #     return False

    return True


async def forward_event(event_obj: dict):
    """Formats and sends the event to the self-healing API."""
    raw_event_payload = {
        "event_data": event_obj,
        # "received_at" will be set by the Pydantic model on the server side
    }
    logger.info(f"Forwarding event: {event_obj.get('metadata', {}).get('name')} (Reason: {event_obj.get('reason', 'N/A')})")
    logger.debug(f"Payload: {json.dumps(raw_event_payload, indent=2)}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client: # Use async client
            response = await http_client.post(SELF_HEAL_API_ENDPOINT, json=raw_event_payload)
            response.raise_for_status() # Raise exception for 4xx/5xx responses
            logger.info(f"Event forwarded successfully. Response status: {response.status_code}")
            # Optionally log response body if needed: logger.debug(f"API Response: {response.text}")
    except httpx.RequestError as e:
        logger.error(f"HTTP error forwarding event to {SELF_HEAL_API_ENDPOINT}: {e}", exc_info=True)
    except httpx.HTTPStatusError as e:
         logger.error(f"API returned error status {e.response.status_code} forwarding event: {e.response.text}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error forwarding event: {e}", exc_info=True)


# --- Main Watch Loop ---

async def watch_kubernetes_events():
    """Watches Kubernetes events and forwards them."""
    load_kube_config()
    v1 = client.CoreV1Api()
    w = watch.Watch()

    resource_version = '' # Start watching from the latest events

    logger.info(f"Starting Kubernetes event watcher for namespace: '{WATCH_NAMESPACE or 'all'}'")
    logger.info(f"Watching event types: {WATCH_EVENT_TYPES or 'all'}")
    logger.info(f"Watching object kinds: {WATCH_OBJECT_KINDS or 'all'}")
    logger.info(f"Forwarding events to: {SELF_HEAL_API_ENDPOINT}")

    while True:
        try:
            if WATCH_NAMESPACE:
                stream = w.stream(v1.list_namespaced_event, namespace=WATCH_NAMESPACE, resource_version=resource_version, timeout_seconds=60)
            else:
                stream = w.stream(v1.list_event_for_all_namespaces, resource_version=resource_version, timeout_seconds=60)

            for event in stream:
                event_obj = event['object'].to_dict()
                event_type = event['type'] # ADDED, MODIFIED, DELETED
                resource_version = event_obj['metadata']['resource_version'] # Keep track for next watch iteration

                logger.debug(f"Received event: Type={event_type}, Name={event_obj['metadata']['name']}, Reason={event_obj.get('reason')}")

                # We are interested in ADDED or MODIFIED events that match our filters
                if event_type in ["ADDED", "MODIFIED"]:
                    if should_process_event(event_obj):
                        await forward_event(event_obj)
                    else:
                        logger.debug("Event skipped by filters.")
                elif event_type == "DELETED":
                     logger.debug("Ignoring DELETED event type.")
                elif event_type == "BOOKMARK":
                     logger.debug(f"Received BOOKMARK event at resource version {resource_version}")
                elif event_type == "ERROR":
                     # Handle error events from the watch stream itself
                     # The raw_object usually contains details about the error (e.g., 410 Gone)
                     raw_object = event.get('raw_object', {})
                     status_details = raw_object.get('details', {})
                     message = raw_object.get('message', 'Unknown watch error')
                     code = raw_object.get('code')
                     logger.error(f"Watch stream error: Code={code}, Message='{message}', Details={status_details}")
                     if code == 410: # Resource version too old
                         logger.warning("Resource version too old (410 Gone). Resetting watch.")
                         resource_version = '' # Reset to watch from latest
                         time.sleep(1) # Brief pause before restarting watch
                         break # Break inner loop to restart watch
                     else:
                         # For other errors, maybe pause and retry
                         logger.warning("Pausing for 10 seconds due to watch stream error.")
                         time.sleep(10)
                         break # Restart watch

        except client.ApiException as e:
            logger.error(f"Kubernetes API Exception during watch: {e.status} {e.reason}", exc_info=True)
            if e.status == 401: # Unauthorized
                 logger.critical("Received 401 Unauthorized. Check RBAC permissions for the watcher.")
                 # Stop trying if auth fails persistently
                 break
            logger.info("Retrying watch after 15 seconds...")
            time.sleep(15)
        except Exception as e:
            logger.error(f"Unexpected error in watch loop: {e}", exc_info=True)
            logger.info("Retrying watch after 15 seconds...")
            time.sleep(15)
        finally:
             # Ensure resource_version is updated even if loop breaks unexpectedly
             # This might not always be correct if the break was before processing an event
             pass


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(watch_kubernetes_events())
    except KeyboardInterrupt:
        logger.info("Watcher stopped manually.")
    except RuntimeError as e:
         logger.critical(f"Watcher failed to start: {e}")
         exit(1)
    except Exception as e:
        logger.critical(f"Watcher stopped due to unexpected error: {e}", exc_info=True)
        exit(1)
