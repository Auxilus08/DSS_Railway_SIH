-- Railway Traffic Management System Database Schema
-- Production-ready schema with proper constraints and relationships

-- Enable TimescaleDB extension for time-series data
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enum types for better data integrity
CREATE TYPE train_type AS ENUM ('express', 'local', 'freight', 'maintenance');
CREATE TYPE conflict_severity AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE controller_auth_level AS ENUM ('operator', 'supervisor', 'manager', 'admin');
CREATE TYPE decision_action AS ENUM ('reroute', 'delay', 'priority_change', 'emergency_stop', 'speed_limit', 'manual_override');

-- Controllers table - Railway traffic controllers
CREATE TABLE controllers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    section_responsibility TEXT[], -- Array of section IDs they're responsible for
    auth_level controller_auth_level NOT NULL DEFAULT 'operator',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT controllers_name_check CHECK (LENGTH(name) >= 2),
    CONSTRAINT controllers_employee_id_check CHECK (LENGTH(employee_id) >= 3)
);

-- Sections table - Track sections, junctions, stations
CREATE TABLE sections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    section_code VARCHAR(20) UNIQUE NOT NULL,
    section_type VARCHAR(20) NOT NULL CHECK (section_type IN ('track', 'junction', 'station', 'yard')),
    length_meters DECIMAL(10,2) NOT NULL CHECK (length_meters > 0),
    max_speed_kmh INTEGER NOT NULL CHECK (max_speed_kmh > 0 AND max_speed_kmh <= 300),
    capacity INTEGER NOT NULL DEFAULT 1 CHECK (capacity > 0),
    junction_ids INTEGER[], -- Connected junction section IDs
    coordinates GEOMETRY(LINESTRING, 4326), -- Geographic coordinates using PostGIS
    elevation_start DECIMAL(8,2), -- Elevation in meters
    elevation_end DECIMAL(8,2),
    gradient DECIMAL(5,3), -- Grade percentage
    electrified BOOLEAN NOT NULL DEFAULT false,
    signaling_system VARCHAR(50),
    maintenance_window_start TIME,
    maintenance_window_end TIME,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT sections_name_check CHECK (LENGTH(name) >= 2),
    CONSTRAINT sections_code_check CHECK (LENGTH(section_code) >= 2),
    CONSTRAINT sections_gradient_check CHECK (gradient BETWEEN -10.0 AND 10.0)
);

-- Trains table - All train information
CREATE TABLE trains (
    id SERIAL PRIMARY KEY,
    train_number VARCHAR(20) UNIQUE NOT NULL,
    type train_type NOT NULL,
    current_section_id INTEGER REFERENCES sections(id),
    speed_kmh DECIMAL(5,2) NOT NULL DEFAULT 0 CHECK (speed_kmh >= 0),
    max_speed_kmh INTEGER NOT NULL CHECK (max_speed_kmh > 0 AND max_speed_kmh <= 300),
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    current_load INTEGER NOT NULL DEFAULT 0 CHECK (current_load >= 0),
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10), -- 1 = highest priority
    destination_section_id INTEGER REFERENCES sections(id),
    origin_section_id INTEGER REFERENCES sections(id),
    scheduled_departure TIMESTAMP WITH TIME ZONE,
    scheduled_arrival TIMESTAMP WITH TIME ZONE,
    actual_departure TIMESTAMP WITH TIME ZONE,
    estimated_arrival TIMESTAMP WITH TIME ZONE,
    driver_id VARCHAR(20),
    conductor_id VARCHAR(20),
    length_meters DECIMAL(8,2) NOT NULL CHECK (length_meters > 0),
    weight_tons DECIMAL(10,2) NOT NULL CHECK (weight_tons > 0),
    engine_power_kw INTEGER,
    fuel_type VARCHAR(20) CHECK (fuel_type IN ('diesel', 'electric', 'hybrid')),
    operational_status VARCHAR(20) NOT NULL DEFAULT 'active' 
        CHECK (operational_status IN ('active', 'maintenance', 'out_of_service', 'emergency')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT trains_number_check CHECK (LENGTH(train_number) >= 2),
    CONSTRAINT trains_load_capacity_check CHECK (current_load <= capacity),
    CONSTRAINT trains_schedule_check CHECK (
        scheduled_departure IS NULL OR scheduled_arrival IS NULL OR 
        scheduled_departure < scheduled_arrival
    )
);

