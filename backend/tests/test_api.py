"""
Unit tests for Railway Traffic Management API
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import get_session
from app.models import Base, Controller, Train, Section, Position
from app.auth import create_access_token
from app.redis_client import RedisClient

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database
Base.metadata.create_all(bind=engine)


def override_get_session():
    """Override database session for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Mock Redis client for testing
class MockRedisClient:
    def __init__(self):
        self.data = {}
        self.counters = {}
    
    async def connect(self):
        pass
    
    async def disconnect(self):
        pass
    
    async def is_connected(self):
        return True
    
    async def get(self, key):
        return self.data.get(key)
    
    async def set(self, key, value, ttl=3600):
        self.data[key] = value
        return True
    
    async def delete(self, key):
        self.data.pop(key, None)
        return True
    
    async def check_rate_limit(self, key, limit, window=60):
        return {
            "allowed": True,
            "remaining": limit - 1,
            "reset_time": datetime.utcnow() + timedelta(seconds=window),
            "current_count": 1
        }
    
    async def increment_counter(self, key, ttl=3600):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]
    
    async def get_counter(self, key):
        return self.counters.get(key, 0)
    
    async def cache_train_position(self, train_id, position_data):
        return await self.set(f"train:position:{train_id}", position_data)
    
    async def get_train_position(self, train_id):
        return await self.get(f"train:position:{train_id}")
    
    async def get_active_trains(self):
        return [1, 2, 3]
    
    async def publish(self, channel, message):
        return True


# Override dependencies
app.dependency_overrides[get_session] = override_get_session

# Test client
client = TestClient(app)


