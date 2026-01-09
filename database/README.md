# PostgreSQL Database Setup for Court Documents Registry

## Overview

This directory contains the PostgreSQL database schema and setup files for storing court documents extracted from the Ukrainian court registry.

## Database Schema

### Tables

1. **search_sessions** - Stores information about each search/extraction session
   - `id` (UUID) - Primary key
   - `search_date` (DATE) - Date used for search
   - `total_extracted` (INTEGER) - Number of documents extracted
   - `created_at`, `updated_at` (TIMESTAMP) - Timestamps

2. **documents** - Stores individual court documents
   - `id` (VARCHAR) - Document ID (primary key)
   - `search_session_id` (UUID) - Foreign key to search_sessions
   - `url` (VARCHAR) - Document URL path
   - `reg_number` (VARCHAR) - Registration number (unique)
   - `decision_type` (VARCHAR) - Type of decision (e.g., "Ухвала")
   - `decision_date` (DATE) - Date of decision
   - `law_date` (DATE) - Date of legal force
   - `case_type` (VARCHAR) - Type of case
   - `case_number` (VARCHAR) - Case number
   - `court_name` (TEXT) - Name of the court
   - `judge_name` (VARCHAR) - Name of the judge
   - `created_at`, `updated_at` (TIMESTAMP) - Timestamps

3. **document_content** - Stores downloaded document content
   - `id` (UUID) - Primary key
   - `document_id` (VARCHAR) - Foreign key to documents
   - `content_type` (VARCHAR) - Type: 'html', 'print_html', 'text', 'pdf'
   - `file_path` (TEXT) - Path to file on disk
   - `content_text` (TEXT) - Text content (for text files)
   - `file_size_bytes` (BIGINT) - File size
   - `created_at` (TIMESTAMP) - Timestamp

### Views

- **documents_summary** - Summary statistics per search session
- **documents_by_court** - Documents grouped by court
- **documents_by_judge** - Documents grouped by judge

## Setup

### 1. Start PostgreSQL in Docker

```bash
docker-compose up -d
```

This will:
- Start PostgreSQL 15 in a Docker container
- Create the database `reyestr_db`
- Create user `reyestr_user` with password `reyestr_password`
- Automatically run `init.sql` to create the schema

### 2. Verify Database is Running

```bash
docker ps | grep reyestr_db
```

### 3. Connect to Database

```bash
# Using psql
docker exec -it reyestr_db psql -U reyestr_user -d reyestr_db

# Or using local psql (if installed)
psql -h localhost -U reyestr_user -d reyestr_db
```

### 4. Import JSON Data

First, install psycopg2:
```bash
pip install psycopg2-binary
```

Then import the JSON file:
```bash
python database/import_json.py extracted_document_links.json
```

## Usage Examples

### Query all documents from a search session

```sql
SELECT * FROM documents 
WHERE search_session_id = (
    SELECT id FROM search_sessions 
    WHERE search_date = '2026-01-07'
    ORDER BY created_at DESC 
    LIMIT 1
);
```

### Count documents by court

```sql
SELECT * FROM documents_by_court 
ORDER BY document_count DESC 
LIMIT 10;
```

### Find documents by judge

```sql
SELECT * FROM documents 
WHERE judge_name LIKE '%Гінда%'
ORDER BY decision_date DESC;
```

### Get summary statistics

```sql
SELECT * FROM documents_summary;
```

## Database Connection

- **Host**: localhost
- **Port**: 5432
- **Database**: reyestr_db
- **User**: reyestr_user
- **Password**: reyestr_password

## Backup and Restore

### Backup

```bash
docker exec reyestr_db pg_dump -U reyestr_user reyestr_db > backup.sql
```

### Restore

```bash
docker exec -i reyestr_db psql -U reyestr_user reyestr_db < backup.sql
```

## Stop Database

```bash
docker-compose down
```

To remove all data:
```bash
docker-compose down -v
```
