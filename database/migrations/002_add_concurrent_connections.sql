-- Migration: Add concurrent_connections field to download_tasks
-- Created: 2025-01-11
-- Description: Adds concurrent_connections field for specifying number of parallel download threads

-- Add concurrent_connections column
ALTER TABLE download_tasks 
ADD COLUMN IF NOT EXISTS concurrent_connections INTEGER DEFAULT 5;

-- Add comment
COMMENT ON COLUMN download_tasks.concurrent_connections IS 'Number of concurrent download connections/threads for this task';
