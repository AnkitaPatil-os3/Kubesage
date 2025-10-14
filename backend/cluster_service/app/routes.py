from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from app.config import settings
from app.logger import logger
from app.auth import authenticate_request
from app.schemas import NamespacesResponse, NamespaceInfo, ErrorResponse, HealthResponse
from app.websocket_client import send_request_to_agent
from app.rate_limiter import rate_limit
from datetime import datetime
import uuid
from typing import Optional

router = APIRouter()

# API Key header dependency
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="cluster_service",
        timestamp=datetime.utcnow().isoformat()
    )

@router.get("/namespaces", response_model=NamespacesResponse)
async def get_namespaces(
    request: Request,
    agent_id: str,
    cluster_id: Optional[int] = None,
    api_key: str = Depends(api_key_header),
    _: bool = Depends(rate_limit(max_requests=30, window_seconds=60))  # 30 requests per minute
):
    """
    Get namespaces from a Kubernetes cluster via agent.
    
    This is an on-demand service that:
    1. Authenticates the API key via RabbitMQ with user_service
    2. Requests namespace information from the specified agent via WebSocket
    3. Returns the list of namespaces
    
    Args:
        agent_id: The unique identifier of the agent to query
        cluster_id: Optional cluster ID for additional context
        api_key: API key for authentication
    
    Returns:
        NamespacesResponse: List of namespaces and metadata
    
    Raises:
        HTTPException: 401 for authentication failure, 500 for other errors
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Namespaces request {request_id} from agent {agent_id} for cluster {cluster_id}")
    
    try:
        # Authenticate the user via RabbitMQ to user_service
        user_data = await authenticate_request(api_key)
        user_id = user_data.get("id")
        
        logger.info(f"Request {request_id} authenticated for user {user_id}")
        
        # Prepare request for agent
        agent_request = {
            "request_id": request_id,
            "user": {
                "id": user_id,
                "username": user_data.get("username", ""),
                "email": user_data.get("email", "")
            },
            "request": {
                "message": "get-namespaces",
                "cluster_id": cluster_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Send request to agent via WebSocket
        logger.info(f"Sending namespace request {request_id} to agent {agent_id}")
        agent_response = await send_request_to_agent(agent_id, agent_request)
        
        # Parse agent response
        if agent_response.get("error"):
            logger.error(f"Agent {agent_id} returned error: {agent_response['error']}")
            raise HTTPException(
                status_code=500, 
                detail=f"Agent error: {agent_response['error']}"
            )
        
        # Extract namespace data from agent response
        result = agent_response.get("result", "")
        namespaces_data = []
        total_count = 0
        cluster_info = {}
        
        try:
            if isinstance(result, str):
                import json
                result = json.loads(result)
            
            if isinstance(result, dict):
                if "error" in result and result.get("error"):
                    # Handle error response from agent
                    error_msg = result.get("message", "Unknown agent error")
                    logger.error(f"Agent {agent_id} returned error: {error_msg}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Agent error: {error_msg}"
                    )
                
                if "namespaces" in result:
                    namespaces_list = result["namespaces"]
                    total_count = result.get("total_count", len(namespaces_list))
                    cluster_info = result.get("cluster_info", {})
                    
                    # Convert to our schema format
                    for ns in namespaces_list:
                        if isinstance(ns, dict):
                            namespace_info = NamespaceInfo(
                                name=ns.get("name", ""),
                                status=ns.get("status", "Unknown"),
                                created_at=ns.get("createdAt", ""),
                                labels=ns.get("labels", {}),
                                annotations=ns.get("annotations", {})
                            )
                            namespaces_data.append(namespace_info)
                        elif isinstance(ns, str):
                            # Simple string format (backward compatibility)
                            namespace_info = NamespaceInfo(
                                name=ns,
                                status="Active"
                            )
                            namespaces_data.append(namespace_info)
        
        except json.JSONDecodeError as parse_error:
            logger.warning(f"Error parsing agent response as JSON: {str(parse_error)}")
            # Fallback: treat result as simple message
            total_count = 0
        except Exception as parse_error:
            logger.warning(f"Error parsing agent response: {str(parse_error)}")
            # Fallback: treat result as simple message
            total_count = 0
        
        logger.info(f"Successfully retrieved {total_count} namespaces from agent {agent_id}")
        
        return NamespacesResponse(
            success=True,
            agent_id=agent_id,
            cluster_id=cluster_id,
            namespaces=namespaces_data,
            total_count=total_count,
            message=f"Successfully retrieved namespaces from cluster (config: {cluster_info.get('config_type', 'unknown')})",
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like auth failures)
        raise
        
    except Exception as e:
        logger.error(f"Error in get_namespaces for request {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve namespaces: {str(e)}"
        )

@router.get("/agents/connected")
async def get_connected_agents(
    request: Request,
    api_key: str = Depends(api_key_header),
    _: bool = Depends(rate_limit(max_requests=10, window_seconds=60))  # 10 requests per minute
):
    """
    Get list of currently connected agents.
    
    Args:
        api_key: API key for authentication
    
    Returns:
        Dict containing list of connected agent IDs
    """
    try:
        # Authenticate the user
        user_data = await authenticate_request(api_key)
        
        # Get connected agents
        from app.websocket_client import get_connected_agents
        connected_agents = await get_connected_agents()
        
        logger.info(f"User {user_data.get('id')} requested connected agents list")
        
        return {
            "success": True,
            "connected_agents": connected_agents,
            "total_count": len(connected_agents),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error getting connected agents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get connected agents: {str(e)}"
        )
