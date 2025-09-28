"""
AI Monitoring Service

Enhanced monitoring and analytics service for AI optimization system.
Provides detailed performance tracking, health monitoring, and system insights.

Key Features:
- Real-time AI system health monitoring
- Performance analytics and trending
- Anomaly detection for AI behavior
- Resource usage tracking
- Alert generation for system issues

Dependencies:
- app.models: Database models for conflicts and decisions
- app.services.ai_service: Core AI optimization services
- app.redis_client: Caching and real-time data
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import json

from app.models import Conflict, Decision, Train, Section
from app.redis_client import get_redis

logger = logging.getLogger(__name__)


@dataclass
class AIHealthStatus:
    """AI system health status"""
    overall_status: str  # healthy, degraded, critical
    ai_engine_status: str
    database_status: str
    solver_statuses: Dict[str, str]
    last_optimization: Optional[datetime]
    performance_score: float
    error_rate: float
    response_time_avg: float
    issues: List[str]


@dataclass
class PerformanceMetrics:
    """AI performance metrics"""
    total_optimizations: int
    success_rate: float
    average_confidence: float
    average_response_time: float
    solver_usage_distribution: Dict[str, int]
    daily_trend: List[Dict[str, Any]]
    confidence_trend: List[float]
    error_trend: List[int]


class AIMonitoringService:
    """Enhanced AI monitoring and analytics service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.redis_key_prefix = "ai_monitoring"
    
    async def get_ai_health_status(self) -> AIHealthStatus:
        """
        Get comprehensive AI system health status
        """
        try:
            # Get Redis client for real-time metrics
            redis_client = await get_redis()
            
            # Check AI engine status
            ai_engine_status = await self._check_ai_engine_health()
            
            # Check database status
            database_status = await self._check_database_health()
            
            # Check individual solver statuses
            solver_statuses = await self._check_solver_health()
            
            # Calculate performance metrics
            performance_score = await self._calculate_performance_score()
            error_rate = await self._calculate_error_rate()
            response_time_avg = await self._calculate_average_response_time()
            
            # Get last optimization
            last_optimization = self.db.query(func.max(Conflict.ai_analysis_time)).filter(
                Conflict.ai_analyzed == True
            ).scalar()
            
            # Determine overall status
            issues = []
            if ai_engine_status != "healthy":
                issues.append(f"AI Engine: {ai_engine_status}")
            if database_status != "healthy":
                issues.append(f"Database: {database_status}")
            
            unhealthy_solvers = [k for k, v in solver_statuses.items() if v != "healthy"]
            if unhealthy_solvers:
                issues.append(f"Solvers: {', '.join(unhealthy_solvers)}")
            
            if error_rate > 0.1:  # More than 10% error rate
                issues.append(f"High error rate: {error_rate:.2%}")
            
            if response_time_avg > 30:  # Slower than 30 seconds
                issues.append(f"Slow response time: {response_time_avg:.2f}s")
            
            # Determine overall status
            if not issues:
                overall_status = "healthy"
            elif len(issues) <= 2 and error_rate < 0.2:
                overall_status = "degraded"
            else:
                overall_status = "critical"
            
            return AIHealthStatus(
                overall_status=overall_status,
                ai_engine_status=ai_engine_status,
                database_status=database_status,
                solver_statuses=solver_statuses,
                last_optimization=last_optimization,
                performance_score=performance_score,
                error_rate=error_rate,
                response_time_avg=response_time_avg,
                issues=issues
            )
            
        except Exception as e:
            logger.error(f"Error getting AI health status: {e}")
            return AIHealthStatus(
                overall_status="critical",
                ai_engine_status="error",
                database_status="unknown",
                solver_statuses={},
                last_optimization=None,
                performance_score=0.0,
                error_rate=1.0,
                response_time_avg=0.0,
                issues=[f"Health check failed: {str(e)}"]
            )
    
    async def get_performance_metrics(self, days: int = 7) -> PerformanceMetrics:
        """
        Get detailed AI performance metrics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Total optimizations
            total_optimizations = self.db.query(func.count(Conflict.id)).filter(
                and_(
                    Conflict.ai_analyzed == True,
                    Conflict.ai_analysis_time >= cutoff_date
                )
            ).scalar() or 0
            
            # Success rate (conflicts with confidence > 0.5)
            successful_optimizations = self.db.query(func.count(Conflict.id)).filter(
                and_(
                    Conflict.ai_analyzed == True,
                    Conflict.ai_analysis_time >= cutoff_date,
                    Conflict.ai_confidence > 0.5
                )
            ).scalar() or 0
            
            success_rate = successful_optimizations / total_optimizations if total_optimizations > 0 else 0.0
            
            # Average confidence
            avg_confidence = self.db.query(func.avg(Conflict.ai_confidence)).filter(
                and_(
                    Conflict.ai_analyzed == True,
                    Conflict.ai_analysis_time >= cutoff_date,
                    Conflict.ai_confidence.isnot(None)
                )
            ).scalar() or 0.0
            
            # Solver usage distribution
            solver_usage = self.db.query(
                Decision.ai_solver_method,
                func.count(Decision.id)
            ).filter(
                and_(
                    Decision.ai_generated == True,
                    Decision.created_at >= cutoff_date
                )
            ).group_by(Decision.ai_solver_method).all()
            
            solver_usage_distribution = {
                row[0] or "unknown": row[1] for row in solver_usage
            }
            
            # Daily trend
            daily_trend = self.db.query(
                func.date(Conflict.ai_analysis_time).label('date'),
                func.count(Conflict.id).label('count'),
                func.avg(Conflict.ai_confidence).label('avg_confidence')
            ).filter(
                and_(
                    Conflict.ai_analyzed == True,
                    Conflict.ai_analysis_time >= cutoff_date
                )
            ).group_by(func.date(Conflict.ai_analysis_time)).order_by('date').all()
            
            daily_trend_data = [
                {
                    "date": str(row.date),
                    "optimizations": row.count,
                    "avg_confidence": float(row.avg_confidence or 0)
                }
                for row in daily_trend
            ]
            
            # Confidence trend (last 7 days)
            confidence_trend = [row.avg_confidence or 0.0 for row in daily_trend[-7:]]
            
            # Error trend (placeholder - would need error logging)
            error_trend = [0] * min(len(daily_trend), 7)  # Simplified
            
            # Average response time (from Redis cache)
            redis_client = await get_redis()
            response_times_key = f"{self.redis_key_prefix}:response_times"
            response_times_data = await redis_client.lrange(response_times_key, 0, 100)
            
            if response_times_data:
                response_times = [float(t) for t in response_times_data]
                average_response_time = sum(response_times) / len(response_times)
            else:
                average_response_time = 0.0
            
            return PerformanceMetrics(
                total_optimizations=total_optimizations,
                success_rate=success_rate,
                average_confidence=float(avg_confidence),
                average_response_time=average_response_time,
                solver_usage_distribution=solver_usage_distribution,
                daily_trend=daily_trend_data,
                confidence_trend=confidence_trend,
                error_trend=error_trend
            )
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return PerformanceMetrics(
                total_optimizations=0,
                success_rate=0.0,
                average_confidence=0.0,
                average_response_time=0.0,
                solver_usage_distribution={},
                daily_trend=[],
                confidence_trend=[],
                error_trend=[]
            )
    
    async def record_optimization_metrics(
        self,
        conflict_id: int,
        solver_used: str,
        response_time: float,
        confidence: float,
        success: bool
    ):
        """
        Record metrics for an optimization operation
        """
        try:
            redis_client = await get_redis()
            timestamp = datetime.utcnow().isoformat()
            
            # Store response time (keep last 100)
            response_times_key = f"{self.redis_key_prefix}:response_times"
            await redis_client.lpush(response_times_key, str(response_time))
            await redis_client.ltrim(response_times_key, 0, 99)
            
            # Store optimization event
            event_data = {
                "conflict_id": conflict_id,
                "solver_used": solver_used,
                "response_time": response_time,
                "confidence": confidence,
                "success": success,
                "timestamp": timestamp
            }
            
            events_key = f"{self.redis_key_prefix}:recent_events"
            await redis_client.lpush(events_key, json.dumps(event_data))
            await redis_client.ltrim(events_key, 0, 999)  # Keep last 1000 events
            
            # Update counters
            await redis_client.incr(f"{self.redis_key_prefix}:total_optimizations")
            if success:
                await redis_client.incr(f"{self.redis_key_prefix}:successful_optimizations")
            
            # Update solver usage
            solver_key = f"{self.redis_key_prefix}:solver_usage:{solver_used}"
            await redis_client.incr(solver_key)
            
            logger.debug(f"Recorded metrics for optimization {conflict_id}")
            
        except Exception as e:
            logger.error(f"Error recording optimization metrics: {e}")
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """
        Get real-time metrics from Redis cache
        """
        try:
            redis_client = await get_redis()
            
            # Get counters
            total = await redis_client.get(f"{self.redis_key_prefix}:total_optimizations") or "0"
            successful = await redis_client.get(f"{self.redis_key_prefix}:successful_optimizations") or "0"
            
            total_optimizations = int(total)
            successful_optimizations = int(successful)
            
            success_rate = successful_optimizations / total_optimizations if total_optimizations > 0 else 0.0
            
            # Get recent events
            events_key = f"{self.redis_key_prefix}:recent_events"
            recent_events_data = await redis_client.lrange(events_key, 0, 9)  # Last 10 events
            
            recent_events = []
            for event_data in recent_events_data:
                try:
                    event = json.loads(event_data)
                    recent_events.append(event)
                except json.JSONDecodeError:
                    continue
            
            # Get solver usage
            solver_usage = {}
            for solver in ['rule_based', 'constraint_programming', 'reinforcement_learning']:
                count = await redis_client.get(f"{self.redis_key_prefix}:solver_usage:{solver}")
                solver_usage[solver] = int(count or 0)
            
            return {
                "total_optimizations": total_optimizations,
                "successful_optimizations": successful_optimizations,
                "success_rate": success_rate,
                "recent_events": recent_events,
                "solver_usage": solver_usage,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return {
                "total_optimizations": 0,
                "successful_optimizations": 0,
                "success_rate": 0.0,
                "recent_events": [],
                "solver_usage": {},
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def check_system_anomalies(self) -> List[Dict[str, Any]]:
        """
        Check for system anomalies and performance issues
        """
        anomalies = []
        
        try:
            # Check for sudden confidence drops
            recent_confidences = self.db.query(Conflict.ai_confidence).filter(
                and_(
                    Conflict.ai_analyzed == True,
                    Conflict.ai_analysis_time >= datetime.utcnow() - timedelta(hours=1),
                    Conflict.ai_confidence.isnot(None)
                )
            ).limit(10).all()
            
            if recent_confidences and len(recent_confidences) >= 5:
                avg_recent = sum(c[0] for c in recent_confidences) / len(recent_confidences)
                if avg_recent < 0.3:
                    anomalies.append({
                        "type": "low_confidence",
                        "severity": "warning",
                        "message": f"Recent optimizations showing low confidence: {avg_recent:.3f}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Check for optimization failures
            recent_failures = self.db.query(func.count(Conflict.id)).filter(
                and_(
                    Conflict.ai_analyzed == True,
                    Conflict.ai_analysis_time >= datetime.utcnow() - timedelta(hours=1),
                    or_(
                        Conflict.ai_confidence < 0.2,
                        Conflict.ai_confidence.is_(None)
                    )
                )
            ).scalar() or 0
            
            if recent_failures > 3:
                anomalies.append({
                    "type": "high_failure_rate",
                    "severity": "critical",
                    "message": f"{recent_failures} optimization failures in the last hour",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check for no recent optimizations
            last_optimization = self.db.query(func.max(Conflict.ai_analysis_time)).filter(
                Conflict.ai_analyzed == True
            ).scalar()
            
            if last_optimization and (datetime.utcnow() - last_optimization).total_seconds() > 3600:
                anomalies.append({
                    "type": "no_recent_activity",
                    "severity": "warning",
                    "message": f"No AI optimizations in the last hour. Last: {last_optimization}",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error checking system anomalies: {e}")
            anomalies.append({
                "type": "anomaly_check_error",
                "severity": "critical",
                "message": f"Failed to check system anomalies: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return anomalies
    
    # Private helper methods
    async def _check_ai_engine_health(self) -> str:
        """Check AI engine health"""
        try:
            from app.services.ai_service import AIOptimizationService
            ai_service = AIOptimizationService(self.db)
            
            if ai_service.is_ai_enabled():
                return "healthy"
            else:
                return "disabled"
        except Exception as e:
            logger.error(f"AI engine health check failed: {e}")
            return "error"
    
    async def _check_database_health(self) -> str:
        """Check database health for AI operations"""
        try:
            # Test AI-specific database operations
            self.db.query(func.count(Conflict.id)).filter(Conflict.ai_analyzed == True).scalar()
            return "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return "error"
    
    async def _check_solver_health(self) -> Dict[str, str]:
        """Check individual solver health"""
        solvers = {}
        
        try:
            from app.services.ai_service import AIOptimizationService
            ai_service = AIOptimizationService(self.db)
            
            # Rule-based solver (always available)
            solvers["rule_based"] = "healthy"
            
            # OR-Tools constraint programming
            solvers["constraint_programming"] = "healthy" if ai_service.is_or_tools_available() else "unavailable"
            
            # Reinforcement learning
            if ai_service.is_rl_agent_available():
                solvers["reinforcement_learning"] = "healthy" if ai_service.is_rl_agent_trained() else "untrained"
            else:
                solvers["reinforcement_learning"] = "unavailable"
                
        except Exception as e:
            logger.error(f"Solver health check failed: {e}")
            for solver in ["rule_based", "constraint_programming", "reinforcement_learning"]:
                solvers[solver] = "error"
        
        return solvers
    
    async def _calculate_performance_score(self) -> float:
        """Calculate overall AI performance score"""
        try:
            # Get metrics from last 24 hours
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            avg_confidence = self.db.query(func.avg(Conflict.ai_confidence)).filter(
                and_(
                    Conflict.ai_analyzed == True,
                    Conflict.ai_analysis_time >= cutoff,
                    Conflict.ai_confidence.isnot(None)
                )
            ).scalar() or 0.0
            
            # Performance score based on confidence (0-100)
            return min(float(avg_confidence) * 100, 100.0)
            
        except Exception:
            return 0.0
    
    async def _calculate_error_rate(self) -> float:
        """Calculate error rate for AI operations"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            total = self.db.query(func.count(Conflict.id)).filter(
                and_(
                    Conflict.ai_analyzed == True,
                    Conflict.ai_analysis_time >= cutoff
                )
            ).scalar() or 0
            
            errors = self.db.query(func.count(Conflict.id)).filter(
                and_(
                    Conflict.ai_analyzed == True,
                    Conflict.ai_analysis_time >= cutoff,
                    or_(
                        Conflict.ai_confidence < 0.1,
                        Conflict.ai_confidence.is_(None)
                    )
                )
            ).scalar() or 0
            
            return errors / total if total > 0 else 0.0
            
        except Exception:
            return 1.0  # Assume high error rate on failure
    
    async def _calculate_average_response_time(self) -> float:
        """Calculate average response time from Redis cache"""
        try:
            redis_client = await get_redis()
            response_times_key = f"{self.redis_key_prefix}:response_times"
            response_times_data = await redis_client.lrange(response_times_key, 0, 99)
            
            if response_times_data:
                response_times = [float(t) for t in response_times_data]
                return sum(response_times) / len(response_times)
            else:
                return 0.0
                
        except Exception:
            return 0.0