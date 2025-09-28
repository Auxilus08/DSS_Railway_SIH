"""
Pydantic models for Railway Traffic Management API
Request/Response schemas with validation
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, EmailStr
from enum import Enum


class TrainTypeEnum(str, Enum):
    EXPRESS = "express"
    LOCAL = "local"
    FREIGHT = "freight"
    MAINTENANCE = "maintenance"


class ConflictSeverityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OperationalStatusEnum(str, Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"
    EMERGENCY = "emergency"


# Authentication Schemas
class LoginRequest(BaseModel):
    employee_id: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    controller: "ControllerResponse"


class TokenData(BaseModel):
    employee_id: Optional[str] = None
    controller_id: Optional[int] = None


# Position Tracking Schemas
class GPSCoordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    altitude: Optional[float] = Field(None, description="Altitude in meters")


class PositionUpdate(BaseModel):
    train_id: int = Field(..., gt=0, description="Train ID")
    section_id: int = Field(..., gt=0, description="Current section ID")
    coordinates: GPSCoordinates
    speed_kmh: float = Field(..., ge=0, le=300, description="Speed in km/h")
    heading: float = Field(..., ge=0, lt=360, description="Heading in degrees (0-359)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    distance_from_start: Optional[float] = Field(None, ge=0, description="Distance from section start in meters")
    signal_strength: Optional[int] = Field(None, ge=0, le=100, description="GPS signal strength percentage")
    gps_accuracy: Optional[float] = Field(None, ge=0, description="GPS accuracy in meters")

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        # Ensure timestamp is not too far in the future
        if v > datetime.utcnow().replace(microsecond=0) + timedelta(minutes=5):
            raise ValueError("Timestamp cannot be more than 5 minutes in the future")
        return v


class BulkPositionUpdate(BaseModel):
    positions: List[PositionUpdate] = Field(..., min_items=1, max_items=100)
    
    @field_validator('positions')
    @classmethod
    def validate_unique_trains(cls, v):
        train_ids = [pos.train_id for pos in v]
        if len(train_ids) != len(set(train_ids)):
            raise ValueError("Duplicate train IDs in bulk update")
        return v


class PositionResponse(BaseModel):
    train_id: int
    section_id: int
    section_code: str
    section_name: str
    coordinates: GPSCoordinates
    speed_kmh: float
    heading: float
    timestamp: datetime
    distance_from_start: Optional[float]
    signal_strength: Optional[int]
    gps_accuracy: Optional[float]

    class Config:
        from_attributes = True


# Train Schemas
class TrainBase(BaseModel):
    train_number: str = Field(..., min_length=2, max_length=20)
    type: TrainTypeEnum
    max_speed_kmh: int = Field(..., gt=0, le=300)
    capacity: int = Field(..., gt=0)
    priority: int = Field(..., ge=1, le=10)
    length_meters: float = Field(..., gt=0)
    weight_tons: float = Field(..., gt=0)


class TrainCreate(TrainBase):
    current_section_id: Optional[int] = None
    destination_section_id: Optional[int] = None
    origin_section_id: Optional[int] = None
    driver_id: Optional[str] = None
    conductor_id: Optional[str] = None
    engine_power_kw: Optional[int] = None
    fuel_type: Optional[str] = None


class TrainResponse(TrainBase):
    id: int
    current_section_id: Optional[int]
    speed_kmh: float
    current_load: int
    operational_status: OperationalStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainWithPosition(TrainResponse):
    current_position: Optional[PositionResponse] = None


# Section Schemas
class SectionBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    section_code: str = Field(..., min_length=2, max_length=20)
    section_type: str = Field(..., pattern="^(track|junction|station|yard)$")
    length_meters: float = Field(..., gt=0)
    max_speed_kmh: int = Field(..., gt=0, le=300)
    capacity: int = Field(..., gt=0)


class SectionResponse(SectionBase):
    id: int
    electrified: bool
    signaling_system: Optional[str]
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SectionStatus(BaseModel):
    section: SectionResponse
    current_occupancy: int
    utilization_percentage: float
    trains_present: List[TrainResponse]
    status: str  # "available", "busy", "full", "maintenance"


class SectionStatusSummary(BaseModel):
    sections: List[SectionStatus]
    total_sections: int
    occupied_sections: int
    network_utilization: float
    timestamp: datetime


# Controller Schemas
class ControllerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    employee_id: str = Field(..., min_length=3, max_length=20)


class ControllerResponse(ControllerBase):
    id: int
    auth_level: str
    section_responsibility: Optional[List[int]]
    active: bool
    created_at: datetime

    @field_validator('section_responsibility', mode='before')
    @classmethod
    def parse_section_responsibility(cls, v):
        """Handle both JSON string and list formats for SQLite compatibility"""
        if isinstance(v, str) and v:
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        elif isinstance(v, list):
            return v
        return [] if v is None else v

    class Config:
        from_attributes = True


# WebSocket Schemas
class WebSocketMessage(BaseModel):
    type: str  # "position_update", "conflict_alert", "system_status"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PositionBroadcast(BaseModel):
    type: str = "position_update"
    train_id: int
    train_number: str
    train_type: TrainTypeEnum
    position: PositionResponse
    timestamp: datetime


# Conflict Schemas
class ConflictResponse(BaseModel):
    id: int
    conflict_type: str
    severity: ConflictSeverityEnum
    trains_involved: List[int]
    sections_involved: List[int]
    detection_time: datetime
    resolution_time: Optional[datetime]
    description: str
    auto_resolved: bool

    class Config:
        from_attributes = True


# API Response Schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    database_status: str
    redis_status: str
    active_connections: int


# Performance Metrics
class PerformanceMetrics(BaseModel):
    total_trains: int
    active_trains: int
    position_updates_per_minute: int
    average_response_time_ms: float
    active_websocket_connections: int
    cache_hit_rate: float
    database_connections: int


# Rate Limiting
class RateLimitInfo(BaseModel):
    requests_remaining: int
    reset_time: datetime
    limit_per_minute: int


# Validation helpers
from datetime import timedelta

def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate GPS coordinates are within reasonable bounds"""
    return -90 <= lat <= 90 and -180 <= lon <= 180


def validate_train_speed(speed: float, max_speed: int) -> bool:
    """Validate train speed doesn't exceed maximum"""
    return 0 <= speed <= max_speed * 1.1  # Allow 10% tolerance


# Update forward references
LoginResponse.model_rebuild()
TrainWithPosition.model_rebuild()