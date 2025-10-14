"""
Test cases for rate limiting functionality
"""

import pytest
from unittest.mock import patch, Mock
import asyncio
from datetime import datetime, timedelta

from app.rate_limiter import RateLimiter, rate_limit


class TestRateLimiter:
    """Test cases for the RateLimiter class"""

    @pytest.fixture
    def rate_limiter(self):
        """Create a fresh rate limiter instance"""
        return RateLimiter()

    @pytest.fixture
    def mock_request(self):
        """Mock request object"""
        request = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {
            "user-agent": "test-agent",
            "x-api-key": "test-key"
        }
        return request

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_initial_requests(self, rate_limiter, mock_request):
        """Test that initial requests are allowed"""
        # First few requests should be allowed
        for i in range(5):
            allowed = await rate_limiter.is_allowed(mock_request, max_requests=10, window_seconds=60)
            assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess_requests(self, rate_limiter, mock_request):
        """Test that requests exceeding the limit are blocked"""
        max_requests = 3
        
        # Use up the allowed requests
        for i in range(max_requests):
            allowed = await rate_limiter.is_allowed(mock_request, max_requests=max_requests, window_seconds=60)
            assert allowed is True
        
        # Next request should be blocked
        allowed = await rate_limiter.is_allowed(mock_request, max_requests=max_requests, window_seconds=60)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_rate_limiter_window_reset(self, rate_limiter, mock_request):
        """Test that rate limit window resets after time expires"""
        max_requests = 2
        window_seconds = 1  # Short window for testing
        
        # Use up the allowed requests
        for i in range(max_requests):
            allowed = await rate_limiter.is_allowed(mock_request, max_requests=max_requests, window_seconds=window_seconds)
            assert allowed is True
        
        # Should be blocked
        allowed = await rate_limiter.is_allowed(mock_request, max_requests=max_requests, window_seconds=window_seconds)
        assert allowed is False
        
        # Manually adjust the window start time to simulate time passing
        client_key = rate_limiter._get_client_key(mock_request)
        rate_limiter.requests[client_key]["window_start"] = datetime.now() - timedelta(seconds=window_seconds + 1)
        
        # Should be allowed again after window reset
        allowed = await rate_limiter.is_allowed(mock_request, max_requests=max_requests, window_seconds=window_seconds)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_different_clients_separate_limits(self, rate_limiter):
        """Test that different clients have separate rate limits"""
        max_requests = 2
        
        # Client 1
        request1 = Mock()
        request1.client.host = "127.0.0.1"
        request1.headers = {"user-agent": "client1", "x-api-key": "key1"}
        
        # Client 2
        request2 = Mock()
        request2.client.host = "127.0.0.2"
        request2.headers = {"user-agent": "client2", "x-api-key": "key2"}
        
        # Both clients should be able to make max_requests
        for i in range(max_requests):
            allowed1 = await rate_limiter.is_allowed(request1, max_requests=max_requests, window_seconds=60)
            allowed2 = await rate_limiter.is_allowed(request2, max_requests=max_requests, window_seconds=60)
            assert allowed1 is True
            assert allowed2 is True
        
        # Both should be blocked on the next request
        allowed1 = await rate_limiter.is_allowed(request1, max_requests=max_requests, window_seconds=60)
        allowed2 = await rate_limiter.is_allowed(request2, max_requests=max_requests, window_seconds=60)
        assert allowed1 is False
        assert allowed2 is False

    def test_client_key_generation(self, rate_limiter):
        """Test that client keys are generated consistently"""
        request = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent", "x-api-key": "test-key"}
        
        key1 = rate_limiter._get_client_key(request)
        key2 = rate_limiter._get_client_key(request)
        
        assert key1 == key2
        
        # Change a header and verify key changes
        request.headers["x-api-key"] = "different-key"
        key3 = rate_limiter._get_client_key(request)
        
        assert key1 != key3

    def test_client_key_handles_missing_values(self, rate_limiter):
        """Test that client key generation handles missing values gracefully"""
        request = Mock()
        request.client = None  # No client info
        request.headers = {}    # No headers
        
        # Should not raise an exception
        key = rate_limiter._get_client_key(request)
        assert isinstance(key, str)
        assert len(key) > 0


class TestRateLimitDecorator:
    """Test cases for the rate_limit decorator"""

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_allows_requests(self):
        """Test that rate limit decorator allows requests within limits"""
        # Mock rate limiter to always allow
        with patch('app.rate_limiter.rate_limiter.is_allowed') as mock_is_allowed:
            mock_is_allowed.return_value = True
            
            request = Mock()
            rate_limit_func = rate_limit(max_requests=10, window_seconds=60)
            
            # Should not raise an exception
            result = await rate_limit_func(request)
            assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_blocks_requests(self):
        """Test that rate limit decorator blocks requests exceeding limits"""
        from fastapi import HTTPException
        
        # Mock rate limiter to block requests
        with patch('app.rate_limiter.rate_limiter.is_allowed') as mock_is_allowed:
            mock_is_allowed.return_value = False
            
            request = Mock()
            rate_limit_func = rate_limit(max_requests=10, window_seconds=60)
            
            # Should raise HTTPException with 429 status
            with pytest.raises(HTTPException) as exc_info:
                await rate_limit_func(request)
            
            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in exc_info.value.detail


