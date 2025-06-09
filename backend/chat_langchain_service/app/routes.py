from fastapi import Depends, HTTPException, status, Header, Cookie, Response
from typing import Annotated, Optional, AsyncIterator
from app.dependencies import get_db_session, get_current_user_dependency
from sqlmodel import Session
from app.database import get_session
from app.auth import get_current_user
from app.schemas import UserInfo
import json
import asyncio
from app.langchain_service import process_with_langchain, create_memory_from_messages, stream_langchain_response

# Define common dependencies
SessionDep = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
from app.schemas import (
    MessageCreate, 
    MessageResponse, 
    ChatHistoryResponse, 
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatSessionList,
    ChatHistoryEntry,
    ChatRequest
)
from app.services import (
    create_chat_session,
    process_chat_message,
    get_chat_session,
    get_chat_history,
    list_user_chat_sessions,
    update_session_title,
    delete_chat_session,
    get_k8s_analysis,
    get_streaming_llm,
    StreamingCallbackHandler,
    add_chat_message  # Add this line to import the missing function
)
from fastapi import APIRouter, HTTPException, status, Query, Path, Body
from fastapi.responses import StreamingResponse
from app.dependencies import SessionDep, CurrentUser
from datetime import datetime
from app.logger import logger

router = APIRouter(prefix="/chat", tags=["chat"])
#   ----Chat section ----
@router.post("/", response_model=MessageResponse, 
            summary="Send Chat Message", 
            description="Sends a message to the chat service and returns the AI response")
async def chat(
    message: MessageCreate, 
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
    authorization: str = Header(None),
    stream: bool = Query(False, description="Whether to stream the response")
):
    logger.info(f"Session ID: {id(db)}")
    token = authorization.split(" ")[1] if authorization else None
    
    try:
        session_id = message.session_id
        session = None
        is_new_session = False
        
        # Handle session logic
        if session_id:
            # Try to get existing session
            session = await get_chat_session(db, session_id, current_user.id)
            if not session:
                # If session_id provided but doesn't exist, return error
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat session {session_id} not found"
                )
            # Check if this is actually a new session (no messages yet)
            existing_messages = await get_chat_history(db, session_id)
            is_new_session = len(existing_messages) == 0
        else:
            # Create new session only when no session_id provided
            session_create = ChatSessionCreate(title="New Chat")
            session = await create_chat_session(db, current_user.id, session_create)
            session_id = session.session_id
            is_new_session = True
        
        # For new sessions, get K8s analysis first
        analysis_output = ""
        if is_new_session:
            analysis_output = await get_k8s_analysis(current_user.id, token)
        
        # Build the user content
        if is_new_session and analysis_output:
            user_content = f"Analysis results:\n{analysis_output}\n\nUser question: {message.content}"
        else:
            user_content = message.content
        
        # Add user message to history
        await add_chat_message(db, session, "user", user_content)
        
        # Get chat history AFTER adding the user message
        messages = await get_chat_history(db, session_id)
        
        # Create memory from messages
        memory = await create_memory_from_messages(messages)
        
        if stream:
            # Process with LangChain (streaming)
            langchain_result = await process_with_langchain(
                user_message=message.content,
                memory=memory,
                stream=True
            )
            
            # Set up streaming response
            async def stream_response() -> AsyncIterator[str]:
                try:
                    streaming_handler = langchain_result["streaming_handler"]
                    
                    # Stream tokens as they come
                    async for token in stream_langchain_response(streaming_handler):
                        yield f"data: {json.dumps({'token': token, 'session_id': session_id})}\n\n"
                    
                    # Get the full response at the end
                    full_response = streaming_handler.get_full_response()
                    
                    # Store the assistant's response
                    await add_chat_message(db, session, "assistant", full_response)
                    
                    # Update session title if it's a new session
                    if is_new_session:
                        await update_session_title(db, session, message.content)
                    
                    # Send a final message indicating the stream is complete
                    yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Error in streaming response: {str(e)}")
                    yield f"data: {json.dumps({'error': str(e), 'session_id': session_id})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
            
            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream"
            )
        else:
            # Process with LangChain (non-streaming)
            langchain_result = await process_with_langchain(
                user_message=message.content,
                memory=memory,
                stream=False
            )
            
            # Get the result
            assistant_message = langchain_result["result"]
            
            # Store the assistant's response
            assistant_chat_msg = await add_chat_message(db, session, "assistant", assistant_message)
            
            # Update session title if it's a new session
            if is_new_session:
                await update_session_title(db, session, message.content)
            
            # Return the response
            return MessageResponse(
                role="assistant",
                content=assistant_message,
                session_id=session_id,
                created_at=assistant_chat_msg.created_at
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your message: {str(e)}"
        )
