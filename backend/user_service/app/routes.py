from fastapi import APIRouter, Depends, HTTPException, status ,Request
from sqlmodel import Session, select
from typing import List ,  Dict, Optional
from pydantic import BaseModel
# ##
# import datetime  # Added for timestamp
##
from datetime import datetime  # Import the datetime class directly

from app.database import get_session
from app.models import User , UserToken
from app.schemas import UserCreate, UserResponse, UserUpdate, LoginRequest, Token, ChangePasswordRequest
from app.auth import (
    authenticate_user, 
    create_access_token, 
    get_password_hash, 
    get_current_active_user,
    get_current_admin_user,
    verify_password,
    get_current_user
)
from fastapi.responses import HTMLResponse
from app.config import settings
from app.logger import logger
from datetime import timedelta
from app.queue import publish_message  # Import the queue functionality
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security import OAuth2PasswordBearer
from app.models import ApiKey
from app.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyListResponse, ApiKeyUpdate
from app.api_key_utils import generate_api_key, get_api_key_preview
from app.rate_limiter import limiter
from app.email_client import send_confirmation_email, get_confirmation_status, update_confirmation_status
from app.auth import get_user_from_api_key 
from app.auth import get_current_user_from_api_key


# Add a new router for API keys
api_key_router = APIRouter()

# User & Auth router
user_router = APIRouter()
auth_router = APIRouter()



# register user

@auth_router.post("/register", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def register_user(request: Request, user_data: UserCreate, session: Session = Depends(get_session)):
    """
    Registers a new user in the system with email confirmation.
    """
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
            "confirmation_id": confirmation_id,  # Make sure this is included
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


@auth_router.post("/token", summary="User Login", description="Authenticates a user and returns an access token")
@limiter.limit("10/minute")
async def login( request: Request, form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """
    Authenticates a user with username and password.
    
    - Validates user credentials
    - Creates and stores a JWT access token
    - Publishes a user login event to the message queue
    - Returns the access token with expiration information
    
    Returns:
        dict: Contains access token, token type, and expiration timestamp
    
    Raises:
        HTTPException: 401 error if credentials are invalid
    """
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, expires_at = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    # Save UserToken in the database
    user_token = UserToken(
        token=access_token,
        user_id=user.id,
        expires_at=expires_at
    )
    session.add(user_token)
    session.commit()
    session.refresh(user_token)

    print(f"User token is {user_token}, save in the database")
        
    # Publish login event
    publish_message("user_events", {
        "event_type": "user_login",
        "user_id": user.id,
        "username": user.username,
        "timestamp": datetime.now()
    })
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "expires_at": expires_at
    }


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

@auth_router.post("/logout", summary="User Logout", description="Logs out a user by invalidating their access token")
@limiter.limit("10/minute")
async def logout(
    request: Request, 
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
    ):
    """
    Logs out a user by removing their token from the database.
    
    - Finds and deletes the current user's token
    - Publishes a user logout event to the message queue
    - Returns a success message
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException: 500 error if logout process fails
    """
    try:
        # Delete the current token
        user_token = session.exec(
            select(UserToken).where(
                UserToken.token == token,
                UserToken.user_id == current_user.id
            )
        ).first()
        
        if user_token:
            session.delete(user_token)
            session.commit()
        
        # Option 1: Delete all tokens for this user (complete logout from all devices)
        # session.query(UserToken).filter(UserToken.user_id == current_user.id).delete()
        # session.commit()
        
        # Publish logout event
        publish_message("user_events", {
            "event_type": "user_logout",
            "user_id": current_user.id,
            "username": current_user.username,
            "timestamp": datetime.now()
        })
        
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during logout"
        )

# Endpoint to check if user is admin
# @auth_router.get("/check-admin", summary="Check Admin Status", description="Checks if the current user has admin privileges")
# @limiter.limit("10/minute")
# async def check_if_admin(request: Request, current_user: User = Depends(get_current_user)):
#     """
#     Checks if the current authenticated user has admin privileges.
    
#     - Verifies the admin status of the current user
#     - Returns the admin status and username
    
#     Returns:
#         dict: Contains is_admin boolean flag and username
#     """

# Endpoint to check if user is admin
@auth_router.get("/check-admin", summary="Check Admin Status", description="Checks if the current user has admin privileges")
async def check_if_admin(current_user: User = Depends(get_current_user)):
    """
    Checks if the current authenticated user has admin privileges.
    Returns:
        dict: Contains is_admin boolean flag and username
    """
    return {
        "is_admin": "Super Admin" in (current_user.roles or []),  # <-- Check for super_admin role
        "roles": current_user.roles,  ## <-- Return all roles
        "username": current_user.username
    }




