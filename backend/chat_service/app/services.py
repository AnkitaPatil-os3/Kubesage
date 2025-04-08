from app.models import ChatSession, ChatMessage, K8sAnalysisReference
from app.schemas import MessageCreate, MessageResponse, ChatSessionCreate
from app.cache import cache_get, cache_set, get_session_key, get_messages_key
from app.logger import logger
from app.config import settings
from app.queue import publish_session_created, publish_message_created
from app.models import ChatMessage  # Ensure this is the correct import for your models
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy import delete  # Import delete function
import httpx
import openai
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException, Path, Query, Depends, status

import requests


# Initialize OpenAI client
client = openai.OpenAI(
    base_url=settings.OPENAI_BASE_URL,
    api_key=settings.OPENAI_API_KEY,
    timeout=120,
    max_retries=3
)

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
    print(f"Session title updated to: {session.title}")


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
    user_id: Optional[int] = None
) -> List[ChatMessage]:
    """Get chat history for a session"""
    # Check cache first
    cache_key = get_messages_key(session_id)
    cached_messages = cache_get(cache_key)
    
    if cached_messages:
        return cached_messages
    
    # Get from database if not in cache
    query = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)

    # If user_id is provided, verify session ownership
    if user_id is not None:
        session = await get_chat_session(db, session_id, user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this session"
            )
    
    # Retrieve messages from the database
    messages = db.exec(query).all()
    
    # Update cache
    if messages:
        message_list = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
        cache_set(cache_key, message_list, 3600)
    
    return messages

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
        # Build messages array for OpenAI
        openai_messages = [
            {
                "role": "system", 
                "content": "You are a helpful Kubernetes assistant. Use the analysis results and previous context to answer questions. Please respond in Markdown format for all outputs."

            }
        ]
        # Add history to messages
        for msg in messages:
            openai_messages.append({"role": msg.role, "content": msg.content})
        # Get AI response
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=openai_messages,
                max_tokens = 2000
            )
            assistant_message = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            assistant_message = "I'm sorry, I encountered an error processing your request."
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
 
async def get_k8s_analysis(user_id: int, token: str) -> dict:
    """Get K8s analysis from K8sGPT service"""
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
        # Add other fields as required by the /analyze endpoint
    }
    try:
        # Use requests.post to make the API call
        response = requests.post(url, headers=headers, verify=False)
        print(f"K8s analysis response: {response}")
        if response.status_code == 200:
            try:
                result = response.json()
                return result
            except ValueError:
                logger.error("Invalid JSON response received.")
                return {"error": "Invalid JSON response from Kubernetes analysis service."}
        else:
            logger.error(f"Failed to get K8s analysis: {response.status_code} - {response.text}")
            return {"error": f"Error retrieving Kubernetes analysis: {response.status_code}"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error while connecting to Kubeconfig service: {str(e)}")
        return {"error": "HTTP error connecting to Kubernetes analysis service."}
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while connecting to Kubeconfig service: {str(e)}")
        return {"error": "Request error connecting to Kubernetes analysis service."}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": "An unexpected error occurred while fetching Kubernetes analysis."}
