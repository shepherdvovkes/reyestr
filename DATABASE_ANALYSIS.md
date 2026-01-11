# Database Analysis Report

## Current Database Status

### Summary
- **Total Documents**: 2,875
- **Search Sessions**: 10 (3 active sessions with documents)
- **Document Content Records**: 0 ❌
- **Unique Courts**: 6
- **Unique Judges**: 9
- **Unique Case Types**: 3

### Search Sessions
- Most recent session: `4a2cd1dc...` (2026-01-11) - 0 documents
- Largest session: `9e97c463...` (2026-01-10) - 2,850 documents
- Most sessions have 0 documents extracted

### Documents
- All 2,875 documents are missing metadata:
  - `decision_type`: NULL
  - `court_name`: NULL
  - `decision_date`: NULL
  - `case_type`: NULL
  - `judge_name`: NULL
- Only basic fields populated: `id`, `url`, `reg_number`

### Document Content
- **CRITICAL**: 0 content records stored
- All 2,875 documents have no content in `document_content` table
- This means downloaded HTML/text files are not being saved to database

---

## Errors Found

### Error 1: Port Mismatch in `database/import_json.py` ❌

**Location**: `database/import_json.py` line 16

**Problem**: 
```python
'port': 5432,  # WRONG - should be 5433
```

**Impact**: Script will fail to connect to database when run

**Fix**: Change to port 5433 (matches docker-compose.yml mapping)

---

### Error 2: `download_5_documents.py` Doesn't Save to Database ❌

**Location**: `download_5_documents.py`

**Problem**: 
- Script only saves files to disk (`downloaded_100_documents/`)
- No database connection code
- No insertion into `document_content` table

**Impact**: 
- Downloaded documents are not tracked in database
- Cannot query/downloaded status from database
- Content is only stored as files, not in database

**Fix Required**: Add database insertion code to save:
- Document metadata updates
- Content records (HTML, print HTML, text files)

---

### Error 3: Missing Document Content ❌

**Problem**: 
- All 2,875 documents have no content records
- `document_content` table is completely empty

**Possible Causes**:
1. `download_5_documents.py` doesn't save to database (Error 2)
2. No script exists to import downloaded files into database
3. Content was never saved to database after download

**Fix Required**: 
- Create script to import downloaded files into `document_content` table
- Or modify `download_5_documents.py` to save content to database

---

### Error 4: Missing Document Metadata ❌

**Problem**: 
- Documents stored with minimal data (only id, url, reg_number)
- All metadata fields are NULL

**Cause**: 
- `extract_date_search_links.py` inserts documents with NULL metadata (lines 93-99)
- Metadata extraction happens later but may not be updating database

**Impact**: 
- Cannot filter/search by court, judge, case type, etc.
- Limited querying capabilities

**Fix Required**: 
- Update documents with metadata after extraction
- Or extract metadata during initial insertion

---

## How to Fix Errors

### Fix 1: Correct Port in `database/import_json.py`

```python
# Change line 16 from:
'port': 5432,

# To:
'port': 5433,  # Docker container port (mapped from 5432)
```

### Fix 2: Add Database Support to `download_5_documents.py`

Add database connection and content saving:

```python
import psycopg2
from psycopg2.extras import execute_values

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 5433,
    'database': 'reyestr_db',
    'user': 'reyestr_user',
    'password': 'reyestr_password'
}

async def save_document_content_to_db(
    document_id: str,
    content_type: str,
    file_path: str,
    content_text: str = None,
    file_size: int = None
):
    """Save document content to database"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO document_content (
                document_id, content_type, file_path, 
                content_text, file_size_bytes
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (document_id, content_type, str(file_path), content_text, file_size))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save content for {document_id}: {e}")
    finally:
        cur.close()
        conn.close()
```

Then call this function in `process_single_document()` after downloading files.

### Fix 3: Create Script to Import Downloaded Files

Create a script to scan `downloaded_100_documents/` and import all files into database.

### Fix 4: Update Document Metadata

Create a script to:
1. Read downloaded HTML files
2. Extract metadata (court, judge, dates, etc.)
3. Update `documents` table with extracted metadata

---

## Recommendations

1. **Immediate**: Fix port mismatch in `import_json.py`
2. **High Priority**: Add database support to `download_5_documents.py`
3. **High Priority**: Create script to import existing downloaded files into database
4. **Medium Priority**: Update document metadata from downloaded files
5. **Future**: Add metadata extraction during document download

---

## Database Connection Details

- **Host**: 127.0.0.1
- **Port**: 5433 (external) → 5432 (container internal)
- **Database**: reyestr_db
- **User**: reyestr_user
- **Password**: reyestr_password

**Connection String**: 
```
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db
```

Or via Docker:
```
docker exec -it reyestr_db psql -U reyestr_user -d reyestr_db
```
