"""
Redis client for caching and pub/sub functionality
"""

import os
import json
import asyncio
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import Redis
import logging

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# Cache TTL settings (in seconds)
POSITION_CACHE_TTL = 300  # 5 minutes
SECTION_STATUS_CACHE_TTL = 60  # 1 minute
TRAIN_INFO_CACHE_TTL = 3600  # 1 hour
RATE_LIMIT_TTL = 60  # 1 minute


class RedisClient:
    """Redis client wrapper with caching and pub/sub functionality"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.pubsub = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            if REDIS_URL:
                self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            else:
                self.redis = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=True
                )
            
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis:
            return False
        try:
            await self.redis.ping()
            return True
        except:
            return False
    
    # Caching methods
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        if not self.redis:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis:
            return False
        
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    # Rate limiting methods
    async def check_rate_limit(self, key: str, limit: int, window: int = 60) -> Dict[str, Any]:
        """Check rate limit for a key"""
        if not self.redis:
            return {"allowed": True, "remaining": limit, "reset_time": datetime.utcnow()}
        
        try:
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(seconds=window)
            
            # Use sliding window rate limiting
            pipe = self.redis.pipeline()
            
            # Remove old entries
            await pipe.zremrangebyscore(key, 0, window_start.timestamp())
            
            # Count current requests
            current_count = await pipe.zcard(key)
            
            if current_count >= limit:
                # Rate limit exceeded
                oldest_entry = await self.redis.zrange(key, 0, 0, withscores=True)
                reset_time = datetime.fromtimestamp(oldest_entry[0][1] + window) if oldest_entry else current_time
                
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "current_count": current_count
                }
            
            # Add current request
            await pipe.zadd(key, {str(current_time.timestamp()): current_time.timestamp()})
            await pipe.expire(key, window)
            await pipe.execute()
            
            return {
                "allowed": True,
                "remaining": limit - current_count - 1,
                "reset_time": current_time + timedelta(seconds=window),
                "current_count": current_count + 1
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error for key {key}: {e}")
            # Allow request on error
            return {"allowed": True, "remaining": limit, "reset_time": datetime.utcnow()}
    
    # Pub/Sub methods
    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish message to channel"""
        if not self.redis:
            return False
        
        try:
            serialized_message = json.dumps(message, default=str)
            await self.redis.publish(channel, serialized_message)
            return True
        except Exception as e:
            logger.error(f"Redis PUBLISH error for channel {channel}: {e}")
            return False
    
    async def subscribe(self, channels: List[str]):
        """Subscribe to channels"""
        if not self.redis:
            return None
        
        try:
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(*channels)
            return self.pubsub
        except Exception as e:
            logger.error(f"Redis SUBSCRIBE error: {e}")
            return None
    
    # Specialized caching methods for railway system
    async def cache_train_position(self, train_id: int, position_data: Dict[str, Any]) -> bool:
        """Cache latest train position"""
        key = f"train:position:{train_id}"
        return await self.set(key, position_data, POSITION_CACHE_TTL)
    
    async def get_train_position(self, train_id: int) -> Optional[Dict[str, Any]]:
        """Get cached train position"""
        key = f"train:position:{train_id}"
        return await self.get(key)
    
    async def cache_section_status(self, section_id: int, status_data: Dict[str, Any]) -> bool:
        """Cache section status"""
        key = f"section:status:{section_id}"
        return await self.set(key, status_data, SECTION_STATUS_CACHE_TTL)
    
    async def get_section_status(self, section_id: int) -> Optional[Dict[str, Any]]:
        """Get cached section status"""
        key = f"section:status:{section_id}"
        return await self.get(key)
    
    async def cache_train_info(self, train_id: int, train_data: Dict[str, Any]) -> bool:
        """Cache train information"""
        key = f"train:info:{train_id}"
        return await self.set(key, train_data, TRAIN_INFO_CACHE_TTL)
    
    async def get_train_info(self, train_id: int) -> Optional[Dict[str, Any]]:
        """Get cached train information"""
        key = f"train:info:{train_id}"
        return await self.get(key)
    
    async def invalidate_train_cache(self, train_id: int) -> bool:
        """Invalidate all cache entries for a train"""
        keys = [
            f"train:position:{train_id}",
            f"train:info:{train_id}"
        ]
        
        try:
            if self.redis:
                await self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache invalidation error for train {train_id}: {e}")
            return False
    
    async def get_active_trains(self) -> List[int]:
        """Get list of active train IDs from cache"""
        key = "trains:active"
        cached_data = await self.get(key)
        return cached_data if cached_data else []
    
    async def set_active_trains(self, train_ids: List[int]) -> bool:
        """Cache list of active train IDs"""
        key = "trains:active"
        return await self.set(key, train_ids, 300)  # 5 minutes TTL
    
    # Performance metrics
    async def increment_counter(self, key: str, ttl: int = 3600) -> int:
        """Increment counter with TTL"""
        if not self.redis:
            return 0
        
        try:
            pipe = self.redis.pipeline()
            await pipe.incr(key)
            await pipe.expire(key, ttl)
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Counter increment error for key {key}: {e}")
            return 0
    
    async def get_counter(self, key: str) -> int:
        """Get counter value"""
        if not self.redis:
            return 0
        
        try:
            value = await self.redis.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Counter get error for key {key}: {e}")
            return 0


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency to get Redis client"""
    if not redis_client.redis:
        await redis_client.connect()
    return redis_client


# Startup and shutdown events
async def startup_redis():
    """Initialize Redis connection on startup"""
    await redis_client.connect()


async def shutdown_redis():
    """Close Redis connection on shutdown"""
    await redis_client.disconnect()