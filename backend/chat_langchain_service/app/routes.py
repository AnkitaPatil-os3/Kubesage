from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlmodel import Session, select
from typing import List, Optional, AsyncGenerator, Dict, Any
import json
import uuid
from datetime import datetime

from app.database import get_session
from app.models import ChatSession, ChatMessage
from app.schemas import (
    ChatRequest, MessageResponse, ChatHistoryResponse, 
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse, 
    ChatSessionList, HealthResponse
)
from app.auth import get_current_user, get_current_active_user
from app.langchain_service import (
    get_streaming_llm, get_non_streaming_llm, 
    create_memory_from_messages, get_memory_summary
)
from app.services import ChatService, MessageService
from app.logger import logger

router = APIRouter()

# Chat endpoint - API-1
@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Main chat endpoint with streaming support."""
    try:
        user_id = current_user["id"]
        logger.info(f"Chat request from user {user_id}: {request.message[:100]}...")
        
        # Initialize services
        chat_service = ChatService(session)
        message_service = MessageService(session)
        
        # Validate message
        if not message_service.validate_message_content(request.message):
            raise HTTPException(
                status_code=400, 
                detail="Invalid message content"
            )
        
        # Sanitize message
        clean_message = message_service.sanitize_message_content(request.message)
        
        # Get or create session
        if request.session_id:
            chat_session = chat_service.get_session(request.session_id, user_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            chat_session = chat_service.create_session(user_id)
        
        # Save user message
        try:
            user_message = chat_service.add_message(
                chat_session.session_id, 
                "user", 
                clean_message
            )
            logger.info(f"Saved user message: {user_message.id}")
        except Exception as e:
            logger.error(f"Error saving user message: {e}")
            # Continue without saving if there's a DB error
        
        # Get conversation history (with error handling)
        try:
            messages = chat_service.get_session_messages(chat_session.session_id)
            message_history = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Error getting message history: {e}")
            # Use just the current message if history retrieval fails
            message_history = [{"role": "user", "content": clean_message}]
        
        # Create memory from messages
        memory = create_memory_from_messages(message_history)
        
        if request.stream:
            # Streaming response
            async def generate_stream():
                try:
                    llm = get_streaming_llm()
                    
                    # Create the prompt with memory context
                    prompt = f"""You are KubeSage, an AI assistant specialized in Kubernetes operations and troubleshooting.

Previous conversation context:
{memory.buffer if hasattr(memory, 'buffer') else 'No previous context'}

Current user message: {clean_message}

Please provide a helpful response about Kubernetes. If the user asks about kubectl commands, provide them in code blocks. Be concise but informative."""

                    full_response = ""
                    
                    async for chunk in llm.astream(prompt):
                        if chunk.content:
                            full_response += chunk.content
                            yield f"data: {json.dumps({'token': chunk.content, 'done': False})}\n\n"
                    
                    # Save assistant response (with error handling)
                    try:
                        if message_service.should_save_message("assistant", full_response, True):
                            chat_service.add_message(
                                chat_session.session_id,
                                "assistant", 
                                full_response
                            )
                            logger.info("Saved assistant response")
                    except Exception as e:
                        logger.error(f"Error saving assistant response: {e}")
                    
                    # Send completion signal
                    yield f"data: {json.dumps({'token': None, 'done': True, 'session_id': chat_session.session_id})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Error in streaming response: {e}")
                    yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                }
            )
        
        else:
            # Non-streaming response
            try:
                llm = get_non_streaming_llm()
                
                # Create the prompt with memory context
                prompt = f"""You are KubeSage, an AI assistant specialized in Kubernetes operations and troubleshooting.

Previous conversation context:
{memory.buffer if hasattr(memory, 'buffer') else 'No previous context'}

Current user message: {clean_message}

Please provide a helpful response about Kubernetes. If the user asks about kubectl commands, provide them in code blocks. Be concise but informative."""

                response = await llm.ainvoke(prompt)
                assistant_message = response.content
                
                # Save assistant response (with error handling)
                try:
                    if message_service.should_save_message("assistant", assistant_message, True):
                        chat_service.add_message(
                            chat_session.session_id,
                            "assistant", 
                            assistant_message
                        )
                        logger.info("Saved assistant response")
                except Exception as e:
                    logger.error(f"Error saving assistant response: {e}")
                
                return MessageResponse(
                    role="assistant",
                    content=assistant_message,
                    session_id=chat_session.session_id,
                    created_at=datetime.utcnow()
                )
                
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate response"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

# Get chat sessions - API-2
@router.get("/sessions", response_model=ChatSessionList)
async def list_sessions(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 50,
    include_inactive: bool = False
):
    """List user's chat sessions."""
    try:
        user_id = current_user["id"]
        chat_service = ChatService(session)
        sessions = chat_service.list_user_sessions(
            user_id, skip, limit, include_inactive
        )
        
        session_responses = [
            ChatSessionResponse(
                id=s.id,
                session_id=s.session_id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                is_active=s.is_active
            )
            for s in sessions
        ]
        
        return ChatSessionList(sessions=session_responses)
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list sessions")

