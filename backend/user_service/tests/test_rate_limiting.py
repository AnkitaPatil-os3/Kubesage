import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import User
from typing import Dict, List

def test_rate_limiting_users_me(client: TestClient, user_tokens: Dict[str, str], test_users: List[User]):
    """Test that rate limiting works for the /users/me endpoint"""
    
    # Get a regular user token
    regular_user = next(user for user in test_users if not user.is_admin)
    token = user_tokens[regular_user.username]
    
    # Make 12 requests (should hit rate limit after 10)
    responses = []
    for i in range(12):
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        responses.append(response.status_code)
    
    # Check that the first 10 requests succeeded
    assert responses[:10] == [200] * 10
    
    # Check that requests 11 and 12 were rate limited
    assert responses[10:] == [429, 429]