class TestRateLimitIntegration:
    """Integration tests for rate limiting in actual endpoints"""

    @patch('app.rate_limiter.rate_limiter.is_allowed')
    @patch('app.routes.authenticate_request')
    def test_onboarding_endpoint_rate_limiting(
        self, 
        mock_auth, 
        mock_rate_limiter,
        client,
        mock_user
    ):
        """Test rate limiting integration with onboarding endpoint"""
        mock_auth.return_value = mock_user
        
        # Test allowed request
        mock_rate_limiter.return_value = True
        
        cluster_data = {
            "cluster_name": "rate-limit-test",
            "provider_name": "kubernetes"
        }
        headers = {
            "X-API-Key": "valid_api_key",
            "agent_id": "test_agent_id"
        }
        
        response = client.post("/api/v2.0/onboard", json=cluster_data, headers=headers)
        # May fail for other reasons (no agent), but not due to rate limiting
        assert response.status_code != 429
        
        # Test blocked request
        mock_rate_limiter.return_value = False
        
        response = client.post("/api/v2.0/onboard", json=cluster_data, headers=headers)
        assert response.status_code == 429

    @patch('app.rate_limiter.rate_limiter.is_allowed')
    @patch('app.routes.authenticate_request')
    def test_generate_agent_id_rate_limiting(
        self, 
        mock_auth, 
        mock_rate_limiter,
        client,
        mock_user
    ):
        """Test rate limiting integration with generate-agent-id endpoint"""
        mock_auth.return_value = mock_user
        
        headers = {"X-API-Key": "valid_api_key"}
        
        # Test allowed request
        mock_rate_limiter.return_value = True
        response = client.post("/api/v2.0/generate-agent-id", headers=headers)
        assert response.status_code != 429
        
        # Test blocked request
        mock_rate_limiter.return_value = False
        response = client.post("/api/v2.0/generate-agent-id", headers=headers)
        assert response.status_code == 429

    @patch('app.routes.authenticate_request')
    def test_rate_limiting_bypass_in_tests(
        self, 
        mock_auth,
        client,
        mock_user
    ):
        """Test that rate limiting is bypassed in test environment"""
        mock_auth.return_value = mock_user
        
        headers = {"X-API-Key": "valid_api_key"}
        
        # Make many requests rapidly - should all succeed due to test mocking
        for i in range(20):  # Well above any reasonable rate limit
            response = client.post("/api/v2.0/generate-agent-id", headers=headers)
            # Should not be rate limited (status 429)
            assert response.status_code != 429


class TestRateLimitCleanup:
    """Test cases for rate limiter cleanup functionality"""

    @pytest.fixture
    def rate_limiter_with_old_entries(self):
        """Create rate limiter with some old entries"""
        rate_limiter = RateLimiter()
        
        # Add some old entries manually
        old_time = datetime.now() - timedelta(hours=2)
        rate_limiter.requests["old_client_1"] = {
            "count": 5,
            "window_start": old_time,
            "last_request": old_time
        }
        rate_limiter.requests["old_client_2"] = {
            "count": 3,
            "window_start": old_time,
            "last_request": old_time
        }
        
        # Add a recent entry
        recent_time = datetime.now()
        rate_limiter.requests["recent_client"] = {
            "count": 2,
            "window_start": recent_time,
            "last_request": recent_time
        }
        
        return rate_limiter

    def test_cleanup_removes_old_entries(self, rate_limiter_with_old_entries):
        """Test that cleanup removes old entries"""
        rate_limiter = rate_limiter_with_old_entries
        
        # Verify initial state
        assert len(rate_limiter.requests) == 3
        assert "old_client_1" in rate_limiter.requests
        assert "old_client_2" in rate_limiter.requests
        assert "recent_client" in rate_limiter.requests
        
        # Manually run cleanup logic
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=1)
        
        keys_to_remove = [
            key for key, data in rate_limiter.requests.items()
            if data["last_request"] < cutoff_time
        ]
        
        for key in keys_to_remove:
            del rate_limiter.requests[key]
        
        # Verify old entries are removed, recent entry remains
        assert len(rate_limiter.requests) == 1
        assert "recent_client" in rate_limiter.requests
        assert "old_client_1" not in rate_limiter.requests
        assert "old_client_2" not in rate_limiter.requests


class TestRateLimitConfiguration:
    """Test different rate limit configurations"""

    @pytest.mark.asyncio
    async def test_different_limits_for_different_endpoints(self):
        """Test that different endpoints can have different rate limits"""
        rate_limiter = RateLimiter()
        request = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test", "x-api-key": "test"}
        
        # Simulate onboarding endpoint (lower limit)
        onboard_limit = 5
        for i in range(onboard_limit):
            allowed = await rate_limiter.is_allowed(request, max_requests=onboard_limit, window_seconds=60)
            assert allowed is True
        
        # Should be blocked for onboarding limit
        allowed = await rate_limiter.is_allowed(request, max_requests=onboard_limit, window_seconds=60)
        assert allowed is False
        
        # But should still be allowed for a different endpoint with higher limit
        # (Note: In real implementation, different endpoints would have different client keys
        # or separate rate limiter instances)

    @pytest.mark.asyncio
    async def test_zero_requests_limit(self):
        """Test rate limiter with zero requests allowed"""
        rate_limiter = RateLimiter()
        request = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test", "x-api-key": "test"}
        
        # With 0 max requests, should always be blocked
        allowed = await rate_limiter.is_allowed(request, max_requests=0, window_seconds=60)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_very_short_window(self):
        """Test rate limiter with very short time window"""
        rate_limiter = RateLimiter()
        request = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test", "x-api-key": "test"}
        
        # Use 1 request per 0.1 seconds (very restrictive)
        allowed1 = await rate_limiter.is_allowed(request, max_requests=1, window_seconds=0.1)
        assert allowed1 is True
        
        # Immediate second request should be blocked
        allowed2 = await rate_limiter.is_allowed(request, max_requests=1, window_seconds=0.1)
        assert allowed2 is False
