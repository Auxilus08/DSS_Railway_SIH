"""
Seed data for Railway Traffic Management System
Creates realistic network topology with 10 trains and 20 sections
"""

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from models import (
    Base, Controller, Section, Train, Position, Conflict, Decision,
    TrainSchedule, SectionOccupancy, MaintenanceWindow,
    TrainType, ConflictSeverity, ControllerAuthLevel, DecisionAction
)
from db import get_engine


def create_seed_data():
    """Create comprehensive seed data for the railway system"""
    
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("Creating seed data for Railway Traffic Management System...")
        
        # Check if data already exists
        existing_controllers = session.query(Controller).count()
        if existing_controllers > 0:
            print(f"⚠️ Found {existing_controllers} existing controllers, skipping seed data creation")
            print("Use 'python setup_railway_db.py cleanup' first if you want to recreate the data")
            return
        
        # Create Controllers
        controllers = [
            Controller(
                name="Alice Johnson",
                employee_id="CTR001",
                section_responsibility=[1, 2, 3, 4, 5],
                auth_level=ControllerAuthLevel.SUPERVISOR,
                active=True
            ),
            Controller(
                name="Bob Smith",
                employee_id="CTR002", 
                section_responsibility=[6, 7, 8, 9, 10],
                auth_level=ControllerAuthLevel.OPERATOR,
                active=True
            ),
            Controller(
                name="Carol Davis",
                employee_id="CTR003",
                section_responsibility=[11, 12, 13, 14, 15],
                auth_level=ControllerAuthLevel.MANAGER,
                active=True
            ),
            Controller(
                name="David Wilson",
                employee_id="CTR004",
                section_responsibility=[16, 17, 18, 19, 20],
                auth_level=ControllerAuthLevel.OPERATOR,
                active=True
            ),
            Controller(
                name="Eva Martinez",
                employee_id="CTR005",
                section_responsibility=[1, 5, 10, 15, 20],
                auth_level=ControllerAuthLevel.ADMIN,
                active=True
            )
        ]
        
        session.add_all(controllers)
        session.commit()
        print(f"Created {len(controllers)} controllers")
        
        # Create Sections - Realistic railway network topology
        sections = [
            # Main line sections
            Section(
                name="Central Station Platform 1",
                section_code="CS-P1",
                section_type="station",
                length_meters=Decimal("500.00"),
                max_speed_kmh=30,
                capacity=2,
                junction_ids=[2, 3],
                elevation_start=Decimal("100.50"),
                elevation_end=Decimal("100.50"),
                gradient=Decimal("0.000"),
                electrified=True,
                signaling_system="ETCS Level 2"
            ),
            Section(
                name="Central Junction North",
                section_code="CJ-N",
                section_type="junction",
                length_meters=Decimal("200.00"),
                max_speed_kmh=60,
                capacity=1,
                junction_ids=[1, 3, 4],
                elevation_start=Decimal("100.50"),
                elevation_end=Decimal("102.00"),
                gradient=Decimal("0.750"),
                electrified=True,
                signaling_system="ETCS Level 2"
            ),
            Section(
                name="Express Track Section A",
                section_code="EX-A",
                section_type="track",
                length_meters=Decimal("5000.00"),
                max_speed_kmh=160,
                capacity=1,
                junction_ids=[2, 4],
                elevation_start=Decimal("102.00"),
                elevation_end=Decimal("115.00"),
                gradient=Decimal("2.600"),
                electrified=True,
                signaling_system="ETCS Level 2"
            ),
            Section(
                name="North Junction",
                section_code="NJ-1",
                section_type="junction",
                length_meters=Decimal("300.00"),
                max_speed_kmh=80,
                capacity=1,
                junction_ids=[2, 3, 5, 6],
                elevation_start=Decimal("115.00"),
                elevation_end=Decimal("115.50"),
                gradient=Decimal("0.167"),
                electrified=True,
                signaling_system="ETCS Level 2"
            ),
            Section(
                name="Industrial Siding",
                section_code="IND-1",
                section_type="yard",
                length_meters=Decimal("1200.00"),
                max_speed_kmh=40,
                capacity=3,
                junction_ids=[4],
                elevation_start=Decimal("115.50"),
                elevation_end=Decimal("116.00"),
                gradient=Decimal("0.417"),
                electrified=False,
                signaling_system="Traditional"
            ),
            Section(
                name="Suburban Station East",
                section_code="SUB-E",
                section_type="station",
                length_meters=Decimal("400.00"),
                max_speed_kmh=50,
                capacity=2,
                junction_ids=[4, 7],
                elevation_start=Decimal("115.50"),
                elevation_end=Decimal("118.00"),
                gradient=Decimal("6.250"),
                electrified=True,
                signaling_system="ETCS Level 1"
            ),
            Section(
                name="Mountain Pass Track",
                section_code="MP-1",
                section_type="track",
                length_meters=Decimal("8000.00"),
                max_speed_kmh=100,
                capacity=1,
                junction_ids=[6, 8],
                elevation_start=Decimal("118.00"),
                elevation_end=Decimal("145.00"),
                gradient=Decimal("3.375"),
                electrified=True,
                signaling_system="ETCS Level 1"
            ),
            Section(
                name="Summit Junction",
                section_code="SUM-J",
                section_type="junction",
                length_meters=Decimal("250.00"),
                max_speed_kmh=70,
                capacity=1,
                junction_ids=[7, 9, 10],
                elevation_start=Decimal("145.00"),
                elevation_end=Decimal("145.50"),
                gradient=Decimal("2.000"),
                electrified=True,
                signaling_system="ETCS Level 1"
            ),
            Section(
                name="Freight Yard Alpha",
                section_code="FY-A",
                section_type="yard",
                length_meters=Decimal("2000.00"),
                max_speed_kmh=25,
                capacity=5,
                junction_ids=[8],
                elevation_start=Decimal("145.50"),
                elevation_end=Decimal("144.00"),
                gradient=Decimal("-0.750"),
                electrified=False,
                signaling_system="Traditional"
            ),
            Section(
                name="Downhill Express",
                section_code="DH-EX",
                section_type="track",
                length_meters=Decimal("6000.00"),
                max_speed_kmh=140,
                capacity=1,
                junction_ids=[8, 11],
                elevation_start=Decimal("145.50"),
                elevation_end=Decimal("125.00"),
                gradient=Decimal("-3.417"),
                electrified=True,
                signaling_system="ETCS Level 2"
            ),
            Section(
                name="Valley Junction",
                section_code="VJ-1",
                section_type="junction",
                length_meters=Decimal("180.00"),
                max_speed_kmh=90,
                capacity=1,
                junction_ids=[10, 12, 13],
                elevation_start=Decimal("125.00"),
                elevation_end=Decimal("124.50"),
                gradient=Decimal("-2.778"),
                electrified=True,
                signaling_system="ETCS Level 2"
            ),
            Section(
                name="Local Branch Line",
                section_code="LBL-1",
                section_type="track",
                length_meters=Decimal("3500.00"),
                max_speed_kmh=80,
                capacity=1,
                junction_ids=[11, 14],
                elevation_start=Decimal("124.50"),
                elevation_end=Decimal("110.00"),
                gradient=Decimal("-4.143"),
                electrified=True,
                signaling_system="ETCS Level 1"
            ),
            Section(
                name="Coastal Station",
                section_code="COAST-1",
                section_type="station",
                length_meters=Decimal("600.00"),
                max_speed_kmh=40,
                capacity=3,
                junction_ids=[11, 15],
                elevation_start=Decimal("124.50"),
                elevation_end=Decimal("95.00"),
                gradient=Decimal("-4.917"),
                electrified=True,
                signaling_system="ETCS Level 1"
            ),
            Section(
                name="Rural Station North",
                section_code="RUR-N",
                section_type="station",
                length_meters=Decimal("300.00"),
                max_speed_kmh=60,
                capacity=1,
                junction_ids=[12, 16],
                elevation_start=Decimal("110.00"),
                elevation_end=Decimal("108.50"),
                gradient=Decimal("-5.000"),
                electrified=True,
                signaling_system="Traditional"
            ),
            Section(
                name="Seaside Terminal",
                section_code="SEA-T",
                section_type="station",
                length_meters=Decimal("800.00"),
                max_speed_kmh=30,
                capacity=4,
                junction_ids=[13],
                elevation_start=Decimal("95.00"),
                elevation_end=Decimal("5.00"),
                gradient=Decimal("-10.000"),
                electrified=True,
                signaling_system="ETCS Level 1"
            ),
            Section(
                name="Country Track Section",
                section_code="CTR-1",
                section_type="track",
                length_meters=Decimal("4000.00"),
                max_speed_kmh=120,
                capacity=1,
                junction_ids=[14, 17],
                elevation_start=Decimal("108.50"),
                elevation_end=Decimal("125.00"),
                gradient=Decimal("4.125"),
                electrified=True,
                signaling_system="ETCS Level 1"
            ),
            Section(
                name="Highland Junction",
                section_code="HL-J",
                section_type="junction",
                length_meters=Decimal("220.00"),
                max_speed_kmh=75,
                capacity=1,
                junction_ids=[16, 18, 19],
                elevation_start=Decimal("125.00"),
                elevation_end=Decimal("126.00"),
                gradient=Decimal("4.545"),
                electrified=True,
                signaling_system="ETCS Level 1"
            ),
            Section(
                name="Maintenance Depot",
                section_code="MAINT-1",
                section_type="yard",
                length_meters=Decimal("1500.00"),
                max_speed_kmh=20,
                capacity=6,
                junction_ids=[17],
                elevation_start=Decimal("126.00"),
                elevation_end=Decimal("127.50"),
                gradient=Decimal("1.000"),
                electrified=True,
                signaling_system="Traditional",
                maintenance_window_start=datetime.strptime("02:00", "%H:%M").time(),
                maintenance_window_end=datetime.strptime("06:00", "%H:%M").time()
            ),
            Section(
                name="Express Terminal",
                section_code="EX-T",
                section_type="station",
                length_meters=Decimal("700.00"),
                max_speed_kmh=35,
                capacity=3,
                junction_ids=[17, 20],
                elevation_start=Decimal("126.00"),
                elevation_end=Decimal("130.00"),
                gradient=Decimal("5.714"),
                electrified=True,
                signaling_system="ETCS Level 2"
            ),
            Section(
                name="Loop Track Return",
                section_code="LOOP-1",
                section_type="track",
                length_meters=Decimal("3000.00"),
                max_speed_kmh=110,
                capacity=1,
                junction_ids=[19, 1],
                elevation_start=Decimal("130.00"),
                elevation_end=Decimal("100.50"),
                gradient=Decimal("-9.833"),
                electrified=True,
                signaling_system="ETCS Level 2"
            )
        ]
        
        session.add_all(sections)
        session.commit()
        print(f"Created {len(sections)} sections")
        
        # Create Trains with diverse characteristics
        trains = [
            Train(
                train_number="EX001",
                type=TrainType.EXPRESS,
                current_section_id=1,
                speed_kmh=Decimal("0.00"),
                max_speed_kmh=160,
                capacity=400,
                current_load=320,
                priority=1,
                destination_section_id=15,
                origin_section_id=1,
                scheduled_departure=datetime.now() + timedelta(minutes=15),
                scheduled_arrival=datetime.now() + timedelta(hours=2, minutes=30),
                driver_id="DRV001",
                conductor_id="CON001",
                length_meters=Decimal("200.00"),
                weight_tons=Decimal("180.50"),
                engine_power_kw=4000,
                fuel_type="electric",
                operational_status="active"
            ),
            Train(
                train_number="LC002",
                type=TrainType.LOCAL,
                current_section_id=6,
                speed_kmh=Decimal("45.00"),
                max_speed_kmh=100,
                capacity=200,
                current_load=85,
                priority=5,
                destination_section_id=14,
                origin_section_id=1,
                scheduled_departure=datetime.now() - timedelta(minutes=30),
                scheduled_arrival=datetime.now() + timedelta(hours=1, minutes=45),
                driver_id="DRV002",
                conductor_id="CON002",
                length_meters=Decimal("120.00"),
                weight_tons=Decimal("95.25"),
                engine_power_kw=2000,
                fuel_type="electric",
                operational_status="active"
            ),
            Train(
                train_number="FR003",
                type=TrainType.FREIGHT,
                current_section_id=9,
                speed_kmh=Decimal("25.00"),
                max_speed_kmh=80,
                capacity=2000,
                current_load=1850,
                priority=8,
                destination_section_id=5,
                origin_section_id=15,
                scheduled_departure=datetime.now() - timedelta(hours=2),
                scheduled_arrival=datetime.now() + timedelta(hours=3),
                driver_id="DRV003",
                length_meters=Decimal("450.00"),
                weight_tons=Decimal("2100.75"),
                engine_power_kw=6000,
                fuel_type="diesel",
                operational_status="active"
            ),
            Train(
                train_number="EX004",
                type=TrainType.EXPRESS,
                current_section_id=10,
                speed_kmh=Decimal("120.00"),
                max_speed_kmh=160,
                capacity=450,
                current_load=380,
                priority=2,
                destination_section_id=1,
                origin_section_id=19,
                scheduled_departure=datetime.now() - timedelta(hours=1),
                scheduled_arrival=datetime.now() + timedelta(minutes=45),
                driver_id="DRV004",
                conductor_id="CON004",
                length_meters=Decimal("220.00"),
                weight_tons=Decimal("195.00"),
                engine_power_kw=4500,
                fuel_type="electric",
                operational_status="active"
            ),
            Train(
                train_number="MNT005",
                type=TrainType.MAINTENANCE,
                current_section_id=18,
                speed_kmh=Decimal("0.00"),
                max_speed_kmh=60,
                capacity=50,
                current_load=12,
                priority=10,
                destination_section_id=7,
                origin_section_id=18,
                scheduled_departure=datetime.now() + timedelta(hours=1),
                scheduled_arrival=datetime.now() + timedelta(hours=4),
                driver_id="DRV005",
                length_meters=Decimal("80.00"),
                weight_tons=Decimal("65.50"),
                engine_power_kw=1000,
                fuel_type="diesel",
                operational_status="maintenance"
            ),
            Train(
                train_number="LC006",
                type=TrainType.LOCAL,
                current_section_id=12,
                speed_kmh=Decimal("60.00"),
                max_speed_kmh=100,
                capacity=180,
                current_load=95,
                priority=6,
                destination_section_id=1,
                origin_section_id=13,
                scheduled_departure=datetime.now() - timedelta(minutes=45),
                scheduled_arrival=datetime.now() + timedelta(minutes=30),
                driver_id="DRV006",
                conductor_id="CON006",
                length_meters=Decimal("110.00"),
                weight_tons=Decimal("88.75"),
                engine_power_kw=1800,
                fuel_type="electric",
                operational_status="active"
            ),
            Train(
                train_number="FR007",
                type=TrainType.FREIGHT,
                current_section_id=5,
                speed_kmh=Decimal("0.00"),
                max_speed_kmh=70,
                capacity=1500,
                current_load=1200,
                priority=9,
                destination_section_id=9,
                origin_section_id=1,
                scheduled_departure=datetime.now() + timedelta(minutes=30),
                scheduled_arrival=datetime.now() + timedelta(hours=4, minutes=15),
                driver_id="DRV007",
                length_meters=Decimal("380.00"),
                weight_tons=Decimal("1650.25"),
                engine_power_kw=5500,
                fuel_type="diesel",
                operational_status="active"
            ),
            Train(
                train_number="EX008",
                type=TrainType.EXPRESS,
                current_section_id=16,
                speed_kmh=Decimal("95.00"),
                max_speed_kmh=160,
                capacity=420,
                current_load=295,
                priority=3,
                destination_section_id=19,
                origin_section_id=14,
                scheduled_departure=datetime.now() - timedelta(minutes=20),
                scheduled_arrival=datetime.now() + timedelta(hours=1, minutes=10),
                driver_id="DRV008",
                conductor_id="CON008",
                length_meters=Decimal("210.00"),
                weight_tons=Decimal("185.50"),
                engine_power_kw=4200,
                fuel_type="electric",
                operational_status="active"
            ),
            Train(
                train_number="LC009",
                type=TrainType.LOCAL,
                current_section_id=3,
                speed_kmh=Decimal("80.00"),
                max_speed_kmh=100,
                capacity=160,
                current_load=125,
                priority=7,
                destination_section_id=6,
                origin_section_id=1,
                scheduled_departure=datetime.now() - timedelta(minutes=10),
                scheduled_arrival=datetime.now() + timedelta(minutes=50),
                driver_id="DRV009",
                conductor_id="CON009",
                length_meters=Decimal("100.00"),
                weight_tons=Decimal("82.00"),
                engine_power_kw=1600,
                fuel_type="electric",
                operational_status="active"
            ),
            Train(
                train_number="FR010",
                type=TrainType.FREIGHT,
                current_section_id=11,
                speed_kmh=Decimal("40.00"),
                max_speed_kmh=75,
                capacity=1800,
                current_load=1650,
                priority=8,
                destination_section_id=18,
                origin_section_id=13,
                scheduled_departure=datetime.now() - timedelta(hours=1, minutes=30),
                scheduled_arrival=datetime.now() + timedelta(hours=2, minutes=45),
                driver_id="DRV010",
                length_meters=Decimal("420.00"),
                weight_tons=Decimal("1950.00"),
                engine_power_kw=5800,
                fuel_type="diesel",
                operational_status="active"
            )
        ]
        
        session.add_all(trains)
        session.commit()
        print(f"Created {len(trains)} trains")
        
        # Create recent position data for all trains
        positions = []
        base_time = datetime.now()
        
        for i, train in enumerate(trains):
            # Create position history for the last hour
            for j in range(12):  # Every 5 minutes for the last hour
                timestamp = base_time - timedelta(minutes=j*5)
                position = Position(
                    train_id=train.id,
                    section_id=train.current_section_id,
                    timestamp=timestamp,
                    speed_kmh=train.speed_kmh + Decimal(str(j * 2.5)),  # Varying speed
                    direction=Decimal(str((i * 45 + j * 5) % 360)),  # Varying direction
                    distance_from_start=Decimal(str(j * 100 + i * 50)),
                    signal_strength=95 - j,
                    gps_accuracy=Decimal("2.5"),
                    altitude=Decimal(str(100 + i * 10 + j))
                )
                positions.append(position)
        
        session.add_all(positions)
        session.commit()
        print(f"Created {len(positions)} position records")
        
        # Create some conflicts
        conflicts = [
            Conflict(
                conflict_type="collision_risk",
                severity=ConflictSeverity.HIGH,
                trains_involved=[1, 2],
                sections_involved=[1, 2],
                detection_time=datetime.now() - timedelta(minutes=30),
                estimated_impact_minutes=15,
                description="Two trains approaching same junction from different directions",
                auto_resolved=False,
                resolved_by_controller_id=1,
                resolution_time=datetime.now() - timedelta(minutes=25),
                resolution_notes="Delayed train EX001 by 5 minutes to allow LC002 to clear junction"
            ),
            Conflict(
                conflict_type="speed_violation",
                severity=ConflictSeverity.MEDIUM,
                trains_involved=[4],
                sections_involved=[10],
                detection_time=datetime.now() - timedelta(minutes=15),
                estimated_impact_minutes=5,
                description="Train EX004 exceeded speed limit in section DH-EX",
                auto_resolved=True,
                resolution_time=datetime.now() - timedelta(minutes=12),
                resolution_notes="Automatic speed reduction applied"
            ),
            Conflict(
                conflict_type="section_overload",
                severity=ConflictSeverity.LOW,
                trains_involved=[7, 3],
                sections_involved=[5],
                detection_time=datetime.now() - timedelta(minutes=5),
                description="Multiple freight trains in industrial siding approaching capacity",
                auto_resolved=False
            )
        ]
        
        session.add_all(conflicts)
        session.commit()
        print(f"Created {len(conflicts)} conflicts")
        
        # Create controller decisions
        decisions = [
            Decision(
                controller_id=1,
                conflict_id=1,
                train_id=1,
                action_taken=DecisionAction.DELAY,
                timestamp=datetime.now() - timedelta(minutes=25),
                rationale="Delayed express train to prevent collision at junction",
                parameters={"delay_minutes": 5, "priority_maintained": True},
                executed=True,
                execution_time=datetime.now() - timedelta(minutes=24),
                execution_result="Successfully delayed train EX001 by 5 minutes"
            ),
            Decision(
                controller_id=2,
                conflict_id=2,
                train_id=4,
                action_taken=DecisionAction.SPEED_LIMIT,
                timestamp=datetime.now() - timedelta(minutes=12),
                rationale="Applied speed restriction due to excessive speed",
                parameters={"new_speed_limit": 100, "section_id": 10},
                executed=True,
                execution_time=datetime.now() - timedelta(minutes=12),
                execution_result="Speed limit applied automatically"
            ),
            Decision(
                controller_id=3,
                train_id=5,
                action_taken=DecisionAction.REROUTE,
                timestamp=datetime.now() - timedelta(minutes=10),
                rationale="Rerouting maintenance train to avoid passenger traffic",
                parameters={"new_route": [18, 17, 16, 12, 7], "estimated_delay": 20},
                executed=False,
                approval_required=True
            )
        ]
        
        session.add_all(decisions)
        session.commit()
        print(f"Created {len(decisions)} decisions")
        
        # Create train schedules
        schedules = [
            TrainSchedule(
                train_id=1,
                route_sections=[1, 2, 3, 4, 6, 7, 8, 10, 11, 13, 15],
                scheduled_times=[
                    datetime.now() + timedelta(minutes=15),
                    datetime.now() + timedelta(minutes=20),
                    datetime.now() + timedelta(minutes=35),
                    datetime.now() + timedelta(minutes=45),
                    datetime.now() + timedelta(hours=1, minutes=10),
                    datetime.now() + timedelta(hours=1, minutes=25),
                    datetime.now() + timedelta(hours=1, minutes=40),
                    datetime.now() + timedelta(hours=2),
                    datetime.now() + timedelta(hours=2, minutes=10),
                    datetime.now() + timedelta(hours=2, minutes=20),
                    datetime.now() + timedelta(hours=2, minutes=30)
                ],
                active=True
            ),
            TrainSchedule(
                train_id=2,
                route_sections=[6, 7, 8, 11, 12, 14],
                scheduled_times=[
                    datetime.now() - timedelta(minutes=30),
                    datetime.now() - timedelta(minutes=15),
                    datetime.now(),
                    datetime.now() + timedelta(minutes=30),
                    datetime.now() + timedelta(hours=1),
                    datetime.now() + timedelta(hours=1, minutes=45)
                ],
                actual_times=[
                    datetime.now() - timedelta(minutes=30),
                    datetime.now() - timedelta(minutes=12),
                    datetime.now() + timedelta(minutes=3)
                ],
                delays_minutes=[0, 3, 3],
                active=True
            )
        ]
        
        session.add_all(schedules)
        session.commit()
        print(f"Created {len(schedules)} train schedules")
        
        # Create section occupancy records
        occupancy_records = [
            SectionOccupancy(
                section_id=1,
                train_id=1,
                entry_time=datetime.now() - timedelta(minutes=45),
                exit_time=datetime.now() - timedelta(minutes=40),
                expected_exit_time=datetime.now() - timedelta(minutes=42)
            ),
            SectionOccupancy(
                section_id=6,
                train_id=2,
                entry_time=datetime.now() - timedelta(minutes=20),
                expected_exit_time=datetime.now() + timedelta(minutes=10)
            ),
            SectionOccupancy(
                section_id=9,
                train_id=3,
                entry_time=datetime.now() - timedelta(minutes=35),
                expected_exit_time=datetime.now() + timedelta(minutes=25)
            )
        ]
        
        session.add_all(occupancy_records)
        session.commit()
        print(f"Created {len(occupancy_records)} occupancy records")
        
        # Create maintenance windows
        maintenance_windows = [
            MaintenanceWindow(
                section_id=18,
                start_time=datetime.now() + timedelta(hours=2),
                end_time=datetime.now() + timedelta(hours=6),
                maintenance_type="track_inspection",
                description="Routine track inspection and minor repairs",
                affects_traffic=True,
                created_by_controller_id=3
            ),
            MaintenanceWindow(
                section_id=7,
                start_time=datetime.now() + timedelta(days=1, hours=1),
                end_time=datetime.now() + timedelta(days=1, hours=5),
                maintenance_type="signal_upgrade",
                description="Upgrading signaling system to ETCS Level 2",
                affects_traffic=True,
                created_by_controller_id=5
            )
        ]
        
        session.add_all(maintenance_windows)
        session.commit()
        print(f"Created {len(maintenance_windows)} maintenance windows")
        
        print("\n✅ Seed data creation completed successfully!")
        print(f"Database populated with:")
        print(f"  - {len(controllers)} Controllers")
        print(f"  - {len(sections)} Sections")
        print(f"  - {len(trains)} Trains")
        print(f"  - {len(positions)} Position records")
        print(f"  - {len(conflicts)} Conflicts")
        print(f"  - {len(decisions)} Decisions")
        print(f"  - {len(schedules)} Train schedules")
        print(f"  - {len(occupancy_records)} Occupancy records")
        print(f"  - {len(maintenance_windows)} Maintenance windows")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating seed data: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_seed_data()