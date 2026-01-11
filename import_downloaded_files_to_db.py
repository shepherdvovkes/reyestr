"""
Import existing downloaded files into the database
"""

import re
from pathlib import Path
import psycopg2
from datetime import datetime
from typing import Dict, Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich import box
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

# Database connection parameters
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 5433,  # Docker container port
    'database': 'reyestr_db',
    'user': 'reyestr_user',
    'password': 'reyestr_password'
}


def parse_date(date_str: str) -> Optional[datetime.date]:
    """Parse date string in DD.MM.YYYY format"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str.strip(), '%d.%m.%Y').date()
    except ValueError:
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None


def ensure_document_in_db(doc_id: str, metadata: Dict = None) -> bool:
    """
    Ensure document exists in database, create if it doesn't exist
    
    Args:
        doc_id: Document ID
        metadata: Optional metadata dictionary
    
    Returns:
        True if document exists or was created, False on error
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        if not doc_id:
            cur.close()
            conn.close()
            return False
        
        # Check if document exists
        cur.execute("SELECT id FROM documents WHERE id = %s", (doc_id,))
        if cur.fetchone():
            # Document exists, optionally update metadata
            if metadata:
                updates = []
                values = []
                
                if metadata.get('url'):
                    updates.append('url = %s')
                    values.append(metadata['url'])
                
                if metadata.get('reg_number'):
                    updates.append('reg_number = %s')
                    values.append(metadata['reg_number'])
                
                if metadata.get('decision_type'):
                    updates.append('decision_type = %s')
                    values.append(metadata['decision_type'])
                
                if metadata.get('decision_date'):
                    decision_date = parse_date(metadata['decision_date'])
                    if decision_date:
                        updates.append('decision_date = %s')
                        values.append(decision_date)
                
                if metadata.get('law_date'):
                    law_date = parse_date(metadata['law_date'])
                    if law_date:
                        updates.append('law_date = %s')
                        values.append(law_date)
                
                if metadata.get('case_type'):
                    updates.append('case_type = %s')
                    values.append(metadata['case_type'])
                
                if metadata.get('case_number'):
                    updates.append('case_number = %s')
                    values.append(metadata['case_number'])
                
                if metadata.get('court_name'):
                    updates.append('court_name = %s')
                    values.append(metadata['court_name'])
                
                if metadata.get('judge_name'):
                    updates.append('judge_name = %s')
                    values.append(metadata['judge_name'])
                
                if updates:
                    values.append(doc_id)
                    updates.append('updated_at = CURRENT_TIMESTAMP')
                    
                    query = f"""
                        UPDATE documents 
                        SET {', '.join(updates)}
                        WHERE id = %s
                    """
                    cur.execute(query, values)
        else:
            # Document doesn't exist, create it
            # Get or create a default search session
            cur.execute("""
                SELECT id FROM search_sessions 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            session_row = cur.fetchone()
            session_id = session_row[0] if session_row else None
            
            if not session_id:
                # Create a default session for imported documents
                cur.execute("""
                    INSERT INTO search_sessions (search_date, total_extracted)
                    VALUES (CURRENT_DATE, 0)
                    RETURNING id
                """)
                session_id = cur.fetchone()[0]
            
            # Insert document
            cur.execute("""
                INSERT INTO documents (
                    id, search_session_id, url, reg_number, decision_type,
                    decision_date, law_date, case_type, case_number,
                    court_name, judge_name
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                doc_id,
                session_id,
                metadata.get('url', '') if metadata else '',
                metadata.get('reg_number', doc_id) if metadata else doc_id,
                metadata.get('decision_type') if metadata else None,
                parse_date(metadata.get('decision_date', '')) if metadata else None,
                parse_date(metadata.get('law_date', '')) if metadata else None,
                metadata.get('case_type') if metadata else None,
                metadata.get('case_number') if metadata else None,
                metadata.get('court_name') if metadata else None,
                metadata.get('judge_name') if metadata else None
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.warning(f"Database error ensuring document {doc_id}: {e}")
        try:
            conn.rollback()
            cur.close()
            conn.close()
        except:
            pass
        return False


def save_document_content_to_db(
    document_id: str,
    content_type: str,
    file_path: Path,
    content_text: Optional[str] = None,
    file_size: Optional[int] = None
) -> bool:
    """
    Save document content to database
    
    Args:
        document_id: Document ID
        content_type: 'html', 'print_html', 'text', or 'pdf'
        file_path: Path to the file on disk
        content_text: Text content (for text files)
        file_size: File size in bytes
    
    Returns:
        True if saved successfully, False on error
    """
    try:
        # Validate content type
        if content_type not in ['html', 'print_html', 'text', 'pdf']:
            logger.warning(f"Invalid content_type: {content_type}")
            return False
        
        # Read file size if not provided
        if file_path.exists() and file_size is None:
            file_size = file_path.stat().st_size
        
        # Read text content if not provided and it's a text file
        if content_text is None and file_path.exists():
            if content_type == 'text' or file_path.suffix == '.txt':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content_text = f.read()
                except Exception as e:
                    logger.warning(f"Could not read text content from {file_path}: {e}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check if content already exists for this document and type
        cur.execute("""
            SELECT id FROM document_content 
            WHERE document_id = %s AND content_type = %s
        """, (document_id, content_type))
        
        existing = cur.fetchone()
        
        if existing:
            # Update existing content
            cur.execute("""
                UPDATE document_content SET
                    file_path = COALESCE(%s, file_path),
                    content_text = COALESCE(%s, content_text),
                    file_size_bytes = COALESCE(%s, file_size_bytes)
                WHERE document_id = %s AND content_type = %s
            """, (
                str(file_path) if file_path else None,
                content_text,
                file_size,
                document_id,
                content_type
            ))
        else:
            # Insert new content
            cur.execute("""
                INSERT INTO document_content (
                    document_id, content_type, file_path, 
                    content_text, file_size_bytes
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                document_id,
                content_type,
                str(file_path) if file_path else None,
                content_text,
                file_size
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.warning(f"Database error saving content for {document_id} ({content_type}): {e}")
        try:
            conn.rollback()
            cur.close()
            conn.close()
        except:
            pass
        return False


def load_metadata_from_json(metadata_file: Path) -> Optional[Dict]:
    """Load metadata from JSON file"""
    try:
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load metadata from {metadata_file}: {e}")
    return None


def extract_document_id_from_path(doc_dir: Path) -> Optional[str]:
    """Extract document ID from directory name or files"""
    # Try directory name first
    doc_id = doc_dir.name
    if doc_id and doc_id.isdigit():
        return doc_id
    
    # Try to extract from filename patterns
    for file in doc_dir.glob("*"):
        if file.is_file():
            # Pattern: {doc_id}_{reg_number}_print.html
            match = re.match(r'^(\d+)_', file.name)
            if match:
                return match.group(1)
            
            # Pattern: {doc_id}.html
            match = re.match(r'^(\d+)\.html$', file.name)
            if match:
                return match.group(1)
    
    return None


def process_document_directory(doc_dir: Path) -> Dict:
    """
    Process a single document directory and import files to database
    
    Returns:
        Dictionary with processing results
    """
    result = {
        'document_id': None,
        'document_created': False,
        'content_saved': 0,
        'content_types': [],
        'errors': []
    }
    
    try:
        # Extract document ID
        doc_id = extract_document_id_from_path(doc_dir)
        if not doc_id:
            result['errors'].append("Could not extract document ID")
            return result
        
        result['document_id'] = doc_id
        
        # Load metadata from JSON if available
        metadata = None
        metadata_file = doc_dir / f"{doc_id}_metadata.json"
        if metadata_file.exists():
            metadata = load_metadata_from_json(metadata_file)
        
        # If no metadata file, try to extract from HTML
        if not metadata:
            try:
                from update_metadata_from_html import extract_metadata_from_html
                # Try print version first
                print_files = list(doc_dir.glob("*_print.html"))
                if print_files:
                    metadata = extract_metadata_from_html(print_files[0])
                else:
                    # Try regular HTML
                    html_files = list(doc_dir.glob("*.html"))
                    if html_files:
                        metadata = extract_metadata_from_html(html_files[0])
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Could not extract metadata: {e}")
        
        # Ensure document exists in database
        if ensure_document_in_db(doc_id, metadata):
            result['document_created'] = True
            
            # Find and import all content files
            # 1. Print HTML files
            print_files = list(doc_dir.glob("*_print.html"))
            for print_file in print_files:
                if save_document_content_to_db(
                    document_id=doc_id,
                    content_type='print_html',
                    file_path=print_file
                ):
                    result['content_saved'] += 1
                    result['content_types'].append('print_html')
            
            # 2. Regular HTML files (not print versions)
            html_files = [f for f in doc_dir.glob("*.html") 
                         if not f.name.endswith('_print.html')]
            for html_file in html_files:
                if save_document_content_to_db(
                    document_id=doc_id,
                    content_type='html',
                    file_path=html_file
                ):
                    result['content_saved'] += 1
                    result['content_types'].append('html')
            
            # 3. Text files
            txt_files = list(doc_dir.glob("*.txt"))
            for txt_file in txt_files:
                if save_document_content_to_db(
                    document_id=doc_id,
                    content_type='text',
                    file_path=txt_file
                ):
                    result['content_saved'] += 1
                    result['content_types'].append('text')
            
            # 4. PDF files (if any)
            pdf_files = list(doc_dir.glob("*.pdf"))
            for pdf_file in pdf_files:
                if save_document_content_to_db(
                    document_id=doc_id,
                    content_type='pdf',
                    file_path=pdf_file
                ):
                    result['content_saved'] += 1
                    result['content_types'].append('pdf')
        else:
            result['errors'].append("Failed to create/update document in database")
    
    except Exception as e:
        result['errors'].append(str(e))
        logger.warning(f"Error processing {doc_dir}: {e}")
    
    return result


def import_downloaded_files(directory: Path) -> Dict:
    """
    Import all downloaded files from directory into database
    
    Returns:
        Dictionary with import statistics
    """
    stats = {
        'total_dirs': 0,
        'processed': 0,
        'documents_created': 0,
        'content_files_imported': 0,
        'content_types': {
            'html': 0,
            'print_html': 0,
            'text': 0,
            'pdf': 0
        },
        'errors': 0,
        'results': []
    }
    
    if not directory.exists():
        console.print(f"[bold red]Directory not found: {directory}[/bold red]")
        return stats
    
    # Find all document directories
    doc_dirs = [d for d in directory.iterdir() if d.is_dir()]
    stats['total_dirs'] = len(doc_dirs)
    
    if not doc_dirs:
        console.print(f"[yellow]No document directories found in {directory}[/yellow]")
        return stats
    
    console.print(f"\n[bold cyan]Found {len(doc_dirs)} document directories[/bold cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("[cyan]{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
        expand=True
    ) as progress:
        task_id = progress.add_task(
            "[bold cyan]Importing files to database...",
            total=len(doc_dirs)
        )
        
        for doc_dir in doc_dirs:
            result = process_document_directory(doc_dir)
            stats['results'].append(result)
            
            if result['document_id']:
                stats['processed'] += 1
            
            if result['document_created']:
                stats['documents_created'] += 1
            
            if result['content_saved'] > 0:
                stats['content_files_imported'] += result['content_saved']
                for content_type in result['content_types']:
                    if content_type in stats['content_types']:
                        stats['content_types'][content_type] += 1
            
            if result['errors']:
                stats['errors'] += 1
            
            progress.advance(task_id)
    
    return stats


def main():
    """Main function"""
    import sys
    
    # Default directory
    directory = Path("downloaded_100_documents")
    
    if len(sys.argv) > 1:
        directory = Path(sys.argv[1])
    
    console.print(Panel.fit(
        f"[bold cyan]Import Downloaded Files to Database[/bold cyan]\n"
        f"Directory: [yellow]{directory}[/yellow]",
        title="Configuration",
        border_style="cyan"
    ))
    
    # Check database connection
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        console.print("[green]✓ Database connection successful[/green]")
    except Exception as e:
        console.print(f"[bold red]✗ Database connection failed: {e}[/bold red]")
        console.print("\n[yellow]Make sure PostgreSQL container is running: docker-compose up -d[/yellow]")
        return
    
    # Import files
    stats = import_downloaded_files(directory)
    
    # Display summary
    console.print("\n")
    summary_table = Table(title="Import Summary", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    summary_table.add_column("Metric", style="cyan", no_wrap=True)
    summary_table.add_column("Value", style="magenta", justify="right")
    
    summary_table.add_row("Total Directories", str(stats['total_dirs']))
    summary_table.add_row("Processed", f"[green]{stats['processed']}[/green]")
    summary_table.add_row("Documents Created/Updated", f"[green]{stats['documents_created']}[/green]")
    summary_table.add_row("Content Files Imported", f"[green]{stats['content_files_imported']}[/green]")
    summary_table.add_row("Errors", f"[red]{stats['errors']}[/red]" if stats['errors'] > 0 else "0")
    
    console.print(summary_table)
    
    # Show content types breakdown
    if stats['content_files_imported'] > 0:
        console.print("\n[bold cyan]Content Types Imported:[/bold cyan]")
        types_table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        types_table.add_column("Content Type", style="cyan")
        types_table.add_column("Count", style="magenta", justify="right")
        
        for content_type, count in stats['content_types'].items():
            if count > 0:
                types_table.add_row(content_type.replace('_', ' ').title(), str(count))
        
        console.print(types_table)
    
    # Show sample of errors if any
    if stats['errors'] > 0:
        console.print("\n[yellow]Sample Errors:[/yellow]")
        error_count = 0
        for result in stats['results']:
            if result['errors'] and error_count < 5:
                console.print(f"  [red]•[/red] {result['document_id'] or 'Unknown'}: {', '.join(result['errors'][:2])}")
                error_count += 1
    
    console.print(f"\n[dim]All files imported to database[/dim]")
    console.print(f"[dim]Check database with: python3 check_database.py[/dim]")


if __name__ == "__main__":
    main()
