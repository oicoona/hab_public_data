"""
Redis caching utilities
"""
import redis
import json
import hashlib
from backend.config import settings

# Initialize Redis client
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True
)


def get_cache_key(dataset_id: str, message: str) -> str:
    """
    Generate cache key from dataset_id and message
    
    Args:
        dataset_id: Dataset identifier
        message: User message
        
    Returns:
        MD5 hash of dataset_id:message
    """
    content = f"{dataset_id}:{message}"
    return f"chat:{hashlib.md5(content.encode()).hexdigest()}"


def get_cached_response(dataset_id: str, message: str) -> dict | None:
    """
    Retrieve cached response from Redis
    
    Args:
        dataset_id: Dataset identifier
        message: User message
        
    Returns:
        Cached response dict or None if not found
    """
    key = get_cache_key(dataset_id, message)
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    return None


def cache_response(dataset_id: str, message: str, response: dict, ttl: int = None) -> None:
    """
    Cache response in Redis with TTL
    
    Args:
        dataset_id: Dataset identifier
        message: User message
        response: Response dict to cache
        ttl: Time to live in seconds (default: from settings)
    """
    if ttl is None:
        ttl = settings.CACHE_TTL
    
    key = get_cache_key(dataset_id, message)
    redis_client.setex(key, ttl, json.dumps(response))
