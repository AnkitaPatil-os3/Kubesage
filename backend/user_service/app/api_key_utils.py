import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.
    
    Args:
        length: Length of the API key (default: 32)
    
    Returns:
        str: Generated API key
    """
    # Use a combination of letters and digits
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"ks_{api_key}"  # Prefix with 'ks_' for KubeSage

def is_api_key_expired(expires_at: Optional[datetime]) -> bool:
    """
    Check if an API key is expired.
    
    Args:
        expires_at: Expiration datetime
    
    Returns:
        bool: True if expired, False otherwise
    """
    if expires_at is None:
        return False
    return datetime.now() > expires_at

def get_api_key_preview(api_key: str) -> str:
    """
    Get a preview of the API key for display purposes.
    
    Args:
        api_key: Full API key
    
    Returns:
        str: Preview of the API key (first 8 characters + asterisks)
    """
    if len(api_key) <= 8:
        return api_key
    return f"{api_key[:8]}{'*' * (len(api_key) - 8)}"
