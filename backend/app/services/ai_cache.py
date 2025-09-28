#!/usr/bin/env python3
"""
AI Cache Service - Phase 5 Performance Optimization
Provides intelligent caching for AI optimization results
"""

import json
import hashlib
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from app.redis_client import redis_client
from app.ai_config import AIConfig

# Initialize AI config
ai_config = AIConfig()


class CacheStatus(Enum):
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    INVALID = "invalid"


@dataclass
class CachedResult:
    """Cached AI optimization result"""
    result: Dict[Any, Any]
    confidence: float
    solver_method: str
    timestamp: datetime
    cache_key: str
    hits: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedResult':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class AICacheService:
    """
    Phase 5: AI Cache Service for Performance Optimization
    
    Provides intelligent caching for AI optimization results to:
    - Reduce redundant AI calculations
    - Improve response times
    - Track cache performance metrics
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or redis_client
        self.cache_prefix = "ai_cache:"
        self.metrics_prefix = "ai_cache_metrics:"
        
        # Cache configuration
        self.default_ttl = getattr(ai_config, "cache_ttl", 3600)  # 1 hour default
        self.max_cache_size = getattr(ai_config, "max_cache_size", 10000)
        self.cache_invalidation_threshold = getattr(ai_config, "cache_invalidation_threshold", 0.7)
        
        # Performance tracking
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'total_requests': 0
        }
    
    def _generate_cache_key(self, 
                          conflict_data: Dict[str, Any], 
                          solver_method: str = "default") -> str:
        """Generate deterministic cache key for optimization request"""
        # Create a stable representation of the conflict data
        stable_data = {
            'trains': sorted([
                {
                    'id': train.get('id', ''),
                    'position': train.get('position', {}),
                    'priority': train.get('priority', 0),
                    'speed': train.get('speed', 0)
                } 
                for train in conflict_data.get('trains', [])
            ], key=lambda x: x['id']),
            'section_id': conflict_data.get('section_id', ''),
            'conflict_type': conflict_data.get('conflict_type', ''),
            'solver_method': solver_method
        }
        
        # Generate hash
        stable_json = json.dumps(stable_data, sort_keys=True)
        cache_key = hashlib.md5(stable_json.encode()).hexdigest()
        
        return f"{self.cache_prefix}{cache_key}"
    
    async def get_cached_result(self, 
                               conflict_data: Dict[str, Any], 
                               solver_method: str = "default") -> Optional[CachedResult]:
        """
        Retrieve cached AI optimization result
        
        Args:
            conflict_data: Conflict information for optimization
            solver_method: AI solver method used
            
        Returns:
            CachedResult if found and valid, None otherwise
        """
        try:
            cache_key = self._generate_cache_key(conflict_data, solver_method)
            
            # Get from Redis
            cached_data = await self.redis_client.get(cache_key)
            
            if not cached_data:
                self.cache_stats['misses'] += 1
                self.cache_stats['total_requests'] += 1
                return None
            
            # Parse cached result
            cached_result = CachedResult.from_dict(json.loads(cached_data))
            
            # Check if cache entry is still valid
            if self._is_cache_valid(cached_result):
                # Update hit count
                cached_result.hits += 1
                await self._update_cached_result(cache_key, cached_result)
                
                self.cache_stats['hits'] += 1
                self.cache_stats['total_requests'] += 1
                
                return cached_result
            else:
                # Cache expired or invalid
                await self.invalidate_cache_key(cache_key)
                self.cache_stats['misses'] += 1
                self.cache_stats['total_requests'] += 1
                return None
                
        except Exception as e:
            print(f"Error retrieving cached result: {str(e)}")
            return None
    
    async def cache_result(self, 
                          conflict_data: Dict[str, Any], 
                          optimization_result: Dict[str, Any],
                          confidence: float,
                          solver_method: str = "default",
                          ttl: Optional[int] = None) -> bool:
        """
        Cache AI optimization result
        
        Args:
            conflict_data: Original conflict information
            optimization_result: AI optimization result to cache
            confidence: AI confidence score
            solver_method: AI solver method used
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(conflict_data, solver_method)
            
            cached_result = CachedResult(
                result=optimization_result,
                confidence=confidence,
                solver_method=solver_method,
                timestamp=datetime.utcnow(),
                cache_key=cache_key,
                hits=0
            )
            
            # Set TTL
            cache_ttl = ttl or self.default_ttl
            
            # Store in Redis
            await self.redis_client.setex(
                cache_key, 
                cache_ttl, 
                json.dumps(cached_result.to_dict())
            )
            
            # Update cache metrics
            await self._update_cache_metrics(cache_key, cached_result)
            
            return True
            
        except Exception as e:
            print(f"Error caching result: {str(e)}")
            return False
    
    async def invalidate_cache_key(self, cache_key: str) -> bool:
        """Invalidate specific cache key"""
        try:
            result = await self.redis_client.delete(cache_key)
            if result:
                self.cache_stats['invalidations'] += 1
            return bool(result)
        except Exception as e:
            print(f"Error invalidating cache key {cache_key}: {str(e)}")
            return False
    
    async def invalidate_related_cache(self, section_id: str) -> int:
        """
        Invalidate all cache entries related to a section
        (e.g., when track conditions change)
        """
        try:
            pattern = f"{self.cache_prefix}*{section_id}*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                self.cache_stats['invalidations'] += deleted
                return deleted
            
            return 0
            
        except Exception as e:
            print(f"Error invalidating related cache for section {section_id}: {str(e)}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics"""
        try:
            # Calculate hit rate
            total_requests = self.cache_stats['total_requests']
            hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            # Get Redis memory info
            redis_info = await self.redis_client.info('memory')
            
            # Get cache size
            cache_keys = await self.redis_client.keys(f"{self.cache_prefix}*")
            cache_size = len(cache_keys)
            
            stats = {
                'cache_performance': {
                    'hit_rate_percentage': round(hit_rate, 2),
                    'total_requests': total_requests,
                    'cache_hits': self.cache_stats['hits'],
                    'cache_misses': self.cache_stats['misses'],
                    'cache_invalidations': self.cache_stats['invalidations']
                },
                'cache_size': {
                    'current_entries': cache_size,
                    'max_entries': self.max_cache_size,
                    'utilization_percentage': round(cache_size / self.max_cache_size * 100, 2)
                },
                'redis_memory': {
                    'used_memory_human': redis_info.get('used_memory_human', 'N/A'),
                    'used_memory_peak_human': redis_info.get('used_memory_peak_human', 'N/A')
                },
                'configuration': {
                    'default_ttl_seconds': self.default_ttl,
                    'max_cache_size': self.max_cache_size,
                    'cache_prefix': self.cache_prefix
                }
            }
            
            return stats
            
        except Exception as e:
            return {
                'error': f'Failed to get cache stats: {str(e)}',
                'cache_performance': self.cache_stats
            }
    
    async def clear_all_cache(self) -> int:
        """Clear all AI optimization cache entries"""
        try:
            pattern = f"{self.cache_prefix}*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                
                # Reset stats
                self.cache_stats = {
                    'hits': 0,
                    'misses': 0,
                    'invalidations': 0,
                    'total_requests': 0
                }
                
                return deleted
            
            return 0
            
        except Exception as e:
            print(f"Error clearing all cache: {str(e)}")
            return 0
    
    def _is_cache_valid(self, cached_result: CachedResult) -> bool:
        """Check if cached result is still valid"""
        # Check age
        age = datetime.utcnow() - cached_result.timestamp
        if age > timedelta(seconds=self.default_ttl):
            return False
        
        # Check confidence threshold
        if cached_result.confidence < self.cache_invalidation_threshold:
            return False
        
        return True
    
    async def _update_cached_result(self, cache_key: str, cached_result: CachedResult) -> bool:
        """Update cached result (e.g., hit count)"""
        try:
            # Get remaining TTL
            ttl = await self.redis_client.ttl(cache_key)
            if ttl <= 0:
                ttl = self.default_ttl
            
            # Update with same TTL
            await self.redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(cached_result.to_dict())
            )
            return True
            
        except Exception as e:
            print(f"Error updating cached result: {str(e)}")
            return False
    
    async def _update_cache_metrics(self, cache_key: str, cached_result: CachedResult) -> None:
        """Update cache performance metrics"""
        try:
            metrics_key = f"{self.metrics_prefix}entry_count"
            await self.redis_client.incr(metrics_key)
        except Exception as e:
            print(f"Error updating cache metrics: {str(e)}")
    
    async def get_popular_cache_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently accessed cache entries"""
        try:
            cache_keys = await self.redis_client.keys(f"{self.cache_prefix}*")
            entries = []
            
            for key in cache_keys:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    try:
                        cached_result = CachedResult.from_dict(json.loads(cached_data))
                        entries.append({
                            'cache_key': key,
                            'hits': cached_result.hits,
                            'confidence': cached_result.confidence,
                            'solver_method': cached_result.solver_method,
                            'age_hours': (datetime.utcnow() - cached_result.timestamp).total_seconds() / 3600
                        })
                    except Exception:
                        continue
            
            # Sort by hits and return top entries
            entries.sort(key=lambda x: x['hits'], reverse=True)
            return entries[:limit]
            
        except Exception as e:
            print(f"Error getting popular cache entries: {str(e)}")
            return []


# Global cache service instance
ai_cache_service = AICacheService()


# Helper functions for easy integration
async def get_cached_optimization(conflict_data: Dict[str, Any], solver_method: str = "default") -> Optional[Dict[str, Any]]:
    """Convenience function to get cached optimization result"""
    cached_result = await ai_cache_service.get_cached_result(conflict_data, solver_method)
    return cached_result.result if cached_result else None


async def cache_optimization_result(conflict_data: Dict[str, Any], 
                                   result: Dict[str, Any], 
                                   confidence: float, 
                                   solver_method: str = "default") -> bool:
    """Convenience function to cache optimization result"""
    return await ai_cache_service.cache_result(conflict_data, result, confidence, solver_method)


if __name__ == "__main__":
    # Test the cache service
    async def test_cache():
        print("🧪 Testing AI Cache Service...")
        
        # Sample conflict data
        sample_conflict = {
            'trains': [
                {'id': 'T001', 'position': {'lat': 40.7, 'lon': -74.0}, 'priority': 5, 'speed': 80},
                {'id': 'T002', 'position': {'lat': 40.71, 'lon': -74.01}, 'priority': 3, 'speed': 75}
            ],
            'section_id': 'SEC001',
            'conflict_type': 'head_on'
        }
        
        sample_result = {
            'optimization': 'route_adjustment',
            'recommendations': ['slow_T002', 'reroute_T001'],
            'estimated_delay': 120
        }
        
        # Test caching
        cache_success = await ai_cache_service.cache_result(
            sample_conflict, sample_result, 0.95, "constraint_programming"
        )
        print(f"✅ Cache result: {cache_success}")
        
        # Test retrieval
        cached_result = await ai_cache_service.get_cached_result(
            sample_conflict, "constraint_programming"
        )
        print(f"✅ Retrieved cached result: {cached_result is not None}")
        
        # Test stats
        stats = await ai_cache_service.get_cache_stats()
        print(f"✅ Cache stats: {stats}")
    
    # Run test (note: requires Redis connection)
    # asyncio.run(test_cache())