# Add a dedicated streaming endpoint
@router.post("/stream", 
            summary="Stream Chat Message", 
            description="Sends a message to the chat service and streams the AI response")
async def stream_chat(
    message: MessageCreate, 
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
    authorization: str = Header(None)
):
    """
    Sends a message to the chat service and streams the AI response.
    
    - Accepts a message from the user
    - Processes the message through the LangChain AI backend
    - Streams the AI response tokens as they are generated
    
    Parameters:
        message: The message content and session information
        authorization: Bearer token for authentication
    
    Returns:
        StreamingResponse: A streaming response with the AI's tokens
    """
    # Reuse the chat endpoint with stream=True
    return await chat(message, db, current_user, authorization, stream=True)

async def stream_chat_response(
    message: str, 
    session_id: str, 
    user_id: int,
    db: Session,
    token: str = None
) -> AsyncIterator[str]:
    """Generate a streaming response for the chat message."""
    # Create a streaming callback handler
    streaming_handler = StreamingCallbackHandler()
    
    # Get chat history
    messages = await get_chat_history(db, session_id, user_id)
    
    # For new sessions, get K8s analysis first
    is_new_session = len(messages) == 0
    analysis_output = ""
    
    if is_new_session:
        analysis_output = await get_k8s_analysis(user_id, token)
    
    # Build the user content
    if is_new_session and analysis_output:
        user_content = f"Analysis results:\n{analysis_output}\n\nUser question: {message}"
    else:
        user_content = message
    
    # Add user message to history
    from app.models import ChatMessage
    session = await get_chat_session(db, session_id, user_id)
    from app.services import add_chat_message
    await add_chat_message(db, session, "user", user_content)
    
    # Get updated chat history
    messages = await get_chat_history(db, session_id, user_id)
    
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
    
    # Create LLM with streaming
    llm = get_streaming_llm(streaming_handler)
    
    # Start the LLM in a background task
    from app.config import settings
    import openai
    
    task = asyncio.create_task(
        llm.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=openai_messages,
            stream=True
        )
    )
    
    # Stream tokens as they come
    while True:
        try:
            # Get the next token from the queue
            token = await asyncio.wait_for(streaming_handler.tokens_queue.get(), timeout=30.0)
            
            # If token is None, we've reached the end of the stream
            if token is None:
                # Store the complete response in the database
                full_response = streaming_handler.get_full_response()
                await add_chat_message(db, session, "assistant", full_response)
                
                # Update session title if it's a new session
                if is_new_session:
                    await update_session_title(db, session, message)
                break
                
            # Send the token in SSE format
            yield f"data: {json.dumps({'token': token, 'session_id': session_id})}\n\n"
                        
        except asyncio.TimeoutError:
            # If we don't get a token for 30 seconds, assume something went wrong
            yield f"data: {json.dumps({'token': '...', 'error': 'Timeout waiting for response', 'session_id': session_id})}\n\n"
            break
        except Exception as e:
            # Handle any other errors
            yield f"data: {json.dumps({'token': '...', 'error': str(e), 'session_id': session_id})}\n\n"
            break
    
    # Send a final message indicating the stream is complete
    yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
    
    # Make sure the task completes
    try:
        await task
    except Exception as e:
        logger.error(f"Error in streaming task: {str(e)}")

@router.get("/history/{session_id}", response_model=ChatHistoryResponse,
           summary="Get Chat History", 
           description="Retrieves the message history for a specific chat session")
