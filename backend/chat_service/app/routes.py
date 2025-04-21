from fastapi import Depends, HTTPException, status , Header
from typing import Annotated
from app.dependencies import get_db_session, get_current_user_dependency
from sqlmodel import Session
from app.database import get_session
from app.auth import get_current_user
from app.schemas import UserInfo

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
    process_chat_message,
    get_chat_session,
    get_chat_history,
    list_user_chat_sessions,
    update_session_title,
    delete_chat_session,
    get_k8s_analysis
)
from fastapi import APIRouter, HTTPException, status,Query, Path, Body
from app.dependencies import SessionDep, CurrentUser
from app.schemas import MessageCreate, MessageResponse, ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse, ChatSessionList, ChatHistoryResponse, ChatHistoryEntry
from app.services import create_chat_session, process_chat_message, get_chat_session, get_chat_history, list_user_chat_sessions, update_session_title, delete_chat_session, get_k8s_analysis
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["chat"])

#  ---------------------------- working ---------------------------
#  chat_section api
@router.post("/", response_model=MessageResponse)
async def chat(message: MessageCreate, db: Session= get_db_session(),
                    current_user: UserInfo = Depends(get_current_user),
                    authorization: str = Header(None)):
    token = authorization.split(" ")[1] if authorization else None
    response = await process_chat_message(db, current_user.id, message, token)
    return response
    

#  ---------------------------- working ---------------------------

@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_session_history(session_id: str, db: Session= get_db_session(),
                current_user: UserInfo = Depends(get_current_user)):
    session = await get_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    
    messages = await get_chat_history(db, session_id)
    
    return ChatHistoryResponse(
        session_id=session.session_id,
        title=session.title,
        messages=[ChatHistoryEntry(role=msg.role, content=msg.content, created_at=msg.created_at) for msg in messages],
        created_at=session.created_at,
        updated_at=session.updated_at
    )


#  ---------------------------- working ---------------------------

@router.get("/sessions", response_model=ChatSessionList)
async def list_chat_sessions(
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of sessions to return"),
    active_only: bool = Query(True, description="Return only active sessions"),
    # db: Session= get_db_session(),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)

):
    print(f"User {current_user.username} accessing chat sessions...")
    """List all chat sessions for the current user"""
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

#  ---------------------------- working ---------------------------

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """Create a new chat session"""
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

@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str = Path(..., description="The unique ID of the chat session"),
    session_data: ChatSessionUpdate = Body(..., description="Session data to update"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """Update a chat session (title or active status)"""
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

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str = Path(..., description="The unique ID of the chat session"),
    permanent: bool = Query(False, description="Permanently delete the session and all its messages"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """Delete a chat session (soft delete by default, hard delete if permanent=True)"""
    # Get session first to verify ownership
    session = await get_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    await delete_chat_session(db, session, permanent)
    # No content returned for successful deletion

@router.post("/sessions/{session_id}/title", response_model=ChatSessionResponse)
async def generate_session_title(
    session_id: str = Path(..., description="The unique ID of the chat session"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):  
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


@router.get("/analysis", response_model=dict)
async def get_analysis(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get Kubernetes analysis results directly"""
    analysis = await get_k8s_analysis(current_user.id)
    return {"analysis": analysis}

#  ---------------------------- working ---------------------------

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session_info(
    session_id: str = Path(..., description="The unique ID of the chat session"),
    db: Session = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user)
):
    """Get information about a specific chat session"""
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