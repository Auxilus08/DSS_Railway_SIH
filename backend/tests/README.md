# Railway Traffic Management System - Test Suite

This directory contains comprehensive tests for the Railway Traffic Management System with AI integration.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── run_tests.py               # Main test runner script
├── test_api.py                # Original API tests
├── ai/                        # AI and machine learning tests
│   ├── __init__.py
│   └── simple_ai_test.py     # Basic AI integration tests
├── database/                  # Database and persistence tests
│   ├── __init__.py
│   ├── create_tables.py      # Database schema creation utility
│   ├── test_ai_database.py   # AI database integration tests
│   ├── test_database_ai.py   # Alternative AI database tests
│   └── test_db.py           # Basic database connectivity tests
├── integration/               # System integration tests
│   ├── __init__.py
│   └── current_status_assessment.py  # System status assessment
└── phase2/                    # Phase 2 specific tests
    ├── __init__.py
    ├── test_phase2.py         # Basic Phase 2 tests
    ├── test_phase_2_api.py    # Phase 2 API integration tests
    ├── test_phase_2_complete.py      # Complete Phase 2 functionality tests
    ├── test_phase_2_final.py         # Final Phase 2 validation tests
    └── test_phase_2_integration.py   # Phase 2 system integration tests
```

## Test Categories

### 🤖 AI Tests (`tests/ai/`)
Tests for AI optimization algorithms and machine learning components:
- AI service initialization
- Algorithm performance validation
- Model training and inference

### 🗄️ Database Tests (`tests/database/`)
Tests for database connectivity, models, and data persistence:
- PostgreSQL connection validation
- Schema creation and migration
- AI data storage and retrieval
- JSON field functionality
- Performance testing

### 🔗 Integration Tests (`tests/integration/`)
Tests for system integration and end-to-end functionality:
- Component interaction validation
- System status assessment
- Cross-service communication

### 🚀 Phase 2 Tests (`tests/phase2/`)
Comprehensive tests for Phase 2 - AI Database Integration:
- Complete AI + Database integration
- Performance benchmarking
- Data consistency validation
- Production readiness assessment

## Running Tests

### Prerequisites
1. Ensure the database is running:
   ```bash
   docker-compose up postgres redis
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

### Using the Test Runner

#### Run All Tests
```bash
python tests/run_tests.py
```

#### Run Specific Category
```bash
python tests/run_tests.py ai          # AI tests only
python tests/run_tests.py database    # Database tests only
python tests/run_tests.py integration # Integration tests only
python tests/run_tests.py phase2      # Phase 2 tests only
python tests/run_tests.py api         # API tests only
```

#### Verbose Output
```bash
python tests/run_tests.py --verbose
python tests/run_tests.py phase2 -v
```

#### List Available Tests
```bash
python tests/run_tests.py --list
```

### Running Individual Tests

You can also run individual test files directly:

```bash
# Database tests
python tests/database/test_ai_database.py
python tests/database/create_tables.py

# AI tests
python tests/ai/simple_ai_test.py

# Phase 2 tests
python tests/phase2/test_phase_2_final.py
python tests/phase2/test_phase_2_complete.py

# Integration tests
python tests/integration/current_status_assessment.py
```

## Test Requirements

### Database Tests
- PostgreSQL database running on port 5432
- Database credentials: `postgres:1234@localhost:5432/railway_db`
- Required tables created (tests can create them automatically)

### AI Tests
- Python virtual environment with ML dependencies
- Access to railway optimization modules
- Sufficient memory for AI model operations

### Integration Tests
- All system components running
- Database connectivity
- AI service availability

## Test Data

Tests use isolated test data and UUIDs to avoid conflicts:
- Each test run creates unique identifiers
- Test data is cleaned up automatically
- No interference between parallel test runs

## Expected Test Results

### Phase 1 (Basic Railway Optimization)
- ✅ All optimization algorithms working
- ✅ Multiple solver methods (rule-based, constraint programming, RL)
- ✅ Performance benchmarks met

### Phase 2 (AI Database Integration)
- ✅ Database schema with AI enhancement fields
- ✅ AI analysis results stored persistently
- ✅ Complex JSON recommendations working
- ✅ Performance metrics tracking
- ✅ 100% data consistency

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart database
docker-compose restart postgres

# Check connection manually
python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql+psycopg2://postgres:1234@localhost:5432/railway_db'); print('✅ Connected' if engine.connect() else '❌ Failed')"
```

### Import Errors
```bash
# Ensure you're in the backend directory
cd backend/

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Install missing dependencies
pip install -r requirements.txt
```

### Memory Issues
```bash
# For large AI tests, ensure sufficient memory
# Reduce test parameters if needed
```

## Performance Benchmarks

Expected performance metrics:
- Database queries: < 0.01s for simple, < 0.1s for complex
- AI optimization: < 0.5s per conflict scenario
- Full test suite: < 5 minutes
- Phase 2 validation: 100% success rate

## Contributing

When adding new tests:
1. Place in appropriate category directory
2. Follow naming convention: `test_*.py`
3. Include proper docstrings and comments
4. Add error handling and cleanup
5. Update this README if needed

## Test Results Archive

Test results are logged to help track system health over time:
- Successful runs indicate system stability
- Performance regressions can be detected early
- Integration issues are caught before deployment