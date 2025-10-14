from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio
from fastapi import HTTPException, Request
import hashlib

class RateLimiter:
    """Simple in-memory rate limiter for API endpoints"""
    
    def __init__(self):
        self.requests: Dict[str, Dict] = {}
        self.cleanup_task = None
        
    def _get_client_key(self, request: Request) -> str:
        """Generate a unique key for the client"""
        # Use IP address and User-Agent for identification
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        api_key = request.headers.get("x-api-key", "")
        
        # Create a hash of IP + User-Agent + API key for uniqueness
        key_data = f"{client_ip}:{user_agent}:{api_key}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def is_allowed(
        self,
        request: Request,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> bool:
        """
        Check if request is allowed based on rate limiting
        
        Args:
            request: FastAPI request object
            max_requests: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        client_key = self._get_client_key(request)
        current_time = datetime.now()
        
        # Initialize client record if not exists
        if client_key not in self.requests:
            self.requests[client_key] = {
                "count": 0,
                "window_start": current_time,
                "last_request": current_time
            }
        
        client_data = self.requests[client_key]
        
        # Check if we need to reset the window
        if current_time - client_data["window_start"] > timedelta(seconds=window_seconds):
            client_data["count"] = 0
            client_data["window_start"] = current_time
        
        # Check if request is allowed
        if client_data["count"] >= max_requests:
            return False
        
        # Update counters
        client_data["count"] += 1
        client_data["last_request"] = current_time
        
        # Start cleanup task if not running
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_old_entries())
        
        return True
    
    async def _cleanup_old_entries(self):
        """Clean up old entries to prevent memory leak"""
        while True:
            await asyncio.sleep(300)  # Cleanup every 5 minutes
            current_time = datetime.now()
            
            # Remove entries older than 1 hour
            cutoff_time = current_time - timedelta(hours=1)
            keys_to_remove = [
                key for key, data in self.requests.items()
                if data["last_request"] < cutoff_time
            ]
            
            for key in keys_to_remove:
                del self.requests[key]

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    Decorator for rate limiting endpoints
    
    Args:
        max_requests: Maximum requests allowed in the time window
        window_seconds: Time window in seconds
    """
    async def rate_limit_dependency(request: Request):
        if not await rate_limiter.is_allowed(request, max_requests, window_seconds):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
            )
        return True
    
    return rate_limit_dependency
