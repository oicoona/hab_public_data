"""
FastAPI dependencies
"""
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
import redis
from backend.db.session import get_db
from backend.core.cache import redis_client


def get_redis_client() -> redis.Redis:
    """
    Dependency to get Redis client
    """
    return redis_client


def get_anthropic_api_key(x_anthropic_api_key: str = Header(None)) -> str:
    """
    Dependency to extract Anthropic API key from request header
    
    Args:
        x_anthropic_api_key: API key from X-Anthropic-API-Key header
        
    Returns:
        API key string
        
    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    if not x_anthropic_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Anthropic-API-Key header. Please provide your Anthropic API key."
        )
    
    if not x_anthropic_api_key.startswith("sk-ant-"):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format. Anthropic API keys start with 'sk-ant-'."
        )
    
    return x_anthropic_api_key


# Re-export get_db for convenience
__all__ = ["get_db", "get_redis_client", "get_anthropic_api_key"]
