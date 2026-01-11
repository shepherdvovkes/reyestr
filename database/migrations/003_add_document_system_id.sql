-- Migration: Add system ID and classification fields to documents
-- Created: 2025-01-11
-- Description: Adds system UUID ID, classification fields, and improves document tracking

-- Add system_id column (UUID) for internal system identification
-- Keep existing id (VARCHAR) as external/registry ID
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS system_id UUID DEFAULT uuid_generate_v4();

-- Make system_id unique
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_system_id ON documents(system_id);

-- Add classification fields from search parameters
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS court_region VARCHAR(10),  -- Court region ID (e.g., '11', '14')
ADD COLUMN IF NOT EXISTS instance_type VARCHAR(10), -- Instance type: '1'=Перша, '2'=Апеляційна, '3'=Касаційна
ADD COLUMN IF NOT EXISTS classification_date TIMESTAMP WITH TIME ZONE, -- When document was classified
ADD COLUMN IF NOT EXISTS classification_source VARCHAR(50); -- Source of classification (e.g., 'search_params', 'extracted')

-- Add task reference to track which task downloaded this document
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS download_task_id UUID REFERENCES download_tasks(id) ON DELETE SET NULL;

-- Add indexes for new fields
CREATE INDEX IF NOT EXISTS idx_documents_court_region ON documents(court_region);
CREATE INDEX IF NOT EXISTS idx_documents_instance_type ON documents(instance_type);
CREATE INDEX IF NOT EXISTS idx_documents_download_task ON documents(download_task_id);
CREATE INDEX IF NOT EXISTS idx_documents_classification_date ON documents(classification_date);

-- Update existing documents to have system_id (if NULL)
UPDATE documents 
SET system_id = uuid_generate_v4() 
WHERE system_id IS NULL;

-- Create view for document classification summary
CREATE OR REPLACE VIEW documents_classification_summary AS
SELECT 
    court_region,
    instance_type,
    COUNT(*) AS document_count,
    COUNT(DISTINCT court_name) AS unique_courts,
    COUNT(DISTINCT judge_name) AS unique_judges,
    COUNT(DISTINCT case_type) AS unique_case_types,
    MIN(decision_date) AS earliest_date,
    MAX(decision_date) AS latest_date
FROM documents
WHERE court_region IS NOT NULL OR instance_type IS NOT NULL
GROUP BY court_region, instance_type
ORDER BY document_count DESC;

-- Create view for documents with full classification
CREATE OR REPLACE VIEW documents_classified AS
SELECT 
    d.system_id,
    d.id AS external_id,
    d.reg_number,
    d.court_region,
    d.instance_type,
    d.court_name,
    d.judge_name,
    d.case_type,
    d.decision_type,
    d.decision_date,
    d.law_date,
    d.case_number,
    d.classification_date,
    d.classification_source,
    d.download_task_id,
    d.created_at,
    d.updated_at
FROM documents d
WHERE d.system_id IS NOT NULL;

-- Add comment to system_id
COMMENT ON COLUMN documents.system_id IS 'Internal system UUID for document identification';
COMMENT ON COLUMN documents.court_region IS 'Court region ID from search parameters (e.g., 11=Київська область)';
COMMENT ON COLUMN documents.instance_type IS 'Court instance type: 1=Перша інстанція, 2=Апеляційна, 3=Касаційна';
COMMENT ON COLUMN documents.classification_date IS 'Timestamp when document was classified';
COMMENT ON COLUMN documents.classification_source IS 'Source of classification data';
COMMENT ON COLUMN documents.download_task_id IS 'Reference to download task that downloaded this document';
