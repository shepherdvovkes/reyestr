-- PostgreSQL Database Schema for Court Documents Registry
-- Database: reyestr_db

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: search_sessions
-- Stores information about each search/extraction session
CREATE TABLE IF NOT EXISTS search_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    search_date DATE NOT NULL,
    total_extracted INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: documents
-- Stores individual court documents extracted from search results
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(50) PRIMARY KEY,
    search_session_id UUID REFERENCES search_sessions(id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    reg_number VARCHAR(100) NOT NULL,
    decision_type VARCHAR(200),
    decision_date DATE,
    law_date DATE,
    case_type VARCHAR(200),
    case_number VARCHAR(200),
    court_name TEXT,
    judge_name VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for common queries
    CONSTRAINT documents_reg_number_unique UNIQUE (reg_number)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_search_session ON documents(search_session_id);
CREATE INDEX IF NOT EXISTS idx_documents_decision_date ON documents(decision_date);
CREATE INDEX IF NOT EXISTS idx_documents_law_date ON documents(law_date);
CREATE INDEX IF NOT EXISTS idx_documents_case_type ON documents(case_type);
CREATE INDEX IF NOT EXISTS idx_documents_court_name ON documents(court_name);
CREATE INDEX IF NOT EXISTS idx_documents_judge_name ON documents(judge_name);
CREATE INDEX IF NOT EXISTS idx_documents_decision_type ON documents(decision_type);
CREATE INDEX IF NOT EXISTS idx_documents_case_number ON documents(case_number);

-- Table: document_content
-- Stores downloaded document content (HTML, text, etc.)
CREATE TABLE IF NOT EXISTS document_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id VARCHAR(50) REFERENCES documents(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL, -- 'html', 'print_html', 'text', 'pdf'
    file_path TEXT,
    content_text TEXT,
    file_size_bytes BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT document_content_type_check CHECK (content_type IN ('html', 'print_html', 'text', 'pdf'))
);

CREATE INDEX IF NOT EXISTS idx_document_content_document_id ON document_content(document_id);
CREATE INDEX IF NOT EXISTS idx_document_content_type ON document_content(content_type);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to automatically update updated_at
CREATE TRIGGER update_search_sessions_updated_at 
    BEFORE UPDATE ON search_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View: documents_summary
-- Summary view for quick statistics
CREATE OR REPLACE VIEW documents_summary AS
SELECT 
    ss.id AS session_id,
    ss.search_date,
    ss.total_extracted,
    COUNT(d.id) AS documents_count,
    COUNT(DISTINCT d.court_name) AS unique_courts,
    COUNT(DISTINCT d.judge_name) AS unique_judges,
    COUNT(DISTINCT d.case_type) AS unique_case_types,
    MIN(d.decision_date) AS earliest_decision_date,
    MAX(d.decision_date) AS latest_decision_date,
    ss.created_at AS session_created_at
FROM search_sessions ss
LEFT JOIN documents d ON ss.id = d.search_session_id
GROUP BY ss.id, ss.search_date, ss.total_extracted, ss.created_at;

-- View: documents_by_court
-- Documents grouped by court
CREATE OR REPLACE VIEW documents_by_court AS
SELECT 
    court_name,
    COUNT(*) AS document_count,
    COUNT(DISTINCT judge_name) AS judge_count,
    COUNT(DISTINCT case_type) AS case_type_count,
    MIN(decision_date) AS earliest_date,
    MAX(decision_date) AS latest_date
FROM documents
WHERE court_name IS NOT NULL
GROUP BY court_name
ORDER BY document_count DESC;

-- View: documents_by_judge
-- Documents grouped by judge
CREATE OR REPLACE VIEW documents_by_judge AS
SELECT 
    judge_name,
    COUNT(*) AS document_count,
    COUNT(DISTINCT court_name) AS court_count,
    COUNT(DISTINCT case_type) AS case_type_count,
    MIN(decision_date) AS earliest_date,
    MAX(decision_date) AS latest_date
FROM documents
WHERE judge_name IS NOT NULL
GROUP BY judge_name
ORDER BY document_count DESC;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO reyestr_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO reyestr_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO reyestr_user;
