import json
from functools import wraps
from app.logger import logger
import redis
from app.config import settings

# Initialize Redis connection for caching
try:
    redis_cache = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=1  # Use different DB than queue
    )
    # Test connection
    redis_cache.ping()
    logger.info("Redis cache connection established")
except Exception as e:
    logger.warning(f"Redis cache connection failed: {str(e)}")
    redis_cache = None

def get_cache_key(user_id: int, key: str) -> str:
    """Generate a cache key specific to a user"""
    return f"user:{user_id}:{key}"

from app.redis_setup import redis_client
from app.logger import logger
import json
from typing import Any, Dict, Optional

def cache_get(key: str) -> Optional[Dict[str, Any]]:
    """Get a value from cache"""
    if not redis_client:
        logger.warning("Redis client not initialized")
        return None
    
    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Error getting from cache: {str(e)}")
        return None

def cache_set(key: str, value: Dict[str, Any], expire_seconds: int = 3600) -> bool:
    """Set a value in cache with expiration"""
    if not redis_client:
        logger.warning("Redis client not initialized")
        return False
    
    try:
        json_value = json.dumps(value)
        redis_client.set(key, json_value, ex=expire_seconds)
        return True
    except Exception as e:
        logger.error(f"Error setting cache: {str(e)}")
        return False

def cache_delete(key: str) -> bool:
    """Delete a value from cache"""
    if not redis_client:
        logger.warning("Redis client not initialized")
        return False
    
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error deleting from cache: {str(e)}")
        return False

def cache_flush_user(user_id: int) -> bool:
    """Flush all cache entries for a specific user"""
    if not redis_client:
        logger.warning("Redis client not initialized")
        return False
    
    try:
        # Find all keys for this user
        pattern = f"user:{user_id}:*"
        keys = redis_client.keys(pattern)
        
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Flushed {len(keys)} cache entries for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error flushing user cache: {str(e)}")
        return False

def user_cached(expiry: int = None):
    """Decorator to cache function results per user"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Look for current_user argument
            current_user = None
            for arg in args:
                if isinstance(arg, dict) and "id" in arg:
                    current_user = arg
                    break
            
            if not current_user and "current_user" in kwargs:
                current_user = kwargs["current_user"]
            
            if not current_user:
                # If no user found, just execute the function without caching
                return await func(*args, **kwargs)
            
            user_id = current_user["id"]
            
            # Create a cache key based on function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_result = cache_get(user_id, key)
            if cached_result is not None:
                logger.debug(f"Cache hit for user {user_id}: {key}")
                return cached_result
            
            # If not in cache, call the function
            logger.debug(f"Cache miss for user {user_id}: {key}")
            result = await func(*args, **kwargs)
            
            # Cache the result
            cache_set(user_id, key, result, expiry)
            
            return result
        return wrapper
    return decorator