async def get_chat_session_history(
    session_id: str, 
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages to return"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
    ):
    """
    Retrieves the message history for a specific chat session.
    
    - Verifies the session belongs to the current user
    - Retrieves messages with pagination support
    - Returns the session details and message history
    
    Parameters:
        session_id: Unique identifier for the chat session
        limit: Maximum number of messages to return (1-100)
    
    Returns:
        ChatHistoryResponse: Session details and message history
    
    Raises:
        HTTPException: 404 if session not found
        HTTPException: 500 if retrieval fails
    """
    try:
        session = await get_chat_session(db, session_id, current_user.id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
        # Get messages with limit
        messages = await get_chat_history(db, session_id, current_user.id, limit=limit)
        return ChatHistoryResponse(
            session_id=session.session_id,
            title=session.title,
            messages=[ChatHistoryEntry(role=msg.role, content=msg.content, created_at=msg.created_at) for msg in messages],
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history. Please try again."
        )

@router.get("/sessions", response_model=ChatSessionList,
           summary="List Chat Sessions", 
           description="Lists all chat sessions for the current user")
async def list_chat_sessions(
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of sessions to return"),
    active_only: bool = Query(True, description="Return only active sessions"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
    ):
    """
    Lists all chat sessions for the current user.
    
    - Retrieves chat sessions with pagination support
    - Can filter for active sessions only
    - Returns session metadata including creation and update times
    
    Parameters:
        skip: Number of sessions to skip (for pagination)
        limit: Maximum number of sessions to return
        active_only: Whether to return only active sessions
    
    Returns:
        ChatSessionList: List of chat session metadata
    
    Raises:
        HTTPException: 500 if retrieval fails
    """
    try:
        # Add a smaller default limit to improve performance
        if limit > 50:
            limit = 50
        sessions = await list_user_chat_sessions(db, current_user.id, skip, limit, active_only)
        return ChatSessionList(
            sessions=[
                ChatSessionResponse(
                    id=session.id,
                    session_id=session.session_id,
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    is_active=session.is_active
                ) for session in sessions
            ]
        )
    except Exception as e:
        logger.error(f"Error listing chat sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions. Please try again."
        )

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED,
            summary="Create Chat Session", 
            description="Creates a new chat session")
async def create_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Creates a new chat session.
    
    - Creates a new chat session with the provided title
    - Associates the session with the current user
    - Returns the created session details
    
    Parameters:
        session_data: Contains the title for the new session
    
    Returns:
        ChatSessionResponse: The created chat session details
    
    Raises:
        HTTPException: If session creation fails
    """
    session = await create_chat_session(db, current_user.id, session_data)
    
    return ChatSessionResponse(
        id=session.id,
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        is_active=session.is_active
    )

@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse,
             summary="Update Chat Session", 
             description="Updates a chat session's title or active status")
async def update_session(
    session_id: str = Path(..., description="The unique ID of the chat session"),
    session_data: ChatSessionUpdate = Body(..., description="Session data to update"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Updates a chat session's title or active status.
    
    - Verifies the session belongs to the current user
    - Updates the session title and/or active status
    - Returns the updated session details
    
    Parameters:
        session_id: Unique identifier for the chat session
        session_data: Contains the title and/or active status to update
    
    Returns:
        ChatSessionResponse: The updated chat session details
    
    Raises:
        HTTPException: 404 if session not found
    """
    # Get session first to verify ownership
    session = await get_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
        
    
    # Update fields
    if session_data.title is not None:
        session.title = session_data.title
    
    if session_data.is_active is not None:
        session.is_active = session_data.is_active
    
    session.updated_at = datetime.utcnow()
    
    # Save changes
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return ChatSessionResponse(
        id=session.id,
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        is_active=session.is_active
    )

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT,
              summary="Delete Chat Session", 
              description="Deletes a chat session and optionally its messages")
