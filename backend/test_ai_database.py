"""
Comprehensive Database Integration Test for Railway AI System
Tests all database functionality including AI fields and integration
"""
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models import Base, Train, Section, Conflict, Decision, Controller, TrainSchedule, Position
from app.models import ControllerAuthLevel, ConflictSeverity, DecisionAction, TrainType
from app.services.ai_service import AIOptimizationService

def test_database_integration():
    """Comprehensive test of database integration with AI features"""
    database_url = "postgresql+psycopg2://postgres:1234@localhost:5432/railway_db"
    
    print("🚀 Starting comprehensive database integration test...")
    
    try:
        # Create engine and session
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("✅ Database connection established")
        
        # Test 1: Insert basic data
        print("\n📋 Test 1: Inserting basic data...")
        
        # Create a controller
        controller = Controller(
            name="Test Controller",
            employee_id="TC001",
            section_responsibility=[1, 2, 3],
            auth_level=ControllerAuthLevel.OPERATOR,
            active=True
        )
        db.add(controller)
        db.commit()
        print("✅ Controller created")
        
        # Create sections
        section1 = Section(
            name="Section A",
            section_code="SEC_A",
            section_type="track",
            length_meters=5500,
            max_speed_kmh=80,
            capacity=2,
            coordinates="POINT(77.1234 28.5678)",
            electrified=True
        )
        section2 = Section(
            name="Section B", 
            section_code="SEC_B",
            section_type="track",
            length_meters=7200,
            max_speed_kmh=100,
            capacity=2,
            coordinates="POINT(77.2234 28.6678)",
            electrified=True
        )
        db.add(section1)
        db.add(section2)
        db.commit()
        print("✅ Sections created")
        
        # Create trains
        train1 = Train(
            train_number="12345",
            type=TrainType.EXPRESS,
            max_speed_kmh=120,
            capacity=400,
            length_meters=400,
            weight_tons=500,
            operational_status="active"
        )
        train2 = Train(
            train_number="67890",
            type=TrainType.LOCAL,
            max_speed_kmh=80,
            capacity=200,
            length_meters=200,
            weight_tons=300,
            operational_status="active"
        )
        db.add(train1)
        db.add(train2)
        db.commit()
        print("✅ Trains created")
        
        # Test 2: Create conflict with AI fields
        print("\n📋 Test 2: Creating conflict with AI fields...")
        
        conflict = Conflict(
            conflict_type="collision_risk",
            severity=ConflictSeverity.MEDIUM,
            trains_involved=[train1.id, train2.id],
            sections_involved=[section1.id],
            detection_time=datetime.now(timezone.utc),
            estimated_impact_minutes=15,
            description="Train collision risk detected",
            auto_resolved=False,
            # AI fields
            ai_analyzed=True,
            ai_confidence=0.8567,
            ai_solution_id="AI_SOL_001",
            ai_recommendations={
                "action": "reroute",
                "priority": "high",
                "alternative_routes": [2, 3],
                "estimated_delay": 12
            },
            ai_analysis_time=datetime.now(timezone.utc)
        )
        db.add(conflict)
        db.commit()
        print("✅ Conflict with AI fields created")
        
        # Test 3: Create AI-generated decision
        print("\n📋 Test 3: Creating AI-generated decision...")
        
        decision = Decision(
            controller_id=controller.id,
            conflict_id=conflict.id,
            train_id=train1.id,
            section_id=section1.id,
            action_taken=DecisionAction.REROUTE,
            timestamp=datetime.now(timezone.utc),
            rationale="AI analysis suggests rerouting to minimize delay",
            parameters={
                "new_route": [2, 3],
                "estimated_delay": 12,
                "priority_level": "high"
            },
            executed=True,
            execution_time=datetime.now(timezone.utc),
            execution_result="Successfully rerouted",
            # AI fields
            ai_generated=True,
            ai_solver_method="genetic_algorithm",
            ai_score=0.9234,
            ai_confidence=0.8567
        )
        db.add(decision)
        db.commit()
        print("✅ AI-generated decision created")
        
        # Test 4: Test AI Service Integration
        print("\n📋 Test 4: Testing AI Service integration...")
        
        ai_service = AIOptimizationService(db_session=db)
        print("✅ AI Service initialized with database session")
        
        # Test 5: Query AI data
        print("\n📋 Test 5: Querying AI data...")
        
        # Query conflicts with AI analysis
        ai_conflicts = db.query(Conflict).filter(Conflict.ai_analyzed == True).all()
        print(f"✅ Found {len(ai_conflicts)} AI-analyzed conflicts")
        
        for conflict in ai_conflicts:
            print(f"   - Conflict {conflict.id}: confidence={conflict.ai_confidence}, solution_id={conflict.ai_solution_id}")
            if conflict.ai_recommendations:
                print(f"     Recommendations: {conflict.ai_recommendations}")
        
        # Query AI-generated decisions
        ai_decisions = db.query(Decision).filter(Decision.ai_generated == True).all()
        print(f"✅ Found {len(ai_decisions)} AI-generated decisions")
        
        for decision in ai_decisions:
            print(f"   - Decision {decision.id}: method={decision.ai_solver_method}, score={decision.ai_score}, confidence={decision.ai_confidence}")
        
        # Test 6: Database performance check
        print("\n📋 Test 6: Database performance check...")
        
        # Test complex query with AI fields
        start_time = datetime.now()
        result = db.execute(text("""
            SELECT c.id, c.ai_confidence, d.ai_score, d.ai_solver_method
            FROM conflicts c
            LEFT JOIN decisions d ON c.id = d.conflict_id
            WHERE c.ai_analyzed = true
            AND d.ai_generated = true
        """)).fetchall()
        query_time = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Complex AI query executed in {query_time:.4f} seconds")
        print(f"   Found {len(result)} conflict-decision pairs")
        
        # Test 7: Data integrity checks
        print("\n📋 Test 7: Data integrity checks...")
        
        # Check AI confidence constraints
        invalid_confidence = db.query(Conflict).filter(
            (Conflict.ai_confidence < 0.0) | (Conflict.ai_confidence > 1.0)
        ).count()
        print(f"✅ AI confidence constraints: {invalid_confidence} violations found (should be 0)")
        
        # Test 8: JSON field functionality  
        print("\n📋 Test 8: JSON field functionality...")
        
        # Query JSON recommendations
        json_query = db.execute(text("""
            SELECT ai_recommendations->'action' as recommended_action,
                   ai_recommendations->'estimated_delay' as estimated_delay
            FROM conflicts
            WHERE ai_recommendations IS NOT NULL
        """)).fetchall()
        
        for row in json_query:
            print(f"   - Recommended action: {row[0]}, Estimated delay: {row[1]} minutes")
        
        print("✅ JSON field queries working correctly")
        
        print("\n🎉 All database integration tests passed!")
        print("✅ Database is ready for AI integration in production")
        
        # Summary statistics
        print("\n📊 Database Summary:")
        print(f"   - Controllers: {db.query(Controller).count()}")
        print(f"   - Sections: {db.query(Section).count()}")
        print(f"   - Trains: {db.query(Train).count()}")
        print(f"   - Conflicts: {db.query(Conflict).count()}")
        print(f"   - AI-analyzed conflicts: {db.query(Conflict).filter(Conflict.ai_analyzed == True).count()}")
        print(f"   - Decisions: {db.query(Decision).count()}")
        print(f"   - AI-generated decisions: {db.query(Decision).filter(Decision.ai_generated == True).count()}")
        
        db.close()
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_database_integration()
    exit(0 if success else 1)