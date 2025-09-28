"""
Section status and occupancy API routes
Track section monitoring and management
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from ..db import get_session
from ..models import Section, Train, SectionOccupancy, Position, MaintenanceWindow
from ..schemas import (
    SectionResponse, SectionStatus, SectionStatusSummary, 
    TrainResponse, APIResponse
)
from ..auth import get_current_active_controller
from ..redis_client import get_redis, RedisClient
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sections", tags=["Section Management"])


async def calculate_section_status(section: Section, db: Session) -> str:
    """Calculate section status based on occupancy and maintenance"""
    
    # Check for active maintenance
    active_maintenance = db.query(MaintenanceWindow).filter(
        and_(
            MaintenanceWindow.section_id == section.id,
            MaintenanceWindow.start_time <= datetime.utcnow(),
            MaintenanceWindow.end_time >= datetime.utcnow(),
            MaintenanceWindow.affects_traffic == True
        )
    ).first()
    
    if active_maintenance:
        return "maintenance"
    
    # Check current occupancy
    current_occupancy = db.query(SectionOccupancy).filter(
        and_(
            SectionOccupancy.section_id == section.id,
            SectionOccupancy.exit_time.is_(None)
        )
    ).count()
    
    if current_occupancy == 0:
        return "available"
    elif current_occupancy >= section.capacity:
        return "full"
    else:
        return "busy"


async def get_section_trains(section_id: int, db: Session) -> List[TrainResponse]:
    """Get trains currently in the section"""
    
    # Get trains from occupancy records
    occupancy_trains = db.query(Train).join(
        SectionOccupancy,
        and_(
            Train.id == SectionOccupancy.train_id,
            SectionOccupancy.section_id == section_id,
            SectionOccupancy.exit_time.is_(None)
        )
    ).all()
    
    # Also get trains with current_section_id set to this section
    current_section_trains = db.query(Train).filter(
        Train.current_section_id == section_id,
        Train.operational_status.in_(["active", "maintenance"])
    ).all()
    
    # Combine and deduplicate
    all_trains = {train.id: train for train in occupancy_trains + current_section_trains}
    
    return [
        TrainResponse(
            id=train.id,
            train_number=train.train_number,
            type=train.type,
            max_speed_kmh=train.max_speed_kmh,
            capacity=train.capacity,
            priority=train.priority,
            length_meters=float(train.length_meters),
            weight_tons=float(train.weight_tons),
            current_section_id=train.current_section_id,
            speed_kmh=float(train.speed_kmh),
            current_load=train.current_load,
            operational_status=train.operational_status,
            created_at=train.created_at,
            updated_at=train.updated_at
        )
        for train in all_trains.values()
    ]


@router.get("/status", response_model=SectionStatusSummary)
async def get_sections_status(
    section_ids: Optional[List[int]] = Query(None, description="Specific section IDs to query"),
    section_type: Optional[str] = Query(None, description="Filter by section type"),
    include_inactive: bool = Query(False, description="Include inactive sections"),
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis),
    controller = Depends(get_current_active_controller)
):
    """
    Get track section occupancy status
    
    Returns current occupancy, utilization, and trains present for each section
    """
    
    try:
        # Build query
        query = db.query(Section)
        
        if not include_inactive:
            query = query.filter(Section.active == True)
        
        if section_ids:
            query = query.filter(Section.id.in_(section_ids))
        
        if section_type:
            query = query.filter(Section.section_type == section_type)
        
        # Check controller permissions for section access
        if hasattr(controller, 'section_responsibility') and controller.section_responsibility:
            # Handle auth_level checking
            auth_level_val = getattr(controller, 'auth_level', None)
            if hasattr(auth_level_val, 'value'):
                auth_level_str = auth_level_val.value
            else:
                auth_level_str = str(auth_level_val) if auth_level_val else 'operator'
            
            if auth_level_str not in ["MANAGER", "ADMIN"]:
                # Filter to only sections the controller is responsible for
                # Handle both array and JSON string formats
                responsibility = controller.section_responsibility
                if isinstance(responsibility, str):
                    # For SQLite test model (JSON string)
                    import json
                    try:
                        responsibility = json.loads(responsibility)
                    except:
                        responsibility = []
                query = query.filter(Section.id.in_(responsibility))
        
        sections = query.order_by(Section.section_code).all()
        
        if not sections:
            return SectionStatusSummary(
                sections=[],
                total_sections=0,
                occupied_sections=0,
                network_utilization=0.0,
                timestamp=datetime.utcnow()
            )
        
        # Process each section
        section_statuses = []
        occupied_count = 0
        
        for section in sections:
            # Try to get cached status first
            cache_key = f"section:status:{section.id}"
            cached_status = await redis_client.get(cache_key)
            
            if cached_status and datetime.fromisoformat(cached_status["timestamp"]) > datetime.utcnow() - timedelta(minutes=1):
                # Use cached data if less than 1 minute old
                section_status = SectionStatus(**cached_status)
            else:
                # Calculate fresh status
                current_occupancy = db.query(SectionOccupancy).filter(
                    and_(
                        SectionOccupancy.section_id == section.id,
                        SectionOccupancy.exit_time.is_(None)
                    )
                ).count()
                
                utilization_percentage = (current_occupancy / section.capacity * 100) if section.capacity > 0 else 0
                section_status_val = await calculate_section_status(section, db)
                trains_present = await get_section_trains(section.id, db)
                
                section_response = SectionResponse(
                    id=section.id,
                    name=section.name,
                    section_code=section.section_code,
                    section_type=section.section_type,
                    length_meters=float(section.length_meters),
                    max_speed_kmh=section.max_speed_kmh,
                    capacity=section.capacity,
                    electrified=section.electrified,
                    signaling_system=section.signaling_system,
                    active=section.active,
                    created_at=section.created_at
                )
                
                section_status = SectionStatus(
                    section=section_response,
                    current_occupancy=current_occupancy,
                    utilization_percentage=utilization_percentage,
                    trains_present=trains_present,
                    status=section_status_val
                )
                
                # Cache the status
                await redis_client.set(cache_key, section_status.dict(), ttl=60)  # 1 minute TTL
            
            section_statuses.append(section_status)
            
            if section_status.current_occupancy > 0:
                occupied_count += 1
        
        # Calculate network utilization
        total_sections = len(sections)
        network_utilization = (occupied_count / total_sections * 100) if total_sections > 0 else 0
        
        return SectionStatusSummary(
            sections=section_statuses,
            total_sections=total_sections,
            occupied_sections=occupied_count,
            network_utilization=network_utilization,
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Error getting section status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving section status"
        )


@router.get("/{section_id}/status", response_model=SectionStatus)
async def get_section_status(
    section_id: int,
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis),
    controller = Depends(get_current_active_controller)
):
    """
    Get detailed status for a specific section
    """
    
    try:
        # Check if section exists
        section = db.query(Section).filter(Section.id == section_id).first()
        
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section with ID {section_id} not found"
            )
        
        # Check controller permissions  
        if hasattr(controller, 'section_responsibility') and controller.section_responsibility:
            # Handle auth_level checking
            auth_level_val = getattr(controller, 'auth_level', None)
            if hasattr(auth_level_val, 'value'):
                auth_level_str = auth_level_val.value
            else:
                auth_level_str = str(auth_level_val) if auth_level_val else 'operator'
            
            # Handle both array and JSON string formats
            responsibility = controller.section_responsibility
            if isinstance(responsibility, str):
                # For SQLite test model (JSON string)
                import json
                try:
                    responsibility = json.loads(responsibility)
                except:
                    responsibility = []
            
            if (auth_level_str not in ["MANAGER", "ADMIN"] and
                section_id not in responsibility):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to access this section"
                )
        
        # Try cache first
        cache_key = f"section:status:{section_id}"
        cached_status = await redis_client.get(cache_key)
        
        if cached_status and datetime.fromisoformat(cached_status["timestamp"]) > datetime.utcnow() - timedelta(minutes=1):
            return SectionStatus(**cached_status)
        
        # Calculate fresh status
        current_occupancy = db.query(SectionOccupancy).filter(
            and_(
                SectionOccupancy.section_id == section_id,
                SectionOccupancy.exit_time.is_(None)
            )
        ).count()
        
        utilization_percentage = (current_occupancy / section.capacity * 100) if section.capacity > 0 else 0
        section_status_val = await calculate_section_status(section, db)
        trains_present = await get_section_trains(section_id, db)
        
        section_response = SectionResponse(
            id=section.id,
            name=section.name,
            section_code=section.section_code,
            section_type=section.section_type,
            length_meters=float(section.length_meters),
            max_speed_kmh=section.max_speed_kmh,
            capacity=section.capacity,
            electrified=section.electrified,
            signaling_system=section.signaling_system,
            active=section.active,
            created_at=section.created_at
        )
        
        section_status = SectionStatus(
            section=section_response,
            current_occupancy=current_occupancy,
            utilization_percentage=utilization_percentage,
            trains_present=trains_present,
            status=section_status_val
        )
        
        # Cache the status
        await redis_client.set(cache_key, section_status.dict(), ttl=60)
        
        return section_status
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for section {section_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving section status"
        )


@router.get("/{section_id}/occupancy-history")
async def get_section_occupancy_history(
    section_id: int,
    hours: int = Query(24, ge=1, le=168, description="Hours of history (1-168)"),
    db: Session = Depends(get_session),
    controller = Depends(get_current_active_controller)
):
    """
    Get section occupancy history
    
    Shows trains that entered/exited the section in the specified time period
    """
    
    try:
        # Check if section exists
        section = db.query(Section).filter(Section.id == section_id).first()
        
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section with ID {section_id} not found"
            )
        
        # Check controller permissions (occupancy history)
        if hasattr(controller, 'section_responsibility') and controller.section_responsibility:
            # Handle auth_level checking
            auth_level_val = getattr(controller, 'auth_level', None)
            if hasattr(auth_level_val, 'value'):
                auth_level_str = auth_level_val.value
            else:
                auth_level_str = str(auth_level_val) if auth_level_val else 'operator'
            
            # Handle both array and JSON string formats
            responsibility = controller.section_responsibility
            if isinstance(responsibility, str):
                # For SQLite test model (JSON string)
                import json
                try:
                    responsibility = json.loads(responsibility)
                except:
                    responsibility = []
            
            if (auth_level_str not in ["MANAGER", "ADMIN"] and
                section_id not in responsibility):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to access this section"
                )
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get occupancy records
        occupancy_records = db.query(SectionOccupancy).filter(
            and_(
                SectionOccupancy.section_id == section_id,
                SectionOccupancy.entry_time >= start_time
            )
        ).order_by(desc(SectionOccupancy.entry_time)).all()
        
        # Build history
        history = []
        for record in occupancy_records:
            train = db.query(Train).filter(Train.id == record.train_id).first()
            
            duration = None
            if record.exit_time:
                duration = (record.exit_time - record.entry_time).total_seconds() / 60  # minutes
            
            history.append({
                "train_id": record.train_id,
                "train_number": train.train_number if train else "UNKNOWN",
                "train_type": train.type.value if train else "unknown",
                "entry_time": record.entry_time.isoformat(),
                "exit_time": record.exit_time.isoformat() if record.exit_time else None,
                "expected_exit_time": record.expected_exit_time.isoformat() if record.expected_exit_time else None,
                "duration_minutes": duration,
                "still_present": record.exit_time is None
            })
        
        # Calculate statistics
        total_visits = len(history)
        current_occupancy = sum(1 for h in history if h["still_present"])
        completed_visits = [h for h in history if h["duration_minutes"] is not None]
        avg_duration = sum(h["duration_minutes"] for h in completed_visits) / len(completed_visits) if completed_visits else 0
        
        return APIResponse(
            success=True,
            message=f"Retrieved occupancy history for section {section.section_code}",
            data={
                "section": {
                    "id": section.id,
                    "section_code": section.section_code,
                    "name": section.name,
                    "capacity": section.capacity
                },
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "hours": hours
                },
                "statistics": {
                    "total_visits": total_visits,
                    "current_occupancy": current_occupancy,
                    "completed_visits": len(completed_visits),
                    "average_duration_minutes": round(avg_duration, 2),
                    "utilization_percentage": (current_occupancy / section.capacity * 100) if section.capacity > 0 else 0
                },
                "history": history
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting occupancy history for section {section_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving occupancy history"
        )


@router.get("/", response_model=List[SectionResponse])
async def list_sections(
    section_type: Optional[str] = Query(None, description="Filter by section type"),
    active_only: bool = Query(True, description="Only return active sections"),
    db: Session = Depends(get_session),
    controller = Depends(get_current_active_controller)
):
    """
    List all sections accessible to the controller
    """
    
    try:
        # Build query
        query = db.query(Section)
        
        if active_only:
            query = query.filter(Section.active == True)
        
        if section_type:
            query = query.filter(Section.section_type == section_type)
        
        # Apply controller permissions (list sections)
        if hasattr(controller, 'section_responsibility') and controller.section_responsibility:
            # Handle auth_level checking
            auth_level_val = getattr(controller, 'auth_level', None)
            if hasattr(auth_level_val, 'value'):
                auth_level_str = auth_level_val.value
            else:
                auth_level_str = str(auth_level_val) if auth_level_val else 'operator'
            
            if auth_level_str not in ["MANAGER", "ADMIN"]:
                # Handle both array and JSON string formats
                responsibility = controller.section_responsibility
                if isinstance(responsibility, str):
                    # For SQLite test model (JSON string)
                    import json
                    try:
                        responsibility = json.loads(responsibility)
                    except:
                        responsibility = []
                query = query.filter(Section.id.in_(responsibility))
        
        sections = query.order_by(Section.section_code).all()
        
        return [
            SectionResponse(
                id=section.id,
                name=section.name,
                section_code=section.section_code,
                section_type=section.section_type,
                length_meters=float(section.length_meters),
                max_speed_kmh=section.max_speed_kmh,
                capacity=section.capacity,
                electrified=section.electrified,
                signaling_system=section.signaling_system,
                active=section.active,
                created_at=section.created_at
            )
            for section in sections
        ]
    
    except Exception as e:
        logger.error(f"Error listing sections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing sections"
        )