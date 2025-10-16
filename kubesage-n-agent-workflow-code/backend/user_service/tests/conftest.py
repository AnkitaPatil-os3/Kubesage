import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
import os
from typing import Generator, List, Dict  # Added List and Dict for type hints
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import get_session
from app.models import User, UserToken
from app.auth import get_password_hash

# Use in-memory SQLite for testing
@pytest.fixture(name="session")
def session_fixture():
    """
    Creates an in-memory SQLite database session for testing.
    This ensures tests don't affect the real database and run in isolation.
    The StaticPool ensures that the same connection is used for all operations.
    """
    # Create an in-memory SQLite database engine
    # check_same_thread=False allows SQLite to be used with multiple threads
    # StaticPool ensures the same connection is used for all operations
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    
    # Create all tables defined in SQLModel metadata
    SQLModel.metadata.create_all(engine)
    
    # Create and yield a session
    with Session(engine) as session:
        yield session  # Provide the session to tests
        # After the test completes, the session will be closed automatically


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Creates a FastAPI TestClient with the test database session.
    This fixture depends on the session fixture and overrides the
    database session dependency in the FastAPI app.
    Also mocks the publish_message function to avoid actual message publishing during tests.
    """
    # Define a function to override the get_session dependency
    def get_session_override():
        return session  # Return our test session instead of creating a new one
    
    # Override the get_session dependency in the FastAPI app
    app.dependency_overrides[get_session] = get_session_override
    
    # Mock the publish_message function to prevent actual message queue operations
    # This ensures tests don't send real messages to external systems
    with patch("app.routes.publish_message", return_value=None):
        client = TestClient(app)  # Create the test client with our app
        yield client  # Provide the client to tests
    
    # Clean up after tests by removing the dependency override
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """
    Creates a standard test user in the database.
    This fixture depends on the session fixture to access the test database.
    """
    # Create a regular user object with predefined attributes
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),  # Hash the password for security
        first_name="Test",
        last_name="User",
        is_active=True,
        is_admin=False  # This is a regular user, not an admin
    )
    
    session.add(user)  # Add user to the database
    session.commit()  # Commit the transaction to save the user
    session.refresh(user)  # Refresh to get the ID and other DB-generated fields
    return user  # Provide the user to tests

@pytest.fixture(name="test_admin")
def test_admin_fixture(session: Session):
    """
    Creates an admin test user in the database.
    This fixture depends on the session fixture to access the test database.
    """
    # Create an admin user object with predefined attributes
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),  # Hash the password for security
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_admin=True  # This user has admin privileges
    )
    
    session.add(admin)  # Add admin to the database
    session.commit()  # Commit the transaction to save the admin
    session.refresh(admin)  # Refresh to get the ID and other DB-generated fields
    return admin  # Provide the admin to tests

@pytest.fixture(name="user_token")
def user_token_fixture(client: TestClient, test_user: User):
    """
    Gets an authentication token for the test user.
    This fixture depends on both the client and test_user fixtures.
    It performs an actual login request to get a valid token.
    """
    # Make a login request to get a token for the test user
    response = client.post(
        "/auth/token",
        data={"username": test_user.username, "password": "password123"}
    )
    # Extract and return just the token from the response
    return response.json()["access_token"]



@pytest.fixture(name="admin_token")
def admin_token_fixture(client: TestClient, test_admin: User):
    """
    Gets an authentication token for the admin user.
    This fixture depends on both the client and test_admin fixtures.
    It performs an actual login request to get a valid token.
    """
    # Make a login request to get a token for the admin user
    response = client.post(
        "/auth/token",
        data={"username": test_admin.username, "password": "admin123"}
    )
    # Extract and return just the token from the response
    return response.json()["access_token"]

@pytest.fixture(name="test_users")
def test_users_fixture(session: Session) -> List[User]:
    """
    Creates multiple test users (both regular and admin) for testing.
    This fixture depends on the session fixture to access the test database.
    Returns a list of User objects that can be used in tests requiring multiple users.
    """
    users = []  # List to store all created users
    
    # Create 5 regular users with sequential numbering
    for i in range(1, 6):
        user = User(
            username=f"testuser{i}",
            email=f"user{i}@example.com",
            hashed_password=get_password_hash(f"password{i}"),  # Each user has a unique password
            first_name=f"Test{i}",
            last_name="User",
            is_active=True,
            is_admin=False  # Regular users
        )
        session.add(user)  # Add to session
        users.append(user)  # Add to our list
    
    # Create 2 admin users with sequential numbering
    for i in range(1, 3):
        admin = User(
            username=f"admin{i}",
            email=f"admin{i}@example.com",
            hashed_password=get_password_hash(f"admin{i}password"),  # Admin passwords follow a different pattern
            first_name=f"Admin{i}",
            last_name="User",
            is_active=True,
            is_admin=True  # Admin users
        )
        session.add(admin)  # Add to session
        users.append(admin)  # Add to our list
    
    # Commit all users at once for efficiency
    session.commit()
    
    # Refresh all users to get their IDs and other DB-generated fields
    for user in users:
        session.refresh(user)
    
    return users  # Return the list of all users

@pytest.fixture(name="user_tokens")
def user_tokens_fixture(client: TestClient, test_users: List[User]) -> Dict[str, str]:
    """
    Gets authentication tokens for all test users.
    This fixture depends on both the client and test_users fixtures.
    Returns a dictionary mapping usernames to their tokens for easy access in tests.
    """
    tokens = {}  # Dictionary to store username -> token mapping
    
    # Get a token for each user
    for user in test_users:
        # Determine the password based on the user type and username
        # Regular users: password{number}, Admin users: admin{number}password
        password = f"password{user.username[-1]}" if not user.is_admin else f"admin{user.username[-1]}password"
        
        # Make a login request to get a token
        response = client.post(
            "/auth/token",
            data={"username": user.username, "password": password}
        )
        
        # Store the token in our dictionary, keyed by username
        tokens[user.username] = response.json()["access_token"]
    
    return tokens  # Return the dictionary of tokens
