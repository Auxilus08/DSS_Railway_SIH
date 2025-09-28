"""
Performance optimizations for railway conflict detection system.
Optimized for handling 500+ trains with efficient algorithms and database queries.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import heapq
import math

from sqlalchemy.orm import Session
from sqlalchemy import text, select, and_, or_, func
from sqlalchemy.orm import load_only, selectinload
from .models import Train, Position, Section, TrainSchedule
from .conflict_detector import TrainPrediction, DetectedConflict, ConflictType

logger = logging.getLogger(__name__)


@dataclass
class OptimizedTrainData:
    """Optimized train data structure for fast lookups"""
    id: int
    train_number: str
    type: str
    priority: int
    max_speed: int
    capacity: int
    current_load: int
    current_section_id: Optional[int]
    last_position_time: datetime
    speed_kmh: float
    distance_from_start: float


@dataclass
class OptimizedSectionData:
    """Optimized section data structure"""
    id: int
    section_code: str
    section_type: str
    length_meters: float
    max_speed_kmh: int
    capacity: int
    is_junction: bool
    connected_sections: List[int]


class PerformanceOptimizer:
    """
    Performance optimization utilities for conflict detection system.
    Implements various optimization strategies for handling large-scale operations.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.batch_size = 100
        self.max_parallel_operations = 50
        self.cache_ttl_seconds = 300  # 5 minutes
        
        # Performance metrics
        self.metrics = {
            'queries_executed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_operations': 0,
            'optimization_time_saved': 0.0
        }
        
        # In-memory caches
        self._train_cache: Dict[int, OptimizedTrainData] = {}
        self._section_cache: Dict[int, OptimizedSectionData] = {}
        self._route_cache: Dict[int, List[int]] = {}
        self._distance_matrix: Dict[Tuple[int, int], float] = {}
        
        # Spatial indexing for sections
        self._spatial_index: Dict[Tuple[int, int], List[int]] = {}
        
        # Cache expiry tracking
        self._cache_expiry = datetime.utcnow()
    
    async def bulk_load_train_data(self, limit: int = 500) -> Dict[int, OptimizedTrainData]:
        """
        Efficiently load train data using optimized queries with minimal data transfer.
        Uses SQL optimization techniques and batch processing.
        """
        try:
            start_time = datetime.utcnow()
            
            # Optimized query with specific columns only
            query = text("""
                SELECT DISTINCT ON (t.id)
                    t.id, t.train_number, t.type, t.priority, t.max_speed_kmh,
                    t.capacity, t.current_load, t.current_section_id,
                    p.timestamp as last_position_time, p.speed_kmh, p.distance_from_start
                FROM trains t
                LEFT JOIN positions p ON t.id = p.train_id
                WHERE t.operational_status = 'active'
                    AND (p.timestamp IS NULL OR p.timestamp > :time_threshold)
                ORDER BY t.id, p.timestamp DESC
                LIMIT :limit
            """)
            
            result = self.db.execute(query, {
                'time_threshold': datetime.utcnow() - timedelta(minutes=15),
                'limit': limit
            }).fetchall()
            
            # Convert to optimized data structures
            train_data = {}
            for row in result:
                train_data[row.id] = OptimizedTrainData(
                    id=row.id,
                    train_number=row.train_number,
                    type=row.type,
                    priority=row.priority,
                    max_speed=row.max_speed_kmh,
                    capacity=row.capacity,
                    current_load=row.current_load,
                    current_section_id=row.current_section_id,
                    last_position_time=row.last_position_time or datetime.utcnow(),
                    speed_kmh=float(row.speed_kmh or 0),
                    distance_from_start=float(row.distance_from_start or 0)
                )
            
            # Update cache
            self._train_cache = train_data
            
            load_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Bulk loaded {len(train_data)} trains in {load_time:.3f}s")
            
            self.metrics['queries_executed'] += 1
            return train_data
            
        except Exception as e:
            logger.error(f"Error in bulk_load_train_data: {e}")
            return {}
    
    async def bulk_load_section_data(self) -> Dict[int, OptimizedSectionData]:
        """
        Efficiently load section data with connectivity information.
        """
        try:
            start_time = datetime.utcnow()
            
            # Load sections with optimized query
            query = text("""
                SELECT 
                    id, section_code, section_type, length_meters, 
                    max_speed_kmh, capacity, junction_ids
                FROM sections 
                WHERE active = true
                ORDER BY id
            """)
            
            result = self.db.execute(query).fetchall()
            
            section_data = {}
            for row in result:
                # Parse connected sections from junction_ids or implement graph logic
                connected_sections = row.junction_ids or []
                
                section_data[row.id] = OptimizedSectionData(
                    id=row.id,
                    section_code=row.section_code,
                    section_type=row.section_type,
                    length_meters=float(row.length_meters),
                    max_speed_kmh=row.max_speed_kmh,
                    capacity=row.capacity,
                    is_junction=row.section_type == 'junction',
                    connected_sections=connected_sections
                )
            
            self._section_cache = section_data
            
            # Build spatial index for fast proximity queries
            await self._build_spatial_index(section_data)
            
            load_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Bulk loaded {len(section_data)} sections in {load_time:.3f}s")
            
            self.metrics['queries_executed'] += 1
            return section_data
            
        except Exception as e:
            logger.error(f"Error in bulk_load_section_data: {e}")
            return {}
    
    async def _build_spatial_index(self, section_data: Dict[int, OptimizedSectionData]):
        """Build spatial index for fast section proximity queries"""
        try:
            # Simple grid-based spatial indexing
            # In production, this would use more sophisticated spatial indexing like R-tree
            grid_size = 1000  # 1km grid cells
            
            for section_id, section in section_data.items():
                # For now, use section_id as proxy for coordinates
                # In real implementation, would use actual coordinates
                grid_x = (section_id % 100) * grid_size
                grid_y = (section_id // 100) * grid_size
                
                grid_key = (grid_x // grid_size, grid_y // grid_size)
                
                if grid_key not in self._spatial_index:
                    self._spatial_index[grid_key] = []
                
                self._spatial_index[grid_key].append(section_id)
            
            logger.debug(f"Built spatial index with {len(self._spatial_index)} grid cells")
            
        except Exception as e:
            logger.error(f"Error building spatial index: {e}")
    
    async def optimized_predict_train_paths(
        self, 
        train_data: Dict[int, OptimizedTrainData],
        prediction_window_minutes: int = 60
    ) -> Dict[int, List[TrainPrediction]]:
        """
        Optimized train path prediction using parallel processing and caching.
        """
        try:
            start_time = datetime.utcnow()
            
            # Group trains by sections for batch processing
            section_groups = defaultdict(list)
            for train_id, train in train_data.items():
                if train.current_section_id:
                    section_groups[train.current_section_id].append(train_id)
            
            # Process predictions in parallel batches
            prediction_tasks = []
            for section_id, train_ids in section_groups.items():
                # Process in batches to avoid overwhelming the system
                for i in range(0, len(train_ids), self.batch_size):
                    batch = train_ids[i:i + self.batch_size]
                    task = self._predict_batch_paths(batch, train_data, prediction_window_minutes)
                    prediction_tasks.append(task)
            
            # Limit concurrent operations
            semaphore = asyncio.Semaphore(self.max_parallel_operations)
            
            async def limited_predict(task):
                async with semaphore:
                    return await task
            
            # Execute predictions with concurrency limit
            batch_results = await asyncio.gather(
                *[limited_predict(task) for task in prediction_tasks],
                return_exceptions=True
            )
            
            # Combine results
            all_predictions = {}
            for batch_result in batch_results:
                if isinstance(batch_result, dict):
                    all_predictions.update(batch_result)
                elif isinstance(batch_result, Exception):
                    logger.error(f"Batch prediction error: {batch_result}")
            
            prediction_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Generated predictions for {len(all_predictions)} trains in {prediction_time:.3f}s")
            
            return all_predictions
            
        except Exception as e:
            logger.error(f"Error in optimized_predict_train_paths: {e}")
            return {}
    
    async def _predict_batch_paths(
        self,
        train_ids: List[int],
        train_data: Dict[int, OptimizedTrainData],
        prediction_window_minutes: int
    ) -> Dict[int, List[TrainPrediction]]:
        """Predict paths for a batch of trains"""
        batch_predictions = {}
        current_time = datetime.utcnow()
        prediction_end = current_time + timedelta(minutes=prediction_window_minutes)
        
        for train_id in train_ids:
            train = train_data.get(train_id)
            if not train or not train.current_section_id:
                continue
            
            try:
                # Get cached route or compute
                route = await self._get_cached_route(train_id, train.current_section_id)
                
                # Generate predictions using optimized algorithm
                predictions = await self._fast_path_prediction(
                    train, route, current_time, prediction_end
                )
                
                batch_predictions[train_id] = predictions
                
            except Exception as e:
                logger.error(f"Error predicting path for train {train_id}: {e}")
                continue
        
        return batch_predictions
    
    async def _get_cached_route(self, train_id: int, current_section_id: int) -> List[int]:
        """Get cached route or compute if not available"""
        if train_id in self._route_cache:
            route = self._route_cache[train_id]
            # Find current position in route
            try:
                current_index = route.index(current_section_id)
                return route[current_index:]
            except ValueError:
                pass  # Current section not in cached route, recompute
        
        # Compute route (simplified - in reality would use routing algorithms)
        route = await self._compute_train_route(train_id, current_section_id)
        self._route_cache[train_id] = route
        
        return route
    
    async def _compute_train_route(self, train_id: int, current_section_id: int) -> List[int]:
        """Compute train route using graph algorithms"""
        try:
            # Get train schedule
            schedule = self.db.query(TrainSchedule).filter(
                and_(
                    TrainSchedule.train_id == train_id,
                    TrainSchedule.active == True
                )
            ).first()
            
            if schedule and schedule.route_sections:
                try:
                    current_index = schedule.route_sections.index(current_section_id)
                    return schedule.route_sections[current_index:]
                except ValueError:
                    pass
            
            # Fallback: return just current section
            return [current_section_id]
            
        except Exception as e:
            logger.error(f"Error computing route for train {train_id}: {e}")
            return [current_section_id]
    
    async def _fast_path_prediction(
        self,
        train: OptimizedTrainData,
        route: List[int],
        current_time: datetime,
        prediction_end: datetime
    ) -> List[TrainPrediction]:
        """Fast path prediction algorithm"""
        predictions = []
        simulation_time = current_time
        
        try:
            for i, section_id in enumerate(route):
                if simulation_time > prediction_end:
                    break
                
                section = self._section_cache.get(section_id)
                if not section:
                    continue
                
                # Calculate arrival and exit times
                if i == 0:  # Current section
                    arrival_time = current_time
                    remaining_distance = section.length_meters - train.distance_from_start
                    travel_time = self._calculate_travel_time(
                        remaining_distance, train.speed_kmh, section.max_speed_kmh
                    )
                else:
                    arrival_time = simulation_time
                    travel_time = self._calculate_travel_time(
                        section.length_meters, train.speed_kmh, section.max_speed_kmh
                    )
                
                exit_time = arrival_time + timedelta(minutes=travel_time)
                
                # Calculate confidence (decreases over time and distance)
                confidence = max(0.5, 0.95 - i * 0.05)
                
                prediction = TrainPrediction(
                    train_id=train.id,
                    section_id=section_id,
                    arrival_time=arrival_time,
                    exit_time=exit_time,
                    speed_kmh=min(train.speed_kmh, section.max_speed_kmh),
                    distance_to_section=(simulation_time - current_time).total_seconds() / 60 * train.speed_kmh,
                    confidence=confidence
                )
                
                predictions.append(prediction)
                simulation_time = exit_time
        
        except Exception as e:
            logger.error(f"Error in fast path prediction for train {train.id}: {e}")
        
        return predictions
    
    def _calculate_travel_time(self, distance_meters: float, current_speed: float, max_speed: int) -> float:
        """Calculate travel time in minutes for given distance and speeds"""
        if current_speed <= 0:
            effective_speed = max_speed * 0.7  # Assume 70% of max speed
        else:
            effective_speed = min(current_speed, max_speed)
        
        # Convert to minutes: (distance_m / (speed_kmh * 1000/60))
        travel_time = distance_meters / (effective_speed * 1000 / 60)
        return max(0.1, travel_time)  # Minimum 6 seconds
    
    async def optimized_conflict_detection(
        self,
        predictions: Dict[int, List[TrainPrediction]]
    ) -> List[DetectedConflict]:
        """
        Optimized conflict detection using advanced algorithms and data structures.
        """
        try:
            start_time = datetime.utcnow()
            
            # Flatten predictions into time-sorted events
            events = []
            for train_id, train_predictions in predictions.items():
                for pred in train_predictions:
                    events.append(('arrive', pred.arrival_time, pred))
                    events.append(('depart', pred.exit_time, pred))
            
            # Sort events by time
            events.sort(key=lambda x: x[1])
            
            # Use sweep line algorithm for efficient conflict detection
            conflicts = await self._sweep_line_conflict_detection(events)
            
            # Use spatial indexing for junction conflicts
            junction_conflicts = await self._spatial_junction_conflicts(predictions)
            conflicts.extend(junction_conflicts)
            
            # Priority-based conflict detection using heap
            priority_conflicts = await self._heap_based_priority_conflicts(predictions)
            conflicts.extend(priority_conflicts)
            
            detection_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Optimized conflict detection completed in {detection_time:.3f}s, found {len(conflicts)} conflicts")
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error in optimized conflict detection: {e}")
            return []
    
    async def _sweep_line_conflict_detection(self, events: List[Tuple]) -> List[DetectedConflict]:
        """Use sweep line algorithm to detect spatial conflicts efficiently"""
        conflicts = []
        active_sections = defaultdict(list)  # section_id -> list of active trains
        
        try:
            for event_type, event_time, prediction in events:
                section_id = prediction.section_id
                
                if event_type == 'arrive':
                    # Check for conflicts with trains already in section
                    section = self._section_cache.get(section_id)
                    if section and len(active_sections[section_id]) >= section.capacity:
                        # Conflict detected
                        conflicting_trains = [p.train_id for p in active_sections[section_id]]
                        conflicting_trains.append(prediction.train_id)
                        
                        time_to_impact = (event_time - datetime.utcnow()).total_seconds() / 60
                        
                        conflict = DetectedConflict(
                            conflict_type=ConflictType.SPATIAL_COLLISION,
                            severity_score=await self._quick_severity_calculation(conflicting_trains, time_to_impact),
                            trains_involved=conflicting_trains,
                            sections_involved=[section_id],
                            time_to_impact=time_to_impact,
                            description=f"Section capacity exceeded: {len(conflicting_trains)} trains in section {section_id} (capacity: {section.capacity})",
                            predicted_impact_time=event_time,
                            resolution_suggestions=["Implement traffic control", "Delay approaching trains"],
                            metadata={'capacity': section.capacity, 'trains_count': len(conflicting_trains)}
                        )
                        
                        conflicts.append(conflict)
                    
                    active_sections[section_id].append(prediction)
                
                elif event_type == 'depart':
                    # Remove train from active section
                    active_sections[section_id] = [
                        p for p in active_sections[section_id] 
                        if p.train_id != prediction.train_id
                    ]
        
        except Exception as e:
            logger.error(f"Error in sweep line conflict detection: {e}")
        
        return conflicts
    
    async def _spatial_junction_conflicts(self, predictions: Dict[int, List[TrainPrediction]]) -> List[DetectedConflict]:
        """Detect junction conflicts using spatial indexing"""
        conflicts = []
        
        try:
            # Get all junction predictions
            junction_predictions = defaultdict(list)
            
            for train_id, train_predictions in predictions.items():
                for pred in train_predictions:
                    section = self._section_cache.get(pred.section_id)
                    if section and section.is_junction:
                        junction_predictions[pred.section_id].append(pred)
            
            # Check each junction for conflicts
            for junction_id, preds in junction_predictions.items():
                if len(preds) <= 1:
                    continue
                
                section = self._section_cache.get(junction_id)
                if not section:
                    continue
                
                # Sort by arrival time
                preds.sort(key=lambda x: x.arrival_time)
                
                # Check for overlapping time windows
                for i in range(len(preds)):
                    overlapping = [preds[i]]
                    
                    for j in range(i + 1, len(preds)):
                        # Check if trains overlap in time
                        if (preds[j].arrival_time < preds[i].exit_time and
                            preds[i].arrival_time < preds[j].exit_time):
                            overlapping.append(preds[j])
                    
                    if len(overlapping) > section.capacity:
                        train_ids = [p.train_id for p in overlapping]
                        time_to_impact = (preds[i].arrival_time - datetime.utcnow()).total_seconds() / 60
                        
                        conflict = DetectedConflict(
                            conflict_type=ConflictType.JUNCTION_CONFLICT,
                            severity_score=await self._quick_severity_calculation(train_ids, time_to_impact),
                            trains_involved=train_ids,
                            sections_involved=[junction_id],
                            time_to_impact=time_to_impact,
                            description=f"Junction overload: {len(overlapping)} trains at junction {junction_id} (capacity: {section.capacity})",
                            predicted_impact_time=preds[i].arrival_time,
                            resolution_suggestions=["Sequence junction crossings", "Hold trains at approach"],
                            metadata={'junction_capacity': section.capacity, 'overflow': len(overlapping) - section.capacity}
                        )
                        
                        conflicts.append(conflict)
        
        except Exception as e:
            logger.error(f"Error in spatial junction conflict detection: {e}")
        
        return conflicts
    
    async def _heap_based_priority_conflicts(self, predictions: Dict[int, List[TrainPrediction]]) -> List[DetectedConflict]:
        """Detect priority conflicts using heap-based algorithm"""
        conflicts = []
        
        try:
            # Create priority queue of train movements
            priority_queue = []
            
            for train_id, train_predictions in predictions.items():
                train_data = self._train_cache.get(train_id)
                if not train_data:
                    continue
                
                for pred in train_predictions:
                    # Use negative priority for max heap (higher priority first)
                    heapq.heappush(priority_queue, (
                        -train_data.priority,  # Negative for max heap
                        pred.arrival_time,
                        train_id,
                        pred
                    ))
            
            # Process in priority order to detect conflicts
            section_schedules = defaultdict(list)
            
            while priority_queue:
                neg_priority, arrival_time, train_id, prediction = heapq.heappop(priority_queue)
                priority = -neg_priority
                train_data = self._train_cache.get(train_id)
                
                if not train_data:
                    continue
                
                section_id = prediction.section_id
                
                # Check if lower priority train is blocking
                for scheduled_priority, scheduled_time, scheduled_train_id, scheduled_pred in section_schedules[section_id]:
                    if (scheduled_priority < priority and  # Lower priority train
                        scheduled_pred.exit_time > arrival_time and  # Still occupying section
                        train_data.type == 'EXPRESS'):  # High priority train
                        
                        time_to_impact = (arrival_time - datetime.utcnow()).total_seconds() / 60
                        
                        conflict = DetectedConflict(
                            conflict_type=ConflictType.PRIORITY_CONFLICT,
                            severity_score=await self._quick_severity_calculation([train_id, scheduled_train_id], time_to_impact),
                            trains_involved=[scheduled_train_id, train_id],
                            sections_involved=[section_id],
                            time_to_impact=time_to_impact,
                            description=f"Priority conflict: Express train {train_id} blocked by lower priority train {scheduled_train_id}",
                            predicted_impact_time=arrival_time,
                            resolution_suggestions=["Hold lower priority train", "Create express bypass"],
                            metadata={'blocking_priority': scheduled_priority, 'blocked_priority': priority}
                        )
                        
                        conflicts.append(conflict)
                
                section_schedules[section_id].append((priority, arrival_time, train_id, prediction))
        
        except Exception as e:
            logger.error(f"Error in heap-based priority conflict detection: {e}")
        
        return conflicts
    
    async def _quick_severity_calculation(self, train_ids: List[int], time_to_impact: float) -> int:
        """Quick severity calculation for performance optimization"""
        try:
            # Simplified severity calculation
            base_severity = 5
            
            # Time factor
            if time_to_impact <= 1:
                time_bonus = 4
            elif time_to_impact <= 5:
                time_bonus = 3
            elif time_to_impact <= 15:
                time_bonus = 2
            else:
                time_bonus = 0
            
            # Train count factor
            count_bonus = min(3, len(train_ids) - 1)
            
            # Priority factor (simplified)
            priority_bonus = 0
            for train_id in train_ids:
                train_data = self._train_cache.get(train_id)
                if train_data and train_data.priority >= 8:
                    priority_bonus += 1
            
            severity = base_severity + time_bonus + count_bonus + priority_bonus
            return max(1, min(10, severity))
            
        except Exception:
            return 5  # Default medium severity
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance optimization metrics"""
        cache_total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = (self.metrics['cache_hits'] / cache_total * 100) if cache_total > 0 else 0
        
        return {
            **self.metrics,
            'cache_hit_rate_percent': cache_hit_rate,
            'train_cache_size': len(self._train_cache),
            'section_cache_size': len(self._section_cache),
            'route_cache_size': len(self._route_cache),
            'spatial_index_size': len(self._spatial_index),
            'cache_status': 'valid' if datetime.utcnow() < self._cache_expiry else 'expired'
        }
    
    async def cleanup_caches(self):
        """Cleanup and reset caches"""
        self._train_cache.clear()
        self._section_cache.clear()
        self._route_cache.clear()
        self._distance_matrix.clear()
        self._spatial_index.clear()
        self._cache_expiry = datetime.utcnow()
        logger.info("Performance optimization caches cleared")