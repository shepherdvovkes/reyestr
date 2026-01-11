"""
Update document metadata in database from downloaded HTML files
"""

import re
from pathlib import Path
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
from typing import Dict, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich import box
import logging

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
        # Try other formats
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None


def extract_metadata_from_html(html_path: Path) -> Dict[str, Optional[str]]:
    """
    Extract metadata from HTML file
    
    Returns:
        Dictionary with extracted metadata fields
    """
    metadata = {
        'court_name': None,
        'judge_name': None,
        'decision_type': None,
        'decision_date': None,
        'law_date': None,
        'case_type': None,
        'case_number': None,
        'reg_number': None
    }
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get all text content for pattern matching
        text = soup.get_text()
        
        # Extract court name - look for patterns like "Суд:", "Назва суду:", etc.
        court_patterns = [
            r'Суд[:\s]+([^\n]+)',
            r'Назва\s+суду[:\s]+([^\n]+)',
            r'Судовий\s+орган[:\s]+([^\n]+)',
            r'<td[^>]*>Суд[:\s]*</td>\s*<td[^>]*>([^<]+)</td>',
            r'<label[^>]*>Суд[:\s]*</label>\s*<[^>]*>([^<]+)</',
        ]
        
        for pattern in court_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if not match:
                # Try in HTML
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if match:
                court_name = match.group(1).strip()
                if court_name and len(court_name) > 3:
                    metadata['court_name'] = court_name
                    break
        
        # Extract judge name - look for "Суддя:", "ПІБ судді:", etc.
        judge_patterns = [
            r'Суддя[:\s]+([^\n]+)',
            r'ПІБ\s+судді[:\s]+([^\n]+)',
            r'Судд[яі][:\s]+([^\n]+)',
            r'<td[^>]*>Суддя[:\s]*</td>\s*<td[^>]*>([^<]+)</td>',
            r'<label[^>]*>Суддя[:\s]*</label>\s*<[^>]*>([^<]+)</',
        ]
        
        for pattern in judge_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if not match:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if match:
                judge_name = match.group(1).strip()
                if judge_name and len(judge_name) > 3:
                    metadata['judge_name'] = judge_name
                    break
        
        # Extract decision type - look for "Вид рішення:", "Тип рішення:", etc.
        decision_type_patterns = [
            r'Вид\s+рішення[:\s]+([^\n]+)',
            r'Тип\s+рішення[:\s]+([^\n]+)',
            r'Рішення[:\s]+([^\n]+)',
            r'<td[^>]*>Вид\s+рішення[:\s]*</td>\s*<td[^>]*>([^<]+)</td>',
        ]
        
        for pattern in decision_type_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if not match:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if match:
                decision_type = match.group(1).strip()
                if decision_type:
                    metadata['decision_type'] = decision_type
                    break
        
        # Extract decision date - look for "Дата рішення:", "Дата:", etc.
        date_patterns = [
            r'Дата\s+рішення[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
            r'Дата\s+прийняття[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
            r'Дата[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                date_str = match.group(1).strip()
                # Normalize date format
                date_str = date_str.replace('/', '.').replace('-', '.')
                metadata['decision_date'] = date_str
                break
        
        # Extract law date (date of legal force) - "Дата набуття чинності:"
        law_date_patterns = [
            r'Дата\s+набуття\s+чинності[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
            r'Набуття\s+чинності[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
        ]
        
        for pattern in law_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                date_str = match.group(1).strip()
                date_str = date_str.replace('/', '.').replace('-', '.')
                metadata['law_date'] = date_str
                break
        
        # Extract case type - "Вид справи:", "Категорія справи:", etc.
        case_type_patterns = [
            r'Вид\s+справи[:\s]+([^\n]+)',
            r'Категорія\s+справи[:\s]+([^\n]+)',
            r'Тип\s+справи[:\s]+([^\n]+)',
        ]
        
        for pattern in case_type_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if not match:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if match:
                case_type = match.group(1).strip()
                if case_type:
                    metadata['case_type'] = case_type
                    break
        
        # Extract case number - "Номер справи:", "Справа №", etc.
        case_number_patterns = [
            r'Номер\s+справи[:\s]+([^\n]+)',
            r'Справа\s+№[:\s]*([^\n]+)',
            r'№\s+справи[:\s]+([^\n]+)',
        ]
        
        for pattern in case_number_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if not match:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if match:
                case_number = match.group(1).strip()
                if case_number:
                    metadata['case_number'] = case_number
                    break
        
        # Extract registration number - usually in the filename or URL
        # Try to extract from HTML content
        reg_number_patterns = [
            r'Реєстраційний\s+номер[:\s]+([^\n]+)',
            r'Реєстр[:\s]+№[:\s]*([^\n]+)',
        ]
        
        for pattern in reg_number_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                reg_number = match.group(1).strip()
                if reg_number:
                    metadata['reg_number'] = reg_number
                    break
        
        # Also try to extract from table structure (common in Ukrainian court sites)
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'суд' in label and not metadata['court_name']:
                        metadata['court_name'] = value
                    elif 'судд' in label and not metadata['judge_name']:
                        metadata['judge_name'] = value
                    elif 'вид' in label and 'рішення' in label and not metadata['decision_type']:
                        metadata['decision_type'] = value
                    elif 'дата' in label and 'рішення' in label and not metadata['decision_date']:
                        date_str = value.replace('/', '.').replace('-', '.')
                        metadata['decision_date'] = date_str
                    elif 'набуття' in label and 'чинності' in label and not metadata['law_date']:
                        date_str = value.replace('/', '.').replace('-', '.')
                        metadata['law_date'] = date_str
                    elif 'вид' in label and 'справи' in label and not metadata['case_type']:
                        metadata['case_type'] = value
                    elif 'номер' in label and 'справи' in label and not metadata['case_number']:
                        metadata['case_number'] = value
                    elif 'реєстраційний' in label and 'номер' in label and not metadata['reg_number']:
                        metadata['reg_number'] = value
        
    except Exception as e:
        logger.warning(f"Error extracting metadata from {html_path}: {e}")
    
    return metadata


def update_document_metadata_in_db(document_id: str, metadata: Dict) -> bool:
    """
    Update document metadata in database
    
    Returns:
        True if updated successfully, False on error
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Build update query - only update non-None values
        updates = []
        values = []
        
        if metadata.get('court_name'):
            updates.append('court_name = %s')
            values.append(metadata['court_name'])
        
        if metadata.get('judge_name'):
            updates.append('judge_name = %s')
            values.append(metadata['judge_name'])
        
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
        
        if metadata.get('reg_number'):
            updates.append('reg_number = %s')
            values.append(metadata['reg_number'])
        
        if not updates:
            cur.close()
            conn.close()
            return False
        
        # Add document_id and updated_at
        values.append(document_id)
        updates.append('updated_at = CURRENT_TIMESTAMP')
        
        query = f"""
            UPDATE documents 
            SET {', '.join(updates)}
            WHERE id = %s
        """
        
        cur.execute(query, values)
        
        if cur.rowcount > 0:
            conn.commit()
            cur.close()
            conn.close()
            return True
        else:
            conn.rollback()
            cur.close()
            conn.close()
            return False
        
    except Exception as e:
        logger.warning(f"Database error updating {document_id}: {e}")
        try:
            conn.rollback()
            cur.close()
            conn.close()
        except:
            pass
        return False


def process_downloaded_documents(directory: Path) -> Dict:
    """
    Process all downloaded documents and update metadata
    
    Returns:
        Dictionary with statistics
    """
    stats = {
        'total_dirs': 0,
        'processed': 0,
        'updated': 0,
        'errors': 0,
        'fields_updated': {
            'court_name': 0,
            'judge_name': 0,
            'decision_type': 0,
            'decision_date': 0,
            'law_date': 0,
            'case_type': 0,
            'case_number': 0,
        }
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
            "[bold cyan]Processing documents...",
            total=len(doc_dirs)
        )
        
        for doc_dir in doc_dirs:
            try:
                # Try to find HTML files (prefer print version, then regular)
                html_files = list(doc_dir.glob("*_print.html"))
                if not html_files:
                    html_files = list(doc_dir.glob("*.html"))
                
                if not html_files:
                    progress.advance(task_id)
                    continue
                
                # Use first HTML file found
                html_file = html_files[0]
                
                # Extract document ID from directory name
                document_id = doc_dir.name
                
                # Extract metadata
                metadata = extract_metadata_from_html(html_file)
                
                # Count extracted fields
                extracted_fields = sum(1 for v in metadata.values() if v)
                if extracted_fields > 0:
                    # Update database
                    if update_document_metadata_in_db(document_id, metadata):
                        stats['updated'] += 1
                        stats['processed'] += 1
                        
                        # Count which fields were updated
                        for field in stats['fields_updated']:
                            if metadata.get(field):
                                stats['fields_updated'][field] += 1
                    else:
                        stats['errors'] += 1
                else:
                    stats['processed'] += 1
                
                progress.advance(task_id)
                
            except Exception as e:
                logger.warning(f"Error processing {doc_dir}: {e}")
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
        f"[bold cyan]Update Document Metadata from HTML[/bold cyan]\n"
        f"Directory: [yellow]{directory}[/yellow]",
        title="Configuration",
        border_style="cyan"
    ))
    
    # Check database connection
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
    except Exception as e:
        console.print(f"[bold red]✗ Database connection failed: {e}[/bold red]")
        console.print("\n[yellow]Make sure PostgreSQL container is running: docker-compose up -d[/yellow]")
        return
    
    # Process documents
    stats = process_downloaded_documents(directory)
    
    # Display summary
    console.print("\n")
    summary_table = Table(title="Update Summary", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    summary_table.add_column("Metric", style="cyan", no_wrap=True)
    summary_table.add_column("Value", style="magenta", justify="right")
    
    summary_table.add_row("Total Directories", str(stats['total_dirs']))
    summary_table.add_row("Processed", f"[green]{stats['processed']}[/green]")
    summary_table.add_row("Updated in DB", f"[green]{stats['updated']}[/green]")
    summary_table.add_row("Errors", f"[red]{stats['errors']}[/red]" if stats['errors'] > 0 else "0")
    
    console.print(summary_table)
    
    # Show fields updated
    if stats['updated'] > 0:
        console.print("\n[bold cyan]Fields Updated:[/bold cyan]")
        fields_table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        fields_table.add_column("Field", style="cyan")
        fields_table.add_column("Count", style="magenta", justify="right")
        
        for field, count in stats['fields_updated'].items():
            if count > 0:
                fields_table.add_row(field.replace('_', ' ').title(), str(count))
        
        console.print(fields_table)
    
    console.print(f"\n[dim]All metadata updated in database[/dim]")


if __name__ == "__main__":
    main()