@auth_router.post("/change-password/{user_id}", status_code=status.HTTP_200_OK,
                 summary="Admin Change User Password", description="Allows an admin to change another user's password")
@limiter.limit("10/minute")
async def A_change_password(
    request: Request, 
    user_id: int,
    password_data: ChangePasswordRequest,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """
    Allows an admin to change the password of any user.
    
    - Requires admin privileges
    - Finds the target user by ID
    - Updates the user's password with a new hashed password
    - Publishes a password change event to the message queue
    
    Parameters:
        user_id: ID of the user whose password will be changed
        password_data: Contains the new password
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException: 404 error if user not found
    """
    # Fetch the target user by ID
    user = session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update the password
    user.hashed_password = get_password_hash(password_data.new_password)
    session.add(user)
    session.commit()

    logger.info(f"Admin {current_admin.username} changed password for user {user.username}")

    # Publish password change event
    publish_message("user_events", {
        "event_type": "password_changed",
        "admin_id": current_admin.id,
        "user_id": user.id,
        "username": user.username,
        "timestamp": datetime.now()
    })

    return {"detail": "Password updated successfully"}


@user_router.get("/me", response_model=UserResponse, 
                summary="Get Current User", description="Returns the current authenticated user's information")
@limiter.limit("10/minute")
async def read_users_me(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Returns the profile information of the currently authenticated user.
    
    - Requires a valid authentication token
    - Returns the user's profile data
    
    Returns:
        UserResponse: The current user's profile information
    """
    return current_user

@user_router.get("/", response_model=List[UserResponse], 
                summary="List All Users", description="Returns a list of all users (admin only)")
@limiter.limit("10/minute")
async def list_users(
    request: Request, 
    skip: int = 0, 
    limit: int = 100, 
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """
    Lists all users in the system.
    
    - Requires admin privileges
    - Supports pagination with skip and limit parameters
    - Returns a list of user profiles
    
    Parameters:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
    
    Returns:
        List[UserResponse]: List of user profiles
    """
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return users

@user_router.get("/{user_id}", response_model=UserResponse, 
                summary="Get User by ID", description="Returns a specific user's information (admin only)")
@limiter.limit("10/minute")
async def get_user(
    request: Request, 
    user_id: int, 
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """
    Retrieves a specific user by their ID.
    
    - Requires admin privileges
    - Finds and returns the user profile for the specified ID
    
    Parameters:
        user_id: ID of the user to retrieve
    
    Returns:
        UserResponse: The requested user's profile
    
    Raises:
        HTTPException: 404 error if user not found
    """
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

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
    
    return db_user

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



# -------------- api key ------------------

@api_key_router.post("/", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED,
                    summary="Create API Key", description="Creates a new API key for the current user")
async def create_api_key(
    api_key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Creates a new API key for the authenticated user.
    
    - Generates a secure random API key
    - Associates it with the current user
    - Optionally sets an expiration date
    - Returns the full API key (only shown once)
    
    Parameters:
        api_key_data: Contains key name and optional expiration
    
    Returns:
        ApiKeyResponse: The created API key with full key value
    
    Note: The full API key is only returned once during creation
    """
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
        
        # Publish API key creation event
        publish_message("user_events", {
            "event_type": "api_key_created",
            "user_id": current_user.id,
            "username": current_user.username,
            "key_name": api_key_data.key_name,
            "key_id": db_api_key.id,
            "expires_at": api_key_data.expires_at.isoformat() if api_key_data.expires_at else None,
            "timestamp": datetime.now().isoformat()
        })
        
        return db_api_key
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )

@api_key_router.get("/", response_model=List[ApiKeyListResponse],
                   summary="List API Keys", description="Lists all API keys for the current user")
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Lists all API keys for the authenticated user.
    
    - Returns API keys with preview (masked) values for security
    - Shows key status, expiration, and usage information
    
    Returns:
        List[ApiKeyListResponse]: List of user's API keys with masked values
    """
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

@api_key_router.get("/{key_id}", response_model=ApiKeyListResponse,
                   summary="Get API Key", description="Gets a specific API key by ID")
async def get_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Retrieves a specific API key by ID.
    
    - Only returns API keys owned by the current user
    - Returns masked API key value for security
    
    Parameters:
        key_id: ID of the API key to retrieve
    
    Returns:
        ApiKeyListResponse: The API key with masked value
    
    Raises:
        HTTPException: 404 if key not found or not owned by user
    """
    api_key = session.exec(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id
        )
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    key_dict = api_key.model_dump()
    key_dict["api_key_preview"] = get_api_key_preview(api_key.api_key)
    
    return ApiKeyListResponse(**key_dict)

@api_key_router.put("/{key_id}", response_model=ApiKeyListResponse,
                   summary="Update API Key", description="Updates an API key's properties")
async def update_api_key(
    key_id: int,
    api_key_update: ApiKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Updates an API key's properties.
    
    - Can update key name, active status, and expiration
    - Cannot update the actual API key value
    - Only allows updates to keys owned by the current user
    
    Parameters:
        key_id: ID of the API key to update
        api_key_update: Properties to update
    
    Returns:
        ApiKeyListResponse: The updated API key
    
    Raises:
        HTTPException: 404 if key not found or not owned by user
    """
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
    
    # Update fields if provided
    update_data = api_key_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_api_key, key, value)
    
    db_api_key.updated_at = datetime.now()
    
    try:
        session.add(db_api_key)
        session.commit()
        session.refresh(db_api_key)
        
        logger.info(f"API key '{db_api_key.key_name}' updated for user {current_user.username}")
        
        # Publish API key update event
        publish_message("user_events", {
            "event_type": "api_key_updated",
            "user_id": current_user.id,
            "username": current_user.username,
            "key_name": db_api_key.key_name,
            "key_id": db_api_key.id,
            "updated_fields": list(update_data.keys()),
            "timestamp": datetime.now().isoformat()
        })
        
        key_dict = db_api_key.model_dump()
        key_dict["api_key_preview"] = get_api_key_preview(db_api_key.api_key)
        
        return ApiKeyListResponse(**key_dict)
        
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key"
        )

@api_key_router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT,
                      summary="Delete API Key", description="Deletes an API key")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Deletes an API key.
    
    - Permanently removes the API key from the system
    - Only allows deletion of keys owned by the current user
    - Cannot be undone
    
    Parameters:
        key_id: ID of the API key to delete
    
    Returns:
        None: Returns 204 No Content on success
    
    Raises:
        HTTPException: 404 if key not found or not owned by user
    """
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
    
    # Store info for event publishing
    key_info = {
        "key_name": db_api_key.key_name,
        "key_id": db_api_key.id
    }
    
    try:
        session.delete(db_api_key)
        session.commit()
        
        logger.info(f"API key '{key_info['key_name']}' deleted for user {current_user.username}")
        
        # Publish API key deletion event
        publish_message("user_events", {
            "event_type": "api_key_deleted",
            "user_id": current_user.id,
            "username": current_user.username,
            "key_name": key_info["key_name"],
            "key_id": key_info["key_id"],
            "timestamp": datetime.now().isoformat()
        })
        
        return None
        
    except Exception as e:
        logger.error(f"Error deleting API key: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )

@api_key_router.post("/{key_id}/regenerate", response_model=ApiKeyResponse,
                    summary="Regenerate API Key", description="Regenerates a new API key value")
async def regenerate_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Regenerates a new API key value for an existing API key.
    
    - Creates a new random API key value
    - Keeps the same name and settings
    - Invalidates the old API key immediately
    - Returns the new API key (only shown once)
    
    Parameters:
        key_id: ID of the API key to regenerate
    
    Returns:
        ApiKeyResponse: The API key with new value
    
    Raises:
        HTTPException: 404 if key not found or not owned by user
    
    Note: The old API key becomes invalid immediately
    """
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
    
    # Store old key for logging
    old_key_preview = get_api_key_preview(db_api_key.api_key)
    
    # Generate new API key
    new_api_key = generate_api_key()
    db_api_key.api_key = new_api_key
    db_api_key.updated_at = datetime.now()
    
    try:
        session.add(db_api_key)
        session.commit()
        session.refresh(db_api_key)
        
        logger.info(f"API key '{db_api_key.key_name}' regenerated for user {current_user.username}")
        
        # Publish API key regeneration event
        publish_message("user_events", {
            "event_type": "api_key_regenerated",
            "user_id": current_user.id,
            "username": current_user.username,
            "key_name": db_api_key.key_name,
            "key_id": db_api_key.id,
            "old_key_preview": old_key_preview,
            "timestamp": datetime.now().isoformat()
        })
        
        return db_api_key
        
    except Exception as e:
        logger.error(f"Error regenerating API key: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate API key"
        )


# ADD THIS NEW ROUTE
@user_router.get("/me/api-key", response_model=UserResponse, 
                summary="Get Current User via API Key", 
                description="Returns the current user information using API key authentication")
async def get_current_user_via_api_key(
    current_user: User = Depends(get_current_user_from_api_key)
):
    """
    Returns the profile information of the currently authenticated user via API key.
    
    - Requires a valid API key in X-API-Key header
    - Returns the user's profile data
    
    Returns:
        UserResponse: The current user's profile information
    """
    return current_user
