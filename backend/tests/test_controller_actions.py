"""
Unit Tests for Controller Action APIs
Comprehensive test suite with mock scenarios
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    Controller, Conflict, Decision, Train, Section,
    ConflictSeverity, DecisionAction, ControllerAuthLevel, TrainType
)
from app.schemas import (
    ConflictResolveRequest, ConflictResolutionAction,
    TrainControlRequest, TrainControlCommand,
    DecisionLogRequest, AuditQueryFilters
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.query = Mock()
    session.refresh = Mock()
    return session


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.increment_counter = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def mock_controller():
    """Mock controller (supervisor level)"""
    controller = Controller(
        id=1,
        name="Test Controller",
        employee_id="CTR001",
        auth_level=ControllerAuthLevel.SUPERVISOR,
        section_responsibility=[1, 2, 3],
        active=True,
        created_at=datetime.utcnow()
    )
    return controller


@pytest.fixture
def mock_conflict():
    """Mock conflict"""
    conflict = Conflict(
        id=1,
        conflict_type="collision_risk",
        severity=ConflictSeverity.HIGH,
        trains_involved=[1, 2],
        sections_involved=[1, 2],
        detection_time=datetime.utcnow(),
        description="Potential collision detected",
        ai_analyzed=True,
        ai_confidence=0.85,
        ai_solution_id="solution_123",
        ai_recommendations={
            "train_actions": [
                {
                    "train_id": 1,
                    "action": "delay",
                    "parameters": {"delay_minutes": 5}
                }
            ]
        }
    )
    return conflict


@pytest.fixture
def mock_train():
    """Mock train"""
    train = Train(
        id=1,
        train_number="EXP001",
        type=TrainType.EXPRESS,
        current_section_id=1,
        speed_kmh=80.0,
        max_speed_kmh=120,
        capacity=500,
        current_load=350,
        priority=7,
        length_meters=250.0,
        weight_tons=500.0,
        operational_status="active",
        created_at=datetime.utcnow()
    )
    return train


@pytest.fixture
def mock_section():
    """Mock section"""
    section = Section(
        id=1,
        name="Main Line A",
        section_code="MLA001",
        section_type="track",
        length_meters=5000.0,
        max_speed_kmh=120,
        capacity=2,
        active=True,
        created_at=datetime.utcnow()
    )
    return section


# ============================================================================
# CONFLICT RESOLUTION TESTS
# ============================================================================

class TestConflictResolution:
    """Test conflict resolution endpoint"""
    
    @pytest.mark.asyncio
    async def test_resolve_conflict_accept(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller,
        mock_conflict
    ):
        """Test accepting AI recommendation"""
        from app.routes.controller import resolve_conflict
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=mock_conflict)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Create request
        request = ConflictResolveRequest(
            action=ConflictResolutionAction.ACCEPT,
            solution_id="solution_123",
            rationale="AI recommendation is optimal for this scenario"
        )
        
        # Mock background tasks
        background_tasks = Mock()
        background_tasks.add_task = Mock()
        
        # Execute
        response = await resolve_conflict(
            conflict_id=1,
            request=request,
            background_tasks=background_tasks,
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        # Assertions
        assert response.success is True
        assert response.conflict_id == 1
        assert response.action == ConflictResolutionAction.ACCEPT
        assert response.applied_solution is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()
        background_tasks.add_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_conflict_modify(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller,
        mock_conflict
    ):
        """Test modifying AI recommendation"""
        from app.routes.controller import resolve_conflict
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=mock_conflict)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Create request with modifications
        modifications = {
            "train_actions": [
                {
                    "train_id": 1,
                    "action": "delay",
                    "parameters": {"delay_minutes": 10}  # Modified from 5 to 10
                }
            ]
        }
        
        request = ConflictResolveRequest(
            action=ConflictResolutionAction.MODIFY,
            solution_id="solution_123",
            modifications=modifications,
            rationale="Extended delay for better safety margin"
        )
        
        # Mock background tasks
        background_tasks = Mock()
        background_tasks.add_task = Mock()
        
        # Execute
        response = await resolve_conflict(
            conflict_id=1,
            request=request,
            background_tasks=background_tasks,
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        # Assertions
        assert response.success is True
        assert response.action == ConflictResolutionAction.MODIFY
        assert response.applied_solution == modifications
        background_tasks.add_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_conflict_reject(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller,
        mock_conflict
    ):
        """Test rejecting AI recommendation"""
        from app.routes.controller import resolve_conflict
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=mock_conflict)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Create request
        request = ConflictResolveRequest(
            action=ConflictResolutionAction.REJECT,
            solution_id="solution_123",
            rationale="AI recommendation not suitable due to local track conditions"
        )
        
        # Mock background tasks
        background_tasks = Mock()
        background_tasks.add_task = Mock()
        
        # Execute
        response = await resolve_conflict(
            conflict_id=1,
            request=request,
            background_tasks=background_tasks,
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        # Assertions
        assert response.success is True
        assert response.action == ConflictResolutionAction.REJECT
        assert response.applied_solution is None
    
    @pytest.mark.asyncio
    async def test_resolve_conflict_not_found(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller
    ):
        """Test resolving non-existent conflict"""
        from app.routes.controller import resolve_conflict
        
        # Setup mock query to return None
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Create request
        request = ConflictResolveRequest(
            action=ConflictResolutionAction.ACCEPT,
            solution_id="solution_123",
            rationale="Test rationale"
        )
        
        # Mock background tasks
        background_tasks = Mock()
        
        # Execute and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await resolve_conflict(
                conflict_id=999,
                request=request,
                background_tasks=background_tasks,
                controller=mock_controller,
                db=mock_db_session,
                redis_client=mock_redis_client
            )
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_resolve_already_resolved_conflict(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller,
        mock_conflict
    ):
        """Test resolving already resolved conflict"""
        from app.routes.controller import resolve_conflict
        
        # Mark conflict as already resolved
        mock_conflict.resolution_time = datetime.utcnow()
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=mock_conflict)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Create request
        request = ConflictResolveRequest(
            action=ConflictResolutionAction.ACCEPT,
            solution_id="solution_123",
            rationale="Test rationale"
        )
        
        # Mock background tasks
        background_tasks = Mock()
        
        # Execute and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await resolve_conflict(
                conflict_id=1,
                request=request,
                background_tasks=background_tasks,
                controller=mock_controller,
                db=mock_db_session,
                redis_client=mock_redis_client
            )
        
        assert exc_info.value.status_code == 400
        assert "already resolved" in str(exc_info.value.detail).lower()


# ============================================================================
# TRAIN CONTROL TESTS
# ============================================================================

class TestTrainControl:
    """Test train control endpoint"""
    
    @pytest.mark.asyncio
    async def test_control_train_delay(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller,
        mock_train
    ):
        """Test delaying a train"""
        from app.routes.controller import control_train
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=mock_train)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Create request
        request = TrainControlRequest(
            command=TrainControlCommand.DELAY,
            parameters={"delay_minutes": 15},
            reason="Track maintenance ahead requires schedule adjustment",
            emergency=False
        )
        
        # Mock background tasks
        background_tasks = Mock()
        background_tasks.add_task = Mock()
        
        # Execute
        response = await control_train(
            train_id=1,
            request=request,
            background_tasks=background_tasks,
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        # Assertions
        assert response.success is True
        assert response.train_id == 1
        assert response.command == TrainControlCommand.DELAY
        assert response.notification_sent is True
        background_tasks.add_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_control_train_emergency_stop(
        self,
        mock_db_session,
        mock_redis_client,
        mock_train
    ):
        """Test emergency stop command"""
        from app.routes.controller import control_train
        
        # Create manager-level controller for emergency commands
        manager_controller = Controller(
            id=2,
            name="Manager",
            employee_id="MGR001",
            auth_level=ControllerAuthLevel.MANAGER,
            active=True
        )
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=mock_train)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Create request
        request = TrainControlRequest(
            command=TrainControlCommand.STOP,
            parameters={},
            reason="Track obstruction detected - immediate stop required",
            emergency=True
        )
        
        # Mock background tasks
        background_tasks = Mock()
        background_tasks.add_task = Mock()
        
        # Execute
        response = await control_train(
            train_id=1,
            request=request,
            background_tasks=background_tasks,
            controller=manager_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        # Assertions
        assert response.success is True
        assert response.command == TrainControlCommand.STOP
        assert response.notification_sent is True
        assert "emergency" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_control_train_reroute(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller,
        mock_train
    ):
        """Test rerouting a train"""
        from app.routes.controller import control_train
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=mock_train)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Create request
        request = TrainControlRequest(
            command=TrainControlCommand.REROUTE,
            parameters={"new_route": [2, 3, 4, 5]},
            reason="Original route unavailable due to maintenance",
            emergency=False
        )
        
        # Mock background tasks
        background_tasks = Mock()
        background_tasks.add_task = Mock()
        
        # Execute
        response = await control_train(
            train_id=1,
            request=request,
            background_tasks=background_tasks,
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        # Assertions
        assert response.success is True
        assert response.command == TrainControlCommand.REROUTE
    
    @pytest.mark.asyncio
    async def test_control_train_invalid_parameters(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller,
        mock_train
    ):
        """Test train control with invalid parameters"""
        from pydantic import ValidationError
        
        # Test delay with missing delay_minutes
        with pytest.raises(ValidationError):
            TrainControlRequest(
                command=TrainControlCommand.DELAY,
                parameters={},  # Missing delay_minutes
                reason="Test reason",
                emergency=False
            )
        
        # Test delay with invalid delay_minutes
        with pytest.raises(ValidationError):
            TrainControlRequest(
                command=TrainControlCommand.DELAY,
                parameters={"delay_minutes": -5},  # Negative value
                reason="Test reason",
                emergency=False
            )


# ============================================================================
# ACTIVE CONFLICTS TESTS
# ============================================================================

class TestActiveConflicts:
    """Test active conflicts endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_active_conflicts(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller
    ):
        """Test retrieving active conflicts"""
        from app.routes.controller import get_active_conflicts
        
        # Create mock conflicts
        conflicts = [
            Conflict(
                id=1,
                conflict_type="collision_risk",
                severity=ConflictSeverity.CRITICAL,
                trains_involved=[1, 2],
                sections_involved=[1],
                detection_time=datetime.utcnow(),
                estimated_impact_minutes=5,
                description="Critical collision risk",
                ai_confidence=0.95
            ),
            Conflict(
                id=2,
                conflict_type="section_overload",
                severity=ConflictSeverity.MEDIUM,
                trains_involved=[3, 4],
                sections_involved=[2],
                detection_time=datetime.utcnow(),
                estimated_impact_minutes=15,
                description="Section capacity exceeded"
            )
        ]
        
        # Setup mock query
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=conflicts)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Execute
        response = await get_active_conflicts(
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        # Assertions
        assert response.total_conflicts == 2
        assert response.critical_conflicts == 1
        assert len(response.conflicts) == 2
        # Critical conflict should be first (higher priority)
        assert response.conflicts[0].severity == ConflictSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_get_active_conflicts_cached(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller
    ):
        """Test retrieving cached active conflicts"""
        from app.routes.controller import get_active_conflicts
        
        # Setup cached data
        cached_response = {
            "total_conflicts": 1,
            "critical_conflicts": 1,
            "high_priority_conflicts": 1,
            "conflicts": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        mock_redis_client.get = AsyncMock(return_value=cached_response)
        
        # Execute
        response = await get_active_conflicts(
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        # Assertions
        assert response.total_conflicts == 1
        # Database query should not be called due to cache hit
        mock_db_session.query.assert_not_called()


# ============================================================================
# DECISION LOGGING TESTS
# ============================================================================

class TestDecisionLogging:
    """Test decision logging endpoint"""
    
    @pytest.mark.asyncio
    async def test_log_controller_decision(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller,
        mock_conflict,
        mock_train
    ):
        """Test logging a controller decision"""
        from app.routes.controller import log_controller_decision
        
        # Setup mock queries
        def mock_query_side_effect(model):
            mock_query = Mock()
            mock_query.filter = Mock(return_value=mock_query)
            
            if model == Conflict:
                mock_query.first = Mock(return_value=mock_conflict)
            elif model == Train:
                mock_query.first = Mock(return_value=mock_train)
            else:
                mock_query.first = Mock(return_value=None)
            
            return mock_query
        
        mock_db_session.query = Mock(side_effect=mock_query_side_effect)
        
        # Create request
        request = DecisionLogRequest(
            conflict_id=1,
            train_id=1,
            action_taken="delay",
            rationale="Delayed train to prevent section overload",
            parameters={"delay_minutes": 10},
            outcome="Successfully prevented conflict"
        )
        
        # Execute
        response = await log_controller_decision(
            request=request,
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        # Assertions
        assert response.success is True
        assert response.controller_id == mock_controller.id
        assert response.logged is True
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()


# ============================================================================
# AUDIT TRAIL TESTS
# ============================================================================

class TestAuditTrail:
    """Test audit trail endpoint"""
    
    @pytest.mark.asyncio
    async def test_query_audit_trail(
        self,
        mock_db_session,
        mock_controller
    ):
        """Test querying audit trail"""
        from app.routes.controller import query_audit_trail
        
        # Create mock decisions
        decisions = [
            Decision(
                id=1,
                controller_id=1,
                conflict_id=1,
                action_taken=DecisionAction.DELAY,
                timestamp=datetime.utcnow(),
                rationale="Test rationale",
                executed=True,
                execution_time=datetime.utcnow(),
                ai_generated=False
            )
        ]
        
        # Mock controller for decision
        decisions[0].controller = mock_controller
        
        # Setup mock query
        mock_query = Mock()
        mock_query.join = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.count = Mock(return_value=1)
        mock_query.all = Mock(return_value=decisions)
        
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Create filters
        filters = AuditQueryFilters(
            controller_id=1,
            limit=100,
            offset=0
        )
        
        # Execute
        response = await query_audit_trail(
            filters=filters,
            controller=mock_controller,
            db=mock_db_session
        )
        
        # Assertions
        assert response.total_records == 1
        assert response.returned_records == 1
        assert len(response.decisions) == 1
        assert response.performance_metrics is not None


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(
        self,
        mock_redis_client,
        mock_controller
    ):
        """Test rate limit exceeded scenario"""
        from app.routes.controller import RateLimiter
        from fastapi import Request
        
        # Setup rate limiter
        rate_limiter = RateLimiter(requests_per_minute=10)
        
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/conflicts/1/resolve"
        mock_request.state = Mock()
        
        # Mock Redis to return count exceeding limit
        mock_redis_client.increment_counter = AsyncMock(return_value=11)
        
        # Execute and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await rate_limiter(
                request=mock_request,
                controller=mock_controller,
                redis_client=mock_redis_client
            )
        
        assert exc_info.value.status_code == 429
        assert "rate limit" in str(exc_info.value.detail).lower()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_conflict_resolution_workflow(
        self,
        mock_db_session,
        mock_redis_client,
        mock_controller,
        mock_conflict,
        mock_train
    ):
        """Test complete workflow from conflict detection to resolution"""
        from app.routes.controller import resolve_conflict, get_active_conflicts
        
        # Step 1: Get active conflicts
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[mock_conflict])
        mock_query.first = Mock(return_value=mock_conflict)
        mock_db_session.query = Mock(return_value=mock_query)
        
        conflicts_response = await get_active_conflicts(
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        assert conflicts_response.total_conflicts == 1
        
        # Step 2: Resolve the conflict
        request = ConflictResolveRequest(
            action=ConflictResolutionAction.ACCEPT,
            solution_id="solution_123",
            rationale="AI recommendation accepted"
        )
        
        background_tasks = Mock()
        background_tasks.add_task = Mock()
        
        resolution_response = await resolve_conflict(
            conflict_id=1,
            request=request,
            background_tasks=background_tasks,
            controller=mock_controller,
            db=mock_db_session,
            redis_client=mock_redis_client
        )
        
        assert resolution_response.success is True
        assert resolution_response.conflict_id == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
