"""
Import extracted_document_links.json into PostgreSQL database
"""

import json
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from datetime import datetime
import sys
from typing import Dict, List

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,  # Docker container port (mapped from 5432)
    'database': 'reyestr_db',
    'user': 'reyestr_user',
    'password': 'reyestr_password'
}


def parse_date(date_str: str) -> datetime.date:
    """Parse date string in DD.MM.YYYY format"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str.strip(), '%d.%m.%Y').date()
    except ValueError:
        return None


def import_json_to_db(json_file: Path):
    """Import JSON file into PostgreSQL database"""
    
    # Read JSON file
    print(f"Reading {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    search_date_str = data.get('search_date', '')
    total_extracted = data.get('total_extracted', 0)
    documents = data.get('documents', [])
    
    if not documents:
        print("No documents to import")
        return
    
    # Parse search date
    search_date = parse_date(search_date_str)
    if not search_date:
        print(f"Warning: Could not parse search_date '{search_date_str}', using current date")
        search_date = datetime.now().date()
    
    # Connect to database
    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Insert search session
        print(f"Creating search session for date {search_date}...")
        cur.execute("""
            INSERT INTO search_sessions (search_date, total_extracted)
            VALUES (%s, %s)
            RETURNING id
        """, (search_date, total_extracted))
        
        session_id = cur.fetchone()[0]
        print(f"Created session with ID: {session_id}")
        
        # Prepare documents for bulk insert
        print(f"Preparing {len(documents)} documents for import...")
        documents_data = []
        for doc in documents:
            doc_data = (
                doc.get('id', ''),
                session_id,
                doc.get('url', ''),
                doc.get('reg_number', ''),
                doc.get('decision_type') or None,
                parse_date(doc.get('decision_date', '')),
                parse_date(doc.get('law_date', '')),
                doc.get('case_type') or None,
                doc.get('case_number') or None,
                doc.get('court_name') or None,
                doc.get('judge_name') or None
            )
            documents_data.append(doc_data)
        
        # Bulk insert documents
        print("Inserting documents into database...")
        execute_values(
            cur,
            """
            INSERT INTO documents (
                id, search_session_id, url, reg_number, decision_type,
                decision_date, law_date, case_type, case_number,
                court_name, judge_name
            )
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET
                url = EXCLUDED.url,
                reg_number = EXCLUDED.reg_number,
                decision_type = EXCLUDED.decision_type,
                decision_date = EXCLUDED.decision_date,
                law_date = EXCLUDED.law_date,
                case_type = EXCLUDED.case_type,
                case_number = EXCLUDED.case_number,
                court_name = EXCLUDED.court_name,
                judge_name = EXCLUDED.judge_name,
                updated_at = CURRENT_TIMESTAMP
            """,
            documents_data
        )
        
        # Commit transaction
        conn.commit()
        print(f"✓ Successfully imported {len(documents)} documents")
        
        # Print summary
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT court_name) as courts,
                COUNT(DISTINCT judge_name) as judges,
                COUNT(DISTINCT case_type) as case_types
            FROM documents
            WHERE search_session_id = %s
        """, (session_id,))
        
        summary = cur.fetchone()
        print("\n" + "=" * 60)
        print("Import Summary")
        print("=" * 60)
        print(f"Total documents: {summary[0]}")
        print(f"Unique courts: {summary[1]}")
        print(f"Unique judges: {summary[2]}")
        print(f"Unique case types: {summary[3]}")
        print("=" * 60)
        
    except Exception as e:
        conn.rollback()
        print(f"Error importing data: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    json_file = Path("extracted_document_links.json")
    
    if not json_file.exists():
        print(f"Error: {json_file} not found")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        json_file = Path(sys.argv[1])
    
    try:
        import_json_to_db(json_file)
    except Exception as e:
        print(f"Failed to import: {e}")
        sys.exit(1)
