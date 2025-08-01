from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid
from jose import jwt, JWTError

# Database and models
from app.database import get_session
from app.models import User, UserToken, RefreshToken, ApiKey

# Schemas - Import ALL needed schemas
from app.schemas import (
    # User schemas
    UserCreate, UserResponse, UserUpdate, UsersListResponse,
    
    # Auth schemas
    LoginRequest, Token, ChangePasswordRequest, TokenRefreshRequest, 
    TokenData, DeviceFingerprint,
    
    # Session schemas
    SessionInfo, UserSessionsResponse, TerminateSessionRequest,
    TerminateAllSessionsRequest,
    
    # API Key schemas - ADD THESE
    ApiKeyCreate, ApiKeyResponse, ApiKeyListResponse, ApiKeyUpdate
)

# Auth functions
from app.auth import (
    authenticate_user, 
    create_access_token, 
    create_refresh_token,
    get_password_hash, 
    get_current_active_user,
    get_current_admin_user,
    verify_password,
    get_current_user,
    refresh_access_token,
    revoke_refresh_token,
    cleanup_expired_tokens,
    create_device_fingerprint,
    get_user_from_api_key,
    get_current_user_from_api_key
)

# Other imports
from app.config import settings
from app.logger import logger
from app.queue import publish_message
from app.rate_limiter import limiter
from app.email_client import send_confirmation_email, get_confirmation_status, update_confirmation_status
from app.api_key_utils import generate_api_key, get_api_key_preview

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Routers
api_key_router = APIRouter()
user_router = APIRouter()
auth_router = APIRouter()

# Helper function to extract device info from request
def extract_device_fingerprint(request: Request) -> DeviceFingerprint:
    """Extract device fingerprint from request headers"""
    return DeviceFingerprint(
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        device_info=request.headers.get("x-device-info")
    )

# ==================== AUTHENTICATION ROUTES ====================

@auth_router.post("/register", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def register_user(request: Request, user_data: UserCreate, session: Session = Depends(get_session)):
    """Your existing registration code"""
    # Check if username exists
    existing_user = session.exec(select(User).where(User.username == user_data.username)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    existing_email = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Convert user_data to dict for email confirmation
        user_dict = user_data.dict()
        
        # Send confirmation email
        success, confirmation_id = await send_confirmation_email(user_dict)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send confirmation email"
            )
        
        logger.info(f"Registration confirmation email sent for user: {user_data.username}")
        
        return {
            "status": "pending",
            "confirmation_id": confirmation_id,
            "message": f"Confirmation email sent to {user_data.email}. Please confirm within {settings.USER_CONFIRMATION_TIMEOUT} seconds."
        }
    
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed"
        )

