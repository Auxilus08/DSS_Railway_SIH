"""
Controller Action API Routes
Production-ready endpoints for railway traffic controller operations
Includes conflict resolution, train control, audit trail, and decision logging
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from decimal import Decimal
import logging
import asyncio

from ..db import get_session
from ..models import (
    Controller, Conflict, Decision, Train, Section, 
    ConflictSeverity, DecisionAction, ControllerAuthLevel
)
from ..schemas import (
    ConflictResolveRequest, ConflictResolveResponse,
    TrainControlRequest, TrainControlResponse,
    ActiveConflictsResponse, ConflictWithRecommendations,
    DecisionLogRequest, DecisionLogResponse,
    AuditQueryFilters, AuditTrailResponse, DecisionAuditRecord,
    PerformanceMetricsResponse, APIResponse
)
from ..auth import (
    get_current_active_controller, PermissionChecker,
    require_supervisor, require_operator
)
from ..websocket_manager import connection_manager
from ..redis_client import get_redis, RedisClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Controller Actions"])


# ============================================================================
# RATE LIMITING MIDDLEWARE
# ============================================================================

class RateLimiter:
    """Rate limiting for safety-critical controller actions"""
    
    def __init__(self, requests_per_minute: int = 10, critical: bool = False):
        self.requests_per_minute = requests_per_minute
        self.critical = critical
    
    async def __call__(
        self,
        request: Request,
        controller: Controller = Depends(get_current_active_controller),
        redis_client: RedisClient = Depends(get_redis)
    ):
        """Check rate limit for controller"""
        # Build rate limit key
        endpoint = request.url.path
        rate_key = f"rate_limit:{controller.id}:{endpoint}"
        
        # Get current count
        current_count = await redis_client.increment_counter(rate_key, ttl=60)
        
        if current_count > self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for controller {controller.id} "
                f"on endpoint {endpoint}: {current_count}/{self.requests_per_minute}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "60"
                }
            )
        
        # Add rate limit headers to response
        request.state.rate_limit_remaining = self.requests_per_minute - current_count
        request.state.rate_limit_limit = self.requests_per_minute
        
        return controller


# Rate limit dependencies
standard_rate_limit = RateLimiter(requests_per_minute=30)
critical_rate_limit = RateLimiter(requests_per_minute=10, critical=True)


# ============================================================================
# BACKGROUND TASK HANDLERS
# ============================================================================

async def execute_conflict_resolution(
    conflict_id: int,
    decision_id: int,
    action: str,
    modifications: Optional[Dict[str, Any]],
    db_session: Session
):
    """Background task to execute conflict resolution"""
    try:
        # Get conflict and decision
        conflict = db_session.query(Conflict).filter(Conflict.id == conflict_id).first()
        decision = db_session.query(Decision).filter(Decision.id == decision_id).first()
        
        if not conflict or not decision:
            logger.error(f"Conflict {conflict_id} or Decision {decision_id} not found")
            return
        
        # Apply resolution based on action
        if action == "accept":
            # Apply AI recommendation directly
            if conflict.ai_recommendations:
                await apply_ai_recommendation(conflict, conflict.ai_recommendations, db_session)
        
        elif action == "modify":
            # Apply modified recommendation
            if modifications:
                await apply_ai_recommendation(conflict, modifications, db_session)
        
        elif action == "reject":
            # Mark as manually handled (no automatic resolution)
            pass
        
        # Update conflict status
        conflict.resolution_time = datetime.utcnow()
        conflict.resolved_by_controller_id = decision.controller_id
        
        # Mark decision as executed
        decision.executed = True
        decision.execution_time = datetime.utcnow()
        decision.execution_result = "Successfully executed resolution"
        
        db_session.commit()
        
        # Send WebSocket notification
        await connection_manager.broadcast_conflict_alert({
            "type": "conflict_resolved",
            "conflict_id": conflict_id,
            "action": action,
            "resolution_time": conflict.resolution_time.isoformat(),
            "controller_id": decision.controller_id
        })
        
        logger.info(f"Conflict {conflict_id} resolved with action: {action}")
    
    except Exception as e:
        logger.error(f"Error executing conflict resolution {conflict_id}: {e}")
        db_session.rollback()


async def apply_ai_recommendation(
    conflict: Conflict,
    recommendations: Dict[str, Any],
    db_session: Session
):
    """Apply AI recommendations to resolve conflict"""
    try:
        # Extract recommendations
        train_actions = recommendations.get("train_actions", [])
        
        for action in train_actions:
            train_id = action.get("train_id")
            action_type = action.get("action")
            parameters = action.get("parameters", {})
            
            train = db_session.query(Train).filter(Train.id == train_id).first()
            if not train:
                continue
            
            # Apply action based on type
            if action_type == "delay":
                delay_minutes = parameters.get("delay_minutes", 0)
                if train.scheduled_arrival:
                    train.scheduled_arrival += timedelta(minutes=delay_minutes)
                if train.scheduled_departure:
                    train.scheduled_departure += timedelta(minutes=delay_minutes)
            
            elif action_type == "reroute":
                new_route = parameters.get("new_route", [])
                if new_route:
                    # Update train's route (simplified - would need schedule update)
                    logger.info(f"Rerouting train {train_id} to {new_route}")
            
            elif action_type == "priority_change":
                new_priority = parameters.get("new_priority")
                if new_priority:
                    train.priority = new_priority
            
            elif action_type == "speed_limit":
                max_speed = parameters.get("max_speed_kmh")
                if max_speed:
                    train.max_speed_kmh = min(train.max_speed_kmh, max_speed)
        
        db_session.commit()
        logger.info(f"Applied AI recommendations for conflict {conflict.id}")
    
    except Exception as e:
        logger.error(f"Error applying AI recommendations: {e}")
        db_session.rollback()


async def execute_train_control(
    train_id: int,
    command: str,
    parameters: Dict[str, Any],
    decision_id: int,
    controller_id: int,
    db_session: Session
):
    """Background task to execute train control command"""
    try:
        train = db_session.query(Train).filter(Train.id == train_id).first()
        decision = db_session.query(Decision).filter(Decision.id == decision_id).first()
        
        if not train or not decision:
            logger.error(f"Train {train_id} or Decision {decision_id} not found")
            return
        
        execution_result = ""
        
        # Execute command
        if command == "delay":
            delay_minutes = parameters.get("delay_minutes", 0)
            if train.scheduled_arrival:
                train.scheduled_arrival += timedelta(minutes=delay_minutes)
            if train.scheduled_departure:
                train.scheduled_departure += timedelta(minutes=delay_minutes)
            execution_result = f"Train delayed by {delay_minutes} minutes"
        
        elif command == "reroute":
            new_route = parameters.get("new_route", [])
            # Update train destination (simplified)
            if new_route:
                train.destination_section_id = new_route[-1]
            execution_result = f"Train rerouted to {new_route}"
        
        elif command == "priority":
            new_priority = parameters.get("new_priority")
            old_priority = train.priority
            train.priority = new_priority
            execution_result = f"Train priority changed from {old_priority} to {new_priority}"
        
        elif command == "stop":
            train.operational_status = "emergency"
            train.speed_kmh = 0
            execution_result = "Emergency stop initiated"
        
        elif command == "speed_limit":
            max_speed = parameters.get("max_speed_kmh")
            old_max = train.max_speed_kmh
            train.max_speed_kmh = max_speed
            execution_result = f"Speed limit changed from {old_max} to {max_speed} km/h"
        
        elif command == "resume":
            train.operational_status = "active"
            execution_result = "Train operations resumed"
        
        # Update decision
        decision.executed = True
        decision.execution_time = datetime.utcnow()
        decision.execution_result = execution_result
        
        db_session.commit()
        
        # Send WebSocket notification to train operator
        await connection_manager.broadcast_to_all({
            "type": "train_control",
            "train_id": train_id,
            "train_number": train.train_number,
            "command": command,
            "parameters": parameters,
            "controller_id": controller_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": execution_result
        })
        
        logger.info(f"Train control executed for train {train_id}: {command}")
    
    except Exception as e:
        logger.error(f"Error executing train control {train_id}: {e}")
        db_session.rollback()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post(
    "/conflicts/{conflict_id}/resolve",
    response_model=ConflictResolveResponse,
    dependencies=[Depends(critical_rate_limit)]
)
async def resolve_conflict(
    conflict_id: int,
    request: ConflictResolveRequest,
    background_tasks: BackgroundTasks,
    controller: Controller = Depends(require_supervisor),
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    Resolve conflict with controller decision
    
    Controller can:
    - Accept AI recommendations
    - Modify AI suggestions before implementation
    - Reject recommendations with rationale
    
    **Permissions Required:** Supervisor or higher
    
    **Rate Limited:** 10 requests/minute per controller
    """
    try:
        # Get conflict
        conflict = db.query(Conflict).filter(Conflict.id == conflict_id).first()
        
        if not conflict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conflict {conflict_id} not found"
            )
        
        # Check if already resolved
        if conflict.resolution_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conflict already resolved"
            )
        
        # Validate solution_id if provided
        if request.solution_id and conflict.ai_solution_id != request.solution_id:
            logger.warning(
                f"Solution ID mismatch: {request.solution_id} != {conflict.ai_solution_id}"
            )
        
        # Determine decision action
        action_map = {
            "accept": DecisionAction.REROUTE,  # Use appropriate action
            "modify": DecisionAction.MANUAL_OVERRIDE,
            "reject": DecisionAction.MANUAL_OVERRIDE
        }
        
        decision_action = action_map.get(request.action.value, DecisionAction.MANUAL_OVERRIDE)
        
        # Create decision record
        decision = Decision(
            controller_id=controller.id,
            conflict_id=conflict_id,
            action_taken=decision_action,
            rationale=request.rationale,
            parameters={
                "resolution_action": request.action.value,
                "solution_id": request.solution_id,
                "modifications": request.modifications,
                "original_ai_recommendations": conflict.ai_recommendations
            },
            executed=False,
            approval_required=False,
            ai_generated=False
        )
        
        db.add(decision)
        db.commit()
        db.refresh(decision)
        
        # Cache decision in Redis
        await redis_client.set(
            f"decision:{decision.id}",
            {
                "conflict_id": conflict_id,
                "controller_id": controller.id,
                "action": request.action.value,
                "timestamp": datetime.utcnow().isoformat()
            },
            ttl=3600
        )
        
        # Execute resolution in background
        background_tasks.add_task(
            execute_conflict_resolution,
            conflict_id,
            decision.id,
            request.action.value,
            request.modifications,
            db
        )
        
        # Prepare applied solution
        applied_solution = None
        if request.action.value == "accept":
            applied_solution = conflict.ai_recommendations
        elif request.action.value == "modify":
            applied_solution = request.modifications
        
        logger.info(
            f"Conflict {conflict_id} resolution initiated by controller {controller.id} "
            f"with action: {request.action.value}"
        )
        
        return ConflictResolveResponse(
            success=True,
            conflict_id=conflict_id,
            action=request.action,
            decision_id=decision.id,
            resolution_time=datetime.utcnow(),
            message=f"Conflict resolution {request.action.value} initiated. Executing in background.",
            applied_solution=applied_solution
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving conflict {conflict_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during conflict resolution"
        )


@router.post(
    "/trains/{train_id}/control",
    response_model=TrainControlResponse,
    dependencies=[Depends(critical_rate_limit)]
)
async def control_train(
    train_id: int,
    request: TrainControlRequest,
    background_tasks: BackgroundTasks,
    controller: Controller = Depends(require_supervisor),
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    Direct train control for emergencies and manual intervention
    
    Available commands:
    - **delay**: Delay train schedule (parameters: delay_minutes)
    - **reroute**: Change train route (parameters: new_route as list of section IDs)
    - **priority**: Change train priority (parameters: new_priority 1-10)
    - **stop**: Emergency stop (parameters: none)
    - **speed_limit**: Set speed restriction (parameters: max_speed_kmh)
    - **resume**: Resume normal operations (parameters: none)
    
    **Permissions Required:** Supervisor or higher
    
    **Rate Limited:** 10 requests/minute per controller
    
    **Emergency commands** (stop) require immediate notification to train operator
    """
    try:
        # Get train
        train = db.query(Train).filter(Train.id == train_id).first()
        
        if not train:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Train {train_id} not found"
            )
        
        # Check emergency command permissions
        if request.emergency and controller.auth_level.value not in ["manager", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Emergency commands require Manager or Admin authorization"
            )
        
        # Map command to decision action
        command_action_map = {
            "delay": DecisionAction.DELAY,
            "reroute": DecisionAction.REROUTE,
            "priority": DecisionAction.PRIORITY_CHANGE,
            "stop": DecisionAction.EMERGENCY_STOP,
            "speed_limit": DecisionAction.SPEED_LIMIT,
            "resume": DecisionAction.MANUAL_OVERRIDE
        }
        
        decision_action = command_action_map.get(
            request.command.value,
            DecisionAction.MANUAL_OVERRIDE
        )
        
        # Check if approval required for critical actions
        approval_required = request.command.value in ["stop", "reroute"] and not request.emergency
        
        # Create decision record
        decision = Decision(
            controller_id=controller.id,
            train_id=train_id,
            action_taken=decision_action,
            rationale=request.reason,
            parameters={
                "command": request.command.value,
                **request.parameters,
                "emergency": request.emergency
            },
            executed=False,
            approval_required=approval_required,
            ai_generated=False
        )
        
        db.add(decision)
        db.commit()
        db.refresh(decision)
        
        # Cache control command
        await redis_client.set(
            f"train_control:{train_id}:{decision.id}",
            {
                "train_id": train_id,
                "command": request.command.value,
                "controller_id": controller.id,
                "emergency": request.emergency,
                "timestamp": datetime.utcnow().isoformat()
            },
            ttl=3600
        )
        
        # Execute control command in background
        background_tasks.add_task(
            execute_train_control,
            train_id,
            request.command.value,
            request.parameters,
            decision.id,
            controller.id,
            db
        )
        
        logger.info(
            f"Train control command {request.command.value} initiated for train {train_id} "
            f"by controller {controller.id} (emergency: {request.emergency})"
        )
        
        return TrainControlResponse(
            success=True,
            train_id=train_id,
            train_number=train.train_number,
            command=request.command,
            execution_time=datetime.utcnow(),
            decision_id=decision.id,
            notification_sent=True,
            message=f"Train control command {request.command.value} initiated. "
                   f"{'Emergency notification sent to operator.' if request.emergency else ''}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling train {train_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during train control"
        )


@router.get(
    "/conflicts/active",
    response_model=ActiveConflictsResponse
)
async def get_active_conflicts(
    controller: Controller = Depends(require_operator),
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    Get current conflicts requiring controller attention
    
    Returns conflicts sorted by:
    1. Severity (critical > high > medium > low)
    2. Time to impact (urgent conflicts first)
    
    Includes AI recommendations for each conflict when available
    
    **Permissions Required:** Operator or higher
    """
    try:
        # Check cache first
        cache_key = "active_conflicts"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data and isinstance(cached_data, dict):
            # Return cached response (updated within last 30 seconds)
            if cached_data.get("timestamp"):
                cache_time = datetime.fromisoformat(cached_data["timestamp"])
                if (datetime.utcnow() - cache_time).seconds < 30:
                    logger.info("Returning cached active conflicts")
                    return ActiveConflictsResponse(**cached_data)
        
        # Query unresolved conflicts
        conflicts = db.query(Conflict).filter(
            Conflict.resolution_time.is_(None)
        ).all()
        
        # Calculate priority and time to impact
        conflicts_with_priority = []
        
        for conflict in conflicts:
            # Calculate time to impact (simplified - based on estimated_impact_minutes)
            time_to_impact = conflict.estimated_impact_minutes or 999
            
            # Calculate priority score
            severity_scores = {
                ConflictSeverity.CRITICAL: 100,
                ConflictSeverity.HIGH: 75,
                ConflictSeverity.MEDIUM: 50,
                ConflictSeverity.LOW: 25
            }
            
            severity_score = severity_scores.get(conflict.severity, 0)
            
            # Priority score: higher severity and closer time to impact = higher priority
            # Formula: severity_score + (100 / (time_to_impact + 1))
            priority_score = severity_score + (100.0 / (time_to_impact + 1))
            
            conflicts_with_priority.append({
                "conflict": conflict,
                "time_to_impact": float(time_to_impact),
                "priority_score": priority_score
            })
        
        # Sort by priority score (descending)
        conflicts_with_priority.sort(key=lambda x: x["priority_score"], reverse=True)
        
        # Build response
        conflict_responses = []
        for item in conflicts_with_priority:
            conflict = item["conflict"]
            conflict_responses.append(
                ConflictWithRecommendations(
                    id=conflict.id,
                    conflict_type=conflict.conflict_type,
                    severity=conflict.severity,
                    trains_involved=conflict.trains_involved,
                    sections_involved=conflict.sections_involved,
                    detection_time=conflict.detection_time,
                    estimated_impact_minutes=conflict.estimated_impact_minutes,
                    description=conflict.description,
                    time_to_impact=item["time_to_impact"],
                    ai_recommendations=conflict.ai_recommendations,
                    ai_confidence=float(conflict.ai_confidence) if conflict.ai_confidence else None,
                    priority_score=item["priority_score"]
                )
            )
        
        # Count critical and high priority conflicts
        critical_count = sum(
            1 for c in conflict_responses
            if c.severity == ConflictSeverity.CRITICAL
        )
        
        high_priority_count = sum(
            1 for c in conflict_responses
            if c.priority_score >= 75
        )
        
        response = ActiveConflictsResponse(
            total_conflicts=len(conflict_responses),
            critical_conflicts=critical_count,
            high_priority_conflicts=high_priority_count,
            conflicts=conflict_responses,
            timestamp=datetime.utcnow()
        )
        
        # Cache response for 30 seconds
        await redis_client.set(
            cache_key,
            response.model_dump(),
            ttl=30
        )
        
        logger.info(f"Retrieved {len(conflict_responses)} active conflicts")
        
        return response
    
    except Exception as e:
        logger.error(f"Error retrieving active conflicts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving conflicts"
        )


@router.post(
    "/decisions/log",
    response_model=DecisionLogResponse,
    dependencies=[Depends(standard_rate_limit)]
)
async def log_controller_decision(
    request: DecisionLogRequest,
    controller: Controller = Depends(require_operator),
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    Manual logging of controller actions for compliance
    
    Required for:
    - Manual conflict resolutions
    - Override decisions
    - Critical operational changes
    
    Creates permanent audit trail entry
    
    **Permissions Required:** Operator or higher
    
    **Rate Limited:** 30 requests/minute per controller
    """
    try:
        # Validate references exist
        if request.conflict_id:
            conflict = db.query(Conflict).filter(Conflict.id == request.conflict_id).first()
            if not conflict:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conflict {request.conflict_id} not found"
                )
        
        if request.train_id:
            train = db.query(Train).filter(Train.id == request.train_id).first()
            if not train:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Train {request.train_id} not found"
                )
        
        if request.section_id:
            section = db.query(Section).filter(Section.id == request.section_id).first()
            if not section:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Section {request.section_id} not found"
                )
        
        # Map action to DecisionAction enum
        action_map = {
            "reroute": DecisionAction.REROUTE,
            "delay": DecisionAction.DELAY,
            "priority_change": DecisionAction.PRIORITY_CHANGE,
            "emergency_stop": DecisionAction.EMERGENCY_STOP,
            "speed_limit": DecisionAction.SPEED_LIMIT,
            "manual_override": DecisionAction.MANUAL_OVERRIDE
        }
        
        decision_action = action_map.get(request.action_taken, DecisionAction.MANUAL_OVERRIDE)
        
        # Create decision record
        decision = Decision(
            controller_id=controller.id,
            conflict_id=request.conflict_id,
            train_id=request.train_id,
            section_id=request.section_id,
            action_taken=decision_action,
            rationale=request.rationale,
            parameters=request.parameters or {},
            executed=True,  # Manual log assumes action already taken
            execution_time=datetime.utcnow(),
            execution_result=request.outcome,
            approval_required=False,
            ai_generated=False
        )
        
        db.add(decision)
        db.commit()
        db.refresh(decision)
        
        # Cache decision for audit purposes
        await redis_client.set(
            f"decision_log:{decision.id}",
            {
                "decision_id": decision.id,
                "controller_id": controller.id,
                "action": request.action_taken,
                "timestamp": datetime.utcnow().isoformat(),
                "conflict_id": request.conflict_id,
                "train_id": request.train_id
            },
            ttl=86400  # 24 hours
        )
        
        # Send notification
        await connection_manager.broadcast_to_all({
            "type": "decision_logged",
            "decision_id": decision.id,
            "controller_id": controller.id,
            "action": request.action_taken,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(
            f"Decision logged by controller {controller.id}: "
            f"action={request.action_taken}, decision_id={decision.id}"
        )
        
        return DecisionLogResponse(
            success=True,
            decision_id=decision.id,
            controller_id=controller.id,
            timestamp=decision.timestamp,
            logged=True,
            message="Decision successfully logged in audit trail"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging decision: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error logging decision"
        )


@router.get(
    "/audit/decisions",
    response_model=AuditTrailResponse
)
async def query_audit_trail(
    filters: AuditQueryFilters = Depends(),
    controller: Controller = Depends(require_operator),
    db: Session = Depends(get_session)
):
    """
    Query audit trail with filters
    
    **Query Parameters:**
    - controller_id: Filter by controller
    - conflict_id: Filter by conflict
    - train_id: Filter by train
    - section_id: Filter by section
    - action_taken: Filter by action type
    - start_date: Start date for query range
    - end_date: End date for query range
    - executed_only: Only show executed decisions
    - approved_only: Only show approved decisions
    - limit: Maximum results (1-1000)
    - offset: Offset for pagination
    - export_format: Export as json/csv/pdf (optional)
    
    **Export Capability:** Set export_format to download audit report
    
    **Permissions Required:** Operator or higher
    """
    try:
        # Build query
        query = db.query(Decision).join(Controller)
        
        # Apply filters
        if filters.controller_id:
            query = query.filter(Decision.controller_id == filters.controller_id)
        
        if filters.conflict_id:
            query = query.filter(Decision.conflict_id == filters.conflict_id)
        
        if filters.train_id:
            query = query.filter(Decision.train_id == filters.train_id)
        
        if filters.section_id:
            query = query.filter(Decision.section_id == filters.section_id)
        
        if filters.action_taken:
            try:
                action_enum = DecisionAction[filters.action_taken.upper()]
                query = query.filter(Decision.action_taken == action_enum)
            except KeyError:
                pass
        
        if filters.start_date:
            query = query.filter(Decision.timestamp >= filters.start_date)
        
        if filters.end_date:
            query = query.filter(Decision.timestamp <= filters.end_date)
        
        if filters.executed_only:
            query = query.filter(Decision.executed == True)
        
        if filters.approved_only:
            query = query.filter(
                Decision.approval_required == True,
                Decision.approved_by_controller_id.isnot(None)
            )
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting and pagination
        query = query.order_by(desc(Decision.timestamp))
        query = query.offset(filters.offset).limit(filters.limit)
        
        # Execute query
        decisions = query.all()
        
        # Build response records
        decision_records = []
        for decision in decisions:
            # Get approved by controller name if applicable
            approved_by_name = None
            if decision.approved_by_controller_id:
                approved_controller = db.query(Controller).filter(
                    Controller.id == decision.approved_by_controller_id
                ).first()
                if approved_controller:
                    approved_by_name = approved_controller.name
            
            decision_records.append(
                DecisionAuditRecord(
                    id=decision.id,
                    controller_id=decision.controller_id,
                    controller_name=decision.controller.name,
                    controller_employee_id=decision.controller.employee_id,
                    conflict_id=decision.conflict_id,
                    train_id=decision.train_id,
                    section_id=decision.section_id,
                    action_taken=decision.action_taken.value,
                    timestamp=decision.timestamp,
                    rationale=decision.rationale,
                    parameters=decision.parameters,
                    executed=decision.executed,
                    execution_time=decision.execution_time,
                    execution_result=decision.execution_result,
                    approval_required=decision.approval_required,
                    approved_by_controller_id=decision.approved_by_controller_id,
                    approved_by_name=approved_by_name,
                    approval_time=decision.approval_time,
                    ai_generated=decision.ai_generated,
                    ai_confidence=float(decision.ai_confidence) if decision.ai_confidence else None
                )
            )
        
        # Calculate performance metrics
        performance_metrics = None
        if len(decision_records) > 0:
            executed_count = sum(1 for d in decision_records if d.executed)
            execution_rate = (executed_count / len(decision_records)) * 100
            
            # Calculate average resolution time for executed decisions
            resolution_times = []
            for d in decision_records:
                if d.executed and d.execution_time:
                    delta = (d.execution_time - d.timestamp).total_seconds() / 60
                    resolution_times.append(delta)
            
            avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            
            performance_metrics = {
                "execution_rate": round(execution_rate, 2),
                "average_resolution_time_minutes": round(avg_resolution, 2),
                "total_decisions": len(decision_records),
                "executed_decisions": executed_count
            }
        
        response = AuditTrailResponse(
            total_records=total_count,
            returned_records=len(decision_records),
            offset=filters.offset,
            decisions=decision_records,
            performance_metrics=performance_metrics,
            timestamp=datetime.utcnow()
        )
        
        logger.info(
            f"Audit trail query by controller {controller.id}: "
            f"{len(decision_records)} records returned"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error querying audit trail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error querying audit trail"
        )


@router.get(
    "/audit/performance",
    response_model=PerformanceMetricsResponse
)
async def get_performance_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    controller: Controller = Depends(require_supervisor),
    db: Session = Depends(get_session)
):
    """
    Get performance metrics for controller decisions
    
    Provides insights into:
    - Decision execution rates
    - Average resolution times
    - Decisions by controller and action type
    - AI vs manual decision comparison
    - Conflict resolution statistics
    
    **Permissions Required:** Supervisor or higher
    """
    try:
        # Default to last 30 days if not specified
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Query decisions in date range
        decisions = db.query(Decision).filter(
            Decision.timestamp >= start_date,
            Decision.timestamp <= end_date
        ).all()
        
        if not decisions:
            return PerformanceMetricsResponse(
                total_decisions=0,
                executed_decisions=0,
                execution_rate=0.0,
                average_resolution_time_minutes=0.0,
                decisions_by_controller={},
                decisions_by_action={},
                ai_vs_manual_decisions={"ai_generated": 0, "manual": 0},
                conflicts_resolved=0,
                conflicts_pending=0,
                average_ai_confidence=0.0,
                period_start=start_date,
                period_end=end_date
            )
        
        # Calculate metrics
        total_decisions = len(decisions)
        executed_decisions = sum(1 for d in decisions if d.executed)
        execution_rate = (executed_decisions / total_decisions) * 100
        
        # Average resolution time
        resolution_times = []
        for d in decisions:
            if d.executed and d.execution_time:
                delta = (d.execution_time - d.timestamp).total_seconds() / 60
                resolution_times.append(delta)
        
        avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        # Decisions by controller
        decisions_by_controller = {}
        for d in decisions:
            controller_name = d.controller.name if d.controller else "Unknown"
            decisions_by_controller[controller_name] = decisions_by_controller.get(controller_name, 0) + 1
        
        # Decisions by action
        decisions_by_action = {}
        for d in decisions:
            action = d.action_taken.value
            decisions_by_action[action] = decisions_by_action.get(action, 0) + 1
        
        # AI vs manual
        ai_decisions = sum(1 for d in decisions if d.ai_generated)
        manual_decisions = total_decisions - ai_decisions
        
        # Conflict statistics
        conflicts_with_decisions = db.query(Conflict).filter(
            Conflict.detection_time >= start_date,
            Conflict.detection_time <= end_date
        ).all()
        
        conflicts_resolved = sum(
            1 for c in conflicts_with_decisions
            if c.resolution_time is not None
        )
        
        conflicts_pending = len(conflicts_with_decisions) - conflicts_resolved
        
        # Average AI confidence
        ai_confidences = [
            float(d.ai_confidence)
            for d in decisions
            if d.ai_confidence is not None
        ]
        
        avg_ai_confidence = sum(ai_confidences) / len(ai_confidences) if ai_confidences else 0
        
        return PerformanceMetricsResponse(
            total_decisions=total_decisions,
            executed_decisions=executed_decisions,
            execution_rate=round(execution_rate, 2),
            average_resolution_time_minutes=round(avg_resolution, 2),
            decisions_by_controller=decisions_by_controller,
            decisions_by_action=decisions_by_action,
            ai_vs_manual_decisions={
                "ai_generated": ai_decisions,
                "manual": manual_decisions
            },
            conflicts_resolved=conflicts_resolved,
            conflicts_pending=conflicts_pending,
            average_ai_confidence=round(avg_ai_confidence, 4),
            period_start=start_date,
            period_end=end_date
        )
    
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error calculating metrics"
        )