# Create chat session -- API-3
@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    session_data: ChatSessionCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Create a new chat session."""
    try:
        user_id = current_user["id"]
        chat_service = ChatService(session)
        new_session = chat_service.create_session(
            user_id, 
            session_data.title
        )
        
        return ChatSessionResponse(
            id=new_session.id,
            session_id=new_session.session_id,
            title=new_session.title,
            created_at=new_session.created_at,
            updated_at=new_session.updated_at,
            is_active=new_session.is_active
        )
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

# Get session by ID -- API-4
@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    session_data: ChatSessionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Update a chat session."""
    try:
        user_id = current_user["id"]
        chat_service = ChatService(session)
        updated_session = chat_service.update_session(
            session_id, 
            user_id, 
            session_data.model_dump(exclude_unset=True)
        )
        
        if not updated_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return ChatSessionResponse(
            id=updated_session.id,
            session_id=updated_session.session_id,
            title=updated_session.title,
            created_at=updated_session.created_at,
            updated_at=updated_session.updated_at,
            is_active=updated_session.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session")

# Delete sesstion - API-5
@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Delete a chat session."""
    try:
        user_id = current_user["id"]
        chat_service = ChatService(session)
        success = chat_service.delete_session(session_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

#  Get session history - API-6
@router.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_session_history(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session),
    limit: Optional[int] = None
):
    """Get chat history for a session."""
    try:
        user_id = current_user["id"]
        chat_service = ChatService(session)
        
        # Verify session ownership
        chat_session = chat_service.get_session(session_id, user_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages
        messages = chat_service.get_session_messages(session_id, limit)
        
        from app.schemas import ChatHistoryEntry
        history_entries = [
            ChatHistoryEntry(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at
            )
            for msg in messages
        ]
        
        return ChatHistoryResponse(
            session_id=session_id,
            title=chat_session.title,
            messages=history_entries,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session history")

# Clear session messages - API-7
@router.delete("/sessions/{session_id}/messages")
async def clear_session_messages(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Clear all messages in a session."""
    try:
        user_id = current_user["id"]
        chat_service = ChatService(session)
        success = chat_service.clear_session_messages(session_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session messages cleared successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing session messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear messages")

# Get session title - API-8
@router.post("/sessions/{session_id}/title")
async def generate_session_title(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Generate a title for the session based on conversation."""
    try:
        user_id = current_user["id"]
        chat_service = ChatService(session)
        
        # Verify session ownership
        chat_session = chat_service.get_session(session_id, user_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get recent messages
        messages = chat_service.get_session_messages(session_id, limit=10)
        
        if not messages:
            raise HTTPException(status_code=400, detail="No messages to generate title from")
        
        # Generate title using LLM
        try:
            llm = get_non_streaming_llm()
            
            # Create context from messages
            context = "\n".join([
                f"{msg.role}: {msg.content[:200]}..." 
                for msg in messages[:5]  # Use first 5 messages
            ])
            
            prompt = f"""Based on this conversation, generate a short, descriptive title (max 50 characters):

{context}

Title:"""
            
            response = await llm.ainvoke(prompt)
            title = response.content.strip().replace('"', '').replace("'", "")[:50]
            
            # Update session title
            updated_session = chat_service.update_session(
                session_id, 
                user_id, 
                {"title": title}
            )
            
            return {
                "title": title,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            # Fallback to a generic title
            fallback_title = f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            chat_service.update_session(
                session_id, 
                user_id, 
                {"title": fallback_title}
            )
            return {
                "title": fallback_title,
                "session_id": session_id
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate title: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate title")

# Health and debug endpoints

# Cluster health - API-9
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        from app.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Test LLM connection
        llm = get_non_streaming_llm()
        await llm.ainvoke("Hello")
        
        return {
            "status": "healthy",
            "database": "connected",
            "llm": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )
# Debug endpoints - API-10
@router.get("/debug/schema")
async def debug_schema(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Debug endpoint to check database schema."""
    try:
        from app.database import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        schema_info = {}
        for table in tables:
            columns = inspector.get_columns(table)
            schema_info[table] = [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"]
                }
                for col in columns
            ]
        
        return {
            "tables": tables,
            "schema": schema_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Schema debug failed: {e}")
        raise HTTPException(status_code=500, detail=f"Schema check failed: {str(e)}")

# Debug and test -API-11
@router.get("/debug/test-llm")
async def debug_test_llm(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Debug endpoint to test LLM connection."""
    try:
        llm = get_non_streaming_llm()
        response = await llm.ainvoke("Respond with 'LLM is working correctly'")
        
        return {
            "status": "success",
            "response": response.content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"LLM test failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM test failed: {str(e)}")