from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio
from fastapi import HTTPException, Request
import hashlib
from app.config import settings
from app.logger import logger

class RateLimiter:
    """Simple in-memory rate limiter for API endpoints"""
    
    def __init__(self):
        self.requests: Dict[str, Dict] = {}
        self.cleanup_task = None
        
    def _get_client_key(self, request: Request) -> str:
        """Generate a unique key for the client"""
        try:
            # Use IP address and User-Agent for identification
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "")
            api_key = request.headers.get("x-api-key", "")
            
            # Create a hash of IP + User-Agent + API key for uniqueness
            key_data = f"{client_ip}:{user_agent}:{api_key}"
            return hashlib.md5(key_data.encode()).hexdigest()
        except Exception as e:
            # Fallback to a default key if there's any issue
            logger.warning(f"Error generating client key: {e}, using default")
            return "default_client"
    
    async def is_allowed(
        self,
        request: Request,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> bool:
        """Check if request is allowed based on rate limit"""
        try:
            if not settings.RATE_LIMIT_ENABLED:
                return True
                
            client_key = self._get_client_key(request)
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)
            
            # Clean up old requests for this client
            if client_key in self.requests:
                self.requests[client_key]["requests"] = [
                    req_time for req_time in self.requests[client_key]["requests"]
                    if req_time > window_start
                ]
            else:
                self.requests[client_key] = {"requests": []}
            
            # Check if limit exceeded
            current_requests = len(self.requests[client_key]["requests"])
            if current_requests >= max_requests:
                return False
            
            # Add current request
            self.requests[client_key]["requests"].append(now)
            return True
            
        except Exception as e:
            # If there's any error in rate limiting, allow the request to proceed
            # This ensures the service remains available even if rate limiting fails
            logger.warning(f"Rate limiting error: {e}, allowing request")
            return True

    async def cleanup_old_requests(self):
        """Periodic cleanup of old request records"""
        while True:
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                
                # Clean up requests older than 1 hour
                for client_key in list(self.requests.keys()):
                    self.requests[client_key]["requests"] = [
                        req_time for req_time in self.requests[client_key]["requests"]
                        if req_time > cutoff_time
                    ]
                    
                    # Remove empty entries
                    if not self.requests[client_key]["requests"]:
                        del self.requests[client_key]
                        
                await asyncio.sleep(3600)  # Run cleanup every hour
                
            except Exception:
                await asyncio.sleep(3600)  # Continue cleanup even if error occurs

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
        try:
            if not await rate_limiter.is_allowed(request, max_requests, window_seconds):
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
                )
            return True
        except HTTPException:
            # Re-raise HTTP exceptions (like rate limit exceeded)
            raise
        except Exception as e:
            # Log other errors but allow the request to proceed
            # This ensures the service remains available even if rate limiting fails
            logger.warning(f"Rate limit dependency error: {e}, allowing request")
            return True
    
    return rate_limit_dependency
