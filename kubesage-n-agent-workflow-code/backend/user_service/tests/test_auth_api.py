import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User, UserToken
from typing import List, Dict
import asyncio
import concurrent.futures

# Test login functionality with multiple users
def test_login_multiple_users(client: TestClient, test_users: List[User]):
    logged_in_users = []  # List to store successfully logged in users

    for user in test_users:
        print(f"Testing login for user: {user.username}")
        password = f"password{user.username[-1]}" if not user.is_admin else f"admin{user.username[-1]}password"
        
        response = client.post(
            "/auth/token",
            data={"username": user.username, "password": password}
        )
        assert response.status_code == 200, f"Login failed for user: {user.username}"
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data

        # Add user to the list of logged-in users
        logged_in_users.append(user.username)

    print("Successfully logged in users:", logged_in_users)

# Test concurrent login attempts
# def test_concurrent_login(client: TestClient, test_users: List[User]):
#     def login_user(user):
#         password = f"password{user.username[-1]}" if not user.is_admin else f"admin{user.username[-1]}password"
#         return client.post(
#             "/auth/token",
#             data={"username": user.username, "password": password}
#         )
    
#     # Use ThreadPoolExecutor for concurrent requests
#     with concurrent.futures.ThreadPoolExecutor(max_workers=len(test_users)) as executor:
#         responses = list(executor.map(login_user, test_users))
    
#     # Verify all responses
#     for response in responses:
#         assert response.status_code == 200
#         data = response.json()
#         assert "access_token" in data


def test_login_wrong_password(client: TestClient, test_users: List[User]):
    for user in test_users:
        response = client.post(
            "/auth/token",
            data={"username": user.username, "password": "wrongpassword"}
        )
        assert response.status_code == 401


def test_logout_multiple_users(client: TestClient, user_tokens: Dict[str, str], test_users: List[User]):
    for user in test_users:
        token = user_tokens[user.username]
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json() == {"message": "Successfully logged out"}


def test_check_admin_status(client: TestClient, user_tokens: Dict[str, str], test_users: List[User]):
    for user in test_users:
        token = user_tokens[user.username]
        response = client.get(
            "/auth/check-admin",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] == user.is_admin
        assert data["username"] == user.username








