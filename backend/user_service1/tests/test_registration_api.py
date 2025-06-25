import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User
import concurrent.futures
from typing import List

def test_register_multiple_users(client: TestClient):
    # Create 5 new users to register
    new_users = [
        {
            "username": f"newuser{i}",
            "email": f"new{i}@example.com",
            "password": f"newpassword{i}",
            "first_name": f"New{i}",
            "last_name": "User",
            "is_active": True,
            "is_admin": False
        }
        for i in range(1, 6)
    ]
    
    # Register each user
    for new_user in new_users:
        response = client.post("/auth/register", json=new_user)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == new_user["username"]
        assert data["email"] == new_user["email"]
        assert "hashed_password" not in data

# def test_concurrent_user_registration(client: TestClient):
#     # Create 5 more users to register concurrently
#     new_users = [
#         {
#             "username": f"concurrent{i}",
#             "email": f"concurrent{i}@example.com",
#             "password": f"concurrent{i}",
#             "first_name": f"Concurrent{i}",
#             "last_name": "User",
#             "is_active": True,
#             "is_admin": False
#         }
#         for i in range(1, 6)
#     ]
    
#     def register_user(user_data):
#         return client.post("/auth/register", json=user_data)
    
#     # Use ThreadPoolExecutor for concurrent requests
#     with concurrent.futures.ThreadPoolExecutor(max_workers=len(new_users)) as executor:
#         responses = list(executor.map(register_user, new_users))
    
#     # Verify all responses
#     for response in responses:
#         assert response.status_code == 201
#         data = response.json()
#         assert "username" in data
#         assert "email" in data

def test_register_duplicate_usernames(client: TestClient, test_users: List[User]):
    # Try to register users with existing usernames
    for user in test_users[:2]:  # Just test with a couple of users
        new_user = {
            "username": user.username,  # Duplicate username
            "email": f"different_{user.username}@example.com",
            "password": "password123",
            "first_name": "Duplicate",
            "last_name": "User",
            "is_active": True,
            "is_admin": False
        }
        response = client.post("/auth/register", json=new_user)
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

def test_register_duplicate_emails(client: TestClient, test_users: List[User]):
    # Try to register users with existing emails
    for user in test_users[:2]:  # Just test with a couple of users
        new_user = {
            "username": f"different_{user.username}",
            "email": user.email,  # Duplicate email
            "password": "password123",
            "first_name": "Duplicate",
            "last_name": "User",
            "is_active": True,
            "is_admin": False
        }
        response = client.post("/auth/register", json=new_user)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]





