"""
Position tracking API routes
Real-time train position updates and retrieval
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from ..db import get_session
from ..models import Train, Position, Section
from ..schemas import (
    PositionUpdate, BulkPositionUpdate, PositionResponse, 
    APIResponse, ErrorResponse, PositionBroadcast
)


def parse_wkt_coordinates(wkt_string: Optional[str]) -> Tuple[float, float]:
    """Parse WKT POINT string to extract latitude and longitude"""
    if not wkt_string:
        return 0.0, 0.0
    
    try:
        # Format: "POINT(longitude latitude)"
        coords_part = wkt_string.split('(')[1].rstrip(')')
        longitude, latitude = coords_part.split()
        return float(latitude), float(longitude)
    except (IndexError, ValueError):
        return 0.0, 0.0
from ..auth import get_current_active_controller
from ..redis_client import get_redis, RedisClient
from ..websocket_manager import connection_manager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

logger = logging.getLogger(__name__)

# Phase 4: Import AI components for automatic conflict detection
try:
    from ..railway_optimization import OptimizationEngine
    from ..railway_adapter import RailwayAIAdapter
    from ..models import Conflict, Decision
    AI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AI components not available for automatic conflict detection: {e}")
    AI_AVAILABLE = False

router = APIRouter(prefix="/api/trains", tags=["Position Tracking"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


async def validate_train_exists(train_id: int, db: Session) -> Train:
    """Validate that train exists and is active"""
    train = db.query(Train).filter(
        Train.id == train_id,
        Train.operational_status.in_(["active", "maintenance"])
    ).first()
    
    if not train:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Train with ID {train_id} not found or inactive"
        )
    
    return train


async def validate_section_exists(section_id: int, db: Session) -> Section:
    """Validate that section exists and is active"""
    section = db.query(Section).filter(
        Section.id == section_id,
        Section.active == True
    ).first()
    
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section with ID {section_id} not found or inactive"
        )
    
    return section


async def store_position_update(
    position_update: PositionUpdate,
    db: Session,
    redis_client: RedisClient
) -> Position:
    """Store position update in database and cache"""
    
    # Create position record
    position = Position(
        train_id=position_update.train_id,
        section_id=position_update.section_id,
        timestamp=position_update.timestamp,
        coordinates=f"POINT({position_update.coordinates.longitude} {position_update.coordinates.latitude})",
        speed_kmh=position_update.speed_kmh,
        direction=position_update.heading,
        distance_from_start=position_update.distance_from_start,
        signal_strength=position_update.signal_strength,
        gps_accuracy=position_update.gps_accuracy,
        altitude=position_update.coordinates.altitude
    )
    
    db.add(position)
    db.commit()
    db.refresh(position)
    
    # Cache the position
    position_data = {
        "train_id": position.train_id,
        "section_id": position.section_id,
        "coordinates": {
            "latitude": position_update.coordinates.latitude,
            "longitude": position_update.coordinates.longitude,
            "altitude": position_update.coordinates.altitude
        },
        "speed_kmh": float(position.speed_kmh),
        "heading": float(position.direction) if position.direction else None,
        "timestamp": position.timestamp.isoformat(),
        "distance_from_start": float(position.distance_from_start) if position.distance_from_start else None,
        "signal_strength": position.signal_strength,
        "gps_accuracy": float(position.gps_accuracy) if position.gps_accuracy else None
    }
    
    await redis_client.cache_train_position(position.train_id, position_data)
    
    return position


async def broadcast_position_update(
    train_id: int,
    train_number: str,
    train_type: str,
    position_data: dict,
    section_id: int,
    section_code: str,
    section_name: str,
    redis_client: RedisClient
):
    """Broadcast position update via WebSocket and Redis pub/sub"""
    
    position_broadcast = PositionBroadcast(
        train_id=train_id,
        train_number=train_number,
        train_type=train_type,
        position=PositionResponse(
            train_id=position_data["train_id"],
            section_id=section_id,
            section_code=section_code,
            section_name=section_name,
            coordinates=position_data["coordinates"],
            speed_kmh=position_data["speed_kmh"],
            heading=position_data["heading"],
            timestamp=position_data["timestamp"],
            distance_from_start=position_data.get("distance_from_start"),
            signal_strength=position_data.get("signal_strength"),
            gps_accuracy=position_data.get("gps_accuracy")
        ),
        timestamp=datetime.utcnow()
    )
    
    # Broadcast via WebSocket
    await connection_manager.broadcast_position_update(position_broadcast)
    
    # Publish to Redis for cross-instance communication
    await redis_client.publish("railway:positions", position_broadcast.dict())


async def check_for_conflicts_and_optimize(
    train: Train,
    position: Position,
    section: Section,
    db: Session,
    redis_client: RedisClient
):
    """
    Phase 4: Automatic conflict detection and AI optimization
    Check for potential conflicts when train position updates
    """
    if not AI_AVAILABLE:
        return
    
    try:
        # Check for high-risk scenarios that need AI optimization
        should_trigger_ai = False
        conflict_reasons = []
        
        # 1. High speed in congested section
        if position.speed_kmh > 80 and section.capacity_utilization > 0.8:
            should_trigger_ai = True
            conflict_reasons.append("High speed in congested section")
        
        # 2. Multiple trains in same section
        recent_positions = db.query(Position).filter(
            Position.section_id == section.id,
            Position.train_id != train.id,
            Position.timestamp >= datetime.utcnow() - timedelta(minutes=5)
        ).count()
        
        if recent_positions > 0:
            should_trigger_ai = True
            conflict_reasons.append(f"Multiple trains detected in section {section.section_code}")
        
        # 3. Check for existing unresolved conflicts in this section
        unresolved_conflicts = db.query(Conflict).filter(
            Conflict.section_id == section.id,
            Conflict.status.in_(["active", "pending"]),
            Conflict.severity.in_(["high", "critical"])
        ).count()
        
        if unresolved_conflicts > 0:
            should_trigger_ai = True
            conflict_reasons.append(f"Unresolved conflicts in section")
        
        # If AI optimization is needed, trigger it
        if should_trigger_ai:
            logger.info(f"Triggering AI optimization for train {train.train_number}: {', '.join(conflict_reasons)}")
            
            # Create or update conflict record
            conflict = Conflict(
                train_id=train.id,
                section_id=section.id,
                conflict_type="position_based",
                severity="high" if len(conflict_reasons) > 1 else "medium",
                description=f"Automatic conflict detection: {'; '.join(conflict_reasons)}",
                coordinates=position.coordinates,
                detected_at=datetime.utcnow(),
                status="active",
                # Phase 4: Mark for AI processing
                ai_analyzed=False,
                priority=8 if len(conflict_reasons) > 1 else 6
            )
            
            db.add(conflict)
            db.commit()
            db.refresh(conflict)
            
            # Initialize AI components
            try:
                optimizer = OptimizationEngine()
                adapter = RailwayAIAdapter()
                
                # Get conflict data for AI processing
                conflict_data = {
                    "conflict_id": conflict.id,
                    "train_id": train.id,
                    "section_id": section.id,
                    "severity": conflict.severity,
                    "conflict_type": conflict.conflict_type,
                    "current_speed": float(position.speed_kmh),
                    "section_capacity": section.capacity_utilization,
                    "reasons": conflict_reasons
                }
                
                # Run AI optimization
                ai_result = await adapter.optimize_conflict(conflict_data)
                
                if ai_result and ai_result.get("success"):
                    # Update conflict with AI results
                    conflict.ai_analyzed = True
                    conflict.ai_confidence = ai_result.get("confidence", 0.8)
                    conflict.ai_solution_id = ai_result.get("solution_id", f"auto_{conflict.id}")
                    conflict.ai_recommendations = ai_result.get("recommendations", {})
                    conflict.ai_analysis_time = datetime.utcnow()
                    
                    # Create AI-generated decision
                    if "decision" in ai_result:
                        decision = Decision(
                            conflict_id=conflict.id,
                            controller_id=None,  # AI-generated
                            decision_type="ai_optimization",
                            action=ai_result["decision"]["action"],
                            reasoning=ai_result["decision"]["reasoning"],
                            implemented=False,
                            # Phase 4: AI decision fields
                            ai_generated=True,
                            ai_solver_method=ai_result.get("solver_method", "rule_based"),
                            ai_score=ai_result.get("optimization_score", 0.8),
                            ai_confidence=ai_result.get("confidence", 0.8)
                        )
                        
                        db.add(decision)
                    
                    db.commit()
                    
                    # Broadcast AI optimization result
                    await broadcast_ai_optimization_result(
                        conflict, ai_result, redis_client
                    )
                    
                    logger.info(f"AI optimization completed for conflict {conflict.id}")
                    
            except Exception as ai_error:
                logger.error(f"AI optimization error for train {train.train_number}: {ai_error}")
                # Mark conflict as AI processing failed
                conflict.ai_analyzed = True
                conflict.ai_confidence = 0.0
                conflict.ai_recommendations = {"error": str(ai_error)}
                db.commit()
        
    except Exception as e:
        logger.error(f"Error in automatic conflict detection: {e}")


async def broadcast_ai_optimization_result(
    conflict: Conflict,
    ai_result: dict,
    redis_client: RedisClient
):
    """
    Phase 4: Broadcast AI optimization results via WebSocket
    """
    try:
        ai_broadcast = {
            "type": "ai_optimization",
            "conflict_id": conflict.id,
            "train_id": conflict.train_id,
            "section_id": conflict.section_id,
            "severity": conflict.severity,
            "ai_solution": ai_result,
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": ai_result.get("confidence", 0.0),
            "solver_method": ai_result.get("solver_method", "unknown")
        }
        
        # Broadcast via WebSocket
        await connection_manager.broadcast_ai_update(ai_broadcast)
        
        # Cache AI result in Redis
        await redis_client.cache_ai_result(conflict.id, ai_result)
        
        # Publish to Redis pub/sub
        await redis_client.publish("railway:ai_optimizations", ai_broadcast)
        
    except Exception as e:
        logger.error(f"Error broadcasting AI optimization result: {e}")


@router.post("/position", response_model=APIResponse)
@limiter.limit("1000/minute")
async def update_train_position(
    request: Request,
    position_update: PositionUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    Update single train position
    
    Rate limit: 1000 requests per minute per IP
    Response time target: <100ms
    """
    
    try:
        # Validate train exists
        train = await validate_train_exists(position_update.train_id, db)
        
        # Validate section exists
        section = await validate_section_exists(position_update.section_id, db)
        
        # Check rate limit for specific train
        rate_limit_key = f"train_position:{position_update.train_id}"
        rate_limit = await redis_client.check_rate_limit(rate_limit_key, 1000, 60)
        
        if not rate_limit["allowed"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded for this train",
                headers={
                    "X-RateLimit-Remaining": str(rate_limit["remaining"]),
                    "X-RateLimit-Reset": rate_limit["reset_time"].isoformat()
                }
            )
        
        # Store position update
        position = await store_position_update(position_update, db, redis_client)
        
        # Update train's current section if changed
        if train.current_section_id != position_update.section_id:
            train.current_section_id = position_update.section_id
            train.speed_kmh = position_update.speed_kmh
            db.commit()
        
        # Broadcast update in background
        position_data = {
            "train_id": position.train_id,
            "coordinates": {
                "latitude": parse_wkt_coordinates(position.coordinates)[0],
                "longitude": parse_wkt_coordinates(position.coordinates)[1],
                "altitude": position.altitude
            },
            "speed_kmh": float(position.speed_kmh),
            "heading": float(position.direction) if position.direction else 0,
            "timestamp": position.timestamp,
            "distance_from_start": float(position.distance_from_start) if position.distance_from_start else None,
            "signal_strength": position.signal_strength,
            "gps_accuracy": float(position.gps_accuracy) if position.gps_accuracy else None
        }
        
        background_tasks.add_task(
            broadcast_position_update,
            train.id, train.train_number, train.type,
            position_data, section.id, section.section_code, section.name,
            redis_client
        )
        
        # Phase 4: Check for conflicts and trigger AI optimization if needed
        background_tasks.add_task(
            check_for_conflicts_and_optimize,
            train, position, section, db, redis_client
        )
        
        # Increment performance counter
        await redis_client.increment_counter("position_updates_total")
        
        return APIResponse(
            success=True,
            message="Position updated successfully",
            data={
                "train_id": position.train_id,
                "timestamp": position.timestamp.isoformat(),
                "section_code": section.section_code
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating position for train {position_update.train_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating position"
        )


@router.post("/position/bulk", response_model=APIResponse)
@limiter.limit("100/minute")
async def bulk_update_positions(
    request: Request,
    bulk_update: BulkPositionUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis),
    controller = Depends(get_current_active_controller)
):
    """
    Bulk update multiple train positions
    
    Requires authentication
    Rate limit: 100 requests per minute per IP
    Max 100 positions per request
    """
    
    try:
        updated_positions = []
        errors = []
        
        for position_update in bulk_update.positions:
            try:
                # Validate train and section
                train = await validate_train_exists(position_update.train_id, db)
                section = await validate_section_exists(position_update.section_id, db)
                
                # Store position
                position = await store_position_update(position_update, db, redis_client)
                
                # Update train's current section
                if train.current_section_id != position_update.section_id:
                    train.current_section_id = position_update.section_id
                    train.speed_kmh = position_update.speed_kmh
                
                updated_positions.append({
                    "train_id": position.train_id,
                    "timestamp": position.timestamp.isoformat(),
                    "section_code": section.section_code
                })
                
                # Broadcast update in background
                position_data = {
                    "train_id": position.train_id,
                    "coordinates": {
                        "latitude": parse_wkt_coordinates(position.coordinates)[0],
                        "longitude": parse_wkt_coordinates(position.coordinates)[1],
                        "altitude": position.altitude
                    },
                    "speed_kmh": float(position.speed_kmh),
                    "heading": float(position.direction) if position.direction else 0,
                    "timestamp": position.timestamp,
                    "distance_from_start": float(position.distance_from_start) if position.distance_from_start else None,
                    "signal_strength": position.signal_strength,
                    "gps_accuracy": float(position.gps_accuracy) if position.gps_accuracy else None
                }
                
                background_tasks.add_task(
                    broadcast_position_update,
                    train.id, train.train_number, train.type,
                    position_data, section.id, section.section_code, section.name,
                    redis_client
                )
            
            except Exception as e:
                errors.append({
                    "train_id": position_update.train_id,
                    "error": str(e)
                })
        
        # Commit all train updates
        db.commit()
        
        # Update performance counters
        await redis_client.increment_counter("bulk_position_updates_total")
        await redis_client.increment_counter("position_updates_total", len(updated_positions))
        
        response_data = {
            "updated_count": len(updated_positions),
            "error_count": len(errors),
            "updated_positions": updated_positions
        }
        
        if errors:
            response_data["errors"] = errors
        
        return APIResponse(
            success=len(errors) == 0,
            message=f"Bulk update completed: {len(updated_positions)} updated, {len(errors)} errors",
            data=response_data
        )
    
    except Exception as e:
        logger.error(f"Error in bulk position update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during bulk update"
        )


@router.get("/{train_id}/position", response_model=PositionResponse)
async def get_train_position(
    train_id: int,
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    Get current train position
    
    Returns cached position if available, otherwise queries database
    """
    
    try:
        # Try cache first
        cached_position = await redis_client.get_train_position(train_id)
        
        if cached_position:
            # Get section info for cached position
            section = db.query(Section).filter(Section.id == cached_position["section_id"]).first()
            
            if section:
                return PositionResponse(
                    train_id=cached_position["train_id"],
                    section_id=cached_position["section_id"],
                    section_code=section.section_code,
                    section_name=section.name,
                    coordinates=cached_position["coordinates"],
                    speed_kmh=cached_position["speed_kmh"],
                    heading=cached_position["heading"] or 0,
                    timestamp=datetime.fromisoformat(cached_position["timestamp"]),
                    distance_from_start=cached_position.get("distance_from_start"),
                    signal_strength=cached_position.get("signal_strength"),
                    gps_accuracy=cached_position.get("gps_accuracy")
                )
        
        # Query database for latest position
        position = db.query(Position).filter(
            Position.train_id == train_id
        ).order_by(desc(Position.timestamp)).first()
        
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No position data found for train {train_id}"
            )
        
        # Get section info
        section = db.query(Section).filter(Section.id == position.section_id).first()
        
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section {position.section_id} not found"
            )
        
        # Build response
        coordinates = {
            "latitude": parse_wkt_coordinates(position.coordinates)[0],
            "longitude": parse_wkt_coordinates(position.coordinates)[1],
            "altitude": position.altitude
        }
        
        response = PositionResponse(
            train_id=position.train_id,
            section_id=position.section_id,
            section_code=section.section_code,
            section_name=section.name,
            coordinates=coordinates,
            speed_kmh=float(position.speed_kmh),
            heading=float(position.direction) if position.direction else 0,
            timestamp=position.timestamp,
            distance_from_start=float(position.distance_from_start) if position.distance_from_start else None,
            signal_strength=position.signal_strength,
            gps_accuracy=float(position.gps_accuracy) if position.gps_accuracy else None
        )
        
        # Cache the response
        await redis_client.cache_train_position(train_id, {
            "train_id": position.train_id,
            "section_id": position.section_id,
            "coordinates": coordinates,
            "speed_kmh": float(position.speed_kmh),
            "heading": float(position.direction) if position.direction else None,
            "timestamp": position.timestamp.isoformat(),
            "distance_from_start": float(position.distance_from_start) if position.distance_from_start else None,
            "signal_strength": position.signal_strength,
            "gps_accuracy": float(position.gps_accuracy) if position.gps_accuracy else None
        })
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting position for train {train_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving position"
        )


@router.get("/{train_id}/position/history")
async def get_train_position_history(
    train_id: int,
    hours: int = 1,
    limit: int = 100,
    db: Session = Depends(get_session)
):
    """
    Get train position history
    
    Parameters:
    - hours: Number of hours of history to retrieve (default: 1, max: 24)
    - limit: Maximum number of records to return (default: 100, max: 1000)
    """
    
    # Validate parameters
    if hours > 24:
        hours = 24
    if limit > 1000:
        limit = 1000
    
    try:
        # Validate train exists
        train = await validate_train_exists(train_id, db)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Query position history
        positions = db.query(Position).filter(
            and_(
                Position.train_id == train_id,
                Position.timestamp >= start_time,
                Position.timestamp <= end_time
            )
        ).order_by(desc(Position.timestamp)).limit(limit).all()
        
        # Build response
        history = []
        for position in positions:
            section = db.query(Section).filter(Section.id == position.section_id).first()
            
            coordinates = {
                "latitude": parse_wkt_coordinates(position.coordinates)[0],
                "longitude": parse_wkt_coordinates(position.coordinates)[1],
                "altitude": position.altitude
            }
            
            history.append({
                "timestamp": position.timestamp.isoformat(),
                "section_id": position.section_id,
                "section_code": section.section_code if section else "UNKNOWN",
                "coordinates": coordinates,
                "speed_kmh": float(position.speed_kmh),
                "heading": float(position.direction) if position.direction else 0,
                "distance_from_start": float(position.distance_from_start) if position.distance_from_start else None,
                "signal_strength": position.signal_strength,
                "gps_accuracy": float(position.gps_accuracy) if position.gps_accuracy else None
            })
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(history)} position records",
            data={
                "train_id": train_id,
                "train_number": train.train_number,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "hours": hours
                },
                "total_records": len(history),
                "positions": history
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting position history for train {train_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving position history"
        )