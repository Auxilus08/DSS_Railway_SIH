"""
Real-time conflict detection engine for railway traffic management.
Monitors train positions and detects potential conflicts with severity scoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import math
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from .models import Train, Position, Section, Conflict, SectionOccupancy, TrainSchedule, ConflictSeverity
from .db import get_db
from .websocket_manager import connection_manager
from .redis_client import RedisClient

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of conflicts that can be detected"""
    SPATIAL_COLLISION = "spatial_collision"
    TEMPORAL_CONFLICT = "temporal_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    JUNCTION_CONFLICT = "junction_conflict"
    SECTION_OVERLOAD = "section_overload"
    MAINTENANCE_CONFLICT = "maintenance_conflict"


@dataclass
class DetectedConflict:
    """Data class for detected conflicts"""
    conflict_type: ConflictType
    severity_score: int  # 1-10 scale
    trains_involved: List[int]
    sections_involved: List[int]
    time_to_impact: float  # minutes
    description: str
    predicted_impact_time: datetime
    resolution_suggestions: List[str]
    metadata: Dict[str, Any]


@dataclass
class TrainPrediction:
    """Predicted train position and timing"""
    train_id: int
    section_id: int
    arrival_time: datetime
    exit_time: datetime
    speed_kmh: float
    distance_to_section: float
    confidence: float  # 0-1


