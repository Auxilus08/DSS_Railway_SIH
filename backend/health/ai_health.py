#!/usr/bin/env python3
"""
AI Health Check Service - Phase 5 System Monitoring
Provides comprehensive health monitoring for AI services and dependencies
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import json

from sqlalchemy.orm import Session
from sqlalchemy import text
import redis.asyncio as redis

from app.db import get_db
from app.redis_client import redis_client
from app.ai_config import AIConfig

# Initialize AI config
ai_config = AIConfig()


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result"""
    service_name: str
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'service_name': self.service_name,
            'status': self.status.value,
            'response_time_ms': self.response_time_ms,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class AIHealthMonitor:
    """
    Phase 5: AI Health Check Service
    
    Monitors the health of all AI-related services and dependencies:
    - Database connectivity and performance
    - Redis cache connectivity and memory
    - AI model availability and performance
    - WebSocket service health
    - System resource utilization
    """
    
    def __init__(self, db: Session = None, redis_client=None):
        self.db = db
        self.redis_client = redis_client or redis_client
        self.health_check_timeout = getattr(ai_config, "health_check_timeout", 5.0)
        self.alert_thresholds = getattr(ai_config, "alert_thresholds", {
            "response_time_ms": 1000,
            "memory_usage_percent": 80,
            "cache_hit_rate_percent": 50,
            "error_rate_percent": 5
        })
    
    async def check_database_health(self) -> HealthCheck:
        """Check database connectivity and performance"""
        start_time = datetime.utcnow()
        
        try:
            if not self.db:
                # Get a database session for the health check
                db_gen = get_db()
                self.db = next(db_gen)
            
            # Test basic connectivity
            result = self.db.execute(text("SELECT 1")).scalar()
            
            # Test AI-related tables
            conflict_count = self.db.execute(text("SELECT COUNT(*) FROM conflicts")).scalar()
            decision_count = self.db.execute(text("SELECT COUNT(*) FROM decisions")).scalar()
            
            # Test database performance
            ai_analyzed_count = self.db.execute(text(
                "SELECT COUNT(*) FROM conflicts WHERE ai_analyzed = true"
            )).scalar()
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Determine health status
            if response_time > self.alert_thresholds["response_time_ms"]:
                status = HealthStatus.DEGRADED
                message = f"Database responding slowly: {response_time:.1f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "Database connectivity and performance good"
            
            return HealthCheck(
                service_name="database",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "total_conflicts": conflict_count,
                    "total_decisions": decision_count,
                    "ai_analyzed_conflicts": ai_analyzed_count,
                    "connection_test_result": result
                },
                timestamp=start_time
            )
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                service_name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Database health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=start_time
            )
    
    async def check_redis_health(self) -> HealthCheck:
        """Check Redis connectivity and memory usage"""
        start_time = datetime.utcnow()
        
        try:
            # Test basic connectivity
            await self.redis_client.ping()
            
            # Get Redis info
            redis_info = await self.redis_client.info()
            memory_info = await self.redis_client.info('memory')
            
            # Test cache functionality
            test_key = "health_check_test"
            test_value = datetime.utcnow().isoformat()
            await self.redis_client.setex(test_key, 10, test_value)
            retrieved_value = await self.redis_client.get(test_key)
            await self.redis_client.delete(test_key)
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Check memory usage
            used_memory = int(memory_info.get('used_memory', 0))
            max_memory = int(memory_info.get('maxmemory', 0))
            memory_usage_percent = (used_memory / max_memory * 100) if max_memory > 0 else 0
            
            # Determine health status
            if memory_usage_percent > self.alert_thresholds["memory_usage_percent"]:
                status = HealthStatus.DEGRADED
                message = f"Redis memory usage high: {memory_usage_percent:.1f}%"
            elif response_time > self.alert_thresholds["response_time_ms"]:
                status = HealthStatus.DEGRADED
                message = f"Redis responding slowly: {response_time:.1f}ms"
            elif retrieved_value != test_value:
                status = HealthStatus.DEGRADED
                message = "Redis cache test failed"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis connectivity and performance good"
            
            return HealthCheck(
                service_name="redis",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "memory_usage_percent": memory_usage_percent,
                    "used_memory_human": memory_info.get('used_memory_human', 'N/A'),
                    "connected_clients": redis_info.get('connected_clients', 0),
                    "cache_test_success": retrieved_value == test_value
                },
                timestamp=start_time
            )
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                service_name="redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Redis health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=start_time
            )
    
    async def check_ai_models_health(self) -> HealthCheck:
        """Check AI models and optimization services"""
        start_time = datetime.utcnow()
        
        try:
            # Test AI model imports and initialization
            from app.railway_optimization import OptimizationEngine, RailwayAIAdapter
            from app.services.ai_service import AIOptimizationService
            
            # Test basic AI functionality
            ai_service = AIOptimizationService(self.db) if self.db else None
            
            # Test model availability
            models_status = {
                'optimization_engine': False,
                'railway_adapter': False,
                'ai_service': False
            }
            
            try:
                engine = OptimizationEngine()
                models_status['optimization_engine'] = True
            except Exception as e:
                logger.warning(f"OptimizationEngine check failed: {e}")
            
            try:
                adapter = RailwayAIAdapter()
                models_status['railway_adapter'] = True
            except Exception as e:
                logger.warning(f"RailwayAIAdapter check failed: {e}")
            
            if ai_service:
                models_status['ai_service'] = True
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Determine health status
            healthy_models = sum(models_status.values())
            total_models = len(models_status)
            
            if healthy_models == total_models:
                status = HealthStatus.HEALTHY
                message = "All AI models and services available"
            elif healthy_models > 0:
                status = HealthStatus.DEGRADED
                message = f"Some AI models unavailable: {healthy_models}/{total_models} healthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = "No AI models available"
            
            return HealthCheck(
                service_name="ai_models",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "models_status": models_status,
                    "healthy_models": healthy_models,
                    "total_models": total_models,
                    "model_health_percentage": (healthy_models / total_models * 100) if total_models > 0 else 0
                },
                timestamp=start_time
            )
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                service_name="ai_models",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"AI models health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=start_time
            )
    
    async def check_cache_performance(self) -> HealthCheck:
        """Check AI cache performance metrics"""
        start_time = datetime.utcnow()
        
        try:
            from app.services.ai_cache import ai_cache_service
            
            # Get cache statistics
            cache_stats = await ai_cache_service.get_cache_stats()
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Extract performance metrics
            cache_performance = cache_stats.get('cache_performance', {})
            hit_rate = cache_performance.get('hit_rate_percentage', 0)
            cache_size = cache_stats.get('cache_size', {})
            current_entries = cache_size.get('current_entries', 0)
            
            # Determine health status
            if hit_rate < self.alert_thresholds["cache_hit_rate_percent"]:
                status = HealthStatus.DEGRADED
                message = f"Cache hit rate low: {hit_rate:.1f}%"
            elif response_time > self.alert_thresholds["response_time_ms"]:
                status = HealthStatus.DEGRADED
                message = f"Cache responding slowly: {response_time:.1f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "Cache performance good"
            
            return HealthCheck(
                service_name="ai_cache",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "hit_rate_percentage": hit_rate,
                    "current_cache_entries": current_entries,
                    "cache_stats": cache_stats
                },
                timestamp=start_time
            )
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                service_name="ai_cache",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Cache health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=start_time
            )
    
    async def check_websocket_health(self) -> HealthCheck:
        """Check WebSocket manager health"""
        start_time = datetime.utcnow()
        
        try:
            from app.websocket_manager import connection_manager
            
            # Get connection statistics
            connection_stats = await connection_manager.get_connection_stats()
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Determine health status
            total_connections = connection_stats.get('total_connections', 0)
            ai_subscribers = connection_stats.get('ai_subscribers', 0)
            
            if response_time > self.alert_thresholds["response_time_ms"]:
                status = HealthStatus.DEGRADED
                message = f"WebSocket manager responding slowly: {response_time:.1f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = "WebSocket manager operational"
            
            return HealthCheck(
                service_name="websocket",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "total_connections": total_connections,
                    "ai_subscribers": ai_subscribers,
                    "connection_stats": connection_stats
                },
                timestamp=start_time
            )
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheck(
                service_name="websocket",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"WebSocket health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=start_time
            )
    
    async def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status"""
        try:
            # Run all health checks concurrently
            health_checks = await asyncio.gather(
                self.check_database_health(),
                self.check_redis_health(),
                self.check_ai_models_health(),
                self.check_cache_performance(),
                self.check_websocket_health(),
                return_exceptions=True
            )
            
            # Process results
            results = {}
            overall_status = HealthStatus.HEALTHY
            total_response_time = 0
            healthy_services = 0
            total_services = 0
            
            for check in health_checks:
                if isinstance(check, Exception):
                    service_name = "unknown"
                    check = HealthCheck(
                        service_name=service_name,
                        status=HealthStatus.UNHEALTHY,
                        response_time_ms=0,
                        message=f"Health check failed: {str(check)}",
                        details={"error": str(check)},
                        timestamp=datetime.utcnow()
                    )
                
                results[check.service_name] = check.to_dict()
                total_response_time += check.response_time_ms
                total_services += 1
                
                # Determine overall status
                if check.status == HealthStatus.HEALTHY:
                    healthy_services += 1
                elif check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                elif check.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
            
            # Calculate overall metrics
            avg_response_time = total_response_time / total_services if total_services > 0 else 0
            health_percentage = (healthy_services / total_services * 100) if total_services > 0 else 0
            
            return {
                'overall_status': overall_status.value,
                'health_percentage': health_percentage,
                'healthy_services': healthy_services,
                'total_services': total_services,
                'average_response_time_ms': avg_response_time,
                'individual_checks': results,
                'timestamp': datetime.utcnow().isoformat(),
                'alert_thresholds': self.alert_thresholds
            }
            
        except Exception as e:
            logger.error(f"Comprehensive health check failed: {e}")
            return {
                'overall_status': HealthStatus.UNHEALTHY.value,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def get_health_history(self, hours: int = 24) -> Dict[str, Any]:
        """Get health check history from Redis"""
        try:
            # This would typically store health check results in Redis
            # For now, return current status
            current_health = await self.run_comprehensive_health_check()
            
            return {
                'history_hours': hours,
                'current_status': current_health,
                'historical_data': "Health history tracking to be implemented",
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Failed to get health history: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            }


# Global health monitor instance
health_monitor = AIHealthMonitor()


# Convenience functions
async def get_ai_system_health() -> Dict[str, Any]:
    """Get current AI system health status"""
    return await health_monitor.run_comprehensive_health_check()


async def check_service_health(service_name: str) -> HealthCheck:
    """Check health of specific service"""
    if service_name == "database":
        return await health_monitor.check_database_health()
    elif service_name == "redis":
        return await health_monitor.check_redis_health()
    elif service_name == "ai_models":
        return await health_monitor.check_ai_models_health()
    elif service_name == "cache":
        return await health_monitor.check_cache_performance()
    elif service_name == "websocket":
        return await health_monitor.check_websocket_health()
    else:
        raise ValueError(f"Unknown service: {service_name}")


if __name__ == "__main__":
    # Test health monitoring
    async def test_health_monitor():
        print("🧪 Testing AI Health Monitor...")
        
        monitor = AIHealthMonitor()
        health_status = await monitor.run_comprehensive_health_check()
        
        print(f"✅ Overall Status: {health_status.get('overall_status', 'unknown')}")
        print(f"✅ Health Percentage: {health_status.get('health_percentage', 0):.1f}%")
        print(f"✅ Services Checked: {health_status.get('total_services', 0)}")
    
    # Run test
    asyncio.run(test_health_monitor())