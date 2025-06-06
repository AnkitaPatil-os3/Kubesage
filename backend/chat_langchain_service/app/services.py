from app.models import ChatSession, ChatMessage, K8sAnalysisReference
from app.schemas import MessageCreate, MessageResponse, ChatSessionCreate
from app.cache import cache_get, cache_set, get_session_key, get_messages_key
from app.logger import logger
from app.config import settings
from app.queue import publish_session_created, publish_message_created
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy import delete
import httpx
import openai
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException, Path, Query, Depends, status
import requests
import urllib3
from app.langchain_service import process_with_langchain, create_memory_from_messages
 
# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
# Initialize OpenAI client at module level
try:
    import openai
    openai_client = openai.OpenAI(
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY
    )
    logger.info(f"OpenAI client initialized with base URL: {settings.OPENAI_BASE_URL}")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")
    openai_client = None
async def get_ai_response(messages):
    """Get AI response using LangChain"""
    try:
        # Convert OpenAI-style messages to LangChain memory
        memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
        
        # Add system message to memory if present
        system_content = None
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user":
                memory.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                memory.chat_memory.add_ai_message(msg["content"])
        
        # Get the last user message
        user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), "")
        
        # Process with LangChain
        result = await process_with_langchain(user_message, memory, stream=False)
        
        if result["type"] == "non_streaming":
            return result["result"]
        else:
            return "I'm sorry, there was an error processing your request."
    except Exception as e:
        logger.error(f"Error getting AI response with LangChain: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return "I'm sorry, I encountered an error processing your request."
        
# Custom streaming callback handler
class StreamingCallbackHandler:
    """Callback handler for streaming LLM responses."""
    
    def __init__(self):
        self.tokens_queue = asyncio.Queue()
        self.full_response = []
    
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Put the new token in the queue."""
        self.full_response.append(token)
        await self.tokens_queue.put(token)
    
    async def on_llm_end(self, response, **kwargs) -> None:
        """Signal the end of the LLM response."""
        await self.tokens_queue.put(None)  # Signal end of stream
    
    async def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Handle LLM errors."""
        await self.tokens_queue.put(f"Error: {str(error)}")
        await self.tokens_queue.put(None)  # Signal end of stream
    
    def get_full_response(self):
        """Get the complete response as a string."""
        return "".join(self.full_response)
 
def get_streaming_llm(streaming_handler):
    """Get an LLM instance configured for streaming"""
    return openai_client  # Changed from client to openai_client
 
async def create_chat_session(
    db: Session,
    user_id: int,
    session_data: ChatSessionCreate
) -> ChatSession:
    """Create a new chat session"""
    new_session = ChatSession(
        user_id=user_id,
        title=session_data.title
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    # Publish event
    session_dict = {
        "id": new_session.id,
        "session_id": new_session.session_id,
        "user_id": new_session.user_id,
        "title": new_session.title,
        "created_at": new_session.created_at.isoformat()
    }
    publish_session_created(session_dict)
    
    return new_session
 
async def get_chat_session(
    db: Session,
    session_id: str,
    user_id: Optional[int] = None
) -> Optional[ChatSession]:
    """Get a chat session by session_id"""
    if db is None:
        # This is for the cookie-based session check
        # Create a temporary session
        from app.database import engine
        from sqlmodel import Session as SQLModelSession
        db = SQLModelSession(engine)
        try:
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            return db.exec(query).first()
        finally:
            db.close()
    
    query = select(ChatSession).where(ChatSession.session_id == session_id)
    
    # If user_id is provided, verify ownership
    if user_id is not None:
        query = query.where(ChatSession.user_id == user_id)
        
    return db.exec(query).first()
 
async def update_session_title(
    db: Session,
    session: ChatSession,
    first_message: str
) -> None:
    """Generate and update the title for a chat session"""
    # Generate a title based on the first message (simplified)
    title_length = min(len(first_message), 50)
    title = first_message[:title_length] + ("..." if len(first_message) > 50 else "")
    
    # Update the session
    session.title = title
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.debug(f"Session title updated to: {session.title}")
 
async def delete_chat_session(
    db: Session,
    session: ChatSession,
    permanent: bool = False
) -> None:
    """Delete a chat session"""
    if permanent:
        # Hard delete - remove from database
        # First delete all messages associated with the session
        db.exec(delete(ChatMessage).where(ChatMessage.session_id == session.session_id))
        # Then delete the session
        db.delete(session)
    else:
        # Soft delete - mark as inactive
        session.is_active = False
        session.updated_at = datetime.utcnow()
        db.add(session)
    
    db.commit()
 
async def list_user_chat_sessions(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True
) -> List[ChatSession]:
    """List all chat sessions for a user"""
    query = select(ChatSession).where(ChatSession.user_id == user_id)
    
    if active_only:
        query = query.where(ChatSession.is_active == True)
        
    query = query.order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit)
    
    return db.exec(query).all()
 
async def add_chat_message(
    db: Session,
    session: ChatSession,
    role: str,
    content: str
) -> ChatMessage:
    """Add a new message to a chat session"""
    new_message = ChatMessage(
        session_id=session.session_id,
        role=role,
        content=content
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # Update session's updated_at timestamp
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()
    
    # Publish event
    message_dict = {
        "id": new_message.id,
        "session_id": new_message.session_id,
        "role": new_message.role,
        "content": new_message.content,
        "created_at": new_message.created_at.isoformat()
    }
    publish_message_created(message_dict)
    
    return new_message
 
async def get_chat_history(
    db: Session,
    session_id: str,
    user_id: Optional[int] = None,
    limit: int = 100
) -> List[ChatMessage]:
    """Get chat history for a session with optional limit"""
    
    # If user_id is provided, verify session ownership first
    if user_id is not None:
        session = await get_chat_session(db, session_id, user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this session"
            )
    
    # Check cache first
    cache_key = get_messages_key(session_id)
    cached_messages = cache_get(cache_key)
    if cached_messages:
        # Apply limit to cached messages if needed
        return cached_messages[:limit] if limit < len(cached_messages) else cached_messages
    
    # Get from database if not in cache
    query = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    
    # Apply limit to query
    query = query.limit(limit)
    
    # Retrieve messages from the database
    messages = db.exec(query).all()
    
    # Update cache with the retrieved messages
    if messages:
        cache_set(cache_key, messages, 3600)
    
    logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
    return messages
 
# Update the process_chat_message function to use LangChain for streaming
async def process_chat_message(
    db: Session,
    user_id: int,
    message_data: MessageCreate,
    token: str
) -> MessageResponse:
    """Process a chat message and get AI response"""
    try:
        session_id = message_data.session_id
        session = None
        if session_id:
            # Get existing session
            session = await get_chat_session(db, session_id, user_id)
            if not session:
                # Create new session if provided ID doesn't exist
                session_create = ChatSessionCreate(title="New Chat")
                session = await create_chat_session(db, user_id, session_create)
                session_id = session.session_id
        else:
            # Create new session
            session_create = ChatSessionCreate(title="New Chat")
            session = await create_chat_session(db, user_id, session_create)
            session_id = session.session_id
        
        # For new sessions, get K8s analysis first
        is_new_session = not await get_chat_history(db, session_id)
        analysis_output = ""
        if is_new_session:
            analysis_output = await get_k8s_analysis(user_id, token)
        
        # Build the user content
        if is_new_session and analysis_output:
            user_content = f"Analysis results:\n{analysis_output}\n\nUser question: {message_data.content}"
        else:
            user_content = message_data.content
        
        # Add user message to history
        await add_chat_message(db, session, "user", user_content)
        
        # Get chat history
        messages = await get_chat_history(db, session_id)
        
        # Create memory from messages
        memory = await create_memory_from_messages(messages)
        
        # Process with LangChain
        result = await process_with_langchain(message_data.content, memory, stream=False)
        
        if result["type"] == "non_streaming":
            assistant_message = result["result"]
        else:
            assistant_message = "I'm sorry, there was an error processing your request."
        
        # Add assistant message to history
        assistant_chat_msg = await add_chat_message(db, session, "assistant", assistant_message)
        
        # Update session title if it's a new session
        if is_new_session:
            await update_session_title(db, session, message_data.content)
        
        return MessageResponse(
            role="assistant",
            content=assistant_message,
            session_id=session_id,
            created_at=assistant_chat_msg.created_at
        )
    except Exception as e:
        logger.error(f"Error in process_chat_message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your message."
        )
        
async def get_k8s_analysis(user_id: int, token: str = None) -> str:
    """Get K8s analysis from K8sGPT service"""
    if not token:
        logger.warning("No token provided for K8s analysis")
        return "No authentication token provided for Kubernetes analysis."
    
    url = f"{settings.KUBECONFIG_SERVICE_URL}/kubeconfig/analyze"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Define the payload with necessary data
    payload = {
        "user_id": user_id,
        "anonymize": False,
        "backend": "default",
        "custom_analysis": False,
        "explain": True,
        "language": "english",
        "namespace": "default",
        "no_cache": True,
        "output": "json"
    }
    
    try:
        # Use requests.post to make the API call
        response = requests.post(url, headers=headers, verify=False, json=payload)
        logger.debug(f"K8s analysis response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                # Format the analysis results as a string
                if isinstance(result, dict):
                    return json.dumps(result, indent=2)
                return str(result)
            except ValueError:
                logger.error("Invalid JSON response received.")
                return "Invalid JSON response from Kubernetes analysis service."
        else:
            logger.error(f"Failed to get K8s analysis: {response.status_code} - {response.text}")
            return f"Error retrieving Kubernetes analysis: {response.status_code}"
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error while connecting to Kubeconfig service: {str(e)}")
        return "HTTP error connecting to Kubernetes analysis service."
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while connecting to Kubeconfig service: {str(e)}")
        return "Request error connecting to Kubernetes analysis service."
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return "An unexpected error occurred while fetching Kubernetes analysis."
 
async def validate_session_access(db: Session, session_id: str, user_id: int) -> ChatSession:
    """Validate that user has access to the session"""
    session = await get_chat_session(db, session_id, user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied"
        )
    return session
 
 