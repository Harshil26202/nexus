-- NEXUS database initialization
-- Creates extensions needed by the app

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- for fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";       -- for composite GIN indexes

-- Performance settings (applied per-session)
SET work_mem = '64MB';
