"""
SQLAlchemy ORM Models for Railway Traffic Management System
Production-ready models with proper relationships and constraints
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Decimal, Boolean, DateTime, Text, Time,
    ForeignKey, CheckConstraint, UniqueConstraint, Index, ARRAY, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from geoalchemy2 import Geometry
from enum import Enum as PyEnum

Base = declarative_base()

# Python Enums for type safety
class TrainType(PyEnum):
    EXPRESS = "express"
    LOCAL = "local"
    FREIGHT = "freight"
    MAINTENANCE = "maintenance"

class ConflictSeverity(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ControllerAuthLevel(PyEnum):
    OPERATOR = "operator"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    ADMIN = "admin"

class DecisionAction(PyEnum):
    REROUTE = "reroute"
    DELAY = "delay"
    PRIORITY_CHANGE = "priority_change"
    EMERGENCY_STOP = "emergency_stop"
    SPEED_LIMIT = "speed_limit"
    MANUAL_OVERRIDE = "manual_override"

# SQLAlchemy ENUM types
train_type_enum = ENUM(TrainType, name='train_type')
conflict_severity_enum = ENUM(ConflictSeverity, name='conflict_severity')
controller_auth_level_enum = ENUM(ControllerAuthLevel, name='controller_auth_level')
decision_action_enum = ENUM(DecisionAction, name='decision_action')


class Controller(Base):
    """Railway traffic controllers"""
    __tablename__ = 'controllers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    employee_id = Column(String(20), unique=True, nullable=False)
    section_responsibility = Column(ARRAY(Integer), nullable=True)
    auth_level = Column(controller_auth_level_enum, nullable=False, default=ControllerAuthLevel.OPERATOR)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resolved_conflicts = relationship("Conflict", back_populates="resolved_by_controller")
    decisions = relationship("Decision", foreign_keys="Decision.controller_id", back_populates="controller")
    approved_decisions = relationship("Decision", foreign_keys="Decision.approved_by_controller_id", back_populates="approved_by_controller")
    maintenance_windows = relationship("MaintenanceWindow", back_populates="created_by_controller")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("LENGTH(name) >= 2", name="controllers_name_check"),
        CheckConstraint("LENGTH(employee_id) >= 3", name="controllers_employee_id_check"),
    )
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) < 2:
            raise ValueError("Controller name must be at least 2 characters")
        return name.strip()
    
    def __repr__(self):
        return f"<Controller(id={self.id}, name='{self.name}', auth_level='{self.auth_level}')>"


class Section(Base):
    """Track sections, junctions, stations"""
    __tablename__ = 'sections'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    section_code = Column(String(20), unique=True, nullable=False)
    section_type = Column(String(20), nullable=False)
    length_meters = Column(Decimal(10, 2), nullable=False)
    max_speed_kmh = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False, default=1)
    junction_ids = Column(ARRAY(Integer), nullable=True)
    coordinates = Column(Geometry('LINESTRING', srid=4326), nullable=True)
    elevation_start = Column(Decimal(8, 2), nullable=True)
    elevation_end = Column(Decimal(8, 2), nullable=True)
    gradient = Column(Decimal(5, 3), nullable=True)
    electrified = Column(Boolean, nullable=False, default=False)
    signaling_system = Column(String(50), nullable=True)
    maintenance_window_start = Column(Time, nullable=True)
    maintenance_window_end = Column(Time, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trains_current = relationship("Train", foreign_keys="Train.current_section_id", back_populates="current_section")
    trains_destination = relationship("Train", foreign_keys="Train.destination_section_id", back_populates="destination_section")
    trains_origin = relationship("Train", foreign_keys="Train.origin_section_id", back_populates="origin_section")
    positions = relationship("Position", back_populates="section")
    decisions = relationship("Decision", back_populates="section")
    occupancy_records = relationship("SectionOccupancy", back_populates="section")
    maintenance_windows = relationship("MaintenanceWindow", back_populates="section")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("LENGTH(name) >= 2", name="sections_name_check"),
        CheckConstraint("LENGTH(section_code) >= 2", name="sections_code_check"),
        CheckConstraint("length_meters > 0", name="sections_length_check"),
        CheckConstraint("max_speed_kmh > 0 AND max_speed_kmh <= 300", name="sections_max_speed_check"),
        CheckConstraint("capacity > 0", name="sections_capacity_check"),
        CheckConstraint("gradient BETWEEN -10.0 AND 10.0", name="sections_gradient_check"),
        CheckConstraint("section_type IN ('track', 'junction', 'station', 'yard')", name="sections_type_check"),
    )
    
    @validates('section_type')
    def validate_section_type(self, key, section_type):
        valid_types = ['track', 'junction', 'station', 'yard']
        if section_type not in valid_types:
            raise ValueError(f"Section type must be one of: {valid_types}")
        return section_type
    
    def __repr__(self):
        return f"<Section(id={self.id}, code='{self.section_code}', type='{self.section_type}')>"


class Train(Base):
    """All train information"""
    __tablename__ = 'trains'
    
    id = Column(Integer, primary_key=True)
    train_number = Column(String(20), unique=True, nullable=False)
    type = Column(train_type_enum, nullable=False)
    current_section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    speed_kmh = Column(Decimal(5, 2), nullable=False, default=0)
    max_speed_kmh = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    current_load = Column(Integer, nullable=False, default=0)
    priority = Column(Integer, nullable=False, default=5)
    destination_section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    origin_section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    scheduled_departure = Column(DateTime(timezone=True), nullable=True)
    scheduled_arrival = Column(DateTime(timezone=True), nullable=True)
    actual_departure = Column(DateTime(timezone=True), nullable=True)
    estimated_arrival = Column(DateTime(timezone=True), nullable=True)
    driver_id = Column(String(20), nullable=True)
    conductor_id = Column(String(20), nullable=True)
    length_meters = Column(Decimal(8, 2), nullable=False)
    weight_tons = Column(Decimal(10, 2), nullable=False)
    engine_power_kw = Column(Integer, nullable=True)
    fuel_type = Column(String(20), nullable=True)
    operational_status = Column(String(20), nullable=False, default='active')
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    current_section = relationship("Section", foreign_keys=[current_section_id], back_populates="trains_current")
    destination_section = relationship("Section", foreign_keys=[destination_section_id], back_populates="trains_destination")
    origin_section = relationship("Section", foreign_keys=[origin_section_id], back_populates="trains_origin")
    positions = relationship("Position", back_populates="train", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="train")
    schedules = relationship("TrainSchedule", back_populates="train", cascade="all, delete-orphan")
    occupancy_records = relationship("SectionOccupancy", back_populates="train")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("LENGTH(train_number) >= 2", name="trains_number_check"),
        CheckConstraint("speed_kmh >= 0", name="trains_speed_check"),
        CheckConstraint("max_speed_kmh > 0 AND max_speed_kmh <= 300", name="trains_max_speed_check"),
        CheckConstraint("capacity > 0", name="trains_capacity_check"),
        CheckConstraint("current_load >= 0", name="trains_load_check"),
        CheckConstraint("current_load <= capacity", name="trains_load_capacity_check"),
        CheckConstraint("priority BETWEEN 1 AND 10", name="trains_priority_check"),
        CheckConstraint("length_meters > 0", name="trains_length_check"),
        CheckConstraint("weight_tons > 0", name="trains_weight_check"),
        CheckConstraint("fuel_type IN ('diesel', 'electric', 'hybrid') OR fuel_type IS NULL", name="trains_fuel_check"),
        CheckConstraint("operational_status IN ('active', 'maintenance', 'out_of_service', 'emergency')", name="trains_status_check"),
        CheckConstraint("""
            scheduled_departure IS NULL OR scheduled_arrival IS NULL OR 
            scheduled_departure < scheduled_arrival
        """, name="trains_schedule_check"),
    )
    
    @validates('operational_status')
    def validate_operational_status(self, key, status):
        valid_statuses = ['active', 'maintenance', 'out_of_service', 'emergency']
        if status not in valid_statuses:
            raise ValueError(f"Operational status must be one of: {valid_statuses}")
        return status
    
    def __repr__(self):
        return f"<Train(id={self.id}, number='{self.train_number}', type='{self.type}')>"


class Position(Base):
    """Real-time train position tracking (TimescaleDB hypertable)"""
    __tablename__ = 'positions'
    
    train_id = Column(Integer, ForeignKey('trains.id', ondelete='CASCADE'), primary_key=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True, default=datetime.utcnow)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=False)
    coordinates = Column(Geometry('POINT', srid=4326), nullable=True)
    speed_kmh = Column(Decimal(5, 2), nullable=False, default=0)
    direction = Column(Decimal(5, 2), nullable=True)
    distance_from_start = Column(Decimal(10, 2), nullable=True)
    signal_strength = Column(Integer, nullable=True)
    gps_accuracy = Column(Decimal(5, 2), nullable=True)
    altitude = Column(Decimal(8, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    train = relationship("Train", back_populates="positions")
    section = relationship("Section", back_populates="positions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("speed_kmh >= 0", name="positions_speed_check"),
        CheckConstraint("direction BETWEEN 0 AND 360 OR direction IS NULL", name="positions_direction_check"),
        CheckConstraint("distance_from_start >= 0 OR distance_from_start IS NULL", name="positions_distance_check"),
        CheckConstraint("signal_strength BETWEEN 0 AND 100 OR signal_strength IS NULL", name="positions_signal_check"),
        CheckConstraint("coordinates IS NOT NULL OR section_id IS NOT NULL", name="positions_coordinates_check"),
    )
    
    def __repr__(self):
        return f"<Position(train_id={self.train_id}, timestamp='{self.timestamp}', section_id={self.section_id})>"


class Conflict(Base):
    """Detected conflicts and their resolution"""
    __tablename__ = 'conflicts'
    
    id = Column(Integer, primary_key=True)
    conflict_type = Column(String(50), nullable=False)
    severity = Column(conflict_severity_enum, nullable=False)
    trains_involved = Column(ARRAY(Integer), nullable=False)
    sections_involved = Column(ARRAY(Integer), nullable=False)
    detection_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    resolution_time = Column(DateTime(timezone=True), nullable=True)
    estimated_impact_minutes = Column(Integer, nullable=True)
    description = Column(Text, nullable=False)
    auto_resolved = Column(Boolean, nullable=False, default=False)
    resolved_by_controller_id = Column(Integer, ForeignKey('controllers.id'), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resolved_by_controller = relationship("Controller", back_populates="resolved_conflicts")
    decisions = relationship("Decision", back_populates="conflict")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("array_length(trains_involved, 1) >= 1", name="conflicts_trains_check"),
        CheckConstraint("array_length(sections_involved, 1) >= 1", name="conflicts_sections_check"),
        CheckConstraint("""
            conflict_type IN ('collision_risk', 'section_overload', 'speed_violation', 
                            'signal_violation', 'maintenance_conflict', 'priority_conflict', 'route_conflict')
        """, name="conflicts_type_check"),
        CheckConstraint("""
            (resolution_time IS NULL AND resolved_by_controller_id IS NULL) OR
            (resolution_time IS NOT NULL AND resolution_time >= detection_time)
        """, name="conflicts_resolution_check"),
    )
    
    @validates('conflict_type')
    def validate_conflict_type(self, key, conflict_type):
        valid_types = [
            'collision_risk', 'section_overload', 'speed_violation', 
            'signal_violation', 'maintenance_conflict', 'priority_conflict', 'route_conflict'
        ]
        if conflict_type not in valid_types:
            raise ValueError(f"Conflict type must be one of: {valid_types}")
        return conflict_type
    
    def __repr__(self):
        return f"<Conflict(id={self.id}, type='{self.conflict_type}', severity='{self.severity}')>"


class Decision(Base):
    """Controller decisions and audit trail"""
    __tablename__ = 'decisions'
    
    id = Column(Integer, primary_key=True)
    controller_id = Column(Integer, ForeignKey('controllers.id'), nullable=False)
    conflict_id = Column(Integer, ForeignKey('conflicts.id'), nullable=True)
    train_id = Column(Integer, ForeignKey('trains.id'), nullable=True)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    action_taken = Column(decision_action_enum, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    rationale = Column(Text, nullable=False)
    parameters = Column(JSONB, nullable=True)
    executed = Column(Boolean, nullable=False, default=False)
    execution_time = Column(DateTime(timezone=True), nullable=True)
    execution_result = Column(Text, nullable=True)
    override_reason = Column(Text, nullable=True)
    approval_required = Column(Boolean, nullable=False, default=False)
    approved_by_controller_id = Column(Integer, ForeignKey('controllers.id'), nullable=True)
    approval_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    controller = relationship("Controller", foreign_keys=[controller_id], back_populates="decisions")
    approved_by_controller = relationship("Controller", foreign_keys=[approved_by_controller_id], back_populates="approved_decisions")
    conflict = relationship("Conflict", back_populates="decisions")
    train = relationship("Train", back_populates="decisions")
    section = relationship("Section", back_populates="decisions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("LENGTH(rationale) >= 10", name="decisions_rationale_check"),
        CheckConstraint("""
            (executed = false AND execution_time IS NULL) OR
            (executed = true AND execution_time IS NOT NULL AND execution_time >= timestamp)
        """, name="decisions_execution_check"),
        CheckConstraint("""
            (approval_required = false) OR
            (approval_required = true AND approved_by_controller_id IS NOT NULL AND approval_time IS NOT NULL)
        """, name="decisions_approval_check"),
    )
    
    def __repr__(self):
        return f"<Decision(id={self.id}, action='{self.action_taken}', controller_id={self.controller_id})>"


class TrainSchedule(Base):
    """Planned routes and timing"""
    __tablename__ = 'train_schedules'
    
    id = Column(Integer, primary_key=True)
    train_id = Column(Integer, ForeignKey('trains.id', ondelete='CASCADE'), nullable=False)
    route_sections = Column(ARRAY(Integer), nullable=False)
    scheduled_times = Column(ARRAY(DateTime(timezone=True)), nullable=False)
    actual_times = Column(ARRAY(DateTime(timezone=True)), nullable=True)
    delays_minutes = Column(ARRAY(Integer), nullable=True, default=[])
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    train = relationship("Train", back_populates="schedules")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("""
            array_length(route_sections, 1) = array_length(scheduled_times, 1)
        """, name="schedules_route_times_match"),
    )
    
    def __repr__(self):
        return f"<TrainSchedule(id={self.id}, train_id={self.train_id}, active={self.active})>"


class SectionOccupancy(Base):
    """Section occupancy tracking"""
    __tablename__ = 'section_occupancy'
    
    section_id = Column(Integer, ForeignKey('sections.id'), primary_key=True)
    train_id = Column(Integer, ForeignKey('trains.id'), primary_key=True)
    entry_time = Column(DateTime(timezone=True), primary_key=True, default=datetime.utcnow)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    expected_exit_time = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    section = relationship("Section", back_populates="occupancy_records")
    train = relationship("Train", back_populates="occupancy_records")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("exit_time IS NULL OR exit_time > entry_time", name="occupancy_exit_check"),
    )
    
    def __repr__(self):
        return f"<SectionOccupancy(section_id={self.section_id}, train_id={self.train_id}, entry_time='{self.entry_time}')>"


class MaintenanceWindow(Base):
    """Maintenance windows"""
    __tablename__ = 'maintenance_windows'
    
    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    maintenance_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    affects_traffic = Column(Boolean, nullable=False, default=True)
    created_by_controller_id = Column(Integer, ForeignKey('controllers.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    section = relationship("Section", back_populates="maintenance_windows")
    created_by_controller = relationship("Controller", back_populates="maintenance_windows")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="maintenance_time_check"),
    )
    
    def __repr__(self):
        return f"<MaintenanceWindow(id={self.id}, section_id={self.section_id}, type='{self.maintenance_type}')>"