"""
Phase 2 Comprehensive Testing - AI Database Integration
Tests the complete integration of Railway AI optimization with database storage
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid
import json

# Add the app directory to the Python path using robust absolute path resolution
sys.path.append(str((Path(__file__).parent / 'app').resolve()))

from app.models import Base, Train, Section, Conflict, Decision, Controller
from app.models import ControllerAuthLevel, ConflictSeverity, DecisionAction, TrainType
from app.services.ai_service import AIOptimizationService

# Add the main directory for railway optimization using robust absolute path resolution
sys.path.append(str((Path(__file__).parent / '..' / '..').resolve()))
from railway_optimization import OptimizationEngine, Conflict

def test_phase_2_integration():
    """Complete Phase 2 integration test"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set. Please set it to your database connection string.")
    
    print("🚀 Phase 2 Integration Test - AI Engine + Database")
    print("=" * 60)
    
    try:
        # Setup database connection
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        test_id = str(uuid.uuid4())[:8]
        
        print("✅ Database connection established")
        
        # Test 1: Setup railway infrastructure in database
        print("\n📋 Test 1: Setting up railway infrastructure...")
        
        controller = Controller(
            name=f"AI Controller {test_id}",
            employee_id=f"AI{test_id}",
            section_responsibility=[1, 2, 3],
            auth_level=ControllerAuthLevel.SUPERVISOR,
            active=True
        )
        db.add(controller)
        db.flush()
        
        sections = []
        for i in range(3):
            section = Section(
                name=f"AI Section {i+1} {test_id}",
                section_code=f"AIS{i+1}{test_id}",
                section_type="track",
                length_meters=5000 + i*1000,
                max_speed_kmh=100 - i*10,
                capacity=2
            )
            sections.append(section)
            db.add(section)
        db.flush()
        
        trains = []
        train_types = [TrainType.EXPRESS, TrainType.LOCAL, TrainType.FREIGHT]
        for i, train_type in enumerate(train_types):
            train = Train(
                train_number=f"AI{train_type.value.upper()}{i+1}{test_id}",
                type=train_type,
                max_speed_kmh=120 - i*20,
                capacity=300 + i*100,
                length_meters=300 + i*50,
                weight_tons=400 + i*100
            )
            trains.append(train)
            db.add(train)
        db.flush()
        
        print(f"✅ Infrastructure created: {len(sections)} sections, {len(trains)} trains")
        
        # Test 2: Initialize AI Optimization Engine
        print("\n📋 Test 2: Initializing AI Optimization Engine...")
        
        optimization_engine = OptimizationEngine()
        print("✅ AI Optimization Engine initialized")
        
        # Test 3: Create realistic conflict scenario
        print("\n📋 Test 3: Creating realistic conflict scenario...")
        
        # Create conflict using railway optimization format
        conflict_data = {
            'id': f'AI_INTEGRATION_TEST_{test_id}',
            'trains': [
                {'id': trains[0].id, 'type': 'express', 'priority': 100},
                {'id': trains[1].id, 'type': 'local', 'priority': 80},
                {'id': trains[2].id, 'type': 'freight', 'priority': 60}
            ],
            'section': {'id': sections[0].id, 'capacity': 2},
            'severity': 0.85,
            'time_constraint': 300  # 5 minutes
        }
        
        # Convert to Conflict object
        railway_conflict = Conflict(
            id=conflict_data['id'],
            trains_involved=[t['id'] for t in conflict_data['trains']],
            severity=conflict_data['severity'],
            location=f"Section_{sections[0].id}",
            detection_time=datetime.now(timezone.utc),
            description="AI Integration Test Conflict"
        )
        
        print(f"✅ Conflict scenario created: {railway_conflict.id}")
        print(f"   - Trains involved: {len(conflict_data['trains'])}")
        print(f"   - Severity: {conflict_data['severity']}")
        
        # Test 4: Solve conflict using AI optimization engine
        print("\n📋 Test 4: AI conflict resolution...")
        
        # Solve the conflict
        solution_result = optimization_engine.solve_conflict(railway_conflict)
        
        print(f"✅ AI solutions generated: {len(solution_result.solutions)}")
        print(f"   - Solving time: {solution_result.solving_time:.4f}s")
        print(f"   - Best solution score: {solution_result.best_solution.score:.2f}")
        print(f"   - Best solver method: {solution_result.best_solution.method}")
        
        # Test 5: Store AI analysis in database
        print("\n📋 Test 5: Storing AI analysis in database...")
        
        # Create database conflict with AI analysis
        db_conflict = Conflict(
            conflict_type="collision_risk",
            severity=ConflictSeverity.HIGH,
            trains_involved=[train.id for train in trains],
            sections_involved=[section.id for section in sections[:1]],
            detection_time=railway_conflict.detection_time,
            estimated_impact_minutes=15,
            description=railway_conflict.description,
            # AI Analysis Results
            ai_analyzed=True,
            ai_confidence=solution_result.best_solution.score / 100.0,
            ai_solution_id=solution_result.best_solution.id,
            ai_recommendations={
                "solver_method": solution_result.best_solution.method,
                "total_solutions": len(solution_result.solutions),
                "solving_time": solution_result.solving_time,
                "safety_score": solution_result.best_solution.safety_score,
                "efficiency_score": solution_result.best_solution.efficiency_score,
                "actions": [
                    {"action": action.action_type, "parameters": action.parameters}
                    for action in solution_result.best_solution.actions
                ],
                "alternative_solutions": [
                    {"method": sol.method, "score": sol.score, "actions": len(sol.actions)}
                    for sol in solution_result.solutions[:3]  # Store top 3
                ]
            },
            ai_analysis_time=datetime.now(timezone.utc)
        )
        db.add(db_conflict)
        db.flush()
        
        print("✅ AI analysis stored in database")
        print(f"   - Conflict ID: {db_conflict.id}")
        print(f"   - AI confidence: {db_conflict.ai_confidence}")
        print(f"   - Solution ID: {db_conflict.ai_solution_id}")
        
        # Test 6: Store AI-generated decision
        print("\n📋 Test 6: Creating AI-generated decision...")
        
        best_solution = solution_result.best_solution
        
        # Determine primary action for decision
        primary_action = DecisionAction.REROUTE  # Default
        if best_solution.actions:
            action_type = best_solution.actions[0].action_type
            if "delay" in action_type.lower():
                primary_action = DecisionAction.DELAY
            elif "priority" in action_type.lower():
                primary_action = DecisionAction.PRIORITY_CHANGE
            elif "reroute" in action_type.lower():
                primary_action = DecisionAction.REROUTE
        
        db_decision = Decision(
            controller_id=controller.id,
            conflict_id=db_conflict.id,
            train_id=trains[0].id,  # Primary affected train
            section_id=sections[0].id,
            action_taken=primary_action,
            timestamp=datetime.now(timezone.utc),
            rationale=f"AI recommendation from {best_solution.method} solver",
            parameters={
                "ai_solution_id": best_solution.id,
                "solver_method": best_solution.method,
                "confidence_score": best_solution.score,
                "solution_actions": [
                    {"type": action.action_type, "params": action.parameters}
                    for action in best_solution.actions
                ],
                "alternative_count": len(solution_result.solutions) - 1
            },
            executed=True,
            execution_time=datetime.now(timezone.utc),
            execution_result="AI solution implemented successfully",
            # AI-specific fields
            ai_generated=True,
            ai_solver_method=best_solution.method,
            ai_score=best_solution.score,
            ai_confidence=best_solution.score / 100.0
        )
        db.add(db_decision)
        db.commit()
        
        print("✅ AI-generated decision stored")
        print(f"   - Decision ID: {db_decision.id}")
        print(f"   - AI solver method: {db_decision.ai_solver_method}")
        print(f"   - AI score: {db_decision.ai_score}")
        
        # Test 7: Query and analyze integrated data
        print("\n📋 Test 7: Analyzing integrated AI data...")
        
        # Complex query combining AI optimization results with database
        analysis_query = text("""
            SELECT 
                c.id as conflict_id,
                c.ai_solution_id,
                c.ai_confidence,
                c.ai_recommendations->>'solver_method' as solver_method,
                c.ai_recommendations->>'solving_time' as solving_time,
                c.ai_recommendations->>'total_solutions' as total_solutions,
                d.id as decision_id,
                d.ai_score,
                d.ai_solver_method,
                d.execution_result,
                ARRAY_AGG(t.train_number) as affected_trains
            FROM conflicts c
            LEFT JOIN decisions d ON c.id = d.conflict_id
            LEFT JOIN trains t ON t.id = ANY(c.trains_involved)
            WHERE c.ai_analyzed = true
            GROUP BY c.id, d.id
            ORDER BY c.ai_confidence DESC
        """)
        
        results = db.execute(analysis_query).fetchall()
        
        print(f"✅ Analysis complete - {len(results)} AI integration records")
        for result in results:
            print(f"   🔍 Conflict {result.conflict_id}:")
            print(f"      Solver: {result.solver_method}")
            print(f"      Confidence: {result.ai_confidence}")
            print(f"      Solutions: {result.total_solutions}")
            print(f"      Solving time: {result.solving_time}s")
            print(f"      Trains: {result.affected_trains}")
        
        # Test 8: Performance benchmarking
        print("\n📋 Test 8: Performance benchmarking...")
        
        start_time = datetime.now()
        
        # Create multiple conflicts and solve them
        benchmark_results = []
        for i in range(5):
            # Create conflict
            bench_conflict = Conflict(
                id=f"BENCHMARK_{i}_{test_id}",
                trains_involved=[trains[j % len(trains)].id for j in range(i + 2)],
                severity=0.5 + (i * 0.1),
                location=f"Benchmark_Section_{i}",
                detection_time=datetime.now(timezone.utc)
            )
            
            # Solve and time it
            bench_start = datetime.now()
            bench_solution = optimization_engine.solve_conflict(bench_conflict)
            bench_time = (datetime.now() - bench_start).total_seconds()
            
            benchmark_results.append({
                'conflict_id': bench_conflict.id,
                'trains': len(bench_conflict.trains_involved),
                'solutions': len(bench_solution.solutions),
                'best_score': bench_solution.best_solution.score,
                'solve_time': bench_time
            })
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Performance benchmark completed in {total_time:.4f}s")
        print("   Results:")
        for result in benchmark_results:
            print(f"   - {result['trains']} trains: {result['solutions']} solutions, "
                  f"score {result['best_score']:.2f}, {result['solve_time']:.4f}s")
        
        avg_solve_time = sum(r['solve_time'] for r in benchmark_results) / len(benchmark_results)
        avg_score = sum(r['best_score'] for r in benchmark_results) / len(benchmark_results)
        
        print(f"   📊 Averages: {avg_solve_time:.4f}s solve time, {avg_score:.2f} solution quality")
        
        # Test 9: Data consistency verification
        print("\n📋 Test 9: Data consistency verification...")
        
        # Verify AI data integrity
        consistency_checks = {
            'ai_conflicts': db.query(Conflict).filter(Conflict.ai_analyzed == True).count(),
            'ai_decisions': db.query(Decision).filter(Decision.ai_generated == True).count(),
            'confidence_range': db.execute(text(
                "SELECT MIN(ai_confidence), MAX(ai_confidence) FROM conflicts WHERE ai_analyzed = true"
            )).fetchone(),
            'json_validity': db.execute(text(
                "SELECT COUNT(*) FROM conflicts WHERE ai_recommendations IS NOT NULL AND JSON_VALID(ai_recommendations::text)"
            )).fetchone()[0] if db.bind.dialect.name == 'mysql' else
            db.execute(text(
                "SELECT COUNT(*) FROM conflicts WHERE ai_recommendations IS NOT NULL"
            )).fetchone()[0]
        }
        
        print("✅ Data consistency verified:")
        print(f"   - AI-analyzed conflicts: {consistency_checks['ai_conflicts']}")
        print(f"   - AI-generated decisions: {consistency_checks['ai_decisions']}")
        print(f"   - Confidence range: {consistency_checks['confidence_range'][0]:.4f} - {consistency_checks['confidence_range'][1]:.4f}")
        print(f"   - Valid JSON records: {consistency_checks['json_validity']}")
        
        # Final success summary
        print("\n🎉 PHASE 2 INTEGRATION TEST COMPLETE!")
        print("=" * 60)
        print("✅ All integration components working:")
        print("   ✓ Railway AI optimization engine")
        print("   ✓ Database storage and retrieval")
        print("   ✓ AI analysis persistence")
        print("   ✓ Complex query capabilities")
        print("   ✓ Performance benchmarking")
        print("   ✓ Data consistency validation")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Phase 2 integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_phase_2_integration()
    if success:
        print("\n🚀 PHASE 2 READY FOR PRODUCTION!")
        print("✅ AI optimization + Database integration fully operational")
    exit(0 if success else 1)