-- Positions table - Real-time train position tracking (TimescaleDB hypertable)
CREATE TABLE positions (
    train_id INTEGER NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL REFERENCES sections(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    coordinates GEOMETRY(POINT, 4326), -- Exact GPS coordinates
    speed_kmh DECIMAL(5,2) NOT NULL DEFAULT 0 CHECK (speed_kmh >= 0),
    direction DECIMAL(5,2) CHECK (direction BETWEEN 0 AND 360), -- Compass bearing
    distance_from_start DECIMAL(10,2) CHECK (distance_from_start >= 0), -- Distance from section start
    signal_strength INTEGER CHECK (signal_strength BETWEEN 0 AND 100),
    gps_accuracy DECIMAL(5,2), -- GPS accuracy in meters
    altitude DECIMAL(8,2), -- Altitude in meters
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (train_id, timestamp),
    CONSTRAINT positions_coordinates_check CHECK (coordinates IS NOT NULL OR section_id IS NOT NULL)
);

-- Convert positions table to TimescaleDB hypertable
SELECT create_hypertable('positions', 'timestamp', chunk_time_interval => INTERVAL '1 hour');

-- Conflicts table - Detected conflicts and their resolution
CREATE TABLE conflicts (
    id SERIAL PRIMARY KEY,
    conflict_type VARCHAR(50) NOT NULL CHECK (conflict_type IN (
        'collision_risk', 'section_overload', 'speed_violation', 'signal_violation', 
        'maintenance_conflict', 'priority_conflict', 'route_conflict'
    )),
    severity conflict_severity NOT NULL,
    trains_involved INTEGER[] NOT NULL, -- Array of train IDs
    sections_involved INTEGER[] NOT NULL, -- Array of section IDs
    detection_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolution_time TIMESTAMP WITH TIME ZONE,
    estimated_impact_minutes INTEGER,
    description TEXT NOT NULL,
    auto_resolved BOOLEAN NOT NULL DEFAULT false,
    resolved_by_controller_id INTEGER REFERENCES controllers(id),
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT conflicts_trains_check CHECK (array_length(trains_involved, 1) >= 1),
    CONSTRAINT conflicts_sections_check CHECK (array_length(sections_involved, 1) >= 1),
    CONSTRAINT conflicts_resolution_check CHECK (
        (resolution_time IS NULL AND resolved_by_controller_id IS NULL) OR
        (resolution_time IS NOT NULL AND resolution_time >= detection_time)
    )
);

-- Decisions table - Controller decisions and audit trail
CREATE TABLE decisions (
    id SERIAL PRIMARY KEY,
    controller_id INTEGER NOT NULL REFERENCES controllers(id),
    conflict_id INTEGER REFERENCES conflicts(id),
    train_id INTEGER REFERENCES trains(id),
    section_id INTEGER REFERENCES sections(id),
    action_taken decision_action NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rationale TEXT NOT NULL,
    parameters JSONB, -- Flexible storage for action-specific parameters
    executed BOOLEAN NOT NULL DEFAULT false,
    execution_time TIMESTAMP WITH TIME ZONE,
    execution_result TEXT,
    override_reason TEXT, -- If this decision overrides another
    approval_required BOOLEAN NOT NULL DEFAULT false,
    approved_by_controller_id INTEGER REFERENCES controllers(id),
    approval_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT decisions_rationale_check CHECK (LENGTH(rationale) >= 10),
    CONSTRAINT decisions_execution_check CHECK (
        (executed = false AND execution_time IS NULL) OR
        (executed = true AND execution_time IS NOT NULL AND execution_time >= timestamp)
    ),
    CONSTRAINT decisions_approval_check CHECK (
        (approval_required = false) OR
        (approval_required = true AND approved_by_controller_id IS NOT NULL AND approval_time IS NOT NULL)
    )
);

-- Train schedules table - Planned routes and timing
CREATE TABLE train_schedules (
    id SERIAL PRIMARY KEY,
    train_id INTEGER NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    route_sections INTEGER[] NOT NULL, -- Ordered array of section IDs
    scheduled_times TIMESTAMP WITH TIME ZONE[] NOT NULL, -- Corresponding arrival times
    actual_times TIMESTAMP WITH TIME ZONE[], -- Actual arrival times
    delays_minutes INTEGER[] DEFAULT '{}', -- Delay at each section
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT schedules_route_times_match CHECK (
        array_length(route_sections, 1) = array_length(scheduled_times, 1)
    )
);

-- Section occupancy tracking
CREATE TABLE section_occupancy (
    section_id INTEGER NOT NULL REFERENCES sections(id),
    train_id INTEGER NOT NULL REFERENCES trains(id),
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    exit_time TIMESTAMP WITH TIME ZONE,
    expected_exit_time TIMESTAMP WITH TIME ZONE,
    
    PRIMARY KEY (section_id, train_id, entry_time),
    CONSTRAINT occupancy_exit_check CHECK (exit_time IS NULL OR exit_time > entry_time)
);

-- Maintenance windows
CREATE TABLE maintenance_windows (
    id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES sections(id),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    maintenance_type VARCHAR(50) NOT NULL,
    description TEXT,
    affects_traffic BOOLEAN NOT NULL DEFAULT true,
    created_by_controller_id INTEGER REFERENCES controllers(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT maintenance_time_check CHECK (end_time > start_time)
);

-- Add triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_controllers_updated_at BEFORE UPDATE ON controllers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sections_updated_at BEFORE UPDATE ON sections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trains_updated_at BEFORE UPDATE ON trains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conflicts_updated_at BEFORE UPDATE ON conflicts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_train_schedules_updated_at BEFORE UPDATE ON train_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();