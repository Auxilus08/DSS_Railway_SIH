# Railway AI Database Testing Setup

This document explains how to set up and test the database with AI integration.

## Quick Start for Database Testing

### Option 1: Using Docker (Recommended)
```bash
# 1. Create .env file
cp .env.example .env

# 2. Start PostgreSQL with Docker
docker-compose up -d postgres

# 3. Wait for database to be ready (check health)
docker-compose ps

# 4. Run database migrations
cd backend
alembic upgrade head

# 5. Run AI database tests
python test_database_ai.py
```

### Option 2: Local PostgreSQL Setup
```bash
# 1. Install PostgreSQL locally
# 2. Create database: railway_db
# 3. Update .env with your credentials
# 4. Run migrations and tests as above
```

## Database Migration Commands

```bash
# Check current database version
alembic current

# Show migration history
alembic history

# Upgrade to latest (includes AI fields)
alembic upgrade head

# Downgrade if needed
alembic downgrade -1

# Show SQL that would be executed
alembic upgrade head --sql
```

## Testing AI Database Integration

```bash
# Run comprehensive AI database tests
python test_database_ai.py

# Test specific AI functionality
python -c "from test_ai_database_functions import test_conflict_ai_storage; test_conflict_ai_storage()"
```

## Database Schema Verification

```bash
# Connect to database and check AI fields
psql -h localhost -U postgres -d railway_db

# Check conflicts table AI fields
\d conflicts

# Check decisions table AI fields  
\d decisions

# Query AI data
SELECT id, ai_analyzed, ai_confidence, ai_solver_method FROM conflicts WHERE ai_analyzed = true;
```

## Environment Variables for Testing

Create `.env` file with these values for local testing:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=railway_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/railway_db
```