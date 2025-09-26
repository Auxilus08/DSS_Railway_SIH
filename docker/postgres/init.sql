-- Railway Traffic Management System Database Initialization
-- This file will be executed when the PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create the railway database if it doesn't exist
-- Note: In Docker, the database is usually created via environment variables
-- This is here for completeness

-- Log successful initialization
SELECT 'Railway Traffic Management Database extensions initialized successfully' AS status;

-- The actual schema will be created by Alembic migrations
-- Run: python setup_railway_db.py after container startup
