import json
from redis import Redis
from app.config import settings
from app.logger import logger
from typing import Any, Dict, Optional, Union
from functools import wraps

# Initialize Redis connection
try:
    redis_client = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Redis connection established")
except Exception as e:
    logger.warning(f"Redis connection failed: {str(e)}")
    redis_client = None

def get_cache_key(key_type: str, identifier: Union[str, int]) -> str:
    """Generate a cache key"""
    return f"langgraph:{key_type}:{identifier}"

def get_user_sessions_key(user_id: int) -> str:
    """Generate a cache key for user sessions list"""
    return get_cache_key("user_sessions", user_id)

def get_session_key(session_id: str) -> str:
    """Generate a cache key for chat session"""
    return get_cache_key("session", session_id)

def get_messages_key(session_id: str) -> str:
    """Generate a cache key for chat messages"""
    return get_cache_key("messages", session_id)

def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache"""
    if not redis_client:
        return None
    
    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Error getting from cache: {str(e)}")
        return None

def cache_set(key: str, value: Any, expire_seconds: int = 3600) -> bool:
    """Set a value in cache with expiration"""
    if not redis_client:
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
        return False
    
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error deleting from cache: {str(e)}")
        return False

def invalidate_user_cache(user_id: int) -> bool:
    """Invalidate all user-related cache entries"""
    if not redis_client:
        return False
    
    try:
        user_pattern = f"langgraph:user*:{user_id}*"
        session_pattern = f"langgraph:session:user:{user_id}:*"
        
        keys = redis_client.keys(user_pattern) + redis_client.keys(session_pattern)
        
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error invalidating user cache: {str(e)}")
        return False