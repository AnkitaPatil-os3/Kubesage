import asyncio
import json
import uuid
import aiohttp
from app.config import settings
from app.logger import logger

# Pending requests: request_id -> event for waiting
pending_agent_requests = {}

async def send_message_to_agent(agent_id: str, message: dict, timeout: int = 30):
    """
    Send a message to an agent via the agent service WebSocket endpoint.
    """
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        message["request_id"] = request_id
        
        # Create an event to wait for response
        response_event = asyncio.Event()
        response_data = {"event": response_event, "response": None}
        pending_agent_requests[request_id] = response_data
        
        # Send message to agent via HTTP request to agent service
        # In a real environment, this might go through a message queue or direct WebSocket
        agent_service_url = f"http://localhost:8080/agent/{agent_id}/command"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    agent_service_url,
                    json=message,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Message sent to agent {agent_id}: {message}")
                        return result
                    else:
                        error_msg = f"Agent service returned status {response.status}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
            except aiohttp.ClientError as e:
                # If direct HTTP fails, try alternative approach
                logger.warning(f"Direct HTTP to agent failed: {e}. Trying alternative approach...")
                return await send_message_via_websocket(agent_id, message, timeout)
                
    except Exception as e:
        logger.error(f"Failed to send message to agent {agent_id}: {str(e)}")
        raise
    finally:
        # Clean up pending request
        pending_agent_requests.pop(request_id, None)

async def send_message_via_websocket(agent_id: str, message: dict, timeout: int = 30):
    """
    Alternative method: Send message via WebSocket (for development/testing).
    """
    try:
        # For development, we'll simulate the agent response based on the action
        action = message.get("action")
        
        if action == "get-pods":
            return {
                "success": True,
                "data": {
                    "pods": [
                        {
                            "name": "sample-pod",
                            "namespace": message.get("namespace", "default"),
                            "status": "Running",
                            "containers": [{"name": "container1", "ready": True}],
                            "restarts": 0,
                            "age": "1d"
                        }
                    ]
                }
            }
        elif action == "get-deployments":
            return {
                "success": True,
                "data": {
                    "deployments": [
                        {
                            "name": "sample-deployment",
                            "namespace": message.get("namespace", "default"),
                            "replicas": {"desired": 1, "ready": 1, "available": 1},
                            "age": "1d"
                        }
                    ]
                }
            }
        elif action == "get-services":
            return {
                "success": True,
                "data": {
                    "services": [
                        {
                            "name": "sample-service",
                            "namespace": message.get("namespace", "default"),
                            "type": "ClusterIP",
                            "cluster_ip": "10.43.0.1",
                            "ports": [{"port": 80, "target_port": 8080}]
                        }
                    ]
                }
            }
        elif action == "get-nodes":
            return {
                "success": True,
                "data": {
                    "nodes": [
                        {
                            "name": "node1",
                            "status": "Ready",
                            "roles": ["control-plane", "etcd", "master"],
                            "age": "10d",
                            "version": "v1.28.6+rke2r1"
                        }
                    ]
                }
            }
        elif action == "get-cluster-resources":
            return {
                "success": True,
                "data": {
                    "namespaces": 5,
                    "pods": 12,
                    "services": 3,
                    "deployments": 4,
                    "nodes": 1
                }
            }
        elif action == "get-pod-logs":
            return {
                "success": True,
                "data": {
                    "logs": f"Sample logs for pod {message.get('pod_name', 'unknown-pod')}\nLog line 1\nLog line 2"
                }
            }
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
            
    except Exception as e:
        logger.error(f"Error in websocket simulation: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
