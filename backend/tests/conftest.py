"""
Test Configuration and Setup
Handles test environment setup and configuration
"""
import os
import sys
from pathlib import Path

# Test configuration
TEST_CONFIG = {
    'database_url': 'postgresql+psycopg2://postgres:1234@localhost:5432/railway_db',
    'test_timeout': 300,  # 5 minutes
    'verbose': False,
    'cleanup_after_tests': True
}

def setup_test_environment():
    """Setup the test environment with proper paths and imports"""
    
    # Get project root directory
    current_file = Path(__file__)
    tests_dir = current_file.parent
    backend_dir = tests_dir.parent
    project_root = backend_dir.parent.parent
    
    # Add necessary paths to Python path
    paths_to_add = [
        str(backend_dir / "app"),  # For app modules
        str(project_root),         # For railway_optimization
        str(backend_dir),          # For backend modules
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # Set environment variables for tests
    os.environ.setdefault('PYTHONPATH', ':'.join(paths_to_add))
    os.environ.setdefault('DATABASE_URL', TEST_CONFIG['database_url'])
    os.environ.setdefault('POSTGRES_PASSWORD', '1234')
    
    return {
        'tests_dir': tests_dir,
        'backend_dir': backend_dir,
        'project_root': project_root,
        'paths_added': paths_to_add
    }

def get_test_database_url():
    """Get the test database URL"""
    return TEST_CONFIG['database_url']

def is_database_available():
    """Check if the test database is available"""
    try:
        from sqlalchemy import create_engine
        engine = create_engine(TEST_CONFIG['database_url'])
        with engine.connect():
            pass
        return True
    except Exception:
        return False

if __name__ == "__main__":
    # Test the setup
    print("🔧 Testing environment setup...")
    setup_info = setup_test_environment()
    
    print(f"✅ Tests directory: {setup_info['tests_dir']}")
    print(f"✅ Backend directory: {setup_info['backend_dir']}")
    print(f"✅ Project root: {setup_info['project_root']}")
    print(f"✅ Paths added: {len(setup_info['paths_added'])}")
    
    print(f"\n🗄️ Database availability: {'✅ Available' if is_database_available() else '❌ Not available'}")
    
    print("\n🎯 Test environment ready!")