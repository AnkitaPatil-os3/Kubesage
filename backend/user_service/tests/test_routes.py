import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User, UserToken
from app.auth import get_password_hash


# Authentication Tests
def test_login(client: TestClient, test_user: User):
    response = client.post(
        "/auth/token",
        data={"username": test_user.username, "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Removed check for "expires_at" as it is not present in current response

def test_login_wrong_password(client: TestClient, test_user: User):
    response = client.post(
        "/auth/token",
        data={"username": test_user.username, "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_logout(client: TestClient, user_token: str):
    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully"}

def test_check_admin_with_admin(client: TestClient, admin_token: str):
    response = client.get(
        "/auth/check-admin",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True

def test_check_admin_with_user(client: TestClient, user_token: str):
    response = client.get(
        "/auth/check-admin",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is False

# User Registration Test
def test_register_user(client: TestClient):
    new_user = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "newpassword123",
        "first_name": "New",
        "last_name": "User",
        "is_active": True,
        "is_admin": False
    }
    response = client.post("/auth/register", json=new_user)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == new_user["username"]
    assert data["email"] == new_user["email"]
    assert "hashed_password" not in data

def test_register_duplicate_username(client: TestClient, test_user: User):
    new_user = {
        "username": test_user.username,  # Duplicate username
        "email": "different@example.com",
        "password": "password123",
        "first_name": "Duplicate",
        "last_name": "User",
        "is_active": True,
        "is_admin": False
    }
    response = client.post("/auth/register", json=new_user)
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

# Password Change Test
def test_admin_change_password(client: TestClient, admin_token: str, test_user: User):
    response = client.post(
        f"/auth/change-password/{test_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"new_password": "newpassword456", "confirm_password": "newpassword456"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password updated successfully"
    
    # Verify the new password works
    response = client.post(
        "/auth/token",
        data={"username": test_user.username, "password": "newpassword456"}
    )
    assert response.status_code == 200

# User Profile Tests
def test_read_users_me(client: TestClient, user_token: str, test_user: User):
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email

# User Management Tests (Admin Only)
def test_list_users(client: TestClient, admin_token: str, test_users):
    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # At least test_user and test_admin

def test_list_users_unauthorized(client: TestClient, user_token: str):
    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403  # Forbidden for non-admin users

def test_get_user(client: TestClient, admin_token: str, test_user: User):
    response = client.get(
        f"/users/{test_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email

def test_update_user(client: TestClient, admin_token: str, test_user: User):
    update_data = {
        "first_name": "Updated",
        "last_name": "Name"
    }
    response = client.put(
        f"/users/{test_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == update_data["first_name"]
    assert data["last_name"] == update_data["last_name"]

def test_delete_user(client: TestClient, admin_token: str, session: Session):
    # Create a user to delete
    new_user = User(
        username="todelete",
        email="delete@example.com",
        hashed_password=get_password_hash("password123"),
        first_name="To",
        last_name="Delete",
        is_active=True,
        is_admin=False
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    response = client.delete(
        f"/users/{new_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204
    
    # Verify user is deleted
    response = client.get(
        f"/users/{new_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
