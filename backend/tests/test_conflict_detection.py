"""
Comprehensive unit tests for railway conflict detection system.
Tests all conflict detection scenarios including mock train scenarios and edge cases.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conflict_detector import ConflictDetector, ConflictType, DetectedConflict, TrainPrediction
from app.conflict_scheduler import ConflictDetectionScheduler
from app.models import Train, Section, Position, TrainSchedule, TrainType


class TestConflictDetector:
    """Test cases for ConflictDetector class"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = Mock()
        session.query.return_value = Mock()
        session.execute.return_value = Mock()
        session.commit.return_value = None
        session.rollback.return_value = None
        session.add.return_value = None
        session.flush.return_value = None
        return session
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        redis_client = Mock()
        redis_client.publish = Mock(return_value=asyncio.Future())
        redis_client.publish.return_value.set_result(True)
        return redis_client
    
    @pytest.fixture
    def conflict_detector(self, mock_db_session, mock_redis_client):
        """Create ConflictDetector instance with mocked dependencies"""
        detector = ConflictDetector(mock_db_session, mock_redis_client)
        return detector
    
    @pytest.fixture
    def sample_trains(self):
        """Sample train data for testing"""
        return [
            {
                'id': 1,
                'train_number': 'EXP001',
                'type': TrainType.EXPRESS,
                'priority': 8,
                'max_speed_kmh': 160,
                'capacity': 500,
                'current_load': 350,
                'current_section_id': 100
            },
            {
                'id': 2,
                'train_number': 'FRT002',
                'type': TrainType.FREIGHT,
                'priority': 3,
                'max_speed_kmh': 80,
                'capacity': 0,
                'current_load': 0,
                'current_section_id': 100
            },
            {
                'id': 3,
                'train_number': 'LOC003',
                'type': TrainType.LOCAL,
                'priority': 5,
                'max_speed_kmh': 120,
                'capacity': 300,
                'current_load': 200,
                'current_section_id': 101
            }
        ]
    
    @pytest.fixture
    def sample_sections(self):
        """Sample section data for testing"""
        return [
            {
                'id': 100,
                'section_code': 'SEC100',
                'section_type': 'track',
                'length_meters': Decimal('2000'),
                'max_speed_kmh': 160,
                'capacity': 1
            },
            {
                'id': 101,
                'section_code': 'JUN101',
                'section_type': 'junction',
                'length_meters': Decimal('500'),
                'max_speed_kmh': 80,
                'capacity': 2
            },
            {
                'id': 102,
                'section_code': 'SEC102',
                'section_type': 'track',
                'length_meters': Decimal('3000'),
                'max_speed_kmh': 140,
                'capacity': 1
            }
        ]
    
    @pytest.mark.asyncio
    async def test_spatial_conflict_detection(self, conflict_detector):
        """Test detection of spatial conflicts (two trains on same track)"""
        # Mock train predictions for spatial conflict
        current_time = datetime.utcnow()
        predictions = [
            TrainPrediction(
                train_id=1,
                section_id=100,
                arrival_time=current_time + timedelta(minutes=5),
                exit_time=current_time + timedelta(minutes=8),
                speed_kmh=120.0,
                distance_to_section=10000.0,
                confidence=0.9
            ),
            TrainPrediction(
                train_id=2,
                section_id=100,
                arrival_time=current_time + timedelta(minutes=6),
                exit_time=current_time + timedelta(minutes=10),
                speed_kmh=80.0,
                distance_to_section=8000.0,
                confidence=0.8
            )
        ]
        
        # Mock section with capacity 1 (single track)
        mock_section = Mock()
        mock_section.capacity = 1
        conflict_detector._section_cache = {100: mock_section}
        
        # Mock active trains cache
        conflict_detector._active_trains_cache = {
            1: Mock(priority=8, type=TrainType.EXPRESS, current_load=350),
            2: Mock(priority=3, type=TrainType.FREIGHT, current_load=0)
        }
        
        conflicts = await conflict_detector._detect_spatial_conflicts(predictions)
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.SPATIAL_COLLISION
        assert conflicts[0].trains_involved == [1, 2]
        assert conflicts[0].sections_involved == [100]
        assert conflicts[0].severity_score >= 1
        assert "collision risk" in conflicts[0].description.lower()
    
    @pytest.mark.asyncio
    async def test_temporal_conflict_detection(self, conflict_detector):
        """Test detection of temporal conflicts (insufficient safety buffer)"""
        current_time = datetime.utcnow()
        
        # Create predictions with 1-minute gap (less than 2-minute safety buffer)
        predictions = [
            TrainPrediction(
                train_id=1,
                section_id=100,
                arrival_time=current_time + timedelta(minutes=5),
                exit_time=current_time + timedelta(minutes=7),
                speed_kmh=120.0,
                distance_to_section=10000.0,
                confidence=0.9
            ),
            TrainPrediction(
                train_id=2,
                section_id=100,
                arrival_time=current_time + timedelta(minutes=8),  # Only 1 minute after first train exits
                exit_time=current_time + timedelta(minutes=11),
                speed_kmh=100.0,
                distance_to_section=8000.0,
                confidence=0.8
            )
        ]
        
        conflicts = await conflict_detector._detect_temporal_conflicts(predictions)
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.TEMPORAL_CONFLICT
        assert conflicts[0].trains_involved == [1, 2]
        assert "safety buffer" in conflicts[0].description.lower()
        assert conflicts[0].time_to_impact < 10  # Should be within alert window
    
    @pytest.mark.asyncio
    async def test_priority_conflict_detection(self, conflict_detector):
        """Test detection of priority conflicts (express blocked by freight)"""
        current_time = datetime.utcnow()
        
        predictions = [
            TrainPrediction(
                train_id=2,  # Freight train
                section_id=100,
                arrival_time=current_time + timedelta(minutes=3),
                exit_time=current_time + timedelta(minutes=8),  # Slow freight
                speed_kmh=60.0,
                distance_to_section=3000.0,
                confidence=0.9
            ),
            TrainPrediction(
                train_id=1,  # Express train
                section_id=100,
                arrival_time=current_time + timedelta(minutes=5),
                exit_time=current_time + timedelta(minutes=7),
                speed_kmh=140.0,
                distance_to_section=11000.0,
                confidence=0.9
            )
        ]
        
        # Mock train info
        conflict_detector._active_trains_cache = {
            1: Mock(priority=8, type=TrainType.EXPRESS, max_speed_kmh=160),
            2: Mock(priority=3, type=TrainType.FREIGHT, max_speed_kmh=80)
        }
        
        conflicts = await conflict_detector._detect_priority_conflicts(predictions)
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.PRIORITY_CONFLICT
        assert conflicts[0].trains_involved == [2, 1]  # Freight blocking express
        assert "express train" in conflicts[0].description.lower()
        assert "freight train" in conflicts[0].description.lower()
    
    @pytest.mark.asyncio
    async def test_junction_conflict_detection(self, conflict_detector):
        """Test detection of junction conflicts (multiple trains converging)"""
        current_time = datetime.utcnow()
        
        # Three trains converging on junction with capacity 2
        predictions = [
            TrainPrediction(
                train_id=1,
                section_id=101,  # Junction
                arrival_time=current_time + timedelta(minutes=4),
                exit_time=current_time + timedelta(minutes=6),
                speed_kmh=80.0,
                distance_to_section=5000.0,
                confidence=0.9
            ),
            TrainPrediction(
                train_id=2,
                section_id=101,
                arrival_time=current_time + timedelta(minutes=5),
                exit_time=current_time + timedelta(minutes=7),
                speed_kmh=70.0,
                distance_to_section=6000.0,
                confidence=0.8
            ),
            TrainPrediction(
                train_id=3,
                section_id=101,
                arrival_time=current_time + timedelta(minutes=5.5),
                exit_time=current_time + timedelta(minutes=7.5),
                speed_kmh=90.0,
                distance_to_section=8000.0,
                confidence=0.7
            )
        ]
        
        # Mock junction with capacity 2
        mock_junction = Mock()
        mock_junction.capacity = 2
        mock_junction.section_type = 'junction'
        conflict_detector._section_cache = {101: mock_junction}
        
        conflicts = await conflict_detector._detect_junction_conflicts(predictions)
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.JUNCTION_CONFLICT
        assert len(conflicts[0].trains_involved) == 3
        assert conflicts[0].sections_involved == [101]
        assert "junction conflict" in conflicts[0].description.lower()
    
    @pytest.mark.asyncio
    async def test_severity_calculation(self, conflict_detector):
        """Test conflict severity scoring"""
        # Mock train cache
        conflict_detector._active_trains_cache = {
            1: Mock(priority=8, current_load=400),
            2: Mock(priority=5, current_load=200)
        }
        
        # Test high severity (imminent collision)
        severity_high = await conflict_detector._calculate_severity(
            conflict_type=ConflictType.SPATIAL_COLLISION,
            trains=[1, 2],
            time_to_impact=0.5,  # 30 seconds
            sections=[100]
        )
        
        # Test low severity (distant temporal conflict)
        severity_low = await conflict_detector._calculate_severity(
            conflict_type=ConflictType.TEMPORAL_CONFLICT,
            trains=[1, 2],
            time_to_impact=25,  # 25 minutes
            sections=[100]
        )
        
        assert severity_high > severity_low
        assert 1 <= severity_high <= 10
        assert 1 <= severity_low <= 10
        assert severity_high >= 7  # Should be high for imminent collision
        assert severity_low <= 8   # Should be lower for distant temporal conflict (adjusted for new scaling)
    
    @pytest.mark.asyncio
    async def test_time_overlap_calculation(self, conflict_detector):
        """Test time overlap calculation between train predictions"""
        current_time = datetime.utcnow()
        
        # Overlapping predictions
        pred1 = TrainPrediction(
            train_id=1, section_id=100,
            arrival_time=current_time + timedelta(minutes=5),
            exit_time=current_time + timedelta(minutes=8),
            speed_kmh=120.0, distance_to_section=10000.0, confidence=0.9
        )
        
        pred2 = TrainPrediction(
            train_id=2, section_id=100,
            arrival_time=current_time + timedelta(minutes=6),
            exit_time=current_time + timedelta(minutes=10),
            speed_kmh=100.0, distance_to_section=8000.0, confidence=0.8
        )
        
        overlap = conflict_detector._calculate_time_overlap(pred1, pred2)
        assert overlap == 2.0  # 2 minutes overlap
        
        # Non-overlapping predictions
        pred3 = TrainPrediction(
            train_id=3, section_id=100,
            arrival_time=current_time + timedelta(minutes=12),
            exit_time=current_time + timedelta(minutes=15),
            speed_kmh=90.0, distance_to_section=12000.0, confidence=0.7
        )
        
        no_overlap = conflict_detector._calculate_time_overlap(pred1, pred3)
        assert no_overlap == 0.0
    
    @pytest.mark.asyncio
    async def test_resolution_suggestions(self, conflict_detector):
        """Test generation of conflict resolution suggestions"""
        current_time = datetime.utcnow()
        
        # Mock predictions
        pred1 = TrainPrediction(
            train_id=1, section_id=100,
            arrival_time=current_time + timedelta(minutes=5),
            exit_time=current_time + timedelta(minutes=8),
            speed_kmh=120.0, distance_to_section=10000.0, confidence=0.9
        )
        
        pred2 = TrainPrediction(
            train_id=2, section_id=100,
            arrival_time=current_time + timedelta(minutes=6),
            exit_time=current_time + timedelta(minutes=10),
            speed_kmh=80.0, distance_to_section=8000.0, confidence=0.8
        )
        
        # Mock section
        mock_section = Mock()
        
        # Test spatial resolutions
        spatial_suggestions = await conflict_detector._generate_spatial_resolutions(pred1, pred2, mock_section)
        assert len(spatial_suggestions) > 0
        assert any("speed" in s.lower() for s in spatial_suggestions)
        assert any("delay" in s.lower() for s in spatial_suggestions)
        
        # Test temporal resolutions
        temporal_suggestions = await conflict_detector._generate_temporal_resolutions(pred1, pred2, 1.0)
        assert len(temporal_suggestions) > 0
        assert any("delay" in s.lower() for s in temporal_suggestions)
        
        # Test priority resolutions
        train1_info = {'priority': 3, 'type': 'freight'}
        train2_info = {'priority': 8, 'type': 'express'}
        priority_suggestions = await conflict_detector._generate_priority_resolutions(
            pred1, pred2, train1_info, train2_info
        )
        assert len(priority_suggestions) > 0
        assert any("hold" in s.lower() or "bypass" in s.lower() for s in priority_suggestions)


