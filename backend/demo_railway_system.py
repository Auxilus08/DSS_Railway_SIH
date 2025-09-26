#!/usr/bin/env python3
"""
Railway Traffic Management System - Complete Demo
Demonstrates all key features and capabilities
"""

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from models import *
from db import get_session


def demo_railway_system():
    """Comprehensive demonstration of the railway system"""
    
    print("🚂 Railway Traffic Management System - Complete Demo")
    print("=" * 60)
    
    session = get_session()
    
    try:
        # Demo 1: Real-time Train Tracking
        print("\n1. 🎯 REAL-TIME TRAIN TRACKING")
        print("-" * 40)
        
        # Get all active trains with their latest positions
        active_trains = session.query(Train).filter(
            Train.operational_status == 'active'
        ).all()
        
        print(f"Monitoring {len(active_trains)} active trains:")
        
        for train in active_trains[:5]:  # Show first 5 trains
            # Get latest position
            latest_position = session.query(Position).filter(
                Position.train_id == train.id
            ).order_by(Position.timestamp.desc()).first()
            
            if latest_position:
                section = session.query(Section).filter(
                    Section.id == latest_position.section_id
                ).first()
                
                print(f"  🚄 {train.train_number} ({train.type.value.upper()})")
                print(f"     Location: {section.section_code} - {section.name}")
                print(f"     Speed: {latest_position.speed_kmh} km/h")
                print(f"     Last Update: {latest_position.timestamp.strftime('%H:%M:%S')}")
                print(f"     Priority: {train.priority}/10")
                print()
        
        # Demo 2: Conflict Detection and Resolution
        print("\n2. 🚨 CONFLICT DETECTION & RESOLUTION")
        print("-" * 40)
        
        conflicts = session.query(Conflict).order_by(
            Conflict.detection_time.desc()
        ).limit(3).all()
        
        print(f"Recent conflicts ({len(conflicts)} shown):")
        
        for conflict in conflicts:
            status = "✅ RESOLVED" if conflict.resolution_time else "⚠️ ACTIVE"
            severity_icon = {
                ConflictSeverity.CRITICAL: "🔴",
                ConflictSeverity.HIGH: "🟠", 
                ConflictSeverity.MEDIUM: "🟡",
                ConflictSeverity.LOW: "🟢"
            }.get(conflict.severity, "⚪")
            
            print(f"  {severity_icon} Conflict #{conflict.id} - {status}")
            print(f"     Type: {conflict.conflict_type.replace('_', ' ').title()}")
            print(f"     Severity: {conflict.severity.value.upper()}")
            print(f"     Trains Involved: {conflict.trains_involved}")
            print(f"     Detected: {conflict.detection_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if conflict.resolution_time:
                duration = (conflict.resolution_time - conflict.detection_time).total_seconds() / 60
                print(f"     Resolution Time: {duration:.1f} minutes")
                if conflict.resolution_notes:
                    print(f"     Resolution: {conflict.resolution_notes}")
            print()
        
        # Demo 3: Controller Decision Audit Trail
        print("\n3. 📋 CONTROLLER DECISION AUDIT TRAIL")
        print("-" * 40)
        
        recent_decisions = session.query(Decision).join(
            Controller, Decision.controller_id == Controller.id
        ).order_by(Decision.timestamp.desc()).limit(3).all()
        
        print(f"Recent controller decisions ({len(recent_decisions)} shown):")
        
        for decision in recent_decisions:
            controller = session.query(Controller).filter(
                Controller.id == decision.controller_id
            ).first()
            
            status_icon = "✅" if decision.executed else "⏳"
            print(f"  {status_icon} Decision #{decision.id}")
            print(f"     Controller: {controller.name} ({controller.auth_level.value.upper()})")
            print(f"     Action: {decision.action_taken.value.replace('_', ' ').title()}")
            print(f"     Timestamp: {decision.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Rationale: {decision.rationale}")
            
            if decision.parameters:
                print(f"     Parameters: {decision.parameters}")
            
            if decision.executed and decision.execution_result:
                print(f"     Result: {decision.execution_result}")
            print()
        
        # Demo 4: Network Utilization Analysis
        print("\n4. 📊 NETWORK UTILIZATION ANALYSIS")
        print("-" * 40)
        
        # Calculate section occupancy
        occupancy_data = session.query(
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
        ).order_by(func.count(SectionOccupancy.train_id).desc()).limit(8).all()
        
        print("Section utilization (top 8 by occupancy):")
        
        for occ in occupancy_data:
            utilization = (occ.current_trains / occ.capacity * 100) if occ.capacity > 0 else 0
            
            if utilization >= 100:
                status_icon = "🔴"
                status = "FULL"
            elif utilization >= 80:
                status_icon = "🟡"
                status = "HIGH"
            elif utilization > 0:
                status_icon = "🟢"
                status = "NORMAL"
            else:
                status_icon = "⚪"
                status = "EMPTY"
            
            print(f"  {status_icon} {occ.section_code} - {occ.name}")
            print(f"     Occupancy: {occ.current_trains}/{occ.capacity} trains ({utilization:.1f}%) - {status}")
        
        # Demo 5: Performance Metrics
        print("\n\n5. ⚡ PERFORMANCE METRICS")
        print("-" * 40)
        
        # Train type performance
        performance_data = session.query(
            Train.type,
            func.avg(Position.speed_kmh).label('avg_speed'),
            func.max(Position.speed_kmh).label('max_speed'),
            func.count(Position.train_id).label('data_points')
        ).join(
            Position, Train.id == Position.train_id
        ).filter(
            Position.timestamp >= datetime.now() - timedelta(hours=2)
        ).group_by(Train.type).all()
        
        print("Train performance by type (last 2 hours):")
        
        for perf in performance_data:
            type_icon = {
                TrainType.EXPRESS: "🚄",
                TrainType.LOCAL: "🚃",
                TrainType.FREIGHT: "🚛",
                TrainType.MAINTENANCE: "🔧"
            }.get(perf.type, "🚂")
            
            print(f"  {type_icon} {perf.type.value.upper()}")
            print(f"     Average Speed: {perf.avg_speed:.1f} km/h")
            print(f"     Maximum Speed: {perf.max_speed:.1f} km/h")
            print(f"     Data Points: {perf.data_points}")
        
        # Demo 6: Upcoming Maintenance
        print("\n\n6. 🔧 UPCOMING MAINTENANCE WINDOWS")
        print("-" * 40)
        
        upcoming_maintenance = session.query(
            MaintenanceWindow,
            Section.section_code,
            Section.name
        ).join(
            Section, MaintenanceWindow.section_id == Section.id
        ).filter(
            MaintenanceWindow.start_time >= datetime.now()
        ).order_by(MaintenanceWindow.start_time).limit(3).all()
        
        if upcoming_maintenance:
            print(f"Next {len(upcoming_maintenance)} maintenance windows:")
            
            for maint, section_code, section_name in upcoming_maintenance:
                duration = maint.end_time - maint.start_time
                hours = duration.total_seconds() / 3600
                
                impact_icon = "⚠️" if maint.affects_traffic else "✅"
                print(f"  🔧 {section_code} - {section_name}")
                print(f"     Type: {maint.maintenance_type.replace('_', ' ').title()}")
                print(f"     Start: {maint.start_time.strftime('%Y-%m-%d %H:%M')}")
                print(f"     Duration: {hours:.1f} hours")
                print(f"     Traffic Impact: {impact_icon}")
                if maint.description:
                    print(f"     Description: {maint.description}")
                print()
        else:
            print("  ✅ No upcoming maintenance windows scheduled")
        
        # Demo 7: System Health Summary
        print("\n7. 💚 SYSTEM HEALTH SUMMARY")
        print("-" * 40)
        
        # Collect system statistics
        total_trains = session.query(Train).filter(Train.operational_status == 'active').count()
        total_sections = session.query(Section).filter(Section.active == True).count()
        active_conflicts = session.query(Conflict).filter(Conflict.resolution_time.is_(None)).count()
        pending_decisions = session.query(Decision).filter(Decision.executed == False).count()
        occupied_sections = session.query(SectionOccupancy).filter(
            SectionOccupancy.exit_time.is_(None)
        ).count()
        
        network_utilization = (occupied_sections / total_sections * 100) if total_sections > 0 else 0
        
        # Calculate health score
        health_score = 100
        if active_conflicts > 0:
            health_score -= min(active_conflicts * 15, 40)
        if pending_decisions > 3:
            health_score -= min((pending_decisions - 3) * 8, 25)
        if network_utilization > 85:
            health_score -= 20
        
        health_status = (
            "🟢 EXCELLENT" if health_score >= 90 else
            "🟡 GOOD" if health_score >= 75 else
            "🟠 FAIR" if health_score >= 60 else
            "🔴 NEEDS ATTENTION"
        )
        
        print("Current system status:")
        print(f"  🚂 Active Trains: {total_trains}")
        print(f"  🛤️ Total Sections: {total_sections}")
        print(f"  📊 Network Utilization: {network_utilization:.1f}%")
        print(f"  ⚠️ Active Conflicts: {active_conflicts}")
        print(f"  ⏳ Pending Decisions: {pending_decisions}")
        print(f"  🏥 System Health: {health_status} ({health_score}/100)")
        
        # Demo 8: Sample API Endpoints
        print("\n\n8. 🌐 SAMPLE API INTEGRATION")
        print("-" * 40)
        
        print("Key API endpoints for integration:")
        print("  GET  /trains                    - List all trains")
        print("  GET  /trains/{id}/position      - Get train's current position")
        print("  GET  /conflicts/active          - Get active conflicts")
        print("  POST /decisions                 - Create controller decision")
        print("  GET  /sections/occupancy        - Get section occupancy data")
        print("  GET  /analytics/performance     - Get performance metrics")
        
        print("\nSample FastAPI integration:")
        print("""
@app.get("/trains/{train_id}/realtime")
def get_train_realtime(train_id: int, db: Session = Depends(get_session)):
    train = db.query(Train).filter(Train.id == train_id).first()
    position = db.query(Position).filter(
        Position.train_id == train_id
    ).order_by(Position.timestamp.desc()).first()
    
    return {
        "train": train,
        "current_position": position,
        "status": "active" if train.operational_status == "active" else "inactive"
    }
        """)
        
        print("\n" + "=" * 60)
        print("🎉 Railway Traffic Management System Demo Complete!")
        print("\nKey Features Demonstrated:")
        print("✅ Real-time train position tracking")
        print("✅ Conflict detection and resolution")
        print("✅ Controller decision audit trail")
        print("✅ Network utilization monitoring")
        print("✅ Performance analytics")
        print("✅ Maintenance scheduling")
        print("✅ System health monitoring")
        print("✅ API integration examples")
        
        print("\nNext Steps:")
        print("1. Start the FastAPI server: uvicorn app.main:app --reload")
        print("2. Access API docs: http://localhost:8000/docs")
        print("3. Run validation queries: python validation_queries.py")
        print("4. Monitor system: python demo_railway_system.py")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    demo_railway_system()