-- Performance Indexes for Railway Traffic Management System
-- Optimized for real-time queries and conflict detection

-- Controllers indexes
CREATE INDEX idx_controllers_active ON controllers(active) WHERE active = true;
CREATE INDEX idx_controllers_auth_level ON controllers(auth_level);
CREATE INDEX idx_controllers_section_responsibility ON controllers USING GIN(section_responsibility);

-- Sections indexes
CREATE INDEX idx_sections_active ON sections(active) WHERE active = true;
CREATE INDEX idx_sections_type ON sections(section_type);
CREATE INDEX idx_sections_code ON sections(section_code);
CREATE INDEX idx_sections_junction_ids ON sections USING GIN(junction_ids);
CREATE INDEX idx_sections_coordinates ON sections USING GIST(coordinates);
CREATE INDEX idx_sections_max_speed ON sections(max_speed_kmh);
CREATE INDEX idx_sections_capacity ON sections(capacity);

-- Trains indexes
CREATE INDEX idx_trains_current_section ON trains(current_section_id) WHERE current_section_id IS NOT NULL;
CREATE INDEX idx_trains_type ON trains(type);
CREATE INDEX idx_trains_priority ON trains(priority);
CREATE INDEX idx_trains_status ON trains(operational_status);
CREATE INDEX idx_trains_number ON trains(train_number);
CREATE INDEX idx_trains_destination ON trains(destination_section_id) WHERE destination_section_id IS NOT NULL;
CREATE INDEX idx_trains_origin ON trains(origin_section_id) WHERE origin_section_id IS NOT NULL;
CREATE INDEX idx_trains_scheduled_departure ON trains(scheduled_departure) WHERE scheduled_departure IS NOT NULL;
CREATE INDEX idx_trains_scheduled_arrival ON trains(scheduled_arrival) WHERE scheduled_arrival IS NOT NULL;
CREATE INDEX idx_trains_speed ON trains(speed_kmh);

-- Positions indexes (TimescaleDB hypertable)
-- TimescaleDB automatically creates time-based indexes, but we add spatial and query-specific ones
CREATE INDEX idx_positions_train_id ON positions(train_id);
CREATE INDEX idx_positions_section_id ON positions(section_id);
CREATE INDEX idx_positions_coordinates ON positions USING GIST(coordinates);
CREATE INDEX idx_positions_speed ON positions(speed_kmh);
CREATE INDEX idx_positions_train_time ON positions(train_id, timestamp DESC);
CREATE INDEX idx_positions_section_time ON positions(section_id, timestamp DESC);

-- Composite index for real-time position queries
CREATE INDEX idx_positions_realtime ON positions(train_id, timestamp DESC, section_id);

-- Conflicts indexes
CREATE INDEX idx_conflicts_detection_time ON conflicts(detection_time DESC);
CREATE INDEX idx_conflicts_severity ON conflicts(severity);
CREATE INDEX idx_conflicts_unresolved ON conflicts(resolution_time) WHERE resolution_time IS NULL;
CREATE INDEX idx_conflicts_trains_involved ON conflicts USING GIN(trains_involved);
CREATE INDEX idx_conflicts_sections_involved ON conflicts USING GIN(sections_involved);
CREATE INDEX idx_conflicts_type ON conflicts(conflict_type);
CREATE INDEX idx_conflicts_resolved_by ON conflicts(resolved_by_controller_id) WHERE resolved_by_controller_id IS NOT NULL;

-- Composite index for recent conflicts query
CREATE INDEX idx_conflicts_recent ON conflicts(detection_time DESC, severity) 
    WHERE resolution_time IS NULL OR detection_time >= CURRENT_TIMESTAMP - INTERVAL '24 hours';

-- Decisions indexes
CREATE INDEX idx_decisions_timestamp ON decisions(timestamp DESC);
CREATE INDEX idx_decisions_controller ON decisions(controller_id);
CREATE INDEX idx_decisions_conflict ON decisions(conflict_id) WHERE conflict_id IS NOT NULL;
CREATE INDEX idx_decisions_train ON decisions(train_id) WHERE train_id IS NOT NULL;
CREATE INDEX idx_decisions_section ON decisions(section_id) WHERE section_id IS NOT NULL;
CREATE INDEX idx_decisions_action ON decisions(action_taken);
CREATE INDEX idx_decisions_executed ON decisions(executed, execution_time);
CREATE INDEX idx_decisions_approval ON decisions(approval_required, approved_by_controller_id);

-- Train schedules indexes
CREATE INDEX idx_train_schedules_train ON train_schedules(train_id);
CREATE INDEX idx_train_schedules_active ON train_schedules(active) WHERE active = true;
CREATE INDEX idx_train_schedules_route ON train_schedules USING GIN(route_sections);
CREATE INDEX idx_train_schedules_times ON train_schedules USING GIN(scheduled_times);

-- Section occupancy indexes
CREATE INDEX idx_section_occupancy_section ON section_occupancy(section_id);
CREATE INDEX idx_section_occupancy_train ON section_occupancy(train_id);
CREATE INDEX idx_section_occupancy_current ON section_occupancy(section_id, entry_time) 
    WHERE exit_time IS NULL;
CREATE INDEX idx_section_occupancy_entry_time ON section_occupancy(entry_time DESC);
CREATE INDEX idx_section_occupancy_exit_time ON section_occupancy(exit_time DESC) 
    WHERE exit_time IS NOT NULL;

