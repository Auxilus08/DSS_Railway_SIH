"""
Validation queries for Railway Traffic Management System
Demonstrates key functionality and performance
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import text, func, and_, or_
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from models import (
    Controller, Section, Train, Position, Conflict, Decision,
    TrainSchedule, SectionOccupancy, MaintenanceWindow,
    TrainType, ConflictSeverity
)
from db import get_engine


def run_validation_queries():
    """Run comprehensive validation queries to test the system"""
    
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🚂 Railway Traffic Management System - Validation Queries")
        print("=" * 60)
        
        # Query 1: Find all conflicts in the last hour
        print("\n1. 📊 CONFLICTS IN LAST HOUR")
        print("-" * 30)
        
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_conflicts = session.query(Conflict).filter(
            Conflict.detection_time >= one_hour_ago
        ).order_by(Conflict.detection_time.desc()).all()
        
        print(f"Found {len(recent_conflicts)} conflicts in the last hour:")
        for conflict in recent_conflicts:
            status = "RESOLVED" if conflict.resolution_time else "ACTIVE"
            print(f"  • ID: {conflict.id} | Type: {conflict.conflict_type} | "
                  f"Severity: {conflict.severity.value.upper()} | Status: {status}")
            print(f"    Trains: {conflict.trains_involved} | Sections: {conflict.sections_involved}")
            print(f"    Detected: {conflict.detection_time.strftime('%H:%M:%S')}")
            if conflict.resolution_time:
                duration = (conflict.resolution_time - conflict.detection_time).total_seconds() / 60
                print(f"    Resolved in: {duration:.1f} minutes")
            print()
        
        # Query 2: Get real-time train positions
        print("\n2. 🎯 REAL-TIME TRAIN POSITIONS")
        print("-" * 30)
        
        # Get latest position for each train
        latest_positions_subquery = session.query(
            Position.train_id,
            func.max(Position.timestamp).label('latest_timestamp')
        ).group_by(Position.train_id).subquery()
        
        current_positions = session.query(
            Train.train_number,
            Train.type,
            Section.name.label('section_name'),
            Section.section_code,
            Position.speed_kmh,
            Position.timestamp,
            Train.operational_status
        ).join(
            Position, Train.id == Position.train_id
        ).join(
            Section, Position.section_id == Section.id
        ).join(
            latest_positions_subquery,
            and_(
                Position.train_id == latest_positions_subquery.c.train_id,
                Position.timestamp == latest_positions_subquery.c.latest_timestamp
            )
        ).order_by(Train.train_number).all()
        
        print(f"Current positions for {len(current_positions)} trains:")
        for pos in current_positions:
            status_icon = "🟢" if pos.operational_status == "active" else "🟡"
            print(f"  {status_icon} {pos.train_number} ({pos.type.value.upper()}) | "
                  f"Section: {pos.section_code} ({pos.section_name})")
            print(f"    Speed: {pos.speed_kmh} km/h | Last update: {pos.timestamp.strftime('%H:%M:%S')}")
        
        # Query 3: Calculate section occupancy
        print("\n\n3. 📈 SECTION OCCUPANCY ANALYSIS")
        print("-" * 30)
        
        # Current occupancy
        current_occupancy = session.query(
            Section.section_code,
            Section.name,
            Section.capacity,
            func.count(SectionOccupancy.train_id).label('current_trains')
        ).outerjoin(
            SectionOccupancy,
            and_(
                Section.id == SectionOccupancy.section_id,
                SectionOccupancy.exit_time.is_(None)
            )
        ).group_by(
            Section.id, Section.section_code, Section.name, Section.capacity
        ).order_by(Section.section_code).all()
        
        print("Current section occupancy:")
        for occ in current_occupancy:
            utilization = (occ.current_trains / occ.capacity) * 100 if occ.capacity > 0 else 0
            status_icon = "🔴" if utilization >= 100 else "🟡" if utilization >= 80 else "🟢"
            print(f"  {status_icon} {occ.section_code} ({occ.name}): "
                  f"{occ.current_trains}/{occ.capacity} trains ({utilization:.1f}%)")
        
        # Query 4: Train performance metrics
        print("\n\n4. ⚡ TRAIN PERFORMANCE METRICS")
        print("-" * 30)
        
        # Average speed by train type
        avg_speeds = session.query(
            Train.type,
            func.avg(Position.speed_kmh).label('avg_speed'),
            func.max(Position.speed_kmh).label('max_speed'),
            func.count(Position.train_id).label('position_count')
        ).join(
            Position, Train.id == Position.train_id
        ).filter(
            Position.timestamp >= datetime.now() - timedelta(hours=1)
        ).group_by(Train.type).all()
        
        print("Average speeds by train type (last hour):")
        for speed_data in avg_speeds:
            print(f"  🚄 {speed_data.type.value.upper()}: "
                  f"Avg: {speed_data.avg_speed:.1f} km/h | "
                  f"Max: {speed_data.max_speed:.1f} km/h | "
                  f"Data points: {speed_data.position_count}")
        
        # Query 5: Controller workload analysis
        print("\n\n5. 👥 CONTROLLER WORKLOAD ANALYSIS")
        print("-" * 30)
        
        controller_stats = session.query(
            Controller.name,
            Controller.auth_level,
            func.count(Decision.id).label('decisions_made'),
            func.count(Conflict.id).label('conflicts_resolved')
        ).outerjoin(
            Decision, Controller.id == Decision.controller_id
        ).outerjoin(
            Conflict, Controller.id == Conflict.resolved_by_controller_id
        ).filter(
            Controller.active == True
        ).group_by(
            Controller.id, Controller.name, Controller.auth_level
        ).order_by(func.count(Decision.id).desc()).all()
        
        print("Controller activity summary:")
        for stats in controller_stats:
            print(f"  👤 {stats.name} ({stats.auth_level.value.upper()}): "
                  f"{stats.decisions_made} decisions | {stats.conflicts_resolved} conflicts resolved")
        
        # Query 6: Upcoming maintenance windows
        print("\n\n6. 🔧 UPCOMING MAINTENANCE WINDOWS")
        print("-" * 30)
        
        upcoming_maintenance = session.query(
            MaintenanceWindow,
            Section.section_code,
            Section.name,
            Controller.name.label('controller_name')
        ).join(
            Section, MaintenanceWindow.section_id == Section.id
        ).outerjoin(
            Controller, MaintenanceWindow.created_by_controller_id == Controller.id
        ).filter(
            MaintenanceWindow.start_time >= datetime.now()
        ).order_by(MaintenanceWindow.start_time).all()
        
        print(f"Found {len(upcoming_maintenance)} upcoming maintenance windows:")
        for maint, section_code, section_name, controller_name in upcoming_maintenance:
            duration = maint.end_time - maint.start_time
            hours = duration.total_seconds() / 3600
            traffic_impact = "⚠️ AFFECTS TRAFFIC" if maint.affects_traffic else "✅ No traffic impact"
            print(f"  🔧 {section_code} ({section_name})")
            print(f"    Type: {maint.maintenance_type} | Duration: {hours:.1f} hours")
            print(f"    Start: {maint.start_time.strftime('%Y-%m-%d %H:%M')} | {traffic_impact}")
            if controller_name:
                print(f"    Scheduled by: {controller_name}")
            print()
        
        # Query 7: Route efficiency analysis
        print("\n\n7. 🛤️ ROUTE EFFICIENCY ANALYSIS")
        print("-" * 30)
        
        # Analyze train schedules vs actual performance
        schedule_analysis = session.query(
            Train.train_number,
            Train.type,
            TrainSchedule.route_sections,
            TrainSchedule.scheduled_times,
            TrainSchedule.actual_times,
            TrainSchedule.delays_minutes
        ).join(
            TrainSchedule, Train.id == TrainSchedule.train_id
        ).filter(
            TrainSchedule.active == True
        ).all()
        
        print("Schedule performance analysis:")
        for analysis in schedule_analysis:
            if analysis.delays_minutes:
                avg_delay = sum(analysis.delays_minutes) / len(analysis.delays_minutes)
                max_delay = max(analysis.delays_minutes)
                print(f"  🚂 {analysis.train_number} ({analysis.type.value.upper()}): "
                      f"Avg delay: {avg_delay:.1f} min | Max delay: {max_delay} min")
            else:
                print(f"  🚂 {analysis.train_number} ({analysis.type.value.upper()}): On schedule")
        
        # Query 8: Safety metrics
        print("\n\n8. 🛡️ SAFETY METRICS")
        print("-" * 30)
        
        # Count conflicts by severity
        safety_stats = session.query(
            Conflict.severity,
            func.count(Conflict.id).label('count'),
            func.avg(
                func.extract('epoch', Conflict.resolution_time - Conflict.detection_time) / 60
            ).label('avg_resolution_minutes')
        ).filter(
            Conflict.detection_time >= datetime.now() - timedelta(days=1)
        ).group_by(Conflict.severity).all()
        
        print("Conflict statistics (last 24 hours):")
        total_conflicts = sum(stat.count for stat in safety_stats)
        for stat in safety_stats:
            percentage = (stat.count / total_conflicts * 100) if total_conflicts > 0 else 0
            resolution_time = f"{stat.avg_resolution_minutes:.1f} min" if stat.avg_resolution_minutes else "N/A"
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(stat.severity.value, "⚪")
            print(f"  {severity_icon} {stat.severity.value.upper()}: {stat.count} conflicts ({percentage:.1f}%) | "
                  f"Avg resolution: {resolution_time}")
        
        # Query 9: Network utilization heatmap data
        print("\n\n9. 🗺️ NETWORK UTILIZATION HEATMAP")
        print("-" * 30)
        
        utilization_data = session.query(
            Section.section_code,
            Section.name,
            Section.section_type,
            func.count(Position.train_id).label('train_passages'),
            func.avg(Position.speed_kmh).label('avg_speed')
        ).join(
            Position, Section.id == Position.section_id
        ).filter(
            Position.timestamp >= datetime.now() - timedelta(hours=2)
        ).group_by(
            Section.id, Section.section_code, Section.name, Section.section_type
        ).order_by(func.count(Position.train_id).desc()).limit(10).all()
        
        print("Top 10 most utilized sections (last 2 hours):")
        for i, util in enumerate(utilization_data, 1):
            type_icon = {"station": "🚉", "junction": "🔀", "track": "🛤️", "yard": "🏭"}.get(util.section_type, "📍")
            print(f"  {i:2d}. {type_icon} {util.section_code} ({util.name}): "
                  f"{util.train_passages} passages | Avg speed: {util.avg_speed:.1f} km/h")
        
        # Query 10: System health summary
        print("\n\n10. 💚 SYSTEM HEALTH SUMMARY")
        print("-" * 30)
        
        # Overall system statistics
        total_trains = session.query(Train).filter(Train.operational_status == 'active').count()
        total_sections = session.query(Section).filter(Section.active == True).count()
        active_conflicts = session.query(Conflict).filter(Conflict.resolution_time.is_(None)).count()
        pending_decisions = session.query(Decision).filter(Decision.executed == False).count()
        
        # Calculate system utilization
        occupied_sections = session.query(SectionOccupancy).filter(
            SectionOccupancy.exit_time.is_(None)
        ).count()
        
        utilization_percentage = (occupied_sections / total_sections * 100) if total_sections > 0 else 0
        
        print("System overview:")
        print(f"  🚂 Active trains: {total_trains}")
        print(f"  ����️ Total sections: {total_sections}")
        print(f"  📊 Network utilization: {utilization_percentage:.1f}%")
        print(f"  ⚠️ Active conflicts: {active_conflicts}")
        print(f"  ⏳ Pending decisions: {pending_decisions}")
        
        # System health indicator
        health_score = 100
        if active_conflicts > 0:
            health_score -= min(active_conflicts * 10, 30)
        if pending_decisions > 5:
            health_score -= min((pending_decisions - 5) * 5, 20)
        if utilization_percentage > 90:
            health_score -= 20
        
        health_status = "🟢 EXCELLENT" if health_score >= 90 else \
                        "🟡 GOOD" if health_score >= 70 else \
                        "🟠 FAIR" if health_score >= 50 else "🔴 POOR"
        
        print(f"  🏥 System health: {health_status} ({health_score}/100)")
        
        print("\n" + "=" * 60)
        print("✅ All validation queries completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running validation queries: {e}")
        raise
    finally:
        session.close()


def run_performance_tests():
    """Run performance tests on key queries"""
    
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\n🚀 PERFORMANCE TESTS")
        print("=" * 30)
        
        import time
        
        # Test 1: Real-time position query performance
        start_time = time.time()
        
        latest_positions = session.query(Position).filter(
            Position.timestamp >= datetime.now() - timedelta(minutes=5)
        ).count()
        
        query_time = (time.time() - start_time) * 1000
        print(f"Real-time positions query: {query_time:.2f}ms ({latest_positions} records)")
        
        # Test 2: Conflict detection query performance
        start_time = time.time()
        
        recent_conflicts = session.query(Conflict).filter(
            Conflict.detection_time >= datetime.now() - timedelta(hours=1)
        ).count()
        
        query_time = (time.time() - start_time) * 1000
        print(f"Recent conflicts query: {query_time:.2f}ms ({recent_conflicts} records)")
        
        # Test 3: Section occupancy calculation performance
        start_time = time.time()
        
        occupancy_count = session.query(SectionOccupancy).filter(
            SectionOccupancy.exit_time.is_(None)
        ).count()
        
        query_time = (time.time() - start_time) * 1000
        print(f"Section occupancy query: {query_time:.2f}ms ({occupancy_count} records)")
        
        print("✅ Performance tests completed!")
        
    except Exception as e:
        print(f"❌ Error running performance tests: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_validation_queries()
    run_performance_tests()