-- Migration: Add tables for distributed download system
-- Created: 2025-01-11
-- Description: Adds tables for managing download clients and tasks

-- Table: download_clients
-- Tracks registered download clients
CREATE TABLE IF NOT EXISTS download_clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_name VARCHAR(200) NOT NULL,
    client_host VARCHAR(200),
    api_key VARCHAR(255) UNIQUE, -- For authentication
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'error'
    total_tasks_completed INTEGER DEFAULT 0,
    total_documents_downloaded INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: download_tasks
-- Manages download tasks assigned to clients
CREATE TABLE IF NOT EXISTS download_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES download_clients(id) ON DELETE SET NULL,
    search_params JSONB NOT NULL, -- Parameters for search (CourtRegion, INSType, etc.)
    start_page INTEGER NOT NULL,
    max_documents INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled'
    assigned_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    documents_downloaded INTEGER DEFAULT 0,
    documents_failed INTEGER DEFAULT 0,
    documents_skipped INTEGER DEFAULT 0,
    error_message TEXT,
    result_summary JSONB, -- Full result summary from downloader
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT download_tasks_status_check CHECK (status IN ('pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_download_tasks_status ON download_tasks(status, created_at);
CREATE INDEX IF NOT EXISTS idx_download_tasks_client ON download_tasks(client_id);
CREATE INDEX IF NOT EXISTS idx_download_tasks_search_params ON download_tasks USING GIN(search_params);
CREATE INDEX IF NOT EXISTS idx_download_clients_status ON download_clients(status);
CREATE INDEX IF NOT EXISTS idx_download_clients_api_key ON download_clients(api_key);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_download_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE FUNCTION update_download_clients_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers
CREATE TRIGGER update_download_tasks_updated_at 
    BEFORE UPDATE ON download_tasks 
    FOR EACH ROW EXECUTE FUNCTION update_download_tasks_updated_at();

CREATE TRIGGER update_download_clients_updated_at 
    BEFORE UPDATE ON download_clients 
    FOR EACH ROW EXECUTE FUNCTION update_download_clients_updated_at();

-- View: tasks_summary
-- Summary view for task statistics
CREATE OR REPLACE VIEW tasks_summary AS
SELECT 
    status,
    COUNT(*) AS total_tasks,
    COUNT(CASE WHEN client_id IS NOT NULL THEN 1 END) AS assigned_tasks,
    SUM(documents_downloaded) AS total_documents_downloaded,
    SUM(documents_failed) AS total_documents_failed,
    SUM(documents_skipped) AS total_documents_skipped,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) AS avg_duration_seconds
FROM download_tasks
GROUP BY status;

-- View: clients_summary
-- Summary view for client statistics
CREATE OR REPLACE VIEW clients_summary AS
SELECT 
    dc.id,
    dc.client_name,
    dc.client_host,
    dc.status,
    dc.last_heartbeat,
    dc.total_tasks_completed,
    dc.total_documents_downloaded,
    COUNT(dt.id) AS active_tasks,
    COUNT(CASE WHEN dt.status = 'in_progress' THEN 1 END) AS in_progress_tasks
FROM download_clients dc
LEFT JOIN download_tasks dt ON dc.id = dt.client_id AND dt.status IN ('assigned', 'in_progress')
GROUP BY dc.id, dc.client_name, dc.client_host, dc.status, dc.last_heartbeat, 
         dc.total_tasks_completed, dc.total_documents_downloaded;

-- Grant permissions
GRANT ALL PRIVILEGES ON download_clients TO reyestr_user;
GRANT ALL PRIVILEGES ON download_tasks TO reyestr_user;
GRANT ALL PRIVILEGES ON tasks_summary TO reyestr_user;
GRANT ALL PRIVILEGES ON clients_summary TO reyestr_user;
