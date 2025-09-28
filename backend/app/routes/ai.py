"""
AI Optimization API Routes

This module provides REST API endpoints for AI-powered railway conflict
optimization and management. Integrates with the existing FastAPI application
to provide comprehensive AI functionality.

Key Features:
- Conflict optimization endpoints
- Batch processing capabilities  
- Real-time AI status monitoring
- Performance metrics and analytics
- RL agent training management
- WebSocket integration for live updates

Dependencies:
- app.services.ai_service: Core AI optimization services
- app.models: Database models for conflicts and decisions
- app.websocket_manager: Real-time notifications
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel, Field, validator

from app.db import get_db
from app.auth import get_current_user
from app.models import Conflict, Decision, Train, Section, Controller
from app.services.ai_service import AIOptimizationService, AIMetricsService
from app.services.ai_monitoring import AIMonitoringService
from app.schemas import APIResponse
from app.websocket_manager import connection_manager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/ai",
    tags=["AI Optimization"],
    responses={
        500: {"description": "Internal server error"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"}
    }
)

# Pydantic models for API requests/responses
class OptimizationRequest(BaseModel):
    solver_preference: Optional[str] = Field(None, description="Preferred AI solver")
    force_reanalysis: bool = Field(False, description="Force re-analysis of already analyzed conflicts")
    timeout: Optional[float] = Field(30.0, description="Optimization timeout in seconds")
    
    @validator('solver_preference')
    def validate_solver(cls, v):
        if v and v not in ['rule_based', 'constraint_programming', 'reinforcement_learning']:
            raise ValueError('Invalid solver preference')
        return v

class BatchOptimizationRequest(BaseModel):
    conflict_ids: List[int] = Field(..., description="List of conflict IDs to optimize")
    solver_preference: Optional[str] = None
    force_reanalysis: bool = False
    max_concurrent: int = Field(5, description="Maximum concurrent optimizations")

class OptimizationResponse(BaseModel):
    success: bool
    conflict_id: int
    optimization_time: float
    ai_confidence: float
    solver_used: str
    solutions_count: int
    best_solution_id: Optional[str]
    recommendations: List[Dict[str, Any]]
    fallback_used: bool
    timestamp: datetime

class AIStatusResponse(BaseModel):
    ai_available: bool
    solvers_status: Dict[str, bool]
    rl_agent_trained: bool
    last_optimization: Optional[datetime]
    total_optimizations_today: int
    average_confidence: float
    performance_score: float

class TrainingRequest(BaseModel):
    episodes: int = Field(1000, description="Number of training episodes")
    use_historical_data: bool = Field(True, description="Use historical conflict data for training")
    background: bool = Field(True, description="Run training in background")


# AI Optimization Endpoints
@router.post("/conflicts/{conflict_id}/optimize", response_model=OptimizationResponse)
async def optimize_conflict(
    conflict_id: int,
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Controller = Depends(get_current_user)
):
    """
    Optimize a specific conflict using AI
    
    This endpoint triggers AI optimization for a railway conflict,
    returning optimization results and storing them in the database.
    """
    try:
        # Initialize AI service
        ai_service = AIOptimizationService(db)
        
        # Check if conflict exists
        conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
        if not conflict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conflict {conflict_id} not found"
            )
        
        # Check if user has permission to optimize conflicts
        if not current_user.can_resolve_conflicts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to optimize conflicts"
            )
        
        # Run optimization
        logger.info(f"Starting AI optimization for conflict {conflict_id} by user {current_user.employee_id}")
        start_time = datetime.utcnow()
        
        result = await ai_service.optimize_conflict(
            conflict_id=conflict_id,
            solver_preference=request.solver_preference,
            force_reanalysis=request.force_reanalysis
        )
        
        optimization_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create response
        response = OptimizationResponse(
            success=True,
            conflict_id=conflict_id,
            optimization_time=optimization_time,
            ai_confidence=result.get('ai_confidence', 0.0),
            solver_used=result.get('solver_used', 'unknown'),
            solutions_count=len(result.get('solutions', [])),
            best_solution_id=result.get('best_solution_id'),
            recommendations=result.get('recommendations', []),
            fallback_used=result.get('fallback_used', False),
            timestamp=datetime.utcnow()
        )
        
        # Send WebSocket notification for real-time updates
        background_tasks.add_task(
            send_optimization_notification,
            conflict_id,
            response.dict(),
            current_user.employee_id
        )
        
        # Log optimization activity
        background_tasks.add_task(
            log_ai_activity,
            "optimization",
            conflict_id,
            current_user.employee_id,
            result
        )
        
        logger.info(f"AI optimization completed for conflict {conflict_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI optimization failed for conflict {conflict_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI optimization failed: {str(e)}"
        )


@router.post("/conflicts/batch-optimize")
async def batch_optimize_conflicts(
    request: BatchOptimizationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Controller = Depends(get_current_user)
):
    """
    Optimize multiple conflicts in batch
    
    Processes multiple conflicts concurrently for efficient batch optimization.
    Returns a summary of results and queues individual optimizations.
    """
    try:
        if not current_user.can_resolve_conflicts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to batch optimize conflicts"
            )
        
        # Validate conflict IDs exist
        conflicts = db.query(Conflict).filter(Conflict.id.in_(request.conflict_ids)).all()
        found_ids = {c.id for c in conflicts}
        missing_ids = set(request.conflict_ids) - found_ids
        
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conflicts not found: {list(missing_ids)}"
            )
        
        # Initialize AI service
        ai_service = AIOptimizationService(db)
        
        # Queue batch optimization
        logger.info(f"Starting batch optimization for {len(request.conflict_ids)} conflicts by user {current_user.employee_id}")
        
        # Run batch optimization in background
        background_tasks.add_task(
            process_batch_optimization,
            request.conflict_ids,
            request.solver_preference,
            request.force_reanalysis,
            request.max_concurrent,
            current_user.employee_id
        )
        
        return APIResponse(
            success=True,
            message=f"Batch optimization queued for {len(request.conflict_ids)} conflicts",
            data={
                "conflict_ids": request.conflict_ids,
                "estimated_completion": datetime.utcnow() + timedelta(minutes=len(request.conflict_ids) * 2),
                "max_concurrent": request.max_concurrent,
                "user": current_user.employee_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch optimization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch optimization failed: {str(e)}"
        )


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status(
    db: Session = Depends(get_db),
    current_user: Controller = Depends(get_current_user)
):
    """
    Get current AI system status and performance metrics
    """
    try:
        ai_service = AIOptimizationService(db)
        metrics_service = AIMetricsService(db)
        
        # Check AI availability
        ai_available = ai_service.is_ai_enabled()
        
        # Get solver status
        solvers_status = {
            'rule_based': True,  # Always available
            'constraint_programming': ai_service.is_or_tools_available(),
            'reinforcement_learning': ai_service.is_rl_agent_available()
        }
        
        # Get today's metrics
        today = datetime.utcnow().date()
        optimizations_today = db.query(func.count(Conflict.id)).filter(
            and_(
                Conflict.ai_analyzed == True,
                func.date(Conflict.ai_analysis_time) == today
            )
        ).scalar() or 0
        
        # Calculate average confidence
        avg_confidence = db.query(func.avg(Conflict.ai_confidence)).filter(
            and_(
                Conflict.ai_analyzed == True,
                Conflict.ai_confidence.isnot(None)
            )
        ).scalar() or 0.0
        
        # Get performance score (simplified metric)
        performance_score = min(float(avg_confidence) * 100, 100.0)
        
        # Get last optimization time
        last_optimization = db.query(func.max(Conflict.ai_analysis_time)).filter(
            Conflict.ai_analyzed == True
        ).scalar()
        
        return AIStatusResponse(
            ai_available=ai_available,
            solvers_status=solvers_status,
            rl_agent_trained=ai_service.is_rl_agent_trained(),
            last_optimization=last_optimization,
            total_optimizations_today=optimizations_today,
            average_confidence=float(avg_confidence),
            performance_score=performance_score
        )
        
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving AI status: {str(e)}"
        )


@router.get("/performance/metrics")
async def get_ai_performance_metrics(
    days: int = Query(7, description="Number of days for metrics calculation"),
    db: Session = Depends(get_db),
    current_user: Controller = Depends(get_current_user)
):
    """
    Get detailed AI performance metrics and analytics
    """
    try:
        metrics_service = AIMetricsService(db)
        
        # Get comprehensive metrics
        performance_metrics = await metrics_service.get_ai_performance_metrics(hours=days * 24)
        solver_metrics = await metrics_service.get_solver_performance_metrics(days=days)
        confidence_metrics = await metrics_service.get_confidence_metrics(days=days)
        
        # Calculate additional metrics
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Optimization trends
        daily_optimizations = db.query(
            func.date(Conflict.ai_analysis_time).label('date'),
            func.count(Conflict.id).label('count')
        ).filter(
            and_(
                Conflict.ai_analyzed == True,
                Conflict.ai_analysis_time >= cutoff_date
            )
        ).group_by(func.date(Conflict.ai_analysis_time)).all()
        
        # Success rate by solver
        solver_success_rates = db.query(
            Decision.ai_solver_method,
            func.avg(Decision.ai_confidence).label('avg_confidence'),
            func.count(Decision.id).label('usage_count')
        ).filter(
            and_(
                Decision.ai_generated == True,
                Decision.created_at >= cutoff_date
            )
        ).group_by(Decision.ai_solver_method).all()
        
        return APIResponse(
            success=True,
            message=f"AI performance metrics for last {days} days",
            data={
                "period_days": days,
                "performance_metrics": performance_metrics,
                "solver_metrics": solver_metrics,
                "confidence_metrics": confidence_metrics,
                "optimization_trends": [
                    {"date": str(row.date), "count": row.count}
                    for row in daily_optimizations
                ],
                "solver_success_rates": [
                    {
                        "solver": row.ai_solver_method or "unknown",
                        "avg_confidence": float(row.avg_confidence or 0),
                        "usage_count": row.usage_count
                    }
                    for row in solver_success_rates
                ],
                "generated_at": datetime.utcnow()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting AI performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving performance metrics: {str(e)}"
        )


@router.post("/train")
async def train_rl_agent(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Controller = Depends(get_current_user)
):
    """
    Train or retrain the Reinforcement Learning agent
    """
    try:
        # Check permissions (admin only)
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can trigger RL training"
            )
        
        ai_service = AIOptimizationService(db)
        
        if not ai_service.is_ai_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI system is not available"
            )
        
        logger.info(f"RL training requested by admin {current_user.employee_id}")
        
        if request.background:
            # Queue training in background
            background_tasks.add_task(
                execute_rl_training,
                request.episodes,
                request.use_historical_data,
                current_user.employee_id
            )
            
            return APIResponse(
                success=True,
                message=f"RL training queued with {request.episodes} episodes",
                data={
                    "episodes": request.episodes,
                    "use_historical_data": request.use_historical_data,
                    "estimated_duration_minutes": request.episodes // 10,
                    "started_by": current_user.employee_id,
                    "started_at": datetime.utcnow()
                }
            )
        else:
            # Run training synchronously (not recommended for large episodes)
            if request.episodes > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Synchronous training limited to 100 episodes. Use background=true for larger training."
                )
            
            start_time = datetime.utcnow()
            training_result = await ai_service.train_rl_agent(episodes=request.episodes)
            training_time = (datetime.utcnow() - start_time).total_seconds()
            
            return APIResponse(
                success=True,
                message="RL training completed",
                data={
                    "training_result": training_result,
                    "training_time_seconds": training_time,
                    "episodes_completed": request.episodes
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RL training failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RL training failed: {str(e)}"
        )


# Background task functions
async def send_optimization_notification(conflict_id: int, result: Dict[str, Any], user_id: str):
    """Send WebSocket notification for optimization completion"""
    try:
        message = {
            "type": "ai_optimization_complete",
            "conflict_id": conflict_id,
            "result": result,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await connection_manager.broadcast_to_controllers(message)
    except Exception as e:
        logger.error(f"Failed to send optimization notification: {e}")


async def log_ai_activity(activity_type: str, conflict_id: int, user_id: str, result: Dict[str, Any]):
    """Log AI activity for audit purposes"""
    try:
        # Implementation would log to audit system
        logger.info(
            f"AI Activity: {activity_type} for conflict {conflict_id} by user {user_id}. "
            f"Result: {result.get('solver_used', 'unknown')} solver, "
            f"confidence: {result.get('ai_confidence', 0.0):.3f}"
        )
    except Exception as e:
        logger.error(f"Failed to log AI activity: {e}")


async def process_batch_optimization(
    conflict_ids: List[int],
    solver_preference: Optional[str],
    force_reanalysis: bool,
    max_concurrent: int,
    user_id: str
):
    """Process batch optimization in background"""
    try:
        # Implementation would process conflicts concurrently
        # This is a placeholder for the background processing
        logger.info(f"Processing batch optimization for {len(conflict_ids)} conflicts")
        
        # Send progress updates via WebSocket
        progress_message = {
            "type": "batch_optimization_progress",
            "total_conflicts": len(conflict_ids),
            "user_id": user_id,
            "status": "processing"
        }
        await connection_manager.broadcast_to_user(user_id, progress_message)
        
    except Exception as e:
        logger.error(f"Batch optimization processing failed: {e}")


async def execute_rl_training(episodes: int, use_historical_data: bool, admin_id: str):
    """Execute RL training in background"""
    try:
        logger.info(f"Starting RL training with {episodes} episodes for admin {admin_id}")
        
        # Send training progress updates
        training_message = {
            "type": "rl_training_progress",
            "episodes": episodes,
            "admin_id": admin_id,
            "status": "training_started",
            "timestamp": datetime.utcnow().isoformat()
        }
        await connection_manager.broadcast_to_admins(training_message)
        
        # Training implementation would go here
        
    except Exception as e:
        logger.error(f"RL training execution failed: {e}")