"""
Redis cache management for API responses and database queries
"""
import json
import logging
from typing import Optional, Any, Dict
import redis
from server.config import config

logger = logging.getLogger(__name__)

# Redis connection pool
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client"""
    global _redis_client
    
    if not config.cache_enabled:
        return None
    
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
                password=config.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            _redis_client.ping()
            logger.info(f"Redis cache connected: {config.redis_host}:{config.redis_port}")
        except Exception as e:
            logger.warning(f"Redis cache not available: {e}. Continuing without cache.")
            _redis_client = None
    
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    """Get value from cache"""
    if not config.cache_enabled:
        return None
    
    client = get_redis_client()
    if not client:
        return None
    
    try:
        value = client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
    except Exception as e:
        logger.warning(f"Cache get error for key {key}: {e}")
    
    return None


def cache_set(key: str, value: Any, ttl: int = 60) -> bool:
    """Set value in cache with TTL"""
    if not config.cache_enabled:
        return False
    
    client = get_redis_client()
    if not client:
        return False
    
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        client.setex(key, ttl, value)
        return True
    except Exception as e:
        logger.warning(f"Cache set error for key {key}: {e}")
    
    return False


def cache_delete(key: str) -> bool:
    """Delete value from cache"""
    if not config.cache_enabled:
        return False
    
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
    
    return False


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching pattern"""
    if not config.cache_enabled:
        return 0
    
    client = get_redis_client()
    if not client:
        return 0
    
    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache delete pattern error for {pattern}: {e}")
    
    return 0


def cache_clear_all() -> bool:
    """Clear all cache"""
    if not config.cache_enabled:
        return False
    
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.flushdb()
        logger.info("Cache cleared")
        return True
    except Exception as e:
        logger.warning(f"Cache clear error: {e}")
    
    return False


# Cache key generators
def cache_key_pending_tasks() -> str:
    """Generate cache key for pending tasks list"""
    return "cache:pending_tasks"


def cache_key_task(task_id: str) -> str:
    """Generate cache key for task"""
    return f"cache:task:{task_id}"


def cache_key_client_statistics(client_id: str) -> str:
    """Generate cache key for client statistics"""
    return f"cache:client_stats:{client_id}"


def cache_key_document(system_id: str) -> str:
    """Generate cache key for document"""
    return f"cache:document:{system_id}"


def cache_key_tasks_summary(status_filter: Optional[str] = None) -> str:
    """Generate cache key for tasks summary"""
    if status_filter:
        return f"cache:tasks_summary:{status_filter}"
    return "cache:tasks_summary:all"
