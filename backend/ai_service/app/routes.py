from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import List, Dict, Optional
import datetime
from app.database import get_session
from app.models import QueryHistory
from app.schemas import (
    Query, 
    ExecuteRequest, 
    CommandResponse, 
    MessageResponse
)
from app.auth import get_current_user
from app.config import settings, limiter, cache
from app.logger import logger
from app.llm_service import get_command_from_llm, is_safe_kubectl_command
from app.utils import execute_command_async, sanitize_query
from app.queue import publish_message
from slowapi.errors import RateLimitExceeded

ai_router = APIRouter()

@ai_router.post("/kubectl-command",
             response_model=CommandResponse,
             summary="Generate kubectl commands from natural language",
             responses={
                 200: {"description": "Commands generated successfully"},
                 400: {"description": "Invalid input query or non-Kubernetes request"},
                 401: {"description": "Unauthorized"},
                 422: {"description": "Unsafe command generated or validation failed"},
                 429: {"description": "Rate limit exceeded"},
                 500: {"description": "Internal server error"},
                 503: {"description": "Service unavailable (LLM issue)"},
                 504: {"description": "Gateway timeout (LLM)"}
             })
@limiter.limit("10/minute")
async def get_kubectl_command(
    q: Query,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    # current_user: Dict = Depends(get_current_user)
    current_user = {
            "id": 1,
            "username": "nisha",
            "email": "nisha@example.com",
            "first_name": "nisha",
            "last_name": "nisha",
            "is_active": True,
            "is_admin": False,
            "created_at": "2025-04-26T11:40:06.512880",
            "updated_at": "2025-04-26T11:40:06.512996"
        }
    ):

    logger.info(f"Received command generation query: '{q.query}'")
    sanitized_query = sanitize_query(q.query)

    from_cache = False
    command_string = None # Store the raw string from LLM/cache
    try:
        cached_commands = cache.get(sanitized_query)
        if cached_commands is not None:
            logger.info(f"Cache hit for query: {sanitized_query}")
            command_string = cached_commands
            from_cache = True
        else:
            logger.info(f"Cache miss for query: {sanitized_query}")
            command_string = await get_command_from_llm(sanitized_query)
            cache[sanitized_query] = command_string # Cache the raw string
            logger.debug(f"Stored result in cache for query: {sanitized_query}")

    except HTTPException as http_exc:
        # Log the specific HTTP exception details
        logger.error(f"HTTPException during command generation for '{sanitized_query}': Status={http_exc.status_code}, Detail={http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error processing query '{sanitized_query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing request"
        )

    # Split the command string into a list
    command_list = [cmd.strip() for cmd in command_string.splitlines() if cmd.strip()]
    logger.debug(f"Split commands into list: {command_list}")

    # Prepare metadata
    metadata = {
        "start_time": datetime.datetime.utcnow().isoformat(),
        "end_time": datetime.datetime.utcnow().isoformat(),
        "duration_ms": 0.0,
        "success": True, # Indicates generation success
        "error_type": None,
        "error_code": None
    }
    
    # Store query history in database
    query_history = QueryHistory(
        user_id=current_user["id"],
        query=q.query,
        generated_commands=command_string,
        execution_success=True
    )
    session.add(query_history)
    session.commit()
    
    # Publish event to message queue
    publish_message("ai_events", {
        "event_type": "command_generated",
        "user_id": current_user["id"],
        "username": current_user.get("username", "unknown"),
        "query": q.query,
        "commands": command_list,
        "from_cache": from_cache,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return CommandResponse(
        kubectl_command=command_list,
        execution_result=None, # No execution in this endpoint
        execution_error=None,
        from_cache=from_cache,
        metadata=metadata
    )

@ai_router.post("/execute",
             response_model=CommandResponse,
             summary="Execute a single kubectl command",
             responses={
                 200: {"description": "Command executed successfully"},
                 400: {"description": "Invalid or unsafe command"},
                 401: {"description": "Unauthorized"},
                 429: {"description": "Rate limit exceeded"},
                 500: {"description": "Internal server error"},
                 504: {"description": "Gateway timeout (execution)"}
             })
@limiter.limit("10/minute")
async def execute_kubectl_command(
    req: ExecuteRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    command_to_execute = req.execute.strip()
    logger.info(f"Received execute request for command: '{command_to_execute}'")

    # Use the updated safety check from llm_service
    if not is_safe_kubectl_command(command_to_execute):
        logger.error(f"Execution rejected: Command failed safety checks: {command_to_execute}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Command failed safety checks. Cannot execute."
        )

    logger.info(f"Executing command: {command_to_execute}")
    execution_data = await execute_command_async(command_to_execute, settings.EXECUTION_TIMEOUT)

    # Ensure metadata reflects execution success/failure
    final_metadata = execution_data.get("metadata", {})
    if "execution_error" in execution_data:
        final_metadata["success"] = False
    
    # Store execution history in database
    query_history = QueryHistory(
        user_id=current_user["id"],
        query=f"Direct execution: {command_to_execute}",
        generated_commands=command_to_execute,
        execution_result=execution_data.get("execution_result"),
        execution_error=execution_data.get("execution_error"),
        execution_success=final_metadata.get("success", False)
    )
    session.add(query_history)
    session.commit()
    
    # Publish event to message queue
    publish_message("ai_events", {
        "event_type": "command_executed",
        "user_id": current_user["id"],
        "username": current_user.get("username", "unknown"),
        "command": command_to_execute,
        "success": final_metadata.get("success", False),
        "error": execution_data.get("execution_error"),
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return CommandResponse(
        kubectl_command=[command_to_execute], # Return as a list with one item
        execution_result=execution_data.get("execution_result"),
        execution_error=execution_data.get("execution_error"),
        from_cache=False, # Execution is never cached
        metadata=final_metadata
    )

@ai_router.get("/history")
async def get_query_history(
    limit: int = 50,
    session: Session = Depends(get_session),
    current_user: Dict = Depends(get_current_user)
):
    """Get the query history for the current user"""
    history = session.exec(
        select(QueryHistory)
        .where(QueryHistory.user_id == current_user["id"])
        .order_by(QueryHistory.created_at.desc())
        .limit(limit)
    ).all()
    
    return {"history": history}
