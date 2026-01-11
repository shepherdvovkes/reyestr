-- Migration: Add client_id to documents for client statistics
-- Created: 2025-01-11
-- Description: Adds client_id to documents table to track which client downloaded each document

-- Add client_id column to documents table
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES download_clients(id) ON DELETE SET NULL;

-- Add index for client_id
CREATE INDEX IF NOT EXISTS idx_documents_client_id ON documents(client_id);

-- Update client statistics view to include documents
CREATE OR REPLACE VIEW clients_statistics AS
SELECT 
    dc.id AS client_id,
    dc.client_name,
    dc.client_host,
    dc.status,
    dc.last_heartbeat,
    dc.total_tasks_completed,
    dc.total_documents_downloaded,
    COUNT(DISTINCT dt.id) AS total_tasks_assigned,
    COUNT(DISTINCT CASE WHEN dt.status = 'completed' THEN dt.id END) AS completed_tasks,
    COUNT(DISTINCT CASE WHEN dt.status = 'in_progress' THEN dt.id END) AS in_progress_tasks,
    COUNT(DISTINCT CASE WHEN dt.status = 'failed' THEN dt.id END) AS failed_tasks,
    COUNT(DISTINCT d.system_id) AS documents_registered,
    COUNT(DISTINCT CASE WHEN d.classification_date IS NOT NULL THEN d.system_id END) AS documents_classified,
    SUM(CASE WHEN dt.status = 'completed' THEN dt.documents_downloaded ELSE 0 END) AS total_docs_from_tasks,
    MIN(d.created_at) AS first_document_date,
    MAX(d.created_at) AS last_document_date,
    dc.created_at AS client_created_at,
    dc.updated_at AS client_updated_at
FROM download_clients dc
LEFT JOIN download_tasks dt ON dc.id = dt.client_id
LEFT JOIN documents d ON dc.id = d.client_id
GROUP BY dc.id, dc.client_name, dc.client_host, dc.status, dc.last_heartbeat,
         dc.total_tasks_completed, dc.total_documents_downloaded, dc.created_at, dc.updated_at;

-- Create view for documents by client
CREATE OR REPLACE VIEW documents_by_client AS
SELECT 
    dc.id AS client_id,
    dc.client_name,
    COUNT(DISTINCT d.system_id) AS document_count,
    COUNT(DISTINCT d.court_region) AS unique_regions,
    COUNT(DISTINCT d.instance_type) AS unique_instance_types,
    COUNT(DISTINCT d.case_type) AS unique_case_types,
    MIN(d.decision_date) AS earliest_document_date,
    MAX(d.decision_date) AS latest_document_date,
    COUNT(DISTINCT CASE WHEN d.classification_date IS NOT NULL THEN d.system_id END) AS classified_count
FROM download_clients dc
LEFT JOIN documents d ON dc.id = d.client_id
WHERE d.system_id IS NOT NULL
GROUP BY dc.id, dc.client_name;

-- Add comment
COMMENT ON COLUMN documents.client_id IS 'Client that downloaded/registered this document';
