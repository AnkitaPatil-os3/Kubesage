from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid
from jose import jwt, JWTError

# Database and models
from app.database import get_session
from app.models import User, UserToken, RefreshToken, ApiKey, License  # Add License here
from datetime import datetime, timedelta, UTC

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
    ApiKeyCreate, ApiKeyResponse, ApiKeyListResponse, ApiKeyUpdate,

    # Admin schemas
    AdminPasswordReset,
    AdminRegistration
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
license_router = APIRouter()

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


@auth_router.get("/confirm-admin/{confirmation_id}/{response}", response_class=HTMLResponse)
async def confirm_admin_registration(confirmation_id: str, response: str, session: Session = Depends(get_session)):
    """
    Handle admin user response to registration confirmation email.

    - Validates the response (must be 'yes' or 'no')
    - Checks if the confirmation exists and is not expired
    - Creates the admin user if confirmed
    - Returns an HTML page confirming the action

    Parameters:
        confirmation_id: Unique identifier for the confirmation
        response: User's response ('yes' to confirm, 'no' to reject)
    """
    logger.info(f"Received admin confirmation response: {response} for ID: {confirmation_id}")

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
        logger.warning(f"Admin confirmation ID not found: {confirmation_id}")
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
                    <p>If you were trying to register the admin account, please start the registration process again.</p>
                </div>
            </body>
        </html>
        """)

    # Check if the confirmation is still pending
    if confirmation_data["status"] != "pending":
        status_message = confirmation_data["status"]
        action_taken = ""

        if status_message == "confirmed":
            action_taken = "The admin account has already been created successfully."
            color = "#4CAF50"  # Green for success
        elif status_message == "rejected":
            action_taken = "You previously rejected this admin registration."
            color = "#f44336"  # Red for rejection
        elif status_message == "expired":
            action_taken = "The confirmation link expired. Please register the admin account again."
            color = "#FF9800"  # Orange for expired
        else:
            action_taken = "This confirmation has already been processed."
            color = "#2196F3"  # Blue for other statuses

        logger.info(f"Admin confirmation {confirmation_id} already processed with status: {status_message}")
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
        logger.warning(f"Admin confirmation {confirmation_id} has expired")
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
            # Get admin user data from confirmation
            user_data = confirmation_data["user_data"]

            # Create new admin user
            hashed_password = get_password_hash(user_data["password"])
            db_user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=hashed_password,
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", ""),
                is_active=True,
                roles="Super Admin",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                confirmed=True  # Set confirmed to True
            )
            # Add user to the session and commit the transaction
            session.add(db_user)
            session.commit()
            session.refresh(db_user)

            logger.info(f"Admin user {db_user.username} registered successfully after confirmation")
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
                    "roles": db_user.roles,
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"Published user_created event for admin user {db_user.username}")
            except Exception as e:
                logger.error(f"Failed to publish user_created event: {e}")

            # Update confirmation status
            update_confirmation_status(confirmation_id, "confirmed")

            return HTMLResponse(content=f"""
            <html>
                <head>
                    <title>Admin Registration Confirmed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                        h1 {{ color: #4CAF50; }}
                        .button {{ display: inline-block; background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Admin Registration Confirmed!</h1>
                        <p>Thank you for confirming the admin registration, <strong>{user_data["first_name"]} {user_data["last_name"]}</strong>!</p>
                        <p>The admin account has been successfully created and is now active.</p>
                        <p>You can now log in to KubeSage with the username <strong>admin</strong> and your password.</p>
                        <a href="{settings.FRONTEND_BASE_URL}/" class="button">Go to Login</a>
                    </div>
                </body>
            </html>
            """)

        except Exception as e:
            logger.error(f"Error during admin confirmation: {e}")
            update_confirmation_status(confirmation_id, "error")

            return HTMLResponse(content=f"""
            <html>
                <head>
                    <title>Admin Registration Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                        h1 {{ color: #f44336; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Admin Registration Error</h1>
                        <p>There was an error creating the admin account:</p>
                        <p><strong>{str(e)}</strong></p>
                        <p>This could be because:</p>
                        <ul>
                            <li>The username or email is already registered</li>
                            <li>There was a database connection issue</li>
                            <li>The server encountered an internal error</li>
                        </ul>
                        <p>Please try registering the admin account again or contact support if the problem persists.</p>
                    </div>
                </body>
            </html>
            """)
    else:
        # Admin rejected the registration
        update_confirmation_status(confirmation_id, "rejected")
        logger.info(f"Admin rejected registration for confirmation {confirmation_id}")

        return HTMLResponse(content=f"""
        <html>
            <head>
                <title>Admin Registration Rejected</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                    h1 {{ color: #f44336; }}
                    .button {{ display: inline-block; background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Admin Registration Rejected</h1>
                    <p>You have rejected this admin registration attempt.</p>
                    <p>No admin account has been created.</p>
                    <p>If you did not initiate this registration, no further action is needed.</p>
                    <p>If this was a mistake and you do want to register the admin account, please start the registration process again.</p>

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

@auth_router.get("/check-admin-exists", summary="Check if Admin User Exists")
async def check_admin_exists(session: Session = Depends(get_session)):
    """Check if any admin user exists in the system"""
    admin_user = session.exec(
        select(User).where(User.roles.contains("Super Admin"))
    ).first()

    return {"admin_exists": admin_user is not None}

@auth_router.post("/register-admin", status_code=status.HTTP_202_ACCEPTED)
async def register_admin(
    request: Request,
    admin_data: AdminRegistration,
    session: Session = Depends(get_session)
):
    """Register the first admin user with email verification (only if no admin exists)"""

    # Check if admin already exists
    existing_admin = session.exec(
        select(User).where(User.roles.contains("Super Admin"))
    ).first()

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin user already exists"
        )

    # Check if username or email already exists
    existing_user = session.exec(
        select(User).where(
            (User.username == "admin") | (User.email == admin_data.email)
        )
    ).first()

    if existing_user:
        if existing_user.username == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username 'admin' is already taken"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    try:
        # Prepare admin user data for email confirmation
        admin_dict = {
            "username": "admin",
            "email": admin_data.email,
            "password": admin_data.password,
            "first_name": admin_data.first_name,
            "last_name": admin_data.last_name,
            "is_active": True,
            "is_admin": True,
            "roles": "Super Admin",
            "confirmed": False  # Will be set to True after confirmation
        }

        # Send confirmation email
        success, confirmation_id = await send_confirmation_email(admin_dict, confirm_path="confirm-admin")

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send confirmation email"
            )

        logger.info(f"Admin registration confirmation email sent for email: {admin_data.email}")

        return {
            "status": "pending",
            "confirmation_id": confirmation_id,
            "message": f"Confirmation email sent to {admin_data.email}. Please confirm within {settings.USER_CONFIRMATION_TIMEOUT} seconds."
        }

    except Exception as e:
        logger.error(f"Error during admin registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin registration failed"
        )

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



 
@user_router.put("/{user_id}", response_model=UserResponse,
                summary="Update User", description="Updates a user's information (admin only)")
@limiter.limit("10/minute")
async def update_user(
    request: Request,
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """
    Updates a user's profile information.
    
    - Requires admin privileges
    - Finds the user by ID
    - Updates the user's information with the provided data
    - Handles password updates separately with proper hashing
    - Publishes a user update event to the message queue
    
    Parameters:
        user_id: ID of the user to update
        user_update: Data to update in the user profile
    
    Returns:
        UserResponse: The updated user profile
    
    Raises:
        HTTPException: 404 error if user not found
    """
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields if provided
    user_data = user_update.model_dump(exclude_unset=True)
    
    # Handle password update separately
    if "password" in user_data:
        password = user_data.pop("password")
        db_user.hashed_password = get_password_hash(password)
    
    # Update other fields
    for key, value in user_data.items():
        setattr(db_user, key, value)
    
    db_user.updated_at = datetime.now()
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    logger.info(f"User {db_user.username} updated successfully")
    
    # Publish user update event
    publish_message("user_events", {
        "event_type": "user_updated",
        "user_id": db_user.id,
        "username": db_user.username,
        "updated_fields": list(user_data.keys()),
        "timestamp": datetime.now().isoformat()
    })
    
    user_dict = db_user.model_dump()
    if isinstance(user_dict.get("roles"), list):
        user_dict["roles"] = ",".join(user_dict["roles"])
    return user_dict
 
@user_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
                   summary="Delete User", description="Deletes a user account (admin only)")
@limiter.limit("10/minute")
async def delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """
    Deletes a user from the system.
    
    - Requires admin privileges
    - Finds the user by ID
    - Prevents admins from deleting their own account
 
    - Removes the user's tokens first, then the user from the database
    - Publishes a user deletion event to the message queue
    
    Parameters:
        user_id: ID of the user to delete
    
    Returns:
        None: Returns 204 No Content on success
    
    Raises:
        HTTPException: 404 error if user not found
        HTTPException: 400 error if attempting to delete own account
    """
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
 
    try:
        # Store user info before deletion for event publishing
        user_info = {
            "user_id": db_user.id,
            "username": db_user.username
        }
        
        # First, delete all tokens associated with this user
        user_tokens = session.exec(select(UserToken).where(UserToken.user_id == user_id)).all()
        for token in user_tokens:
            session.delete(token)
        
        # Commit the token deletions
        session.commit()
        
        # Now delete the user
        session.delete(db_user)
        session.commit()
        
        logger.info(f"User {user_info['username']} and associated tokens deleted successfully")
        
        # Publish user deletion event
        publish_message("user_events", {
            "event_type": "user_deleted",
            "user_id": user_info["user_id"],
            "username": user_info["username"],
            "timestamp": datetime.now()
        })
        
        return None
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
 
 
 
 
 
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


# ADD THIS NEW ROUTE

 
@user_router.get("/me/api-key", response_model=UserResponse,
                summary="Get Current User via API Key",
                description="Returns the current user information using API key authentication")
async def get_current_user_via_api_key(
    api_key: str = Header(None, alias="X-API-Key"),
    session: Session = Depends(get_session)
):
    """
    Returns the profile information of the currently authenticated user via API key.
    
    - Requires a valid API key in X-API-Key header
    - Returns the user's profile data
    
    Returns:
        UserResponse: The current user's profile information
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required in X-API-Key header")
    
    try:
        # Find the API key in database
        db_api_key = session.exec(
            select(ApiKey).where(
                ApiKey.api_key == api_key,
                ApiKey.is_active == True
            )
        ).first()
        
        if not db_api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Check if API key is expired
        if db_api_key.expires_at and db_api_key.expires_at < datetime.now():
            raise HTTPException(status_code=401, detail="API key expired")
        
        # Get the user
        user = session.exec(
            select(User).where(User.id == db_api_key.user_id)
        ).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="User account is disabled")
        
        # Update last_used_at
        db_api_key.last_used_at = datetime.now()
        session.add(db_api_key)
        session.commit()
        
        # Build complete response
        user_response = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "is_active": user.is_active,
            "roles": user.roles or "",
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "confirmed": getattr(user, 'confirmed', False)
        }
        
        return user_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user_via_api_key: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== LICENSE ROUTES ====================z ab    

@license_router.get("/license/status")
async def get_license_status(session: Session = Depends(get_session)):
    """Check if the license is valid"""
    try:
        # Get the latest active license
        license = session.exec(
            select(License)
            .where(License.is_active == True)
            .order_by(License.created_at.desc())
        ).first()

        if not license:
            return {
                "is_valid": False,
                "message": "No valid license found",
                "error": "LICENSE_NOT_FOUND"
            }

        # Convert current time to UTC for comparison
        current_time = datetime.now(UTC)
        
        # Ensure license.expires_at is timezone-aware
        license_expiry = license.expires_at.replace(tzinfo=UTC) if license.expires_at.tzinfo is None else license.expires_at

        # Check if license is expired
        if current_time > license_expiry:
            return {
                "is_valid": False,
                "message": "Your license has expired",
                "error": "LICENSE_EXPIRED",
                "expires_at": license_expiry.isoformat()
            }

        # License is valid
        return {
            "is_valid": True,
            "message": "License is valid",
            "expires_at": license_expiry.isoformat()
        }

    except Exception as e:
        logger.error(f"Error checking license status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check license status"
        )

@auth_router.post("/reset-admin-password")
async def reset_admin_password(
    reset_data: AdminPasswordReset,
    session: Session = Depends(get_session)
):
    """Reset admin user password or skip reset"""
    if reset_data.skip_reset:
        return {"message": "Password reset skipped"}
        
    try:
        # Get admin user
        admin_user = session.exec(
            select(User).where(
                User.username == "admin",
                User.roles.contains("Super Admin")
            )
        ).first()
        
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin user not found"
            )
        
        # Check if password has already been changed
        if admin_user.password_changed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin password can only be changed once"
            )
        
        # Update password
        admin_user.hashed_password = get_password_hash(reset_data.new_password)
        admin_user.updated_at = datetime.now()
        admin_user.password_changed = True
        session.add(admin_user)
        session.commit()
        
        return {"message": "Admin password updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting admin password: {e}")
        # Show the actual error in response instead of generic "Failed..."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)  # this will give {"detail": "Database connection failed"} etc.
        )

@auth_router.get("/check-password-reset-status")
async def check_password_reset_status(session: Session = Depends(get_session)):
    """Check if admin has already reset their password"""
    try:
        admin_user = session.exec(
            select(User).where(
                User.username == "admin",
                User.roles.contains("Super Admin")
            )
        ).first()
        
        if not admin_user:
            return {"can_reset": False, "message": "Admin user not found"}
            
        return {
            "can_reset": not admin_user.password_changed,
            "message": "Password can be reset" if not admin_user.password_changed else "Password has already been reset"
        }
        
    except Exception as e:
        logger.error(f"Error checking password reset status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check password reset status"
        )




