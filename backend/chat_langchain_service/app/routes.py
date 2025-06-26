from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
import json
from app.config import settings

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
    collect_all_k8s_errors, process_with_llm, execute_kubectl_command,
    perform_cluster_health_check, get_cluster_summary, create_memory_from_messages,
    KUBERNETES_SERVICE_VERSION
)
from app.services import ChatService, MessageService
from app.logger import logger

router = APIRouter()

# Chat endpoint - API-1 (Simplified without agents)
@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Main chat endpoint with K8s error collection and direct LLM processing."""
    try:
        user_id = current_user["id"]
        logger.info(f"💬 Chat request from user {user_id}: {request.message[:100]}...")
        
        # Initialize services
        chat_service = ChatService(session)
        message_service = MessageService(session)
        
        # Validate message
        if not request.message or not request.message.strip():
            raise HTTPException(
                status_code=400, 
                detail="Message cannot be empty"
            )
        
        clean_message = request.message.strip()
        if len(clean_message) > settings.MAX_MESSAGE_LENGTH:
            clean_message = clean_message[:settings.MAX_MESSAGE_LENGTH] + "... (message truncated)"
        
        # Get or create session
        if request.session_id:
            chat_session = chat_service.get_session(request.session_id, user_id)
            if not chat_session:
                chat_session = chat_service.create_session(user_id, "Kubernetes Chat")
        else:
            chat_session = chat_service.create_session(user_id, "Kubernetes Chat")
        
        # Check if this is a new session (no messages yet)
        existing_messages = chat_service.get_session_messages(chat_session.session_id)
        is_new_session = len(existing_messages) == 0
        
        # Collect K8s errors for new sessions or when explicitly requested
        k8s_errors = None
        if is_new_session or "error" in clean_message.lower() or "issue" in clean_message.lower():
            logger.info("🔍 Collecting K8s errors for context...")
            k8s_errors = collect_all_k8s_errors()
        
        # Save user message
        try:
            user_message = chat_service.add_message(
                chat_session.session_id, 
                "user", 
                clean_message
            )
            logger.info(f"💾 Saved user message: {user_message.id}")
        except Exception as e:
            logger.error(f"❌ Error saving user message: {e}")
            # Continue without saving if there's a DB error
        
        # Get conversation history for context
        conversation_history = []
        try:
            messages = chat_service.get_session_messages(chat_session.session_id)
            conversation_history = create_memory_from_messages([
                {"role": msg.role, "content": msg.content}
                for msg in messages[-10:]  # Last 10 messages for context
            ])
            logger.info(f"📚 Retrieved {len(conversation_history)} messages for context")
        except Exception as e:
            logger.error(f"❌ Error getting conversation history: {e}")
        
        if request.stream:
            # Streaming response (simplified)
            async def generate_stream():
                try:
                    logger.info("🌊 Starting streaming response...")
                    
                    # Process with LLM
                    result = await process_with_llm(
                        clean_message,
                        k8s_errors=k8s_errors,
                        conversation_history=conversation_history
                    )
                    
                    if result["success"]:
                        assistant_message = result["response"]
                        
                        # Stream the response word by word for better UX
                        words = assistant_message.split()
                        for i, word in enumerate(words):
                            if i == 0:
                                yield f"data: {json.dumps({'token': word, 'done': False})}\n\n"
                            else:
                                yield f"data: {json.dumps({'token': ' ' + word, 'done': False})}\n\n"
                            
                            # Small delay for streaming effect
                            import asyncio
                            await asyncio.sleep(0.05)
                        
                        # Save assistant response
                        try:
                            chat_service.add_message(
                                chat_session.session_id,
                                "assistant", 
                                assistant_message
                            )
                            logger.info("💾 Saved streaming assistant response")
                        except Exception as e:
                            logger.error(f"❌ Error saving streaming response: {e}")
                        
                        # Send completion signal
                        yield f"data: {json.dumps({'token': None, 'done': True, 'session_id': chat_session.session_id})}\n\n"
                    
                    else:
                        # Handle error case
                        error_msg = result.get("response", result.get("error", "Unknown error occurred"))
                        yield f"data: {json.dumps({'token': error_msg, 'done': False})}\n\n"
                        yield f"data: {json.dumps({'token': None, 'done': True, 'session_id': chat_session.session_id, 'error': True})}\n\n"
                    
                except Exception as e:
                    logger.error(f"💥 Critical error in streaming response: {e}")
                    error_response = f"❌ **Critical Error:** {str(e)}\n\n💡 **Please try again** or contact support if the issue persists."
                    yield f"data: {json.dumps({'token': error_response, 'done': False})}\n\n"
                    yield f"data: {json.dumps({'token': None, 'done': True, 'error': True})}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "X-Kubernetes-Service": KUBERNETES_SERVICE_VERSION,
                }
            )
        
        else:
            # Non-streaming response
            try:
                logger.info("📝 Processing non-streaming response...")
                
                # Process with LLM
                result = await process_with_llm(
                    clean_message,
                    k8s_errors=k8s_errors,
                    conversation_history=conversation_history
                )
                
                if result["success"]:
                    assistant_message = result["response"]
                    execution_time = result.get("execution_time", 0)
                    
                    logger.info(f"✅ LLM completed successfully in {execution_time:.2f}s")
                    
                    # Save assistant response
                    try:
                        chat_service.add_message(
                            chat_session.session_id,
                            "assistant", 
                            assistant_message
                        )
                        logger.info("💾 Saved non-streaming assistant response")
                    except Exception as e:
                        logger.error(f"❌ Error saving non-streaming response: {e}")
                    
                    return MessageResponse(
                        role="assistant",
                        content=assistant_message,
                        session_id=chat_session.session_id,
                        created_at=datetime.utcnow()
                    )
                else:
                    # Handle error case
                    error_message = result.get("response", result.get("error", "Unknown error"))
                    logger.error(f"❌ LLM processing failed: {error_message}")
                    
                    return MessageResponse(
                        role="assistant",
                        content=error_message,
                        session_id=chat_session.session_id,
                        created_at=datetime.utcnow()
                    )
                
            except Exception as e:
                logger.error(f"💥 Critical error in non-streaming response: {e}")
                error_response = f"❌ **Critical Error:** {str(e)}\n\n💡 **Troubleshooting:**\n- Check if kubectl is configured\n- Verify cluster connectivity\n- Try a simpler command first"
                
                return MessageResponse(
                    role="assistant",
                    content=error_response,
                    session_id=chat_session.session_id,
                    created_at=datetime.utcnow()
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Critical error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )



# Execute kubectl command - API-2
@router.post("/execute")
async def execute_kubectl(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Execute kubectl commands directly."""
    try:
        command = request.get("command", "").strip()
        if not command:
            raise HTTPException(status_code=400, detail="Command is required")
        
        logger.info(f"🚀 Direct kubectl execution by user {current_user['id']}: {command}")
        
        # Execute the command
        result = execute_kubectl_command(command)
        
        return {
            "command": f"kubectl {command}",
            "output": result,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user["id"],
            "success": not result.startswith("Error") and not result.startswith("kubectl error")
        }
        
    except Exception as e:
        logger.error(f"Direct kubectl execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")

# Get chat sessions - API-3
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

# Create chat session - API-4
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
            session_data.title or "Kubernetes Chat"
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

# Update session - API-5
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

# Delete session - API-6
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

# Get session history - API-7
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

# Clear session messages - API-8
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

# Generate session title - API-9
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
        messages = chat_service.get_session_messages(session_id, limit=5)
        
        if not messages:
            raise HTTPException(status_code=400, detail="No messages to generate title from")
        
        # Generate title using first user message
        try:
            first_user_message = next((msg.content for msg in messages if msg.role == "user"), "")
            
            if first_user_message:
                # Extract key terms for title
                words = first_user_message.lower().split()
                k8s_terms = ["pod", "deployment", "service", "node", "namespace", "cluster", "kubectl", "error", "issue", "troubleshoot"]
                found_terms = [word for word in words if word in k8s_terms]
                
                if found_terms:
                    title = f"K8s {' '.join(found_terms[:3]).title()}"
                else:
                    title = f"Kubernetes Chat {datetime.utcnow().strftime('%m-%d %H:%M')}"
            else:
                title = f"Kubernetes Chat {datetime.utcnow().strftime('%m-%d %H:%M')}"
            
            # Update session title
            updated_session = chat_service.update_session(
                session_id, 
                user_id, 
                {"title": title[:50]}  # Limit title length
            )
            
            return {
                "title": title[:50],
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            # Fallback to a generic title
            fallback_title = f"Kubernetes Chat {datetime.utcnow().strftime('%m-%d %H:%M')}"
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

# Get cluster status - API-10
@router.get("/cluster/status")
async def get_cluster_status(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Get comprehensive cluster status and health information."""
    try:
        # Get cluster health
        health_info = perform_cluster_health_check()
        
        # Get cluster summary
        cluster_summary = get_cluster_summary()
        
        # Get recent errors
        recent_errors = collect_all_k8s_errors()
        
        return {
            "health": health_info,
            "summary": cluster_summary,
            "recent_errors": {
                "total_errors": recent_errors.get("summary", {}).get("total_errors", 0),
                "critical_events": len([e for e in recent_errors.get("events", []) if e.get("type") == "Error"]),
                "pod_issues": len(recent_errors.get("pods", [])),
                "deployment_issues": len(recent_errors.get("deployments", [])),
                "node_issues": len(recent_errors.get("nodes", []))
            },
            "service_version": KUBERNETES_SERVICE_VERSION,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cluster status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cluster status: {str(e)}")

# Get all errors - API-11
@router.get("/cluster/errors")
async def get_cluster_errors(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Get all current cluster errors."""
    try:
        logger.info(f"🔍 User {current_user['id']} requesting cluster errors")
        
        errors = collect_all_k8s_errors()
        
        return {
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
            "collected_by": current_user["id"]
        }
        
    except Exception as e:
        logger.error(f"Error collecting cluster errors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect cluster errors: {str(e)}")

# Health check - API-12
@router.get("/health")
async def health_check():
    """Enhanced health check endpoint with Kubernetes cluster status."""
    try:
        # Test database connection
        from app.database import engine
        from sqlalchemy import text
        
        db_status = "disconnected"
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Test LLM connection
        llm_status = "disconnected"
        try:
            from app.langchain_service import get_llm
            llm = get_llm()
            # Quick test without actual API call to save costs
            llm_status = "configured"
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
        
        # Perform Kubernetes health check
        k8s_health = perform_cluster_health_check()
        
        # Determine overall status
        overall_status = "healthy"
        if db_status != "connected":
            overall_status = "degraded"
        if not k8s_health.get("cluster_accessible", False):
            overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": KUBERNETES_SERVICE_VERSION,
            "components": {
                "database": db_status,
                "llm": llm_status,
                "kubernetes": {
                    "client_available": k8s_health.get("kubernetes_client", False),
                    "kubectl_available": k8s_health.get("kubectl_available", False),
                    "cluster_accessible": k8s_health.get("cluster_accessible", False),
                    "cluster_version": k8s_health.get("cluster_version"),
                    "node_count": k8s_health.get("node_count", 0),
                    "namespace_count": k8s_health.get("namespace_count", 0)
                }
            },
            "capabilities": [
                "k8s_error_collection",
                "direct_llm_processing",
                "kubectl_command_execution",
                "conversation_history",
                "cluster_monitoring"
            ],
            "errors": k8s_health.get("error_messages", [])
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )

# Service information - API-13
@router.get("/info")
async def service_info():
    """Get service information and capabilities."""
    return {
        "service_name": "KubeSage Simplified Chat Service",
        "version": KUBERNETES_SERVICE_VERSION,
        "description": "AI-powered Kubernetes assistant with error collection and direct LLM processing",
        "capabilities": {
            "chat": {
                "streaming": True,
                "non_streaming": True,
                "conversation_memory": True,
                "session_management": True,
                "k8s_error_context": True
            },
            "kubernetes": {
                "error_collection": True,
                "kubectl_execution": True,
                "cluster_monitoring": True,
                "multi_namespace_support": True
            },
            "ai_features": {
                "direct_llm_processing": True,
                "context_aware_responses": True,
                "error_analysis": True,
                "troubleshooting_guidance": True
            }
        },
        "workflow": {
            "new_chat": "Collect all K8s errors → Add to user message → Send to LLM",
            "existing_chat": "Use conversation history → Send to LLM",
            "storage": "Store only user messages and LLM responses"
        },
        "endpoints": {
            "chat": "/chat",
            "execute": "/execute",
            "sessions": "/sessions",
            "cluster_status": "/cluster/status",
            "cluster_errors": "/cluster/errors",
            "health": "/health",
            "info": "/info"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