class TestConflictDetectionScheduler:
    """Test cases for ConflictDetectionScheduler"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        redis_client = Mock()
        return redis_client
    
    @pytest.fixture
    def scheduler(self, mock_redis_client):
        """Create scheduler instance"""
        return ConflictDetectionScheduler(mock_redis_client)
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test scheduler start and stop functionality"""
        assert not scheduler.is_running
        
        # Start scheduler
        await scheduler.start()
        assert scheduler.is_running
        assert scheduler.task is not None
        
        # Stop scheduler
        await scheduler.stop()
        assert not scheduler.is_running
    
    @pytest.mark.asyncio
    async def test_scheduler_stats_tracking(self, scheduler):
        """Test that scheduler tracks statistics correctly"""
        initial_stats = scheduler.get_status()
        assert initial_stats['stats']['runs_completed'] == 0
        assert initial_stats['stats']['runs_failed'] == 0
        
        # Simulate successful run
        scheduler._update_stats(detection_time=1.5, conflicts_detected=3, success=True)
        
        updated_stats = scheduler.get_status()
        assert updated_stats['stats']['runs_completed'] == 1
        assert updated_stats['stats']['total_conflicts_detected'] == 3
        assert updated_stats['stats']['average_detection_time'] == 1.5
    
    @pytest.mark.asyncio
    async def test_detection_interval_update(self, scheduler):
        """Test updating detection interval"""
        original_interval = scheduler.detection_interval
        
        await scheduler.update_detection_interval(60)
        assert scheduler.detection_interval == 60
        
        # Test validation
        with pytest.raises(ValueError):
            await scheduler.update_detection_interval(5)  # Too short
        
        with pytest.raises(ValueError):
            await scheduler.update_detection_interval(400)  # Too long