async def delete_session(
    session_id: str = Path(..., description="The unique ID of the chat session"),
    permanent: bool = Query(False, description="Permanently delete the session and all its messages"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Deletes a chat session and optionally its messages.
    
    - Verifies the session belongs to the current user
    - Performs either a soft delete (marking as inactive) or hard delete (removing from database)
    - Returns no content on success
    
    Parameters:
        session_id: Unique identifier for the chat session
        permanent: Whether to permanently delete the session and all its messages
    
    Returns:
        None: Returns 204 No Content on success
    
    Raises:
        HTTPException: 404 if session not found
    """
    # Get session first to verify ownership
    session = await get_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    await delete_chat_session(db, session, permanent)
    # No content returned for successful deletion

@router.post("/sessions/{session_id}/title", response_model=ChatSessionResponse,
            summary="Generate Session Title", 
            description="Auto-generates a title for the chat session based on its content")
async def generate_session_title(
    session_id: str = Path(..., description="The unique ID of the chat session"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):  
    """
    Auto-generates a title for the chat session based on its content.
    
    - Verifies the session belongs to the current user
    - Retrieves the chat history
    - Uses the first user message to generate a title
    - Updates the session with the generated title
    - Returns the updated session details
    
    Parameters:
        session_id: Unique identifier for the chat session
    
    Returns:
        ChatSessionResponse: The updated chat session details with the generated title
    
    Raises:
        HTTPException: 404 if session not found
        HTTPException: 400 if session has no messages
    """
    logger.debug(f"Received session_id: {session_id}, current_user.id: {current_user.id}")
    """Auto-generate a title for the chat session based on content"""
    # Get session first to verify ownership
    session = await get_chat_session(db, session_id, current_user.id)
    if not session:
        logger.debug(f"Session with ID {session_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    else:
        logger.debug(f"Session found: {session.session_id}")
    
    # Get chat history
    messages = await get_chat_history(db, session_id, current_user.id)
    if not messages:
        logger.debug(f"No messages found for session_id: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate title for empty chat session"
        )
    else:
        logger.debug(f"Messages found: {len(messages)}")
    
    # Use the first user message to generate title
    user_messages = [msg for msg in messages if msg.role == "user"]
    if not user_messages:
        logger.debug(f"No user messages found in session: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user messages found in chat session"
        )
    else:
        logger.debug(f"User messages found: {len(user_messages)}")
    
    first_message = user_messages[0].content
    logger.debug(f"First user message: {first_message}")
   
    # Generate and update title
    await update_session_title(db, session, first_message)
    
    return ChatSessionResponse(
        id=session.id,
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        is_active=session.is_active
    )

@router.get("/analysis", response_model=dict,
           summary="Get Kubernetes Analysis", 
           description="Retrieves Kubernetes cluster analysis results")
async def get_analysis(
    current_user: UserInfo = Depends(get_current_user),
    authorization: str = Header(None)
):
    """
    Retrieves Kubernetes cluster analysis results directly.
    
    - Uses the K8sGPT service to analyze the user's Kubernetes cluster
    - Returns the analysis results
    
    Returns:
        dict: The Kubernetes analysis results
    
    Raises:
        HTTPException: If analysis fails or connection to K8sGPT service fails
    """
    token = authorization.split(" ")[1] if authorization else None
    analysis = await get_k8s_analysis(current_user.id, token)
    return {"analysis": analysis}

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse,
           summary="Get Session Info", 
           description="Retrieves information about a specific chat session")
async def get_session_info(
    session_id: str = Path(..., description="The unique ID of the chat session"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Retrieves information about a specific chat session.
    
    - Verifies the session belongs to the current user
    - Returns the session metadata including creation and update times
    
    Parameters:
        session_id: Unique identifier for the chat session
    
    Returns:
        ChatSessionResponse: The chat session details
    
    Raises:
        HTTPException: 404 if session not found
    """
    session = await get_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    return ChatSessionResponse(
        id=session.id,
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        is_active=session.is_active
    )

@router.get("/conversation/{session_id}", 
           summary="View Conversation", 
           description="View the full conversation history for a session")
async def view_conversation(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """View the full conversation history for a session."""
    session = await get_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = await get_chat_history(db, session_id, current_user.id)
    
    # Format the conversation in a readable way
    formatted_conversation = []
    for msg in messages:
        formatted_conversation.append({
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        })
    
    return {
        "session_id": session_id,
        "title": session.title,
        "conversation": formatted_conversation
    }

@router.delete("/conversation/{session_id}", 
              summary="Clear Conversation", 
              description="Clear the conversation history for a session")
async def clear_conversation(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """Clear the conversation history for a session."""
    session = await get_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    from sqlalchemy import delete
    from app.models import ChatMessage
    
    # Delete all messages for this session
    db.exec(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    db.commit()
    
    return {"message": f"Conversation history cleared for session {session_id}"}

@router.get("/debug/session/{session_id}", 
           summary="Debug Session Memory", 
           description="Debug endpoint to check session memory state")
async def debug_session_memory(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """Debug endpoint to check session memory state."""
    try:
        # Get session
        session = await get_chat_session(db, session_id, current_user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages
        messages = await get_chat_history(db, session_id, current_user.id)
        
        # Create memory
        memory = await create_memory_from_messages(messages)
        
        # Get memory buffer
        buffer = memory.buffer if hasattr(memory, 'buffer') else "No buffer"
        
        return {
            "session_id": session_id,
            "message_count": len(messages),
            "messages": [{"role": msg.role, "content": msg.content[:100]} for msg in messages],
            "memory_buffer": buffer[:500] if buffer else "No buffer",
            "memory_messages": [{"type": type(msg).__name__, "content": msg.content[:100]} for msg in memory.chat_memory.messages] if hasattr(memory.chat_memory, 'messages') else []
        }
    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
