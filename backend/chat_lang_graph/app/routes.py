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
    
    # Remove duplicate processing indicators
    formatted = formatted.replace('**Tool Results:**\n', '')
    formatted = formatted.replace('**Response:**\n', '')
    
    # Clean up excessive newlines
    import re
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    
    # Remove duplicate list patterns (comma-separated followed by bullet list)
    # This regex looks for patterns like "item1, item2, item3\nHere are...\n- item1\n- item2"
    formatted = re.sub(r'([a-zA-Z0-9\-_,\s]+): ([a-zA-Z0-9\-_,\s]+)\n+(?:Here are|The following are)[^\n]*:\n((?:- [^\n]+\n?)+)', r'\1:\n\3', formatted)
    
    return formatted

def get_user_token(request: Request) -> str:
    """Extract user token from request headers"""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        print(f"🔑 Extracted user token: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
        return token
    print("❌ No valid authorization header found")
    return ""


from app.auth_permission import require_permission

from fastapi import Depends


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW}")
async def chat_invoke(
    request: Request,
    chat_request: ChatRequest,
    db_session: SessionDep,
    # current_user: CurrentUser
    current_user = Depends(require_permission("chatops"))
):
    """Process a chat message with LangGraph agent."""
    try:
        print(f" Chat request received:")
        print(f" Message: {chat_request.message[:100]}...")
        print(f" Cluster name: {chat_request.cluster_name}")
        print(f" Session ID: {chat_request.session_id}")
        print(f" User: {current_user.get('username', 'unknown')}")
        
        # Initialize services
        chat_service = ChatService(db_session)
        message_service = MessageService(db_session)
        
        # Get user token
        user_token = get_user_token(request)
        print(f"🔑 User token extracted: {'Yes' if user_token else 'No'}")
        
        # Validate message
        if not message_service.validate_message_content(chat_request.message):
            print("❌ Message validation failed")
            raise HTTPException(status_code=400, detail="Invalid message content")
        
        print("✅ Message validation passed")
        
        # Get or create session
        session_id = chat_request.session_id or str(uuid.uuid4())
        print(f"📝 Using session ID: {session_id}")
        
        if chat_request.session_id:
            session = chat_service.get_session(session_id, current_user["id"])
            if not session:
                print("❌ Session not found")
                raise HTTPException(status_code=404, detail="Session not found")
            print("✅ Existing session found")
        else:
            session = chat_service.create_session(current_user)
            session_id = session.session_id
            print(f"✅ New session created: {session_id}")
        
        # Add user message to session
        chat_service.add_message(session_id, "user", chat_request.message)
        print("✅ User message added to session")
        
        # Get conversation history
        history = chat_service.get_session_history(session_id)
        print(f"📚 Retrieved {len(history)} messages from history")
        
        # Process with LangGraph - pass cluster name and user token
        print(f"🚀 Processing with LangGraph...")
        result = await langgraph_service.process_message(
            chat_request.message,
            history[:-1],  # Exclude the just-added user message
            chat_request.enable_tool_response,
            cluster_name=chat_request.cluster_name,
            user_token=user_token
        )
        
        print(f"✅ LangGraph processing result: {result.get('success', False)}")
        
        if not result["success"]:
            print(f"❌ LangGraph processing failed: {result.get('error', 'Unknown error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
        
        # Add assistant response to session
        if result["response"]:
            chat_service.add_message(session_id, "assistant", result["response"])
            print("✅ Assistant response added to session")
        
        # Prepare response
        tools_info = [ToolInfo(**tool) for tool in result.get("tools_info", [])]
        tool_responses = [ToolResponse(**tool) for tool in result.get("tool_responses", [])]
        
        print(f"✅ Chat response prepared successfully")
        
        return ChatResponse(
            session_id=session_id,
            response=result["response"],
            tools_info=tools_info,
            tool_response=tool_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat_invoke: {e}")
        print(f"   Error type: {type(e)}")
        logger.error(f"❌ Error in chat_invoke: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 


@router.post("/chat/stream")
@limiter.limit(f"{int(settings.RATE_LIMIT_REQUESTS/2)}/{settings.RATE_LIMIT_WINDOW}")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db_session: SessionDep,
    # current_user: CurrentUser
    current_user = Depends(require_permission("chatops"))
):
    """Stream a chat response from LangGraph agent."""
    try:
        print(f"🌊 Stream chat request received:")
        print(f"   Message: {chat_request.message[:100]}...")
        print(f"   Cluster name: {chat_request.cluster_name}")
        
        # Initialize services
        chat_service = ChatService(db_session)
        message_service = MessageService(db_session)
        
        # Get user token
        user_token = get_user_token(request)
        
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
                print(f"🌊 Starting stream for cluster: {chat_request.cluster_name}")
                async for token in langgraph_service.stream_message(
                    chat_request.message,
                    history[:-1],  # Exclude the just-added user message
                    cluster_name=chat_request.cluster_name,
                    user_token=user_token
                ):
                    full_response += token
                    yield f"data: {token}\n\n"
                print(f"✅ Stream completed. Full response length: {len(full_response)}")
                
                # Save the complete response
                if full_response:
                    chat_service.add_message(session_id, "assistant", full_response)
                    
            except Exception as e:
                print(f"❌ Error in streaming: {e}")
                logger.error(f"❌ Error in streaming: {e}")
                yield f"data: ❌ Error: {str(e)}\n\n"
        
        return StreamingResponse(stream_tokens(), media_type="text/event-stream")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat_stream: {e}")
        logger.error(f"❌ Error in chat_stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Session Management Endpoints
@router.get("/sessions", response_model=ChatSessionList)
async def list_sessions(
    db_session: SessionDep,
    # current_user: CurrentUser,
    current_user = Depends(require_permission("chatops")),
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
    # current_user: CurrentUser
    current_user = Depends(require_permission("chatops"))
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
    # current_user: CurrentUser
    current_user = Depends(require_permission("chatops"))
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
    # current_user: CurrentUser
    current_user = Depends(require_permission("chatops"))
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
    """Health check endpoint with detailed component checks."""
    try:
        # Check LangGraph service
        langgraph_health = await langgraph_service.health_check()
        
        # Check database with connection pool info
        db_status = "healthy"
        try:
            from .database import engine
            from sqlalchemy import text
            
            with engine.connect() as conn:
                # Test basic connectivity
                result = conn.execute(text("SELECT 1 as test_value"))
                test_result = result.fetchone()
                
                if test_result and test_result[0] == 1:
                    # Get connection pool info
                    pool = engine.pool
                    db_status = f"healthy"
                else:
                    db_status = "unhealthy: Test query failed"
                    
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Check Kubernetes tools with more details
        k8s_status = "healthy"
        try:
            from .k8s_tools import k8s_tools, _cluster_name, _cluster_server_url
            
            if not k8s_tools:
                k8s_status = "no tools available"
            else:
                tool_count = len(k8s_tools)
                cluster_info = f" - cluster: {_cluster_name or 'default'}" if _cluster_name else ""
                k8s_status = f"healthy"
                
        except Exception as e:
            k8s_status = f"unhealthy: {str(e)}"
        
        # Determine overall status
        overall_status = "healthy"
        if "unhealthy" in db_status:
            overall_status = "degraded"
        if langgraph_health["status"] != "healthy":
            overall_status = "degraded" 
        if "unhealthy" in k8s_status:
            overall_status = "degraded"
            
        # If all components are unhealthy, mark as unhealthy
        if all("unhealthy" in status for status in [db_status, langgraph_health["status"], k8s_status]):
            overall_status = "unhealthy"
        
        logger.info(f"🏥 Health check completed: {overall_status}")
        
        return HealthResponse(
            status=overall_status,
            database=db_status,
            llm=langgraph_health["status"],
            kubernetes=k8s_status,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database=f"error: {str(e)}",
            llm="unknown",
            kubernetes="unknown",
            timestamp=datetime.utcnow().isoformat()
        )