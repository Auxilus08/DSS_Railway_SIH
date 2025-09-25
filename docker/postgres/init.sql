-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Example table to validate extension works (optional)
CREATE TABLE IF NOT EXISTS sensor_readings (
    id SERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    value DOUBLE PRECISION NOT NULL
);

-- Create hypertable
SELECT create_hypertable('sensor_readings', 'ts', if_not_exists => TRUE);