@pytest.fixture
def test_db():
    """Create test database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_controller(test_db):
    """Create test controller"""
    controller = Controller(
        name="Test Controller",
        employee_id="TEST001",
        auth_level="supervisor",
        section_responsibility=[1, 2, 3],
        active=True
    )
    test_db.add(controller)
    test_db.commit()
    test_db.refresh(controller)
    return controller


@pytest.fixture
def test_section(test_db):
    """Create test section"""
    section = Section(
        name="Test Section",
        section_code="TEST-1",
        section_type="track",
        length_meters=1000.0,
        max_speed_kmh=100,
        capacity=1,
        electrified=True,
        active=True
    )
    test_db.add(section)
    test_db.commit()
    test_db.refresh(section)
    return section


@pytest.fixture
def test_train(test_db, test_section):
    """Create test train"""
    train = Train(
        train_number="TEST001",
        type="express",
        current_section_id=test_section.id,
        max_speed_kmh=160,
        capacity=400,
        priority=1,
        length_meters=200.0,
        weight_tons=180.0,
        operational_status="active"
    )
    test_db.add(train)
    test_db.commit()
    test_db.refresh(train)
    return train


@pytest.fixture
def auth_token(test_controller):
    """Create authentication token"""
    return create_access_token(
        data={
            "sub": test_controller.employee_id,
            "controller_id": test_controller.id,
            "auth_level": test_controller.auth_level.value
        }
    )


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "1.0.0"
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data


class TestAuthenticationEndpoints:
    """Test authentication endpoints"""
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post("/api/auth/login", json={
            "employee_id": "INVALID",
            "password": "wrong_password"
        })
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid employee ID or password"
    
    def test_login_valid_credentials(self, test_controller):
        """Test login with valid credentials"""
        response = client.post("/api/auth/login", json={
            "employee_id": test_controller.employee_id,
            "password": f"password_{test_controller.employee_id}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "controller" in data
    
    def test_get_current_controller(self, auth_headers):
        """Test get current controller info"""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "employee_id" in data
    
    def test_validate_token(self, auth_headers):
        """Test token validation"""
        response = client.get("/api/auth/validate-token", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "controller" in data["data"]
    
    def test_unauthorized_access(self):
        """Test unauthorized access"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestPositionEndpoints:
    """Test position tracking endpoints"""
    
    def test_update_train_position(self, test_train, test_section):
        """Test single train position update"""
        position_data = {
            "train_id": test_train.id,
            "section_id": test_section.id,
            "coordinates": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "altitude": 10.0
            },
            "speed_kmh": 80.0,
            "heading": 45.0,
            "timestamp": datetime.utcnow().isoformat(),
            "signal_strength": 95,
            "gps_accuracy": 2.5
        }
        
        response = client.post("/api/trains/position", json=position_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "train_id" in data["data"]
    
    def test_bulk_position_update(self, test_train, test_section, auth_headers):
        """Test bulk position update"""
        bulk_data = {
            "positions": [
                {
                    "train_id": test_train.id,
                    "section_id": test_section.id,
                    "coordinates": {
                        "latitude": 40.7128,
                        "longitude": -74.0060
                    },
                    "speed_kmh": 80.0,
                    "heading": 45.0,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        response = client.post("/api/trains/position/bulk", json=bulk_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["updated_count"] == 1
    
    def test_get_train_position(self, test_train, test_section, test_db):
        """Test get train position"""
        # Create a position record
        position = Position(
            train_id=test_train.id,
            section_id=test_section.id,
            timestamp=datetime.utcnow(),
            speed_kmh=80.0,
            direction=45.0
        )
        test_db.add(position)
        test_db.commit()
        
        response = client.get(f"/api/trains/{test_train.id}/position")
        assert response.status_code == 200
        data = response.json()
        assert data["train_id"] == test_train.id
        assert data["section_id"] == test_section.id
    
    def test_get_train_position_history(self, test_train):
        """Test get train position history"""
        response = client.get(f"/api/trains/{test_train.id}/position/history?hours=1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "positions" in data["data"]
    
    def test_invalid_train_position_update(self):
        """Test position update for non-existent train"""
        position_data = {
            "train_id": 99999,
            "section_id": 1,
            "coordinates": {
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "speed_kmh": 80.0,
            "heading": 45.0
        }
        
        response = client.post("/api/trains/position", json=position_data)
        assert response.status_code == 404


class TestSectionEndpoints:
    """Test section status endpoints"""
    
    def test_get_sections_status(self, auth_headers):
        """Test get sections status"""
        response = client.get("/api/sections/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "sections" in data
        assert "total_sections" in data
        assert "network_utilization" in data
    
    def test_get_section_status(self, test_section, auth_headers):
        """Test get specific section status"""
        response = client.get(f"/api/sections/{test_section.id}/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["section"]["id"] == test_section.id
        assert "current_occupancy" in data
        assert "status" in data
    
    def test_get_section_occupancy_history(self, test_section, auth_headers):
        """Test get section occupancy history"""
        response = client.get(f"/api/sections/{test_section.id}/occupancy-history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "history" in data["data"]
    
    def test_list_sections(self, auth_headers):
        """Test list sections"""
        response = client.get("/api/sections/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestWebSocketEndpoints:
    """Test WebSocket endpoints"""
    
    def test_websocket_stats(self):
        """Test WebSocket statistics endpoint"""
        response = client.get("/ws/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_connections" in data["data"]


class TestValidation:
    """Test input validation"""
    
    def test_invalid_coordinates(self):
        """Test invalid GPS coordinates"""
        position_data = {
            "train_id": 1,
            "section_id": 1,
            "coordinates": {
                "latitude": 91.0,  # Invalid latitude
                "longitude": -74.0060
            },
            "speed_kmh": 80.0,
            "heading": 45.0
        }
        
        response = client.post("/api/trains/position", json=position_data)
        assert response.status_code == 422  # Validation error
    
    def test_invalid_speed(self):
        """Test invalid speed value"""
        position_data = {
            "train_id": 1,
            "section_id": 1,
            "coordinates": {
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "speed_kmh": -10.0,  # Invalid negative speed
            "heading": 45.0
        }
        
        response = client.post("/api/trains/position", json=position_data)
        assert response.status_code == 422  # Validation error
    
    def test_invalid_heading(self):
        """Test invalid heading value"""
        position_data = {
            "train_id": 1,
            "section_id": 1,
            "coordinates": {
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "speed_kmh": 80.0,
            "heading": 400.0  # Invalid heading > 360
        }
        
        response = client.post("/api/trains/position", json=position_data)
        assert response.status_code == 422  # Validation error


class TestPerformance:
    """Test performance-related functionality"""
    
    def test_performance_metrics(self):
        """Test performance metrics endpoint"""
        response = client.get("/api/performance")
        assert response.status_code == 200
        data = response.json()
        assert "total_trains" in data
        assert "active_trains" in data
        assert "position_updates_per_minute" in data
    
    def test_system_info(self):
        """Test system information endpoint"""
        response = client.get("/api/system-info")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "api_version" in data["data"]
        assert "features" in data["data"]["environment"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])