-- Maintenance windows indexes
CREATE INDEX idx_maintenance_windows_section ON maintenance_windows(section_id);
CREATE INDEX idx_maintenance_windows_time_range ON maintenance_windows(start_time, end_time);
CREATE INDEX idx_maintenance_windows_active ON maintenance_windows(start_time, end_time) 
    WHERE affects_traffic = true;
CREATE INDEX idx_maintenance_windows_type ON maintenance_windows(maintenance_type);

-- Partial indexes for common queries
CREATE INDEX idx_trains_active_express ON trains(current_section_id, priority) 
    WHERE type = 'express' AND operational_status = 'active';

CREATE INDEX idx_trains_active_freight ON trains(current_section_id, speed_kmh) 
    WHERE type = 'freight' AND operational_status = 'active';

CREATE INDEX idx_sections_high_capacity ON sections(id, max_speed_kmh) 
    WHERE capacity > 1 AND active = true;

-- Covering indexes for frequent queries
CREATE INDEX idx_positions_covering ON positions(train_id, timestamp DESC) 
    INCLUDE (section_id, coordinates, speed_kmh);

CREATE INDEX idx_conflicts_covering ON conflicts(detection_time DESC) 
    INCLUDE (severity, trains_involved, sections_involved, resolution_time);

-- Function-based indexes for calculated fields
CREATE INDEX idx_trains_load_percentage ON trains((current_load::float / capacity::float * 100)) 
    WHERE operational_status = 'active';

CREATE INDEX idx_sections_utilization ON section_occupancy(section_id, 
    EXTRACT(EPOCH FROM (COALESCE(exit_time, CURRENT_TIMESTAMP) - entry_time))) 
    WHERE exit_time IS NULL OR exit_time >= CURRENT_TIMESTAMP - INTERVAL '1 hour';

-- Unique constraints as indexes
CREATE UNIQUE INDEX idx_trains_number_unique ON trains(train_number) WHERE operational_status != 'out_of_service';
CREATE UNIQUE INDEX idx_sections_code_unique ON sections(section_code) WHERE active = true;
CREATE UNIQUE INDEX idx_controllers_employee_unique ON controllers(employee_id) WHERE active = true;

-- Performance indexes specifically for conflict detection system
-- Optimized for 500+ trains with sub-second detection time

-- Conflict detection spatial queries
CREATE INDEX idx_positions_spatial_detection ON positions(section_id, timestamp DESC, train_id)
    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour';

-- Temporal conflict detection - overlapping time windows
CREATE INDEX idx_positions_temporal_detection ON positions(train_id, section_id, timestamp)
    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '2 hours';

-- Priority conflict detection - train priorities with sections
CREATE INDEX idx_trains_priority_sections ON trains(priority DESC, current_section_id, type)
    WHERE operational_status = 'active';

-- Junction conflict detection - junction sections with capacity
CREATE INDEX idx_sections_junctions ON sections(id, capacity, max_speed_kmh)
    WHERE section_type = 'junction' AND active = true;

-- Real-time conflict monitoring - recent positions with speed
CREATE INDEX idx_positions_realtime_monitoring ON positions(timestamp DESC, section_id, speed_kmh)
    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '15 minutes';

-- Train prediction queries - route sections with timing
CREATE INDEX idx_train_schedules_prediction ON train_schedules(train_id, active)
    INCLUDE (route_sections, scheduled_times)
    WHERE active = true;

-- Bulk train data loading optimization
CREATE INDEX idx_trains_bulk_load ON trains(operational_status, id)
    INCLUDE (train_number, type, priority, max_speed_kmh, capacity, current_load, current_section_id)
    WHERE operational_status = 'active';

-- Section occupancy for capacity checking
CREATE INDEX idx_section_occupancy_capacity ON section_occupancy(section_id, exit_time)
    WHERE exit_time IS NULL OR exit_time >= CURRENT_TIMESTAMP - INTERVAL '30 minutes';

-- Conflict resolution tracking
CREATE INDEX idx_conflicts_resolution_tracking ON conflicts(detection_time DESC, resolution_time)
    INCLUDE (severity, trains_involved, sections_involved, auto_resolved);

-- Performance monitoring indexes
CREATE INDEX idx_positions_performance_monitoring ON positions(timestamp DESC)
    INCLUDE (train_id, section_id, speed_kmh)
    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour';

-- Emergency response indexes - critical conflicts
CREATE INDEX idx_conflicts_emergency ON conflicts(severity, detection_time DESC)
    WHERE severity IN ('high', 'critical') AND resolution_time IS NULL;

-- Statistics targets for better query planning
ALTER TABLE positions ALTER COLUMN timestamp SET STATISTICS 1000;
ALTER TABLE positions ALTER COLUMN train_id SET STATISTICS 1000;
ALTER TABLE conflicts ALTER COLUMN detection_time SET STATISTICS 1000;
ALTER TABLE trains ALTER COLUMN current_section_id SET STATISTICS 1000;
ALTER TABLE sections ALTER COLUMN id SET STATISTICS 1000;

-- Enable parallel query execution for large datasets
ALTER TABLE positions SET (parallel_workers = 4);
ALTER TABLE trains SET (parallel_workers = 2);
ALTER TABLE conflicts SET (parallel_workers = 2);

-- Optimize autovacuum for high-frequency tables
ALTER TABLE positions SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

ALTER TABLE conflicts SET (
    autovacuum_vacuum_scale_factor = 0.2,
    autovacuum_analyze_scale_factor = 0.1
);