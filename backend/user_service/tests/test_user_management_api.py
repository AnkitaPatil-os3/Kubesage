import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import User
from app.auth import get_password_hash
from typing import List, Dict
import concurrent.futures

def test_admin_change_password_for_multiple_users(
    client: TestClient, 
    admin_token: str, 
    test_users: List[User]
):
    # Admin changes password for multiple regular users
    regular_users = [user for user in test_users if not user.is_admin][:3]  # Take first 3 regular users
    
    for user in regular_users:
        response = client.post(
            f"/auth/change-password/{user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"new_password": f"newpass_{user.username}", "confirm_password": f"newpass_{user.username}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password updated successfully"
        
        # Verify the new password works
        response = client.post(
            "/auth/token",
            data={"username": user.username, "password": f"newpass_{user.username}"}
        )
        assert response.status_code == 200

# def test_read_users_me_multiple_users(
#     client: TestClient, 
#     user_tokens: Dict[str, str], 
#     test_users: List[User]
# ):
#     for user in test_users:
#         token = user_tokens[user.username]
#         response = client.get(
#             "/users/me",
#             headers={"Authorization": f"Bearer {token}"}
#         )
#         assert response.status_code == 200
#         data = response.json()
#         assert data["username"] == user.username
#         assert data["email"] == user.email

# def test_concurrent_profile_access(
#     client: TestClient, 
#     user_tokens: Dict[str, str], 
#     test_users: List[User]
# ):
#     def access_profile(user):
#         token = user_tokens[user.username]
#         return client.get(
#             "/users/me",
#             headers={"Authorization": f"Bearer {token}"}
#         )
    
#     # Use ThreadPoolExecutor for concurrent requests
#     with concurrent.futures.ThreadPoolExecutor(max_workers=len(test_users)) as executor:
#         responses = list(executor.map(access_profile, test_users))
    
#     # Verify all responses
#     for i, response in enumerate(responses):
#         assert response.status_code == 200
#         data = response.json()
#         assert data["username"] == test_users[i].username



# def test_list_users_by_admins(
#     client: TestClient, 
#     user_tokens: Dict[str, str], 
#     test_users: List[User]
# ):
#     admin_users = [user for user in test_users if user.is_admin]
    
#     for admin in admin_users:
#         token = user_tokens[admin.username]
#         response = client.get(
#             "/users/",
#             headers={"Authorization": f"Bearer {token}"}
#         )
#         assert response.status_code == 200
#         data = response.json()
#         assert isinstance(data, list)
#         assert len(data) >= len(test_users)  # Should return at least all our test users

# def test_update_multiple_users(
#     client: TestClient, 
#     admin_token: str, 
#     test_users: List[User]
# ):
#     # Update multiple regular users
#     regular_users = [user for user in test_users if not user.is_admin][:3]
    
#     for i, user in enumerate(regular_users):
#         update_data = {
#             "first_name": f"Updated{i}",
#             "last_name": f"Name{i}"
#         }
#         response = client.put(
#             f"/users/{user.id}",
#             headers={"Authorization": f"Bearer {admin_token}"},
#             json=update_data
#         )
#         assert response.status_code == 200
#         data = response.json()
#         assert data["first_name"] == update_data["first_name"]
#         assert data["last_name"] == update_data["last_name"]

# def test_delete_multiple_users(
#     client: TestClient, 
#     admin_token: str, 
#     session: Session
# ):
#     # Create multiple users to delete
#     users_to_delete = []
#     for i in range(1, 4):
#         new_user = User(
#             username=f"todelete{i}",
#             email=f"delete{i}@example.com",
#             hashed_password=get_password_hash("password123"),
#             first_name=f"ToDelete{i}",
#             last_name="User",
#             is_active=True,
#             is_admin=False
#         )
#         session.add(new_user)
#         users_to_delete.append(new_user)
    
#     session.commit()
    
#     # Refresh all users to get their IDs
#     for user in users_to_delete:
#         session.refresh(user)
    
#     # Delete each user and verify
#     for user in users_to_delete:
#         response = client.delete(
#             f"/users/{user.id}",
#             headers={"Authorization": f"Bearer {admin_token}"}
#         )
#         assert response.status_code == 204
        
#         # Verify user is deleted
#         response = client.get(
#             f"/users/{user.id}",
#             headers={"Authorization": f"Bearer {admin_token}"}
#         )
#         assert response.status_code == 404
