import asyncio
import websockets
import json
import threading
from app.config import settings
from app.logger import logger

# WebSocket connections: agent_id -> websocket connection
websocket_connections = {}

async def connect_to_agent_websocket(agent_id: str):
    """
    Establish WebSocket connection to agent.
    """
    try:
        # WebSocket URL for the agent (assuming agents run on localhost for now)
        websocket_url = f"ws://localhost:9000/ws/agent/{agent_id}"

        # Create WebSocket connection
        websocket = await websockets.connect(websocket_url)

        # Store connection
        websocket_connections[agent_id] = websocket

        # Start listening for messages in background
        asyncio.create_task(listen_for_messages(agent_id, websocket))

        logger.info(f"WebSocket connection established for agent {agent_id}")

        return {
            "success": True,
            "websocket_url": websocket_url,
            "message": "WebSocket connection established"
        }

    except Exception as e:
        logger.error(f"Failed to connect to agent WebSocket: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to establish WebSocket connection: {str(e)}"
        }

async def listen_for_messages(agent_id: str, websocket):
    """
    Listen for incoming messages from the agent.
    """
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"Received message from agent {agent_id}: {data}")

                # Handle different message types
                message_type = data.get("type")
                if message_type == "heartbeat":
                    # Update agent's last seen timestamp
                    await update_agent_last_seen(agent_id)
                elif message_type == "status":
                    # Handle status updates
                    await handle_agent_status_update(agent_id, data)
                elif message_type == "error":
                    # Handle error messages
                    await handle_agent_error(agent_id, data)
                else:
                    # Check if this is a response to a namespace request
                    request_id = data.get("request_id")
                    if request_id:
                        await handle_agent_response(agent_id, data)
                    else:
                        logger.warning(f"Unknown message type from agent {agent_id}: {message_type}")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON message from agent {agent_id}: {message}")

    except websockets.exceptions.ConnectionClosed:
        logger.warning(f"WebSocket connection closed for agent {agent_id}")
        await handle_agent_disconnection(agent_id)
    except Exception as e:
        logger.error(f"Error listening for messages from agent {agent_id}: {str(e)}")
        await handle_agent_disconnection(agent_id)

async def send_message_to_agent(agent_id: str, message: dict):
    """
    Send a message to a connected agent.
    """
    websocket = websocket_connections.get(agent_id)
    if not websocket:
        raise Exception(f"No WebSocket connection found for agent {agent_id}")

    try:
        await websocket.send(json.dumps(message))
        logger.info(f"Sent message to agent {agent_id}: {message}")
    except Exception as e:
        logger.error(f"Failed to send message to agent {agent_id}: {str(e)}")
        raise

async def update_agent_last_seen(agent_id: str):
    """
    Update the last seen timestamp for an agent.
    """
    # This would typically update the database
    # For now, just log it
    logger.debug(f"Agent {agent_id} heartbeat received")

async def handle_agent_status_update(agent_id: str, data: dict):
    """
    Handle status update from agent.
    """
    logger.info(f"Agent {agent_id} status update: {data}")

async def handle_agent_error(agent_id: str, data: dict):
    """
    Handle error message from agent.
    """
    logger.error(f"Agent {agent_id} error: {data}")

async def handle_agent_response(agent_id: str, data: dict):
    """
    Handle response from agent and forward to appropriate service.
    """
    try:
        request_id = data.get("request_id")
        result = data.get("result")
        error = data.get("error")
        
        logger.info(f"Handling response from agent {agent_id} for request {request_id}")
        
        # Check if this might be a namespace request response
        if result and ("namespaces" in str(result) or "namespace" in str(result).lower()):
            # This looks like a namespace response, forward to cluster service
            from app.rabbitmq import publish_message
            
            namespace_result = {
                "request_id": request_id,
                "agent_id": agent_id,
                "result": result,
                "error": error,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            publish_message("cluster_namespace_results", namespace_result)
            logger.info(f"Forwarded namespace response for request {request_id} to cluster service")
        else:
            # Handle other types of responses (onboarding, etc.)
            logger.debug(f"Received non-namespace response from agent {agent_id}: {data}")
            
    except Exception as e:
        logger.error(f"Error handling agent response: {str(e)}")

async def handle_agent_disconnection(agent_id: str):
    """
    Handle agent disconnection.
    """
    # Remove from connections
    websocket_connections.pop(agent_id, None)

    # Update agent status in database
    # This would typically update the database
    logger.info(f"Agent {agent_id} disconnected")

def get_connected_agents():
    """
    Get list of currently connected agents.
    """
    return list(websocket_connections.keys())
