#!/usr/bin/env python3
"""
Railway Traffic Management System Database Setup Script
Comprehensive setup for production-ready railway database
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from db import get_engine, init_database
from models import Base


def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr.strip()}")
        return False


def setup_database():
    """Complete database setup process"""
    print("🚂 Railway Traffic Management System - Database Setup")
    print("=" * 60)
    
    # Step 1: Initialize Alembic if not already done
    alembic_dir = Path("alembic")
    if not alembic_dir.exists():
        print("\n📁 Initializing Alembic...")
        if not run_command("alembic init alembic", "Alembic initialization"):
            return False
    
    # Step 2: Initialize database with extensions
    print("\n🔧 Initializing database extensions...")
    try:
        init_database()
        print("✅ Database extensions initialized")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False
    
    # Step 3: Create database tables using Alembic
    print("\n📊 Creating database schema...")
    if not run_command("alembic upgrade head", "Database schema creation"):
        print("⚠️ Alembic migration failed, trying direct table creation...")
        try:
            engine = get_engine()
            Base.metadata.create_all(engine)
            print("✅ Tables created directly using SQLAlchemy")
        except Exception as e:
            print(f"❌ Direct table creation failed: {e}")
            return False
    
    # Step 4: Apply performance indexes
    print("\n⚡ Creating performance indexes...")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            with open("schema/02_create_indexes.sql", "r") as f:
                index_sql = f.read()
            
            # Split and execute each statement
            statements = [stmt.strip() for stmt in index_sql.split(';') if stmt.strip()]
            for stmt in statements:
                if stmt and not stmt.startswith('--'):
                    try:
                        conn.execute(stmt)
                    except Exception as e:
                        print(f"⚠️ Index creation warning: {e}")
            
            conn.commit()
        print("✅ Performance indexes created")
    except Exception as e:
        print(f"❌ Index creation failed: {e}")
        return False
    
    # Step 5: Load seed data
    print("\n🌱 Loading seed data...")
    try:
        from seed_data import create_seed_data
        create_seed_data()
        print("✅ Seed data loaded successfully")
    except Exception as e:
        print(f"❌ Seed data loading failed: {e}")
        return False
    
    # Step 6: Run validation queries
    print("\n🔍 Running validation queries...")
    try:
        from validation_queries import run_validation_queries
        run_validation_queries()
        print("✅ Validation queries completed")
    except Exception as e:
        print(f"❌ Validation queries failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Railway Traffic Management System setup completed successfully!")
    print("\nNext steps:")
    print("1. Start the FastAPI server: uvicorn app.main:app --reload")
    print("2. Access the API documentation at: http://localhost:8000/docs")
    print("3. Monitor the system using the validation queries")
    print("\nDatabase features enabled:")
    print("• TimescaleDB for high-performance time-series data")
    print("• PostGIS for geographic/spatial queries")
    print("• Comprehensive indexing for optimal performance")
    print("• Real-time conflict detection and resolution")
    print("• Audit trail for all controller decisions")
    
    return True


def cleanup_database():
    """Clean up database (for development/testing)"""
    print("🧹 Cleaning up database...")
    
    response = input("⚠️ This will delete all data. Are you sure? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cleanup cancelled")
        return
    
    try:
        engine = get_engine()
        Base.metadata.drop_all(engine)
        print("✅ All tables dropped")
        
        # Drop Alembic version table
        with engine.connect() as conn:
            conn.execute("DROP TABLE IF EXISTS alembic_version")
            conn.commit()
        
        print("✅ Database cleanup completed")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")


def check_requirements():
    """Check if all required packages are installed"""
    print("📋 Checking requirements...")
    
    required_packages = [
        'sqlalchemy', 'psycopg2-binary', 'alembic', 
        'geoalchemy2', 'fastapi', 'uvicorn'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All required packages are installed")
    return True


def main():
    """Main setup function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "cleanup":
            cleanup_database()
            return
        elif sys.argv[1] == "check":
            check_requirements()
            return
        elif sys.argv[1] == "help":
            print("Railway Traffic Management System Setup")
            print("Usage:")
            print("  python setup_railway_db.py        - Full setup")
            print("  python setup_railway_db.py check  - Check requirements")
            print("  python setup_railway_db.py cleanup - Clean database")
            print("  python setup_railway_db.py help   - Show this help")
            return
    
    # Check requirements first
    if not check_requirements():
        return
    
    # Run full setup
    setup_database()


if __name__ == "__main__":
    main()