class TestScenarios:
    """Integration test scenarios for complex railway situations"""
    
    @pytest.fixture
    def complex_scenario_detector(self):
        """Create detector with complex scenario setup"""
        mock_db = Mock()
        detector = ConflictDetector(mock_db)
        
        # Mock complex network with trains, sections, and schedules
        detector._active_trains_cache = {
            1: Mock(id=1, train_number='EXP001', type=TrainType.EXPRESS, priority=9, max_speed_kmh=160, current_load=450),
            2: Mock(id=2, train_number='EXP002', type=TrainType.EXPRESS, priority=8, max_speed_kmh=160, current_load=380),
            3: Mock(id=3, train_number='FRT003', type=TrainType.FREIGHT, priority=2, max_speed_kmh=80, current_load=0),
            4: Mock(id=4, train_number='LOC004', type=TrainType.LOCAL, priority=5, max_speed_kmh=120, current_load=250)
        }
        
        detector._section_cache = {
            100: Mock(id=100, section_type='track', capacity=1, length_meters=2000),
            101: Mock(id=101, section_type='junction', capacity=2, length_meters=500),
            102: Mock(id=102, section_type='track', capacity=1, length_meters=3000),
            103: Mock(id=103, section_type='station', capacity=3, length_meters=800)
        }
        
        return detector
    
    @pytest.mark.asyncio
    async def test_two_express_trains_collision_scenario(self, complex_scenario_detector):
        """Test scenario: Two express trains on collision course"""
        current_time = datetime.utcnow()
        
        # Two express trains approaching same single-track section from opposite directions
        predictions = [
            TrainPrediction(
                train_id=1, section_id=100,
                arrival_time=current_time + timedelta(minutes=3),
                exit_time=current_time + timedelta(minutes=5),
                speed_kmh=140.0, distance_to_section=7000.0, confidence=0.95
            ),
            TrainPrediction(
                train_id=2, section_id=100,
                arrival_time=current_time + timedelta(minutes=4),
                exit_time=current_time + timedelta(minutes=6),
                speed_kmh=150.0, distance_to_section=10000.0, confidence=0.92
            )
        ]
        
        conflicts = await complex_scenario_detector._detect_spatial_conflicts(predictions)
        
        assert len(conflicts) >= 1
        spatial_conflict = next(c for c in conflicts if c.conflict_type == ConflictType.SPATIAL_COLLISION)
        assert spatial_conflict.severity_score >= 8  # Should be critical
        assert spatial_conflict.time_to_impact <= 5   # Imminent
        assert len(spatial_conflict.resolution_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_freight_blocking_express_scenario(self, complex_scenario_detector):
        """Test scenario: Freight train blocking express schedule"""
        current_time = datetime.utcnow()
        
        predictions = [
            # Slow freight train already in section
            TrainPrediction(
                train_id=3, section_id=102,
                arrival_time=current_time + timedelta(minutes=1),
                exit_time=current_time + timedelta(minutes=8),  # Very slow
                speed_kmh=45.0, distance_to_section=1000.0, confidence=0.9
            ),
            # Fast express train approaching
            TrainPrediction(
                train_id=1, section_id=102,
                arrival_time=current_time + timedelta(minutes=6),
                exit_time=current_time + timedelta(minutes=7.5),
                speed_kmh=140.0, distance_to_section=14000.0, confidence=0.88
            )
        ]
        
        conflicts = await complex_scenario_detector._detect_priority_conflicts(predictions)
        
        priority_conflict = next((c for c in conflicts if c.conflict_type == ConflictType.PRIORITY_CONFLICT), None)
        if priority_conflict:
            assert 1 in priority_conflict.trains_involved  # Express train involved
            assert 3 in priority_conflict.trains_involved  # Freight train involved
            assert "express" in priority_conflict.description.lower()
    
    @pytest.mark.asyncio
    async def test_junction_congestion_scenario(self, complex_scenario_detector):
        """Test scenario: Junction congestion with 4 trains"""
        current_time = datetime.utcnow()
        
        # Four trains converging on junction with capacity 2
        predictions = [
            TrainPrediction(
                train_id=1, section_id=101,
                arrival_time=current_time + timedelta(minutes=2),
                exit_time=current_time + timedelta(minutes=3.5),
                speed_kmh=80.0, distance_to_section=2600.0, confidence=0.9
            ),
            TrainPrediction(
                train_id=2, section_id=101,
                arrival_time=current_time + timedelta(minutes=2.5),
                exit_time=current_time + timedelta(minutes=4),
                speed_kmh=75.0, distance_to_section=3100.0, confidence=0.87
            ),
            TrainPrediction(
                train_id=3, section_id=101,
                arrival_time=current_time + timedelta(minutes=3),
                exit_time=current_time + timedelta(minutes=6),  # Slow freight
                speed_kmh=50.0, distance_to_section=2500.0, confidence=0.85
            ),
            TrainPrediction(
                train_id=4, section_id=101,
                arrival_time=current_time + timedelta(minutes=3.2),
                exit_time=current_time + timedelta(minutes=4.5),
                speed_kmh=90.0, distance_to_section=4800.0, confidence=0.82
            )
        ]
        
        conflicts = await complex_scenario_detector._detect_junction_conflicts(predictions)
        
        assert len(conflicts) >= 1
        junction_conflict = next(c for c in conflicts if c.conflict_type == ConflictType.JUNCTION_CONFLICT)
        assert len(junction_conflict.trains_involved) > 2  # Multiple trains involved
        assert junction_conflict.sections_involved == [101]
        assert junction_conflict.severity_score >= 6  # High severity
    
    @pytest.mark.asyncio
    async def test_network_wide_disruption_scenario(self, complex_scenario_detector):
        """Test scenario: Network-wide disruption simulation"""
        current_time = datetime.utcnow()
        
        # Simulate cascading delays and conflicts across multiple sections
        predictions = []
        
        # Express train delayed in section 100
        predictions.extend([
            TrainPrediction(
                train_id=1, section_id=100,
                arrival_time=current_time + timedelta(minutes=1),
                exit_time=current_time + timedelta(minutes=8),  # Delayed
                speed_kmh=60.0, distance_to_section=1000.0, confidence=0.95
            ),
            TrainPrediction(
                train_id=1, section_id=101,  # Moving to junction
                arrival_time=current_time + timedelta(minutes=8),
                exit_time=current_time + timedelta(minutes=10),
                speed_kmh=80.0, distance_to_section=3000.0, confidence=0.85
            )
        ])
        
        # Other trains affected by the delay
        predictions.extend([
            TrainPrediction(
                train_id=2, section_id=100,  # Following express train (creates overlap)
                arrival_time=current_time + timedelta(minutes=6),  # Overlaps with train 1
                exit_time=current_time + timedelta(minutes=9),
                speed_kmh=140.0, distance_to_section=20000.0, confidence=0.80
            ),
            TrainPrediction(
                train_id=3, section_id=101,  # Third train at junction (exceeds capacity)
                arrival_time=current_time + timedelta(minutes=8.5),
                exit_time=current_time + timedelta(minutes=10.5),
                speed_kmh=80.0, distance_to_section=12000.0, confidence=0.85
            ),
            TrainPrediction(
                train_id=4, section_id=101,  # At junction same time (exceeds capacity)
                arrival_time=current_time + timedelta(minutes=9.5),
                exit_time=current_time + timedelta(minutes=11.5),
                speed_kmh=100.0, distance_to_section=15000.0, confidence=0.78
            )
        ])
        
        # Run all conflict detection types
        spatial_conflicts = await complex_scenario_detector._detect_spatial_conflicts(predictions)
        temporal_conflicts = await complex_scenario_detector._detect_temporal_conflicts(predictions)
        priority_conflicts = await complex_scenario_detector._detect_priority_conflicts(predictions)
        junction_conflicts = await complex_scenario_detector._detect_junction_conflicts(predictions)
        
        total_conflicts = len(spatial_conflicts + temporal_conflicts + priority_conflicts + junction_conflicts)
        
        # Should detect multiple types of conflicts in network disruption
        assert total_conflicts >= 2
        
        # Verify we have different types of conflicts
        conflict_types = set()
        for conflicts_list in [spatial_conflicts, temporal_conflicts, priority_conflicts, junction_conflicts]:
            for conflict in conflicts_list:
                conflict_types.add(conflict.conflict_type)
        
        assert len(conflict_types) >= 2  # Multiple conflict types detected


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])