@auth_router.get("/confirm/{confirmation_id}/{response}", response_class=HTMLResponse)
async def confirm_registration(confirmation_id: str, response: str, session: Session = Depends(get_session)):
    """
    Handle user response to registration confirmation email.
    
    - Validates the response (must be 'yes' or 'no')
    - Checks if the confirmation exists and is not expired
    - Creates the user if confirmed
    - Returns an HTML page confirming the action
    
    Parameters:
        confirmation_id: Unique identifier for the confirmation
        response: User's response ('yes' to confirm, 'no' to reject)
    """
    logger.info(f"Received confirmation response: {response} for ID: {confirmation_id}")
    
    # Validate the response
    if response not in ["yes", "no"]:
        return HTMLResponse(content="""
        <html>
            <head>
                <title>Invalid Response</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    h1 { color: #f44336; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Invalid Response</h1>
                    <p>Your response must be either 'yes' or 'no'.</p>
                    <p>Please check your email and try again with a valid link.</p>
                </div>
            </body>
        </html>
        """)
    
    # Check if the confirmation exists
    confirmation_data = get_confirmation_status(confirmation_id)
    if not confirmation_data:
        logger.warning(f"Confirmation ID not found: {confirmation_id}")
        return HTMLResponse(content="""
        <html>
            <head>
                <title>Invalid Confirmation</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    h1 { color: #f44336; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Invalid Confirmation ID</h1>
                    <p>The confirmation link you're using is invalid or has been processed already.</p>
                    <p>If you were trying to register, please start the registration process again.</p>
                </div>
            </body>
        </html>
        """)
    
    # Check if the confirmation is still pending
    if confirmation_data["status"] != "pending":
        status_message = confirmation_data["status"]
        action_taken = ""
        
        if status_message == "confirmed":
            action_taken = "Your account has already been created successfully."
            color = "#4CAF50"  # Green for success
        elif status_message == "rejected":
            action_taken = "You previously rejected this registration."
            color = "#f44336"  # Red for rejection
        elif status_message == "expired":
            action_taken = "The confirmation link expired. Please register again."
            color = "#FF9800"  # Orange for expired
        else:
            action_taken = "This confirmation has already been processed."
            color = "#2196F3"  # Blue for other statuses
        
        logger.info(f"Confirmation {confirmation_id} already processed with status: {status_message}")
        return HTMLResponse(content=f"""
        <html>
            <head>
                <title>Already Processed</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                    h1 {{ color: {color}; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Confirmation Already Processed</h1>
                    <p>{action_taken}</p>
                    <p>Status: <strong>{status_message.capitalize()}</strong></p>
                    <p>If you need assistance, please contact support.</p>
                </div>
            </body>
        </html>
        """)
    
    # Check if the confirmation has expired
    if confirmation_data["expires_at"] < datetime.now():
        update_confirmation_status(confirmation_id, "expired")
        logger.warning(f"Confirmation {confirmation_id} has expired")
        return HTMLResponse(content="""
        <html>
            <head>
                <title>Confirmation Expired</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    h1 { color: #FF9800; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Confirmation Expired</h1>
                    <p>We're sorry, but the confirmation link has expired.</p>
                    <p>For security reasons, confirmation links are only valid for a limited time.</p>
                    <p>Please return to the registration page and try again.</p>
                </div>
            </body>
        </html>
        """)
    
    # Process the confirmation based on the response
    confirmed = (response == "yes")
    
    if confirmed:
        try:
            # Get user data from confirmation
            user_data = confirmation_data["user_data"]
            
            # Create new user
            hashed_password = get_password_hash(user_data["password"])
            # db_user = User(
            #     username=user_data["username"],
            #     email=user_data["email"],
            #     hashed_password=hashed_password,
            #     first_name=user_data.get("first_name", ""),
            #     last_name=user_data.get("last_name", ""),
            #     is_active=user_data.get("is_active", True),
            #     is_admin=user_data.get("is_admin", False)
            # )
            db_user = User(
                  username=user_data["username"],
                  email=user_data["email"],
                  hashed_password=hashed_password,
                  first_name=user_data.get("first_name", ""),
                  last_name=user_data.get("last_name", ""),
                  is_active=user_data.get("is_active", True),
                  roles=user_data.get("roles", ""),
                  created_at=datetime.now(),
                  updated_at=datetime.now(),
                  confirmed=True  # Set confirmed to True
                )
            # Add user to the session and commit the transaction
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            
            # logger.info(f"User {user['username']} registered successfully after confirmation")
            logger.info(f"User {db_user.username} registered successfully after confirmation")
            # Publish user registration event
            try:
                publish_message("user_events", {
                    "event_type": "user_created",
                    "user_id": db_user.id,
                    "username": db_user.username,
                    "email": db_user.email,
                    "first_name": db_user.first_name,
                    "last_name": db_user.last_name,
                    "is_active": db_user.is_active,
                    # #"is_admin": db_user.is_admin,
                    "roles":db_user.roles,
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"Published user_created event for user {db_user.username}")
            except Exception as e:
                logger.error(f"Failed to publish user_created event: {e}")
            
            # Update confirmation status
            update_confirmation_status(confirmation_id, "confirmed")
            
            return HTMLResponse(content=f"""
            <html>
                <head>
                    <title>Registration Confirmed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                        h1 {{ color: #4CAF50; }}
                        .button {{ display: inline-block; background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Registration Confirmed!</h1>
                        <p>Thank you for confirming your registration, <strong>{user_data["username"]}</strong>!</p>
                        <p>Your account has been successfully created and is now active.</p>
                        <p>You can now log in to KubeSage with your username and password.</p>
                        <a href="{settings.FRONTEND_BASE_URL}/" class="button">Go to Login</a>
                    </div>
                </body>
            </html>
            """)
            
        except Exception as e:
            logger.error(f"Error during user confirmation: {e}")
            update_confirmation_status(confirmation_id, "error")
            
            return HTMLResponse(content=f"""
            <html>
                <head>
                    <title>Registration Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                        h1 {{ color: #f44336; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Registration Error</h1>
                        <p>There was an error creating your account:</p>
                        <p><strong>{str(e)}</strong></p>
                        <p>This could be because:</p>
                        <ul>
                            <li>The username or email is already registered</li>
                            <li>There was a database connection issue</li>
                            <li>The server encountered an internal error</li>
                        </ul>
                        <p>Please try registering again or contact support if the problem persists.</p>
                    </div>
                </body>
            </html>
            """)
    else:
        # User rejected the registration
        update_confirmation_status(confirmation_id, "rejected")
        logger.info(f"User rejected registration for confirmation {confirmation_id}")
        
        return HTMLResponse(content=f"""
        <html>
            <head>
                <title>Registration Rejected</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                    h1 {{ color: #f44336; }}
                    .button {{ display: inline-block; background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Registration Rejected</h1>
                    <p>You have rejected this registration attempt.</p>
                    <p>No account has been created.</p>
                    <p>If you did not initiate this registration, no further action is needed.</p>
                    <p>If this was a mistake and you do want to register, please start the registration process again.</p>
                    
                </div>
            </body>
        </html>
        """)


@auth_router.get("/confirmation-status/{confirmation_id}", response_model=dict)
async def check_confirmation_status(
    confirmation_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Check the status of a user registration confirmation.
    Only accessible by admin users.
    
    Parameters:
        confirmation_id: The ID of the confirmation to check
    
    Returns:
        Dict with confirmation status 
    """
    # Handle invalid confirmation IDs
    if not confirmation_id or confirmation_id == "undefined":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid confirmation ID"
        )
    
    confirmation_data = get_confirmation_status(confirmation_id)
    if not confirmation_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Confirmation not found"
        )
    
    return {
        "status": confirmation_data["status"],
        "expires_at": confirmation_data["expires_at"].isoformat() if "expires_at" in confirmation_data else None
    }


@auth_router.post("/token", response_model=Token, 
                 summary="User Login", 
                 description="Authenticates a user and returns access and refresh tokens")
@limiter.limit("10/minute")
async def login(
    request: Request, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    session: Session = Depends(get_session)
):
    """Enhanced login with multi-session support"""
    
    # Authenticate user
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Extract device fingerprint
        device_fingerprint = extract_device_fingerprint(request)
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token, expires_at = create_access_token(
            data={"sub": str(user.id)}, 
            expires_delta=access_token_expires,
            session_id=session_id
        )
        
        # Create refresh token
        refresh_token, refresh_expires_at = create_refresh_token(
            user_id=user.id,
            session_id=session_id,
            device_fingerprint=device_fingerprint,
            session=session
        )
        
        # Store access token session info
        user_token = UserToken(
            token=access_token,
            user_id=user.id,
            session_id=session_id,
            expires_at=expires_at,
            device_info=device_fingerprint.device_info,
            ip_address=device_fingerprint.ip_address,
            user_agent=device_fingerprint.user_agent,
            last_used_at=datetime.now()
        )
        
        session.add(user_token)
        session.commit()
        session.refresh(user_token)
        
        # Publish login event
        publish_message("user_events", {
            "event_type": "user_login",
            "user_id": user.id,
            "username": user.username,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"User {user.username} logged in with session {session_id}")
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_at=expires_at,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@auth_router.post("/logout", summary="User Logout")
@limiter.limit("10/minute")
async def logout(
    request: Request, 
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Logs out user from current session"""
    try:
        # Get current session info from token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        session_id = payload.get("session_id")
        
        # Deactivate current session's access token
        user_token = session.exec(
            select(UserToken).where(
                UserToken.token == token,
                UserToken.user_id == current_user.id
            )
        ).first()
        
        if user_token:
            user_token.is_active = False
            session.add(user_token)
        
        session.commit()
        
        logger.info(f"User {current_user.username} logged out")
        
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during logout"
        )

@auth_router.get("/check-admin", summary="Check Admin Status")
async def check_if_admin(current_user: User = Depends(get_current_user)):
    """Check if current user has admin privileges"""
    return {
        "is_admin": "Super Admin" in (current_user.roles or ""),
        "roles": current_user.roles,
        "username": current_user.username
    }

# ==================== USER ROUTES ====================

@user_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    user_dict = current_user.model_dump()
    if isinstance(user_dict.get("roles"), list):
        user_dict["roles"] = ",".join(user_dict["roles"])
    if "roles" not in user_dict or user_dict["roles"] is None:
        user_dict["roles"] = ""
    return user_dict

@user_router.get("/", response_model=UsersListResponse)
@limiter.limit("10/minute")
async def list_users(
    request: Request, 
    skip: int = 0, 
    limit: int = 100, 
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """List all users (admin only)"""
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    users_list = [user.model_dump() for user in users]
    roles_options = getattr(settings, 'ROLE_OPTIONS', ['User', 'Admin', 'Super Admin'])
    return {"users": users_list, "roles_options": roles_options}

# ==================== API KEY ROUTES ====================

@api_key_router.post("/", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Create a new API key"""
    # Check if user already has an API key with the same name
    existing_key = session.exec(
        select(ApiKey).where(
            ApiKey.user_id == current_user.id,
            ApiKey.key_name == api_key_data.key_name,
            ApiKey.is_active == True
        )
    ).first()
    
    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key with this name already exists"
        )
    
    # Generate new API key
    new_api_key = generate_api_key()
    
    # Create API key record
    db_api_key = ApiKey(
        key_name=api_key_data.key_name,
        api_key=new_api_key,
        user_id=current_user.id,
        expires_at=api_key_data.expires_at
    )
    
    try:
        session.add(db_api_key)
        session.commit()
        session.refresh(db_api_key)
        
        logger.info(f"API key '{api_key_data.key_name}' created for user {current_user.username}")
        
        return db_api_key
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )

@api_key_router.get("/", response_model=List[ApiKeyListResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """List all API keys for current user"""
    api_keys = session.exec(
        select(ApiKey).where(ApiKey.user_id == current_user.id)
    ).all()
    
    # Convert to response format with masked API keys
    response_keys = []
    for key in api_keys:
        key_dict = key.model_dump()
        key_dict["api_key_preview"] = get_api_key_preview(key.api_key)
        response_keys.append(ApiKeyListResponse(**key_dict))
    
    return response_keys

@api_key_router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Delete an API key"""
    db_api_key = session.exec(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    ).first()
    
    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    try:
        session.delete(db_api_key)
        session.commit()
        
        logger.info(f"API key '{db_api_key.key_name}' deleted for user {current_user.username}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error deleting API key: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )
