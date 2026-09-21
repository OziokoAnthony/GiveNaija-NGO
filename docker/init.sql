-- Initialize databases for development and testing
CREATE DATABASE givenaija_test;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE givenaija TO postgres;
GRANT ALL PRIVILEGES ON DATABASE givenaija_test TO postgres;

-- Create dedicated app user to demonstrate database-level append-only permissions
CREATE USER givenaija_app WITH PASSWORD 'apppassword';
GRANT CONNECT ON DATABASE givenaija TO givenaija_app;
GRANT USAGE ON SCHEMA public TO givenaija_app;
