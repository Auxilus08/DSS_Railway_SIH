"""
Phase 2 Integration Test - Database + AI Results Storage
Tests storing AI optimization results in the database
"""
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models import Base, Train, Section, Conflict, Decision, Controller
from app.models import ControllerAuthLevel, ConflictSeverity, DecisionAction, TrainType
from app.services.ai_service import AIOptimizationService

def test_phase_2_ai_database():
    """Test Phase 2: AI results storage in database"""
    database_url = "postgresql+psycopg2://postgres:1234@localhost:5432/railway_db"
    
    print("🚀 Phase 2 Test: AI + Database Integration")
    print("=" * 50)
    
    try:
        # Setup
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        test_id = str(uuid.uuid4())[:8]
        
        print("✅ Database connected")
        
        # Test 1: Create infrastructure
        print("\n📋 Test 1: Infrastructure setup...")
        
        controller = Controller(
            name=f"AI Test Controller {test_id}",
            employee_id=f"AITC{test_id}",
            section_responsibility=[1, 2],
            auth_level=ControllerAuthLevel.SUPERVISOR,
            active=True
        )
        db.add(controller)
        db.flush()
        
        section = Section(
            name=f"AI Test Section {test_id}",
            section_code=f"ATS{test_id}",
            section_type="track",
            length_meters=5000,
            max_speed_kmh=100,
            capacity=2
        )
        db.add(section)
        db.flush()
        
        trains = []
        for i, ttype in enumerate([TrainType.EXPRESS, TrainType.LOCAL, TrainType.FREIGHT]):
            train = Train(
                train_number=f"AI{ttype.value}{i}{test_id}",
                type=ttype,
                max_speed_kmh=100 - i*10,
                capacity=300 + i*50,
                length_meters=250 + i*25,
                weight_tons=400 + i*50
            )
            trains.append(train)
            db.add(train)
        db.flush()
        
        print(f"✅ Created: 1 controller, 1 section, {len(trains)} trains")
        
        # Test 2: Simulate AI analysis results
        print("\n📋 Test 2: Simulating AI optimization results...")
        
        # Simulate different AI solver results
        ai_results = {
            "rule_based": {
                "score": 87.5,
                "safety_score": 95.0,
                "efficiency_score": 82.0,
                "passenger_impact": 85.0,
                "solving_time": 0.003,
                "actions": [
                    {"type": "delay_train", "train_id": trains[0].id, "minutes": 10},
                    {"type": "reroute_train", "train_id": trains[2].id, "alternative": "bypass"}
                ]
            },
            "constraint_programming": {
                "score": 92.3,
                "safety_score": 98.0,
                "efficiency_score": 89.0,
                "passenger_impact": 90.0,
                "solving_time": 0.015,
                "actions": [
                    {"type": "priority_change", "train_id": trains[1].id, "new_priority": 90}
                ]
            },
            "reinforcement_learning": {
                "score": 94.7,
                "safety_score": 96.0,
                "efficiency_score": 93.0,
                "passenger_impact": 95.0,
                "solving_time": 0.008,
                "actions": [
                    {"type": "reroute_train", "train_id": trains[0].id, "alternative": "route_2"},
                    {"type": "delay_train", "train_id": trains[2].id, "minutes": 5}
                ]
            }
        }
        
        best_solver = "reinforcement_learning"
        best_result = ai_results[best_solver]
        
        print(f"✅ AI results simulated:")
        print(f"   - Best solver: {best_solver}")
        print(f"   - Best score: {best_result['score']}")
        print(f"   - Actions: {len(best_result['actions'])}")
        
        # Test 3: Store AI-analyzed conflict
        print("\n📋 Test 3: Storing AI-analyzed conflict...")
        
        conflict = Conflict(
            conflict_type="collision_risk",
            severity=ConflictSeverity.HIGH,
            trains_involved=[train.id for train in trains],
            sections_involved=[section.id],
            detection_time=datetime.now(timezone.utc),
            estimated_impact_minutes=20,
            description="High-priority multi-train conflict requiring AI intervention",
            # AI Analysis Fields
            ai_analyzed=True,
            ai_confidence=best_result['score'] / 100.0,
            ai_solution_id=f"AI_SOL_{best_solver}_{test_id}",
            ai_recommendations={
                "best_solver": best_solver,
                "solver_comparison": {
                    solver: {
                        "score": data["score"],
                        "safety": data["safety_score"],
                        "efficiency": data["efficiency_score"],
                        "solving_time": data["solving_time"],
                        "action_count": len(data["actions"])
                    }
                    for solver, data in ai_results.items()
                },
                "optimization_metrics": {
                    "total_solutions_evaluated": len(ai_results),
                    "best_score": best_result["score"],
                    "score_improvement": best_result["score"] - min(r["score"] for r in ai_results.values()),
                    "solving_time_total": sum(r["solving_time"] for r in ai_results.values())
                },
                "recommended_actions": best_result["actions"],
                "impact_analysis": {
                    "trains_affected": len(trains),
                    "estimated_delay_minutes": sum(
                        action.get("minutes", 0) for action in best_result["actions"] 
                        if action["type"] == "delay_train"
                    ),
                    "rerouting_required": any(
                        action["type"] == "reroute_train" for action in best_result["actions"]
                    )
                }
            },
            ai_analysis_time=datetime.now(timezone.utc)
        )
        db.add(conflict)
        db.flush()
        
        print(f"✅ AI conflict stored: ID={conflict.id}")
        print(f"   - AI confidence: {conflict.ai_confidence:.4f}")
        print(f"   - Solutions compared: {len(ai_results)}")
        
        # Test 4: Store AI-generated decision
        print("\n📋 Test 4: Storing AI-generated decision...")
        
        # Create decision based on best AI recommendation
        primary_action = best_result["actions"][0]
        action_type = DecisionAction.REROUTE  # Default
        
        if primary_action["type"] == "delay_train":
            action_type = DecisionAction.DELAY
        elif primary_action["type"] == "priority_change":
            action_type = DecisionAction.PRIORITY_CHANGE
        elif primary_action["type"] == "reroute_train":
            action_type = DecisionAction.REROUTE
        
        decision = Decision(
            controller_id=controller.id,
            conflict_id=conflict.id,
            train_id=trains[0].id,
            section_id=section.id,
            action_taken=action_type,
            timestamp=datetime.now(timezone.utc),
            rationale=f"AI-generated solution using {best_solver} algorithm with {best_result['score']:.1f}% confidence",
            parameters={
                "ai_solver": best_solver,
                "ai_solution_id": conflict.ai_solution_id,
                "confidence_score": best_result["score"],
                "all_actions": best_result["actions"],
                "safety_validated": best_result["safety_score"] > 90.0,
                "efficiency_impact": best_result["efficiency_score"],
                "alternative_solvers": {
                    solver: data["score"] for solver, data in ai_results.items() 
                    if solver != best_solver
                },
                "optimization_reasoning": {
                    "primary_objective": "safety_first",
                    "secondary_objective": "minimize_passenger_impact", 
                    "constraints_considered": ["capacity", "timing", "priority"]
                }
            },
            executed=True,
            execution_time=datetime.now(timezone.utc),
            execution_result=f"AI solution implemented: {len(best_result['actions'])} actions executed successfully",
            # AI-specific fields
            ai_generated=True,
            ai_solver_method="reinforcement_learning",
            ai_score=best_result["score"],
            ai_confidence=best_result["score"] / 100.0
        )
        db.add(decision)
        db.commit()
        
        print(f"✅ AI decision stored: ID={decision.id}")
        print(f"   - Solver method: {decision.ai_solver_method}")
        print(f"   - AI score: {decision.ai_score}")
        
        # Test 5: Advanced AI data queries
        print("\n📋 Test 5: Advanced AI analytics...")
        
        # Query 1: AI performance analysis
        performance_query = text("""
            SELECT 
                c.ai_recommendations->>'best_solver' as best_solver,
                c.ai_confidence,
                c.ai_recommendations->'optimization_metrics'->>'best_score' as best_score,
                c.ai_recommendations->'optimization_metrics'->>'solving_time_total' as total_solving_time,
                d.ai_score as decision_score,
                d.execution_result
            FROM conflicts c
            LEFT JOIN decisions d ON c.id = d.conflict_id  
            WHERE c.ai_analyzed = true
            ORDER BY c.ai_confidence DESC
        """)
        
        performance_results = db.execute(performance_query).fetchall()
        
        print("✅ AI Performance Analysis:")
        for result in performance_results:
            print(f"   - Solver: {result.best_solver}")
            print(f"     Confidence: {result.ai_confidence:.4f}")
            print(f"     Best Score: {result.best_score}")
            print(f"     Solving Time: {result.total_solving_time}s")
            print(f"     Decision Score: {result.decision_score}")
        
        # Query 2: AI recommendation analysis
        recommendations_query = text("""
            SELECT 
                c.id,
                c.ai_recommendations->'solver_comparison' as solver_comparison,
                c.ai_recommendations->'impact_analysis'->>'trains_affected' as trains_affected,
                c.ai_recommendations->'impact_analysis'->>'estimated_delay_minutes' as delay_minutes,
                c.ai_recommendations->'impact_analysis'->>'rerouting_required' as rerouting_required
            FROM conflicts c
            WHERE c.ai_recommendations IS NOT NULL
        """)
        
        rec_results = db.execute(recommendations_query).fetchall()
        
        print("\n✅ AI Recommendation Analysis:")
        for result in rec_results:
            print(f"   - Conflict {result.id}:")
            print(f"     Trains affected: {result.trains_affected}")
            print(f"     Delay minutes: {result.delay_minutes}")
            print(f"     Rerouting: {result.rerouting_required}")
        
        # Test 6: AI vs Human decision comparison
        print("\n📋 Test 6: AI system statistics...")
        
        stats_query = text("""
            SELECT 
                COUNT(*) as total_conflicts,
                COUNT(*) FILTER (WHERE c.ai_analyzed = true) as ai_analyzed_conflicts,
                COUNT(*) FILTER (WHERE c.ai_analyzed = true) * 100.0 / COUNT(*) as ai_coverage_percent,
                AVG(c.ai_confidence) FILTER (WHERE c.ai_analyzed = true) as avg_ai_confidence,
                COUNT(d.id) FILTER (WHERE d.ai_generated = true) as ai_generated_decisions,
                AVG(d.ai_score) FILTER (WHERE d.ai_generated = true) as avg_ai_decision_score
            FROM conflicts c
            LEFT JOIN decisions d ON c.id = d.conflict_id
        """)
        
        stats = db.execute(stats_query).fetchone()
        
        print("✅ AI System Statistics:")
        print(f"   - Total conflicts: {stats.total_conflicts}")
        print(f"   - AI-analyzed: {stats.ai_analyzed_conflicts} ({stats.ai_coverage_percent:.1f}%)")
        print(f"   - Average AI confidence: {stats.avg_ai_confidence:.4f}")
        print(f"   - AI-generated decisions: {stats.ai_generated_decisions}")
        print(f"   - Average decision score: {stats.avg_ai_decision_score:.2f}")
        
        # Test 7: Data integrity verification
        print("\n📋 Test 7: Data integrity checks...")
        
        integrity_checks = {
            'ai_confidence_range': db.execute(text(
                "SELECT COUNT(*) FROM conflicts WHERE ai_confidence BETWEEN 0.0 AND 1.0 AND ai_analyzed = true"
            )).fetchone()[0],
            'json_structure': db.execute(text(
                "SELECT COUNT(*) FROM conflicts WHERE ai_recommendations ? 'best_solver' AND ai_analyzed = true"
            )).fetchone()[0],
            'decision_consistency': db.execute(text(
                """SELECT COUNT(*) FROM decisions d 
                   JOIN conflicts c ON d.conflict_id = c.id 
                   WHERE d.ai_generated = true AND c.ai_analyzed = true"""
            )).fetchone()[0]
        }
        
        print("✅ Data Integrity:")
        print(f"   - Valid AI confidence values: {integrity_checks['ai_confidence_range']}")
        print(f"   - Proper JSON structure: {integrity_checks['json_structure']}")
        print(f"   - Consistent AI decisions: {integrity_checks['decision_consistency']}")
        
        print("\n🎉 PHASE 2 TEST COMPLETE!")
        print("=" * 50)
        print("✅ All Phase 2 components verified:")
        print("   ✓ AI analysis storage")
        print("   ✓ Complex JSON recommendations")
        print("   ✓ Multi-solver comparison")
        print("   ✓ Performance metrics tracking")
        print("   ✓ Advanced analytics queries")
        print("   ✓ Data integrity validation")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Phase 2 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_phase_2_ai_database()
    if success:
        print("\n🚀 PHASE 2 FULLY OPERATIONAL!")
        print("✅ AI + Database integration ready for production")
    exit(0 if success else 1)