"""Initial railway traffic management schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    
    # Create enum types
    train_type_enum = postgresql.ENUM('express', 'local', 'freight', 'maintenance', name='train_type')
    conflict_severity_enum = postgresql.ENUM('low', 'medium', 'high', 'critical', name='conflict_severity')
    controller_auth_level_enum = postgresql.ENUM('operator', 'supervisor', 'manager', 'admin', name='controller_auth_level')
    decision_action_enum = postgresql.ENUM('reroute', 'delay', 'priority_change', 'emergency_stop', 'speed_limit', 'manual_override', name='decision_action')
    
    train_type_enum.create(op.get_bind())
    conflict_severity_enum.create(op.get_bind())
    controller_auth_level_enum.create(op.get_bind())
    decision_action_enum.create(op.get_bind())
    
    # Create controllers table
    op.create_table('controllers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('employee_id', sa.String(length=20), nullable=False),
        sa.Column('section_responsibility', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('auth_level', controller_auth_level_enum, nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("LENGTH(name) >= 2", name='controllers_name_check'),
        sa.CheckConstraint("LENGTH(employee_id) >= 3", name='controllers_employee_id_check'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id')
    )
    
    # Create sections table
    op.create_table('sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('section_code', sa.String(length=20), nullable=False),
        sa.Column('section_type', sa.String(length=20), nullable=False),
        sa.Column('length_meters', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_speed_kmh', sa.Integer(), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('junction_ids', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('coordinates', geoalchemy2.types.Geometry(geometry_type='LINESTRING', srid=4326), nullable=True),
        sa.Column('elevation_start', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('elevation_end', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('gradient', sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column('electrified', sa.Boolean(), nullable=False),
        sa.Column('signaling_system', sa.String(length=50), nullable=True),
        sa.Column('maintenance_window_start', sa.Time(), nullable=True),
        sa.Column('maintenance_window_end', sa.Time(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("LENGTH(name) >= 2", name='sections_name_check'),
        sa.CheckConstraint("LENGTH(section_code) >= 2", name='sections_code_check'),
        sa.CheckConstraint('length_meters > 0', name='sections_length_check'),
        sa.CheckConstraint('max_speed_kmh > 0 AND max_speed_kmh <= 300', name='sections_max_speed_check'),
        sa.CheckConstraint('capacity > 0', name='sections_capacity_check'),
        sa.CheckConstraint('gradient BETWEEN -10.0 AND 10.0', name='sections_gradient_check'),
        sa.CheckConstraint("section_type IN ('track', 'junction', 'station', 'yard')", name='sections_type_check'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('section_code')
    )
    
    # Create trains table
    op.create_table('trains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('train_number', sa.String(length=20), nullable=False),
        sa.Column('type', train_type_enum, nullable=False),
        sa.Column('current_section_id', sa.Integer(), nullable=True),
        sa.Column('speed_kmh', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('max_speed_kmh', sa.Integer(), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('current_load', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('destination_section_id', sa.Integer(), nullable=True),
        sa.Column('origin_section_id', sa.Integer(), nullable=True),
        sa.Column('scheduled_departure', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_arrival', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_departure', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_arrival', sa.DateTime(timezone=True), nullable=True),
        sa.Column('driver_id', sa.String(length=20), nullable=True),
        sa.Column('conductor_id', sa.String(length=20), nullable=True),
        sa.Column('length_meters', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('weight_tons', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('engine_power_kw', sa.Integer(), nullable=True),
        sa.Column('fuel_type', sa.String(length=20), nullable=True),
        sa.Column('operational_status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("LENGTH(train_number) >= 2", name='trains_number_check'),
        sa.CheckConstraint('speed_kmh >= 0', name='trains_speed_check'),
        sa.CheckConstraint('max_speed_kmh > 0 AND max_speed_kmh <= 300', name='trains_max_speed_check'),
        sa.CheckConstraint('capacity > 0', name='trains_capacity_check'),
        sa.CheckConstraint('current_load >= 0', name='trains_load_check'),
        sa.CheckConstraint('current_load <= capacity', name='trains_load_capacity_check'),
        sa.CheckConstraint('priority BETWEEN 1 AND 10', name='trains_priority_check'),
        sa.CheckConstraint('length_meters > 0', name='trains_length_check'),
        sa.CheckConstraint('weight_tons > 0', name='trains_weight_check'),
        sa.CheckConstraint("fuel_type IN ('diesel', 'electric', 'hybrid') OR fuel_type IS NULL", name='trains_fuel_check'),
        sa.CheckConstraint("operational_status IN ('active', 'maintenance', 'out_of_service', 'emergency')", name='trains_status_check'),
        sa.CheckConstraint("""
            scheduled_departure IS NULL OR scheduled_arrival IS NULL OR 
            scheduled_departure < scheduled_arrival
        """, name='trains_schedule_check'),
        sa.ForeignKeyConstraint(['current_section_id'], ['sections.id'], ),
        sa.ForeignKeyConstraint(['destination_section_id'], ['sections.id'], ),
        sa.ForeignKeyConstraint(['origin_section_id'], ['sections.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('train_number')
    )
    
    # Create positions table
    op.create_table('positions',
        sa.Column('train_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('coordinates', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('speed_kmh', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('direction', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('distance_from_start', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('signal_strength', sa.Integer(), nullable=True),
        sa.Column('gps_accuracy', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('altitude', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('speed_kmh >= 0', name='positions_speed_check'),
        sa.CheckConstraint('direction BETWEEN 0 AND 360 OR direction IS NULL', name='positions_direction_check'),
        sa.CheckConstraint('distance_from_start >= 0 OR distance_from_start IS NULL', name='positions_distance_check'),
        sa.CheckConstraint('signal_strength BETWEEN 0 AND 100 OR signal_strength IS NULL', name='positions_signal_check'),
        sa.CheckConstraint('coordinates IS NOT NULL OR section_id IS NOT NULL', name='positions_coordinates_check'),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ),
        sa.ForeignKeyConstraint(['train_id'], ['trains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('train_id', 'timestamp')
    )
    
    # Create conflicts table
    op.create_table('conflicts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conflict_type', sa.String(length=50), nullable=False),
        sa.Column('severity', conflict_severity_enum, nullable=False),
        sa.Column('trains_involved', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('sections_involved', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('detection_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolution_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_impact_minutes', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('auto_resolved', sa.Boolean(), nullable=False),
        sa.Column('resolved_by_controller_id', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('array_length(trains_involved, 1) >= 1', name='conflicts_trains_check'),
        sa.CheckConstraint('array_length(sections_involved, 1) >= 1', name='conflicts_sections_check'),
        sa.CheckConstraint("""
            conflict_type IN ('collision_risk', 'section_overload', 'speed_violation', 
                            'signal_violation', 'maintenance_conflict', 'priority_conflict', 'route_conflict')
        """, name='conflicts_type_check'),
        sa.CheckConstraint("""
            (resolution_time IS NULL AND resolved_by_controller_id IS NULL) OR
            (resolution_time IS NOT NULL AND resolution_time >= detection_time)
        """, name='conflicts_resolution_check'),
        sa.ForeignKeyConstraint(['resolved_by_controller_id'], ['controllers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create decisions table
    op.create_table('decisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('controller_id', sa.Integer(), nullable=False),
        sa.Column('conflict_id', sa.Integer(), nullable=True),
        sa.Column('train_id', sa.Integer(), nullable=True),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('action_taken', decision_action_enum, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('executed', sa.Boolean(), nullable=False),
        sa.Column('execution_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_result', sa.Text(), nullable=True),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('approval_required', sa.Boolean(), nullable=False),
        sa.Column('approved_by_controller_id', sa.Integer(), nullable=True),
        sa.Column('approval_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('LENGTH(rationale) >= 10', name='decisions_rationale_check'),
        sa.CheckConstraint("""
            (executed = false AND execution_time IS NULL) OR
            (executed = true AND execution_time IS NOT NULL AND execution_time >= timestamp)
        """, name='decisions_execution_check'),
        sa.CheckConstraint("""
            (approval_required = false) OR
            (approval_required = true AND approved_by_controller_id IS NOT NULL AND approval_time IS NOT NULL)
        """, name='decisions_approval_check'),
        sa.ForeignKeyConstraint(['approved_by_controller_id'], ['controllers.id'], ),
        sa.ForeignKeyConstraint(['conflict_id'], ['conflicts.id'], ),
        sa.ForeignKeyConstraint(['controller_id'], ['controllers.id'], ),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ),
        sa.ForeignKeyConstraint(['train_id'], ['trains.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create train_schedules table
    op.create_table('train_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('train_id', sa.Integer(), nullable=False),
        sa.Column('route_sections', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('scheduled_times', postgresql.ARRAY(sa.DateTime(timezone=True)), nullable=False),
        sa.Column('actual_times', postgresql.ARRAY(sa.DateTime(timezone=True)), nullable=True),
        sa.Column('delays_minutes', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("""
            array_length(route_sections, 1) = array_length(scheduled_times, 1)
        """, name='schedules_route_times_match'),
        sa.ForeignKeyConstraint(['train_id'], ['trains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create section_occupancy table
    op.create_table('section_occupancy',
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('train_id', sa.Integer(), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expected_exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('exit_time IS NULL OR exit_time > entry_time', name='occupancy_exit_check'),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ),
        sa.ForeignKeyConstraint(['train_id'], ['trains.id'], ),
        sa.PrimaryKeyConstraint('section_id', 'train_id', 'entry_time')
    )
    
    # Create maintenance_windows table
    op.create_table('maintenance_windows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('maintenance_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('affects_traffic', sa.Boolean(), nullable=False),
        sa.Column('created_by_controller_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('end_time > start_time', name='maintenance_time_check'),
        sa.ForeignKeyConstraint(['created_by_controller_id'], ['controllers.id'], ),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Convert positions table to TimescaleDB hypertable
    op.execute("SELECT create_hypertable('positions', 'timestamp', chunk_time_interval => INTERVAL '1 hour')")
    
    # Create triggers for updated_at timestamps
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)
    
    op.execute("CREATE TRIGGER update_controllers_updated_at BEFORE UPDATE ON controllers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()")
    op.execute("CREATE TRIGGER update_sections_updated_at BEFORE UPDATE ON sections FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()")
    op.execute("CREATE TRIGGER update_trains_updated_at BEFORE UPDATE ON trains FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()")
    op.execute("CREATE TRIGGER update_conflicts_updated_at BEFORE UPDATE ON conflicts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()")
    op.execute("CREATE TRIGGER update_train_schedules_updated_at BEFORE UPDATE ON train_schedules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()")


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_train_schedules_updated_at ON train_schedules")
    op.execute("DROP TRIGGER IF EXISTS update_conflicts_updated_at ON conflicts")
    op.execute("DROP TRIGGER IF EXISTS update_trains_updated_at ON trains")
    op.execute("DROP TRIGGER IF EXISTS update_sections_updated_at ON sections")
    op.execute("DROP TRIGGER IF EXISTS update_controllers_updated_at ON controllers")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop tables
    op.drop_table('maintenance_windows')
    op.drop_table('section_occupancy')
    op.drop_table('train_schedules')
    op.drop_table('decisions')
    op.drop_table('conflicts')
    op.drop_table('positions')
    op.drop_table('trains')
    op.drop_table('sections')
    op.drop_table('controllers')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS decision_action")
    op.execute("DROP TYPE IF EXISTS controller_auth_level")
    op.execute("DROP TYPE IF EXISTS conflict_severity")
    op.execute("DROP TYPE IF EXISTS train_type")