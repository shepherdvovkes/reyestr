-- Migration: Add table for tracking document download progress
-- Created: 2025-01-11
-- Description: Tracks individual document downloads to calculate speed and ETA

-- Table: document_download_progress
-- Tracks when each document download starts for speed/ETA calculation
CREATE TABLE IF NOT EXISTS document_download_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES download_tasks(id) ON DELETE CASCADE,
    document_id VARCHAR(50) NOT NULL,
    reg_number VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'in_progress', -- 'in_progress', 'completed', 'failed'
    client_id UUID REFERENCES download_clients(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT document_download_progress_status_check CHECK (status IN ('in_progress', 'completed', 'failed'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_document_download_progress_task ON document_download_progress(task_id);
CREATE INDEX IF NOT EXISTS idx_document_download_progress_document ON document_download_progress(document_id);
CREATE INDEX IF NOT EXISTS idx_document_download_progress_status ON document_download_progress(status);
CREATE INDEX IF NOT EXISTS idx_document_download_progress_started_at ON document_download_progress(started_at);
CREATE INDEX IF NOT EXISTS idx_document_download_progress_client ON document_download_progress(client_id);

-- Unique constraint to prevent duplicate entries for same task+document
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_download_progress_unique 
    ON document_download_progress(task_id, document_id);

-- Grant permissions
GRANT ALL PRIVILEGES ON document_download_progress TO reyestr_user;
