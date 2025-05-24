from fastapi import Depends, HTTPException, status, Header, Response
from fastapi.responses import StreamingResponse
from typing import Annotated, AsyncIterator
from app.dependencies import get_db_session, get_current_user_dependency
from sqlmodel import Session
from app.database import get_session
from app.auth import get_current_user
from app.schemas import UserInfo
import json
import asyncio

# Import the LangChain service
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
    ChatHistoryEntry
)
from app.services import (
    create_chat_session,
    get_chat_session,
    get_chat_history,
    list_user_chat_sessions,
    update_session_title,
    delete_chat_session,
    get_k8s_analysis,
    add_chat_message
)
from fastapi import APIRouter, HTTPException, status, Query, Path, Body
from app.dependencies import SessionDep, CurrentUser
from datetime import datetime

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
    """
    Sends a message to the chat service and processes it using LangChain.
    
    - Accepts a message from the user
    - Processes the message through the LangChain AI backend
    - Returns the AI response (streaming or non-streaming)
    
    Parameters:
        message: The message content and session information
        authorization: Bearer token for authentication
        stream: Whether to stream the response
    
    Returns:
        MessageResponse: The AI's response to the user's message
        or
        StreamingResponse: A streaming response with the AI's tokens
    """
    try:
        session_id = message.session_id
        session = None
        
        # Get or create session
        if session_id:
            # Get existing session
            session = await get_chat_session(db, session_id, current_user.id)
            if not session:
                # Create new session if provided ID doesn't exist
                session_create = ChatSessionCreate(title="New Chat")
                session = await create_chat_session(db, current_user.id, session_create)
                session_id = session.session_id
        else:
            # Create new session
            session_create = ChatSessionCreate(title="New Chat")
            session = await create_chat_session(db, current_user.id, session_create)
            session_id = session.session_id
        
        # For new sessions, get K8s analysis first
        is_new_session = not await get_chat_history(db, session_id)
        analysis_output = ""
        if is_new_session:
            token = authorization.split(" ")[1] if authorization else None
            analysis_output = await get_k8s_analysis(current_user.id, token)
        
        # Build the user content
        if is_new_session and analysis_output:
            user_content = f"Analysis results:\n{analysis_output}\n\nUser question: {message.content}"
        else:
            user_content = message.content
        
        # Add user message to history
        await add_chat_message(db, session, "user", user_content)
        
        # Get chat history
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
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your message: {str(e)}"
        )

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
    try:
        session_id = message.session_id
        session = None
        
        # Get or create session
        if session_id:
            # Get existing session
            session = await get_chat_session(db, session_id, current_user.id)
            if not session:
                # Create new session if provided ID doesn't exist
                session_create = ChatSessionCreate(title="New Chat")
                session = await create_chat_session(db, current_user.id, session_create)
                session_id = session.session_id
        else:
            # Create new session
            session_create = ChatSessionCreate(title="New Chat")
            session = await create_chat_session(db, current_user.id, session_create)
            session_id = session.session_id
        
        # For new sessions, get K8s analysis first
        is_new_session = not await get_chat_history(db, session_id)
        analysis_output = ""
        if is_new_session:
            token = authorization.split(" ")[1] if authorization else None
            analysis_output = await get_k8s_analysis(current_user.id, token)
        
        # Build the user content
        if is_new_session and analysis_output:
            user_content = f"Analysis results:\n{analysis_output}\n\nUser question: {message.content}"
        else:
            user_content = message.content
        
        # Add user message to history
        await add_chat_message(db, session, "user", user_content)
        
        # Get chat history
        messages = await get_chat_history(db, session_id)
        
        # Create memory from messages
        memory = await create_memory_from_messages(messages)
        
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
    
    except Exception as e:
        logger.error(f"Error in stream_chat endpoint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your message: {str(e)}"
        )

#  ---------------------------- working ---------------------------

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

#  ---------------------------- working ---------------------------

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

#  ---------------------------- working ---------------------------

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

#  ---------------------------- working ---------------------------

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

#  ---------------------------- working ---------------------------

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
    print(f"Received session_id: {session_id}, current_user.id: {current_user.id}")
    """Auto-generate a title for the chat session based on content"""
    # Get session first to verify ownership
    session = await get_chat_session(db, session_id, current_user.id)
    if not session:
        print(f"Session with ID {session_id} not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    else:
        print(f"Session found: {session.session_id}")
    
    # Get chat history
    messages = await get_chat_history(db, session_id , current_user.id)
    if not messages:
        print(f"No messages found for session_id: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate title for empty chat session"
        )
    else:
        print(f"Messages found: {len(messages)}")
    
    # Use the first user message to generate title
    user_messages = [msg for msg in messages if msg.role == "user"]
    if not user_messages:
        print(f"No user messages found in session: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user messages found in chat session"
        )
    else:
        print(f"User messages found: {len(user_messages)}")
    
    first_message = user_messages[0].content
    print(f"First user message: {first_message}")
   
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


#  ---------------------------- working ---------------------------

# 2025-03-20 07:05:31,499 - chat_service - ERROR - Error connecting to K8sGPT service: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:1000) 


@router.get("/analysis", response_model=dict,
           summary="Get Kubernetes Analysis", 
           description="Retrieves Kubernetes cluster analysis results")
async def get_analysis(
    current_user: UserInfo = Depends(get_current_user)
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
    analysis = await get_k8s_analysis(current_user.id)
    return {"analysis": analysis}

#  ---------------------------- working ---------------------------

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