class ConflictDetector:
    """
    Real-time conflict detection engine for railway traffic management.
    
    Monitors all train positions within 1-hour prediction window and detects:
    - Spatial conflicts: Two trains approaching same section
    - Temporal conflicts: Scheduled arrivals within 2-minute safety buffer
    - Priority conflicts: Express trains blocked by slower freight
    - Junction conflicts: Multiple trains converging on junction
    """
    
    def __init__(self, db_session: Session, redis_client: Optional[RedisClient] = None):
        self.db = db_session
        self.redis_client = redis_client
        self.prediction_window_minutes = 60
        self.safety_buffer_minutes = 2
        self.detection_interval_seconds = 30
        self.alert_threshold_minutes = 5
        
        # Conflict severity weights
        self.severity_weights = {
            'time_factor': 0.3,  # How soon the conflict will occur
            'train_priority': 0.2,  # Priority of trains involved
            'passenger_impact': 0.25,  # Number of passengers affected
            'network_impact': 0.15,  # Impact on network flow
            'safety_risk': 0.1  # Safety risk level
        }
        
        # Performance metrics
        self.metrics = {
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'false_positives': 0,
            'detection_time_ms': 0,
            'predictions_made': 0
        }
        
        # Cache for frequent queries
        self._active_trains_cache = {}
        self._section_cache = {}
        self._cache_expiry = datetime.utcnow()
        
    async def detect_conflicts(self) -> List[DetectedConflict]:
        """
        Main conflict detection method.
        Returns list of detected conflicts sorted by severity.
        """
        start_time = datetime.utcnow()
        detected_conflicts = []
        
        try:
            # Update cache if expired
            if datetime.utcnow() > self._cache_expiry:
                await self._update_cache()
            
            # Get active trains and their predictions
            train_predictions = await self._get_train_predictions()
            
            if len(train_predictions) < 2:
                logger.debug("Less than 2 active trains, skipping conflict detection")
                return []
            
            # Detect different types of conflicts
            spatial_conflicts = await self._detect_spatial_conflicts(train_predictions)
            temporal_conflicts = await self._detect_temporal_conflicts(train_predictions)
            priority_conflicts = await self._detect_priority_conflicts(train_predictions)
            junction_conflicts = await self._detect_junction_conflicts(train_predictions)
            
            # Combine all conflicts
            all_conflicts = (
                spatial_conflicts + temporal_conflicts + 
                priority_conflicts + junction_conflicts
            )
            
            # Remove duplicates and calculate final severity
            detected_conflicts = await self._process_conflicts(all_conflicts)
            
            # Update metrics
            detection_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.metrics['detection_time_ms'] = detection_time
            self.metrics['conflicts_detected'] += len(detected_conflicts)
            
            logger.info(f"Detected {len(detected_conflicts)} conflicts in {detection_time:.2f}ms")
            
            return sorted(detected_conflicts, key=lambda x: x.severity_score, reverse=True)
            
        except Exception as e:
            logger.error(f"Error in conflict detection: {e}", exc_info=True)
            return []
    
    async def _get_train_predictions(self) -> List[TrainPrediction]:
        """Get predicted positions for all active trains within prediction window"""
        predictions = []
        current_time = datetime.utcnow()
        prediction_end = current_time + timedelta(minutes=self.prediction_window_minutes)
        
        try:
            # Get active trains with their latest positions
            query = """
                SELECT DISTINCT ON (t.id) 
                    t.id, t.train_number, t.type, t.speed_kmh, t.max_speed_kmh,
                    t.priority, t.capacity, t.current_load, t.current_section_id,
                    p.section_id, p.speed_kmh as current_speed, p.timestamp,
                    p.distance_from_start, s.length_meters, s.max_speed_kmh as section_max_speed
                FROM trains t
                LEFT JOIN positions p ON t.id = p.train_id
                LEFT JOIN sections s ON p.section_id = s.id
                WHERE t.operational_status = 'active'
                    AND p.timestamp > :time_threshold
                ORDER BY t.id, p.timestamp DESC
            """
            
            result = self.db.execute(
                text(query),
                {"time_threshold": current_time - timedelta(minutes=10)}
            ).fetchall()
            
            for row in result:
                if not row.section_id:
                    continue
                
                train_prediction = await self._predict_train_path(
                    train_id=row.id,
                    current_section_id=row.section_id,
                    current_speed=float(row.current_speed or 0),
                    max_speed=row.max_speed_kmh,
                    distance_from_start=float(row.distance_from_start or 0),
                    section_length=float(row.length_meters or 1000),
                    prediction_end=prediction_end
                )
                
                predictions.extend(train_prediction)
            
            self.metrics['predictions_made'] = len(predictions)
            return predictions
            
        except Exception as e:
            logger.error(f"Error getting train predictions: {e}")
            return []
    
    async def _predict_train_path(
        self, 
        train_id: int, 
        current_section_id: int, 
        current_speed: float,
        max_speed: int,
        distance_from_start: float,
        section_length: float,
        prediction_end: datetime
    ) -> List[TrainPrediction]:
        """Predict train path for the next hour"""
        predictions = []
        current_time = datetime.utcnow()
        
        try:
            # Time to exit current section
            remaining_distance = section_length - distance_from_start
            if current_speed > 0:
                time_to_exit = remaining_distance / (current_speed * 1000 / 60)  # Convert to minutes
                exit_time = current_time + timedelta(minutes=time_to_exit)
                
                if exit_time <= prediction_end:
                    predictions.append(TrainPrediction(
                        train_id=train_id,
                        section_id=current_section_id,
                        arrival_time=current_time,
                        exit_time=exit_time,
                        speed_kmh=current_speed,
                        distance_to_section=0,
                        confidence=0.9
                    ))
                
                # Get scheduled route for future sections
                future_sections = await self._get_train_route(train_id, current_section_id)
                
                simulation_time = exit_time
                for next_section_id, section_length in future_sections:
                    if simulation_time > prediction_end:
                        break
                    
                    # Estimate section traverse time
                    section_speed = min(current_speed, max_speed)
                    traverse_time = section_length / (section_speed * 1000 / 60)
                    
                    arrival_time = simulation_time
                    exit_time = simulation_time + timedelta(minutes=traverse_time)
                    
                    predictions.append(TrainPrediction(
                        train_id=train_id,
                        section_id=next_section_id,
                        arrival_time=arrival_time,
                        exit_time=exit_time,
                        speed_kmh=section_speed,
                        distance_to_section=(simulation_time - current_time).total_seconds() / 60 * section_speed,
                        confidence=max(0.5, 0.9 - len(predictions) * 0.1)  # Confidence decreases over time
                    ))
                    
                    simulation_time = exit_time
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting path for train {train_id}: {e}")
            return []
    
    async def _detect_spatial_conflicts(self, predictions: List[TrainPrediction]) -> List[DetectedConflict]:
        """Detect two trains approaching the same track section"""
        conflicts = []
        
        # Group predictions by section
        section_predictions = {}
        for pred in predictions:
            if pred.section_id not in section_predictions:
                section_predictions[pred.section_id] = []
            section_predictions[pred.section_id].append(pred)
        
        # Check each section for conflicts
        for section_id, preds in section_predictions.items():
            if len(preds) < 2:
                continue
            
            # Check section capacity
            section = self._section_cache.get(section_id)
            if not section:
                continue
            
            # Sort by arrival time
            preds.sort(key=lambda x: x.arrival_time)
            
            for i in range(len(preds) - 1):
                for j in range(i + 1, len(preds)):
                    pred1, pred2 = preds[i], preds[j]
                    
                    # Check if trains will overlap in time
                    overlap = self._calculate_time_overlap(pred1, pred2)
                    if overlap > 0 and section.capacity == 1:  # Single track conflict
                        
                        time_to_impact = (pred1.arrival_time - datetime.utcnow()).total_seconds() / 60
                        severity = await self._calculate_severity(
                            conflict_type=ConflictType.SPATIAL_COLLISION,
                            trains=[pred1.train_id, pred2.train_id],
                            time_to_impact=time_to_impact,
                            sections=[section_id]
                        )
                        
                        conflicts.append(DetectedConflict(
                            conflict_type=ConflictType.SPATIAL_COLLISION,
                            severity_score=severity,
                            trains_involved=[pred1.train_id, pred2.train_id],
                            sections_involved=[section_id],
                            time_to_impact=time_to_impact,
                            description=f"Spatial collision risk: Trains {pred1.train_id} and {pred2.train_id} approaching section {section_id}",
                            predicted_impact_time=pred1.arrival_time,
                            resolution_suggestions=await self._generate_spatial_resolutions(pred1, pred2, section),
                            metadata={
                                'overlap_minutes': overlap,
                                'section_capacity': section.capacity,
                                'train1_speed': pred1.speed_kmh,
                                'train2_speed': pred2.speed_kmh
                            }
                        ))
        
        return conflicts
    
    async def _detect_temporal_conflicts(self, predictions: List[TrainPrediction]) -> List[DetectedConflict]:
        """Detect scheduled arrivals within 2-minute safety buffer"""
        conflicts = []
        
        # Group by section
        section_predictions = {}
        for pred in predictions:
            if pred.section_id not in section_predictions:
                section_predictions[pred.section_id] = []
            section_predictions[pred.section_id].append(pred)
        
        for section_id, preds in section_predictions.items():
            if len(preds) < 2:
                continue
            
            preds.sort(key=lambda x: x.arrival_time)
            
            for i in range(len(preds) - 1):
                pred1, pred2 = preds[i], preds[i + 1]
                
                # Check if arrivals are within safety buffer
                time_diff = (pred2.arrival_time - pred1.exit_time).total_seconds() / 60
                
                if 0 < time_diff < self.safety_buffer_minutes:
                    time_to_impact = (pred1.arrival_time - datetime.utcnow()).total_seconds() / 60
                    severity = await self._calculate_severity(
                        conflict_type=ConflictType.TEMPORAL_CONFLICT,
                        trains=[pred1.train_id, pred2.train_id],
                        time_to_impact=time_to_impact,
                        sections=[section_id]
                    )
                    
                    conflicts.append(DetectedConflict(
                        conflict_type=ConflictType.TEMPORAL_CONFLICT,
                        severity_score=severity,
                        trains_involved=[pred1.train_id, pred2.train_id],
                        sections_involved=[section_id],
                        time_to_impact=time_to_impact,
                        description=f"Temporal conflict: Insufficient safety buffer ({time_diff:.1f} min) between trains {pred1.train_id} and {pred2.train_id}",
                        predicted_impact_time=pred1.arrival_time,
                        resolution_suggestions=await self._generate_temporal_resolutions(pred1, pred2, time_diff),
                        metadata={
                            'safety_buffer': time_diff,
                            'required_buffer': self.safety_buffer_minutes
                        }
                    ))
        
        return conflicts
    
    async def _detect_priority_conflicts(self, predictions: List[TrainPrediction]) -> List[DetectedConflict]:
        """Detect express trains blocked by slower freight trains"""
        conflicts = []
        
        # Get train priorities and types
        train_info = {}
        for pred in predictions:
            if pred.train_id not in train_info:
                train = self._active_trains_cache.get(pred.train_id)
                if train:
                    train_info[pred.train_id] = {
                        'priority': train.priority,
                        'type': train.type,
                        'max_speed': train.max_speed_kmh
                    }
        
        # Group by section and check for priority conflicts
        section_predictions = {}
        for pred in predictions:
            if pred.section_id not in section_predictions:
                section_predictions[pred.section_id] = []
            section_predictions[pred.section_id].append(pred)
        
        for section_id, preds in section_predictions.items():
            if len(preds) < 2:
                continue
            
            preds.sort(key=lambda x: x.arrival_time)
            
            for i in range(len(preds) - 1):
                pred1, pred2 = preds[i], preds[i + 1]
                
                train1_info = train_info.get(pred1.train_id)
                train2_info = train_info.get(pred2.train_id)
                
                if not train1_info or not train2_info:
                    continue
                
                # Check if higher priority train is blocked by lower priority
                if (train2_info['priority'] > train1_info['priority'] and 
                    train2_info['type'].value == 'express' and 
                    train1_info['type'].value == 'freight'):
                    
                    time_to_impact = (pred2.arrival_time - datetime.utcnow()).total_seconds() / 60
                    severity = await self._calculate_severity(
                        conflict_type=ConflictType.PRIORITY_CONFLICT,
                        trains=[pred1.train_id, pred2.train_id],
                        time_to_impact=time_to_impact,
                        sections=[section_id]
                    )
                    
                    conflicts.append(DetectedConflict(
                        conflict_type=ConflictType.PRIORITY_CONFLICT,
                        severity_score=severity,
                        trains_involved=[pred1.train_id, pred2.train_id],
                        sections_involved=[section_id],
                        time_to_impact=time_to_impact,
                        description=f"Priority conflict: Express train {pred2.train_id} blocked by freight train {pred1.train_id}",
                        predicted_impact_time=pred2.arrival_time,
                        resolution_suggestions=await self._generate_priority_resolutions(pred1, pred2, train1_info, train2_info),
                        metadata={
                            'blocking_train_priority': train1_info['priority'],
                            'blocked_train_priority': train2_info['priority'],
                            'speed_difference': train2_info['max_speed'] - train1_info['max_speed']
                        }
                    ))
        
        return conflicts
    
    async def _detect_junction_conflicts(self, predictions: List[TrainPrediction]) -> List[DetectedConflict]:
        """Detect multiple trains converging on junction"""
        conflicts = []
        
        # Get junction sections
        junction_sections = {
            section_id: section for section_id, section in self._section_cache.items()
            if section.section_type == 'junction'
        }
        
        for junction_id, junction in junction_sections.items():
            junction_predictions = [p for p in predictions if p.section_id == junction_id]
            
            if len(junction_predictions) < 2:
                continue
            
            junction_predictions.sort(key=lambda x: x.arrival_time)
            
            # Check for conflicts among multiple trains
            for i in range(len(junction_predictions) - 1):
                conflicting_trains = [junction_predictions[i]]
                
                for j in range(i + 1, len(junction_predictions)):
                    pred = junction_predictions[j]
                    overlap = self._calculate_time_overlap(junction_predictions[i], pred)
                    
                    if overlap > 0:
                        conflicting_trains.append(pred)
                
                if len(conflicting_trains) > junction.capacity:
                    train_ids = [p.train_id for p in conflicting_trains]
                    time_to_impact = (junction_predictions[i].arrival_time - datetime.utcnow()).total_seconds() / 60
                    
                    severity = await self._calculate_severity(
                        conflict_type=ConflictType.JUNCTION_CONFLICT,
                        trains=train_ids,
                        time_to_impact=time_to_impact,
                        sections=[junction_id]
                    )
                    
                    conflicts.append(DetectedConflict(
                        conflict_type=ConflictType.JUNCTION_CONFLICT,
                        severity_score=severity,
                        trains_involved=train_ids,
                        sections_involved=[junction_id],
                        time_to_impact=time_to_impact,
                        description=f"Junction conflict: {len(conflicting_trains)} trains converging on junction {junction_id} (capacity: {junction.capacity})",
                        predicted_impact_time=junction_predictions[i].arrival_time,
                        resolution_suggestions=await self._generate_junction_resolutions(conflicting_trains, junction),
                        metadata={
                            'junction_capacity': junction.capacity,
                            'trains_count': len(conflicting_trains),
                            'overflow': len(conflicting_trains) - junction.capacity
                        }
                    ))
        
        return conflicts
    
    async def _calculate_severity(
        self, 
        conflict_type: ConflictType, 
        trains: List[int], 
        time_to_impact: float,
        sections: List[int]
    ) -> int:
        """Calculate conflict severity score (1-10)"""
        try:
            # Time factor (0-3): Less time = higher severity
            if time_to_impact <= 1:
                time_factor = 3.0
            elif time_to_impact <= 5:
                time_factor = 2.5
            elif time_to_impact <= 15:
                time_factor = 2.0
            else:
                time_factor = 1.0
            
            # Train priority factor (0-2)
            priority_factor = 0
            passenger_impact = 0
            
            for train_id in trains:
                train = self._active_trains_cache.get(train_id)
                if train:
                    priority_factor += train.priority * 0.2
                    passenger_impact += train.current_load
            
            # Network impact factor (0-2)
            network_factor = len(sections) * 0.5 + len(trains) * 0.3
            
            # Safety risk factor (0-3)
            safety_factor = {
                ConflictType.SPATIAL_COLLISION: 3.0,
                ConflictType.JUNCTION_CONFLICT: 2.5,
                ConflictType.TEMPORAL_CONFLICT: 2.0,
                ConflictType.PRIORITY_CONFLICT: 1.5,
                ConflictType.SECTION_OVERLOAD: 1.0,
                ConflictType.MAINTENANCE_CONFLICT: 1.0
            }.get(conflict_type, 1.0)
            
            # Calculate weighted score (normalize to 1-10 scale)
            raw_score = (
                time_factor * self.severity_weights['time_factor'] +
                priority_factor * self.severity_weights['train_priority'] +
                (passenger_impact / 100) * self.severity_weights['passenger_impact'] +
                network_factor * self.severity_weights['network_impact'] +
                safety_factor * self.severity_weights['safety_risk']
            )
            
            # Scale to 1-10 range (raw_score typically ranges from ~1 to ~4)
            weighted_score = (raw_score / 4.0) * 9 + 1  # Maps ~1-4 to 1-10
            
            # Ensure score is between 1-10
            return max(1, min(10, int(weighted_score)))
            
        except Exception as e:
            logger.error(f"Error calculating severity: {e}")
            return 5  # Default medium severity
    
    def _calculate_time_overlap(self, pred1: TrainPrediction, pred2: TrainPrediction) -> float:
        """Calculate time overlap between two train predictions in minutes"""
        start1, end1 = pred1.arrival_time, pred1.exit_time
        start2, end2 = pred2.arrival_time, pred2.exit_time
        
        # Check for overlap
        latest_start = max(start1, start2)
        earliest_end = min(end1, end2)
        
        if latest_start < earliest_end:
            return (earliest_end - latest_start).total_seconds() / 60
        return 0
    
    async def _generate_spatial_resolutions(
        self, 
        pred1: TrainPrediction, 
        pred2: TrainPrediction, 
        section: Any
    ) -> List[str]:
        """Generate resolution suggestions for spatial conflicts"""
        suggestions = []
        
        # Speed adjustment
        if pred1.speed_kmh > pred2.speed_kmh:
            suggestions.append(f"Reduce speed of train {pred1.train_id} to allow train {pred2.train_id} to pass")
        else:
            suggestions.append(f"Increase speed of train {pred2.train_id} to reduce conflict window")
        
        # Timing adjustment
        suggestions.append(f"Delay train {pred2.train_id} by 3-5 minutes")
        
        # Rerouting (if applicable)
        suggestions.append(f"Consider alternative route for train {pred2.train_id}")
        
        return suggestions
    
    async def _generate_temporal_resolutions(
        self, 
        pred1: TrainPrediction, 
        pred2: TrainPrediction, 
        buffer_time: float
    ) -> List[str]:
        """Generate resolution suggestions for temporal conflicts"""
        suggestions = []
        
        needed_delay = self.safety_buffer_minutes - buffer_time + 0.5  # Add 0.5min extra buffer
        
        suggestions.append(f"Delay train {pred2.train_id} by {needed_delay:.1f} minutes")
        suggestions.append(f"Increase speed of train {pred1.train_id} to exit section faster")
        suggestions.append("Implement holding signal for train {pred2.train_id}")
        
        return suggestions
    
    async def _generate_priority_resolutions(
        self, 
        pred1: TrainPrediction, 
        pred2: TrainPrediction,
        train1_info: Dict,
        train2_info: Dict
    ) -> List[str]:
        """Generate resolution suggestions for priority conflicts"""
        suggestions = []
        
        suggestions.append(f"Hold freight train {pred1.train_id} at previous station")
        suggestions.append(f"Create express bypass for train {pred2.train_id}")
        suggestions.append(f"Increase priority of train {pred2.train_id} to {train2_info['priority'] + 1}")
        suggestions.append(f"Reroute freight train {pred1.train_id} to alternate track")
        
        return suggestions
    
    async def _generate_junction_resolutions(
        self, 
        conflicting_trains: List[TrainPrediction], 
        junction: Any
    ) -> List[str]:
        """Generate resolution suggestions for junction conflicts"""
        suggestions = []
        
        suggestions.append("Implement sequential junction crossing with 2-minute intervals")
        suggestions.append(f"Hold {len(conflicting_trains) - junction.capacity} trains at approach signals")
        suggestions.append("Prioritize by train type: Express > Local > Freight")
        suggestions.append("Consider temporary speed restrictions approaching junction")
        
        return suggestions
    
    async def _process_conflicts(self, conflicts: List[DetectedConflict]) -> List[DetectedConflict]:
        """Process and deduplicate conflicts"""
        # Remove duplicates based on trains and sections involved
        unique_conflicts = []
        seen_combinations = set()
        
        for conflict in conflicts:
            key = (
                tuple(sorted(conflict.trains_involved)),
                tuple(sorted(conflict.sections_involved)),
                conflict.conflict_type
            )
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_conflicts.append(conflict)
        
        return unique_conflicts
    
    async def _get_train_route(self, train_id: int, current_section_id: int) -> List[Tuple[int, float]]:
        """Get planned route for train from current position"""
        try:
            # Get train schedule
            schedule = self.db.query(TrainSchedule).filter(
                and_(
                    TrainSchedule.train_id == train_id,
                    TrainSchedule.active == True
                )
            ).first()
            
            if not schedule or not schedule.route_sections:
                return []
            
            # Find current position in route
            try:
                current_index = schedule.route_sections.index(current_section_id)
                future_sections = schedule.route_sections[current_index + 1:]
            except ValueError:
                return []
            
            # Get section lengths
            route_with_lengths = []
            if future_sections:
                sections = self.db.query(Section).filter(
                    Section.id.in_(future_sections)
                ).all()
                
                section_lengths = {s.id: float(s.length_meters) for s in sections}
                
                for section_id in future_sections:
                    length = section_lengths.get(section_id, 1000)  # Default 1km
                    route_with_lengths.append((section_id, length))
            
            return route_with_lengths
            
        except Exception as e:
            logger.error(f"Error getting train route for {train_id}: {e}")
            return []
    
    async def _update_cache(self):
        """Update cached data for performance"""
        try:
            # Cache active trains
            active_trains = self.db.query(Train).filter(Train.operational_status == 'active').all()
            self._active_trains_cache = {train.id: train for train in active_trains}
            
            # Cache sections
            sections = self.db.query(Section).filter(Section.active == True).all()
            self._section_cache = {section.id: section for section in sections}
            
            # Set cache expiry
            self._cache_expiry = datetime.utcnow() + timedelta(minutes=5)
            
            logger.debug(f"Updated cache: {len(self._active_trains_cache)} trains, {len(self._section_cache)} sections")
            
        except Exception as e:
            logger.error(f"Error updating cache: {e}")
    
    async def store_conflicts(self, conflicts: List[DetectedConflict]) -> List[int]:
        """Store detected conflicts in database"""
        stored_conflict_ids = []
        
        try:
            for conflict in conflicts:
                # Check if conflict already exists (avoid duplicates)
                existing = self.db.query(Conflict).filter(
                    and_(
                        Conflict.trains_involved == conflict.trains_involved,
                        Conflict.sections_involved == conflict.sections_involved,
                        Conflict.conflict_type == conflict.conflict_type.value,
                        Conflict.resolution_time.is_(None)
                    )
                ).first()
                
                if existing:
                    # Update existing conflict
                    existing.severity = ConflictSeverity(
                        'critical' if conflict.severity_score >= 8 else
                        'high' if conflict.severity_score >= 6 else
                        'medium' if conflict.severity_score >= 4 else 'low'
                    )
                    existing.description = conflict.description
                    existing.updated_at = datetime.utcnow()
                    stored_conflict_ids.append(existing.id)
                else:
                    # Create new conflict
                    db_conflict = Conflict(
                        conflict_type=conflict.conflict_type.value,
                        severity=ConflictSeverity(
                            'critical' if conflict.severity_score >= 8 else
                            'high' if conflict.severity_score >= 6 else
                            'medium' if conflict.severity_score >= 4 else 'low'
                        ),
                        trains_involved=conflict.trains_involved,
                        sections_involved=conflict.sections_involved,
                        detection_time=datetime.utcnow(),
                        estimated_impact_minutes=int(conflict.time_to_impact),
                        description=conflict.description,
                        auto_resolved=False
                    )
                    
                    self.db.add(db_conflict)
                    self.db.flush()
                    stored_conflict_ids.append(db_conflict.id)
            
            self.db.commit()
            return stored_conflict_ids
            
        except Exception as e:
            logger.error(f"Error storing conflicts: {e}")
            self.db.rollback()
            return []
    
    async def send_alerts(self, conflicts: List[DetectedConflict]):
        """Send real-time alerts for high-severity conflicts"""
        try:
            for conflict in conflicts:
                if (conflict.severity_score >= 6 and 
                    conflict.time_to_impact <= self.alert_threshold_minutes):
                    
                    alert_data = {
                        'conflict_id': f"temp_{hash(str(conflict.trains_involved) + str(conflict.sections_involved))}",
                        'type': conflict.conflict_type.value,
                        'severity': conflict.severity_score,
                        'trains_involved': conflict.trains_involved,
                        'sections_involved': conflict.sections_involved,
                        'time_to_impact': conflict.time_to_impact,
                        'description': conflict.description,
                        'resolution_suggestions': conflict.resolution_suggestions,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    # Send via WebSocket
                    await connection_manager.broadcast_conflict_alert(alert_data)
                    
                    # Store in Redis for persistence
                    if self.redis_client:
                        await self.redis_client.publish("railway:conflicts", alert_data)
                    
                    logger.warning(f"High-severity conflict alert sent: {conflict.description}")
            
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            **self.metrics,
            'cache_size': len(self._active_trains_cache),
            'last_cache_update': self._cache_expiry.isoformat() if self._cache_expiry else None
        }