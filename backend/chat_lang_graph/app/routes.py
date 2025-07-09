import uuid
import json
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime

from .dependencies import SessionDep, CurrentUser
from .schemas import (
    ChatRequest, ChatResponse, SessionInfo, SessionHistory, 
    ToolInfo, ToolResponse, ChatSessionCreate, ChatSessionResponse,
    ChatSessionList, HealthResponse
)
from .services import ChatService, MessageService
from .langgraph_service import LangGraphService
from .logger import logger
from .cache import cache_get, cache_set, get_session_key, get_messages_key
from .config import settings

router = APIRouter()

# Initialize services
langgraph_service = LangGraphService()

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

def format_markdown_response(response: str) -> str:
    """Convert escaped newlines to proper markdown formatting."""
    if not response:
        return response
    
    # Replace escaped newlines with actual newlines
    formatted = response.replace('\\n', '\n')
    
    # Additional formatting if needed
    return formatted

@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW}")
async def chat_invoke(
    request: Request,
    chat_request: ChatRequest,
    db_session: SessionDep,
    current_user: CurrentUser
):
    """Process a chat message with LangGraph agent."""
    try:
        # Initialize services
        chat_service = ChatService(db_session)
        message_service = MessageService(db_session)
        
        # Validate message
        if not message_service.validate_message_content(chat_request.message):
            raise HTTPException(status_code=400, detail="Invalid message content")
        
        # Get or create session
        session_id = chat_request.session_id or str(uuid.uuid4())
        
        if chat_request.session_id:
            session = chat_service.get_session(session_id, current_user["id"])
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Pass the full user data to create_session
            session = chat_service.create_session(current_user)
            session_id = session.session_id
        
        # Add user message to session
        chat_service.add_message(session_id, "user", chat_request.message)
        
        # Get conversation history
        history = chat_service.get_session_history(session_id)
        
        # Process with LangGraph
        result = await langgraph_service.process_message(
            chat_request.message,
            history[:-1],  # Exclude the just-added user message
            chat_request.enable_tool_response
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
        
        # Add assistant response to session
        if result["response"]:
            chat_service.add_message(session_id, "assistant", result["response"])
        
        # Prepare response data
        final_response = result["response"]
        tools_info = [ToolInfo(**tool) for tool in result.get("tools_info", [])]
        tool_responses = [ToolResponse(**tool) for tool in result.get("tool_responses", [])]
        
        # CHANGE: Always check for markdown request
        wants_markdown = (
            is_markdown_request(request) or 
            chat_request.format == "markdown" or
            request.headers.get("accept", "").lower().find("markdown") != -1
        )
        
        if wants_markdown:
            formatted_response = format_markdown_response(final_response)
            return PlainTextResponse(
                content=formatted_response,
                media_type="text/markdown"
            )
        
        # Otherwise, respond with the default JSON structure
        return ChatResponse(
            session_id=session_id,
            response=final_response,
            tools_info=tools_info,
            tool_response=tool_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in chat_invoke: {e}")
        raise HTTPException(status_code=500, detail=str(e))


















@router.post("/chat/stream")
@limiter.limit(f"{int(settings.RATE_LIMIT_REQUESTS/2)}/{settings.RATE_LIMIT_WINDOW}")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db_session: SessionDep,
    current_user: CurrentUser
):
    """Stream a chat response from LangGraph agent."""
    try:
        # Initialize services
        chat_service = ChatService(db_session)
        message_service = MessageService(db_session)
        
        # Validate message
        if not message_service.validate_message_content(chat_request.message):
            raise HTTPException(status_code=400, detail="Invalid message content")
        
        # Get or create session
        session_id = chat_request.session_id or str(uuid.uuid4())
        
        if chat_request.session_id:
            session = chat_service.get_session(session_id, current_user["id"])
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            session = chat_service.create_session(current_user)
            session_id = session.session_id
        
        # Add user message to session
        chat_service.add_message(session_id, "user", chat_request.message)
        
        # Get conversation history
        history = chat_service.get_session_history(session_id)
        
        async def stream_tokens():
            full_response = ""
            yield f"data: {json.dumps({'session_id': session_id})}\n\n"
            
            try:
                async for token in langgraph_service.stream_message(
                    chat_request.message,
                    history[:-1]  # Exclude the just-added user message
                ):
                    full_response += token
                    yield f"data: {token}\n\n"
                print(f"--------------- Full Response: {full_response}")
                
                # Save the complete response
                if full_response:
                    chat_service.add_message(session_id, "assistant", full_response)
                    
            except Exception as e:
                logger.error(f"❌ Error in streaming: {e}")
                yield f"data: ❌ Error: {str(e)}\n\n"
        
        return StreamingResponse(stream_tokens(), media_type="text/event-stream")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in chat_stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Session Management Endpoints
@router.get("/sessions", response_model=ChatSessionList)
async def list_sessions(
    db_session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 50
):
    """List user's chat sessions."""
    try:
        chat_service = ChatService(db_session)
        sessions = chat_service.list_user_sessions(current_user["id"], skip, limit)
        
        session_responses = []
        for session in sessions:
            session_responses.append(ChatSessionResponse(
                id=session.id,
                session_id=session.session_id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at,
                is_active=session.is_active
            ))
        
        return ChatSessionList(sessions=session_responses)
        
    except Exception as e:
        logger.error(f"❌ Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}", response_model=SessionHistory)
async def get_session(
    session_id: str,
    db_session: SessionDep,
    current_user: CurrentUser
):
    """Get a specific session with its message history."""
    try:
        chat_service = ChatService(db_session)
        session = chat_service.get_session(session_id, current_user["id"])
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        history = chat_service.get_session_history(session_id)
        
        return SessionHistory(
            id=session.session_id,
            created_at=session.created_at,
            messages=history
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db_session: SessionDep,
    current_user: CurrentUser
):
    """Delete a chat session."""
    try:
        chat_service = ChatService(db_session)
        success = chat_service.delete_session(session_id, current_user["id"])
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    session_create: ChatSessionCreate,
    db_session: SessionDep,
    current_user: CurrentUser
):
    """Create a new chat session."""
    try:
        chat_service = ChatService(db_session)
        session = chat_service.create_session(
            current_user,
            session_create.title or "Kubernetes Chat"
        )
        
        return ChatSessionResponse(
            id=session.id,
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            is_active=session.is_active
        )
        
    except Exception as e:
        logger.error(f"❌ Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health Check Endpoint (no authentication required)
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check LangGraph service
        langgraph_health = await langgraph_service.health_check()
        
        # Check database (basic check)
        db_status = "healthy"
        try:
            from .database import engine
            with engine.connect() as conn:
                conn.execute("SELECT 1")
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Check Kubernetes tools
        k8s_status = "healthy"
        try:
            from .k8s_tools import k8s_tools
            if not k8s_tools:
                k8s_status = "no tools available"
        except Exception as e:
            k8s_status = f"unhealthy: {str(e)}"
        
        return HealthResponse(
            status="healthy" if all([
                langgraph_health["status"] == "healthy",
                db_status == "healthy",
                k8s_status == "healthy"
            ]) else "degraded",
            database=db_status,
            llm=langgraph_health["status"],
            kubernetes=k8s_status,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database="unknown",
            llm="unknown",
            kubernetes="unknown",
            timestamp=datetime.utcnow().isoformat()
        )