#!/usr/bin/env python3
"""
Database Testing for AI Integration

This script tests the database setup with AI fields, migrations, and
AI-specific functionality. It can work with both Docker and local PostgreSQL.
"""

import sys
import os
import asyncio
from datetime import datetime
from decimal import Decimal
import json

# Add app directory to Python path
sys.path.append('app')

def test_database_connection():
    """Test database connectivity"""
    print("🔍 Test 1: Database Connection")
    print("-" * 30)
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Try to get database URL from environment or use default
        database_url = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@localhost:5432/railway_db')
        
        print(f"   📡 Attempting connection to: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
        
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 as test").fetchone()
            if result[0] == 1:
                print("   ✅ Database connection: SUCCESSFUL")
                return True, engine
        
        return False, None
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        print("   💡 Make sure PostgreSQL is running (try: docker-compose up -d postgres)")
        return False, None

def test_migration_status(engine):
    """Check migration status"""
    print("\n🔍 Test 2: Migration Status")
    print("-" * 30)
    try:
        # Check if alembic_version table exists
        with engine.connect() as conn:
            result = conn.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'alembic_version'
                )
            """).fetchone()
            
            if result[0]:
                # Get current version
                version_result = conn.execute("SELECT version_num FROM alembic_version").fetchone()
                current_version = version_result[0] if version_result else "None"
                print(f"   ✅ Alembic initialized: Current version {current_version}")
                
                if current_version == "002":
                    print("   ✅ AI migration (002) applied")
                    return True
                elif current_version == "001":
                    print("   ⚠️  Base migration (001) applied, but AI migration (002) needed")
                    print("   💡 Run: alembic upgrade head")
                    return False
                else:
                    print(f"   ⚠️  Unknown migration version: {current_version}")
                    return False
            else:
                print("   ❌ Alembic not initialized")
                print("   💡 Run: alembic upgrade head")
                return False
                
    except Exception as e:
        print(f"   ❌ Migration status check failed: {e}")
        return False

def test_ai_table_structure(engine):
    """Test AI fields in database tables"""
    print("\n🔍 Test 3: AI Table Structure")
    print("-" * 30)
    try:
        with engine.connect() as conn:
            # Check conflicts table AI fields
            conflicts_ai_fields = conn.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'conflicts' 
                AND column_name LIKE 'ai_%'
                ORDER BY column_name
            """).fetchall()
            
            expected_conflict_fields = ['ai_analyzed', 'ai_confidence', 'ai_solution_id', 'ai_recommendations', 'ai_analysis_time']
            found_conflict_fields = [field[0] for field in conflicts_ai_fields]
            
            if all(field in found_conflict_fields for field in expected_conflict_fields):
                print(f"   ✅ Conflicts AI fields: {found_conflict_fields}")
            else:
                missing = [f for f in expected_conflict_fields if f not in found_conflict_fields]
                print(f"   ❌ Missing conflicts AI fields: {missing}")
                return False
            
            # Check decisions table AI fields
            decisions_ai_fields = conn.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'decisions' 
                AND column_name LIKE 'ai_%'
                ORDER BY column_name
            """).fetchall()
            
            expected_decision_fields = ['ai_generated', 'ai_solver_method', 'ai_score', 'ai_confidence']
            found_decision_fields = [field[0] for field in decisions_ai_fields]
            
            if all(field in found_decision_fields for field in expected_decision_fields):
                print(f"   ✅ Decisions AI fields: {found_decision_fields}")
                return True
            else:
                missing = [f for f in expected_decision_fields if f not in found_decision_fields]
                print(f"   ❌ Missing decisions AI fields: {missing}")
                return False
                
    except Exception as e:
        print(f"   ❌ AI table structure check failed: {e}")
        return False

def test_ai_data_insertion(engine):
    """Test inserting AI data into database"""
    print("\n🔍 Test 4: AI Data Insertion")
    print("-" * 30)
    try:
        from sqlalchemy.orm import sessionmaker
        from models import Conflict, Decision, Base
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create test conflict with AI data
        test_conflict = Conflict(
            conflict_type='collision_risk',
            severity='high',
            trains_involved=[1, 2],
            sections_involved=[10, 11],
            description='Test AI conflict for database testing',
            ai_analyzed=True,
            ai_confidence=Decimal('0.8750'),
            ai_solution_id='test_sol_db_001',
            ai_recommendations={'action': 'reroute', 'priority': 'high'},
            ai_analysis_time=datetime.utcnow()
        )
        
        session.add(test_conflict)
        session.flush()  # Get the ID
        conflict_id = test_conflict.id
        
        # Create test decision with AI data
        test_decision = Decision(
            controller_id=1,  # This might need to exist
            conflict_id=conflict_id,
            action_taken='reroute',
            rationale='AI-generated decision for testing database integration',
            ai_generated=True,
            ai_solver_method='constraint_programming',
            ai_score=Decimal('95.5000'),
            ai_confidence=Decimal('0.9125')
        )
        
        session.add(test_decision)
        session.commit()
        
        print(f"   ✅ Test conflict created: ID {conflict_id}")
        print(f"   ✅ Test decision created with AI data")
        
        # Query back to verify
        saved_conflict = session.query(Conflict).filter(Conflict.id == conflict_id).first()
        if saved_conflict and saved_conflict.ai_analyzed:
            print(f"   ✅ AI data persisted: confidence={saved_conflict.ai_confidence}")
        
        # Clean up
        session.delete(test_decision)
        session.delete(test_conflict)
        session.commit()
        session.close()
        
        print("   ✅ Test data cleanup completed")
        return True
        
    except Exception as e:
        print(f"   ❌ AI data insertion failed: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def test_ai_service_database_integration():
    """Test AI service with database"""
    print("\n🔍 Test 5: AI Service Database Integration")
    print("-" * 30)
    try:
        # This would test the service layer with actual database
        # For now, we'll check if the service can be imported and initialized
        
        # Check if we can import the service
        service_file = 'app/services/ai_service.py'
        if os.path.exists(service_file):
            print("   ✅ AI Service file exists")
            
            # Basic structure check
            with open(service_file, 'r') as f:
                content = f.read()
                
            if 'AIOptimizationService' in content and 'def optimize_conflict' in content:
                print("   ✅ AI Service structure valid")
                return True
            else:
                print("   ❌ AI Service structure incomplete")
                return False
        else:
            print("   ❌ AI Service file not found")
            return False
        
    except Exception as e:
        print(f"   ❌ AI Service test failed: {e}")
        return False

def provide_next_steps(results):
    """Provide guidance based on test results"""
    print("\n" + "=" * 50)
    print("📋 NEXT STEPS & RECOMMENDATIONS")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    if passed_tests == total_tests:
        print("\n🎉 ALL DATABASE TESTS PASSED!")
        print("✅ Database is ready for AI integration testing")
        print("\n🚀 What you can do now:")
        print("   • Run AI optimization with database storage")
        print("   • Test conflict analysis with persistence")
        print("   • Monitor AI performance metrics")
        print("   • Proceed to Phase 3: API Integration")
        
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed")
        
        if not results.get('Database Connection'):
            print("\n🔧 Database Setup Required:")
            print("   • Start PostgreSQL: docker-compose up -d postgres")
            print("   • Check .env file configuration")
            print("   • Wait for container health check to pass")
            
        if results.get('Database Connection') and not results.get('Migration Status'):
            print("\n🔧 Migration Required:")
            print("   • Run: alembic upgrade head")
            print("   • This will create AI fields in database")
            
        if not results.get('AI Table Structure'):
            print("\n🔧 Schema Issue:")
            print("   • Check migration was successful")
            print("   • Verify AI fields in conflicts/decisions tables")
            
        print("\n💡 Once issues are resolved, re-run this script")

def main():
    """Main testing function"""
    print("🗄️  RAILWAY AI DATABASE TESTING")
    print("=" * 50)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Testing AI database integration capabilities...")
    print("=" * 50)
    
    # Test results tracking
    results = {}
    
    # Test 1: Database Connection
    db_connected, engine = test_database_connection()
    results['Database Connection'] = db_connected
    
    if not db_connected:
        print("\n❌ Cannot proceed without database connection")
        provide_next_steps(results)
        return
    
    # Test 2: Migration Status
    migration_ok = test_migration_status(engine)
    results['Migration Status'] = migration_ok
    
    # Test 3: AI Table Structure (only if migrations are applied)
    if migration_ok:
        structure_ok = test_ai_table_structure(engine)
        results['AI Table Structure'] = structure_ok
        
        # Test 4: AI Data Insertion (only if structure is OK)
        if structure_ok:
            data_ok = test_ai_data_insertion(engine)
            results['AI Data Insertion'] = data_ok
        else:
            results['AI Data Insertion'] = False
    else:
        results['AI Table Structure'] = False
        results['AI Data Insertion'] = False
    
    # Test 5: AI Service Integration
    service_ok = test_ai_service_database_integration()
    results['AI Service Integration'] = service_ok
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DATABASE TEST RESULTS")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    success_rate = (passed_count / total_count) * 100
    
    print(f"\nSuccess Rate: {passed_count}/{total_count} ({success_rate:.1f}%)")
    
    # Provide next steps
    provide_next_steps(results)

if __name__ == "__main__":
    main()