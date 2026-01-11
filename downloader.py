"""
Download documents from a specific page with concurrent connections
"""

import asyncio
from pathlib import Path
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig
import logging
import json
from extract_text_from_print import extract_text_from_html
from typing import Dict, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TaskID
from rich.table import Table
from rich.panel import Panel
from rich import box
import psycopg2
from datetime import datetime

# Configure logging to be less verbose (rich will handle display)
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

# Database connection parameters
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 5433,  # Docker container port (mapped from 5432)
    'database': 'reyestr_db',
    'user': 'reyestr_user',
    'password': 'reyestr_password'
}

# Default configuration
DEFAULT_CONFIG = {
    'search_params': {
        'CourtRegion': '11',
        'INSType': '1',
        'ChairmenName': '',
        'SearchExpression': '',
        'RegDateBegin': '',
        'RegDateEnd': '',
        'DateFrom': '',
        'DateTo': ''
    },
    'download_settings': {
        'default_start_page': 6,
        'default_max_documents': 100,
        'concurrent_connections': 5,
        'delay_between_requests': 2.0
    },
    'output': {
        'directory': 'downloaded_100_documents'
    },
    'database': {
        'enabled': True,
        'save_metadata': True,
        'extract_metadata_from_html': True
    }
}


def load_config(config_path: Path = None) -> Dict:
    """
    Load configuration from JSON file
    
    Args:
        config_path: Path to config file (default: downloader.config.json)
    
    Returns:
        Configuration dictionary with defaults for missing values
    """
    if config_path is None:
        config_path = Path("downloader.config.json")
    
    config = DEFAULT_CONFIG.copy()
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Merge with defaults
            if 'search_params' in file_config:
                config['search_params'].update(file_config['search_params'])
            if 'download_settings' in file_config:
                config['download_settings'].update(file_config['download_settings'])
            if 'output' in file_config:
                config['output'].update(file_config['output'])
            if 'database' in file_config:
                config['database'].update(file_config['database'])
            
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Could not load config file {config_path}: {e}")
            logger.warning("Using default configuration")
    else:
        logger.info(f"Config file {config_path} not found, using defaults")
    
    return config


def parse_date(date_str: str) -> Optional[datetime.date]:
    """Parse date string in DD.MM.YYYY format"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str.strip(), '%d.%m.%Y').date()
    except ValueError:
        return None


def ensure_document_in_db(doc_link: Dict) -> bool:
    """
    Ensure document exists in database, create if it doesn't exist
    
    Returns:
        True if document exists or was created, False on error
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        doc_id = doc_link.get('id', '')
        if not doc_id:
            cur.close()
            conn.close()
            return False
        
        # Check if document exists
        cur.execute("SELECT id FROM documents WHERE id = %s", (doc_id,))
        if cur.fetchone():
            # Document exists, optionally update metadata
            cur.execute("""
                UPDATE documents SET
                    url = COALESCE(%s, url),
                    reg_number = COALESCE(%s, reg_number),
                    decision_type = COALESCE(%s, decision_type),
                    decision_date = COALESCE(%s, decision_date),
                    law_date = COALESCE(%s, law_date),
                    case_type = COALESCE(%s, case_type),
                    case_number = COALESCE(%s, case_number),
                    court_name = COALESCE(%s, court_name),
                    judge_name = COALESCE(%s, judge_name),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                doc_link.get('url'),
                doc_link.get('reg_number'),
                doc_link.get('decision_type'),
                parse_date(doc_link.get('decision_date', '')),
                parse_date(doc_link.get('law_date', '')),
                doc_link.get('case_type'),
                doc_link.get('case_number'),
                doc_link.get('court_name'),
                doc_link.get('judge_name'),
                doc_id
            ))
        else:
            # Document doesn't exist, create it
            # First, get or create a default search session
            cur.execute("""
                SELECT id FROM search_sessions 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            session_row = cur.fetchone()
            session_id = session_row[0] if session_row else None
            
            if not session_id:
                # Create a default session for downloaded documents
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
                doc_link.get('url', ''),
                doc_link.get('reg_number', doc_id),
                doc_link.get('decision_type'),
                parse_date(doc_link.get('decision_date', '')),
                parse_date(doc_link.get('law_date', '')),
                doc_link.get('case_type'),
                doc_link.get('case_number'),
                doc_link.get('court_name'),
                doc_link.get('judge_name')
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.warning(f"Database error ensuring document {doc_link.get('id', 'unknown')}: {e}")
        try:
            conn.rollback()
            cur.close()
            conn.close()
        except:
            pass
        return False


def document_has_content_in_db(document_id: str) -> bool:
    """
    Check if document already has content in database
    
    Args:
        document_id: Document ID to check
    
    Returns:
        True if document has at least one content record, False otherwise
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM document_content 
            WHERE document_id = %s
        """, (document_id,))
        
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return count > 0
        
    except Exception as e:
        logger.warning(f"Database error checking content for {document_id}: {e}")
        return False


def save_document_content_to_db(
    document_id: str,
    content_type: str,
    file_path: Optional[Path] = None,
    content_text: Optional[str] = None,
    file_size: Optional[int] = None
) -> bool:
    """
    Save document content to database
    
    Args:
        document_id: Document ID
        content_type: 'html', 'print_html', 'text', or 'pdf'
        file_path: Path to the file on disk
        content_text: Text content (for text files, can be read from file)
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
        if file_path and file_path.exists() and file_size is None:
            file_size = file_path.stat().st_size
        
        # Read text content if not provided and it's a text file
        if content_text is None and file_path and file_path.exists():
            if content_type == 'text' or (content_type == 'print_html' and file_path.suffix == '.txt'):
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


async def process_single_document(
    doc_link: Dict,
    doc_index: int,
    total_docs: int,
    output_dir: Path,
    semaphore: asyncio.Semaphore,
    progress: Progress,
    task_id: TaskID
) -> Dict:
    """
    Process a single document (download print version and extract text)
    
    Args:
        doc_link: Document link dictionary
        doc_index: Index of document (1-based)
        total_docs: Total number of documents
        output_dir: Output directory
        semaphore: Semaphore to limit concurrent connections
        progress: Rich Progress object
        task_id: Task ID for progress tracking
    
    Returns:
        Result dictionary
    """
    # Create a separate handler for this document (concurrent processing)
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=2.0  # Reduced since we have concurrency control
        )
    )
    
    doc_id = doc_link['id']
    reg_number = doc_link['reg_number']
    
    # Check if document already has content in database BEFORE acquiring semaphore
    # This prevents blocking a download slot for already downloaded documents
    if document_has_content_in_db(doc_id):
        progress.update(
            task_id,
            description=f"[yellow]Skipping[/yellow] {reg_number} - already downloaded"
        )
        progress.advance(task_id)
        return {
            'document_id': doc_id,
            'reg_number': reg_number,
            'success': True,
            'skipped': True,
            'reason': 'already_in_database'
        }
    
    async with semaphore:  # Limit concurrent connections
        try:
            # Notify server that download has started (if in distributed mode)
            try:
                from server_document_registry import notify_document_download_start
                notify_document_download_start(
                    document_id=doc_id,
                    reg_number=reg_number
                )
            except ImportError:
                # Module not available, skip notification
                pass
            except Exception as e:
                logger.debug(f"Could not notify document download start: {e}")
            
            # Update progress description
            progress.update(
                task_id,
                description=f"[cyan]Processing[/cyan] {reg_number} - {doc_link.get('decision_type', 'N/A')[:30]}"
            )
            
            # Initialize browser
            await handler.navigate("/")
            
            # Create directory for this document
            doc_dir = output_dir / doc_id
            doc_dir.mkdir(exist_ok=True)
            
            # Download print version using print button
            print_filename = f"{doc_id}_{reg_number}_print.html"
            print_path = doc_dir / print_filename
            
            print_version_path = await handler.download_print_version(
                document_url=doc_link['url'],
                output_path=str(print_path),
                document_id=doc_id
            )
            
            # Also download regular HTML for backup
            doc_filename = f"{doc_id}_{reg_number}.html"
            doc_path = doc_dir / doc_filename
            downloaded_path = await handler.download_document(
                doc_link['url'],
                str(doc_path)
            )
            
            # Extract text from print version
            text_extracted = False
            txt_file = None
            if print_version_path:
                try:
                    text = extract_text_from_html(Path(print_version_path))
                    if text:
                        # Save extracted text
                        txt_file = doc_dir / f"{doc_id}_{reg_number}_print.txt"
                        with open(txt_file, 'w', encoding='utf-8') as f:
                            f.write(text)
                        text_extracted = True
                except Exception as e:
                    pass  # Silently handle extraction errors
            
            # Save metadata
            metadata_file = doc_dir / f"{doc_id}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(doc_link, f, indent=2, ensure_ascii=False)
            
            # Extract metadata from HTML files
            extracted_metadata = {}
            try:
                # Import here to avoid circular dependency
                from update_metadata_from_html import extract_metadata_from_html, update_document_metadata_in_db
                
                if print_version_path and Path(print_version_path).exists():
                    try:
                        extracted_metadata = extract_metadata_from_html(Path(print_version_path))
                    except Exception as e:
                        logger.warning(f"Could not extract metadata from print version: {e}")
                
                # If print version didn't yield metadata, try regular HTML
                if not any(extracted_metadata.values()) and downloaded_path and Path(downloaded_path).exists():
                    try:
                        extracted_metadata = extract_metadata_from_html(Path(downloaded_path))
                    except Exception as e:
                        logger.warning(f"Could not extract metadata from HTML: {e}")
                
                # Merge extracted metadata with existing doc_link metadata
                if extracted_metadata:
                    for key, value in extracted_metadata.items():
                        if value and not doc_link.get(key):
                            doc_link[key] = value
            except ImportError:
                # Module not available, skip metadata extraction
                pass
            except Exception as e:
                logger.warning(f"Metadata extraction failed: {e}")
            
            # Save to database
            db_saved = False
            db_content_saved = 0
            metadata_updated = False
            try:
                # Ensure document exists in database and update with extracted metadata
                if ensure_document_in_db(doc_link):
                    db_saved = True
                    
                    # Update metadata if we extracted new information
                    if extracted_metadata and any(extracted_metadata.values()):
                        try:
                            from update_metadata_from_html import update_document_metadata_in_db
                            if update_document_metadata_in_db(doc_id, extracted_metadata):
                                metadata_updated = True
                        except Exception as e:
                            logger.warning(f"Could not update metadata in DB: {e}")
                    
                    # Register document on server if in distributed mode
                    try:
                        from server_document_registry import register_document_on_server
                        # Merge all metadata sources
                        full_metadata = {**doc_link, **extracted_metadata}
                        full_metadata['document_id'] = doc_id
                        server_result = register_document_on_server(full_metadata)
                        if server_result:
                            logger.info(f"Document registered on server: {server_result.get('system_id')}")
                    except ImportError:
                        # Module not available, skip server registration
                        pass
                    except Exception as e:
                        logger.warning(f"Could not register document on server: {e}")
                    
                    # Save content to database
                    if print_version_path and Path(print_version_path).exists():
                        if save_document_content_to_db(
                            document_id=doc_id,
                            content_type='print_html',
                            file_path=Path(print_version_path)
                        ):
                            db_content_saved += 1
                    
                    if downloaded_path and Path(downloaded_path).exists():
                        if save_document_content_to_db(
                            document_id=doc_id,
                            content_type='html',
                            file_path=Path(downloaded_path)
                        ):
                            db_content_saved += 1
                    
                    if txt_file and txt_file.exists():
                        # Read text content for database
                        try:
                            with open(txt_file, 'r', encoding='utf-8') as f:
                                text_content = f.read()
                            if save_document_content_to_db(
                                document_id=doc_id,
                                content_type='text',
                                file_path=txt_file,
                                content_text=text_content
                            ):
                                db_content_saved += 1
                        except Exception as e:
                            logger.warning(f"Could not save text content to DB: {e}")
            except Exception as e:
                logger.warning(f"Database save failed for {doc_id}: {e}")
                # Don't fail the download if DB save fails
            
            result = {
                'document_id': doc_id,
                'reg_number': reg_number,
                'success': True,
                'skipped': False,
                'print_version_saved': bool(print_version_path),
                'html_saved': bool(downloaded_path),
                'text_extracted': text_extracted,
                'db_saved': db_saved,
                'db_content_records': db_content_saved,
                'metadata_extracted': bool(extracted_metadata and any(extracted_metadata.values())),
                'metadata_updated': metadata_updated
            }
            
            # Update progress
            progress.advance(task_id)
            
            return result
            
        except Exception as e:
            progress.advance(task_id)
            return {
                'document_id': doc_id,
                'reg_number': reg_number,
                'success': False,
                'error': str(e)
            }
        finally:
            await handler.close()


async def download_100_documents(start_page: int = None, max_documents: int = None, config_path: Path = None):
    """
    Download documents from a specific page with concurrent connections
    
    Args:
        start_page: Page number to start from (None = use config default)
        max_documents: Maximum number of documents to download (None = use config default)
        config_path: Path to config file (None = use default downloader.config.json)
    """
    # Load configuration
    config = load_config(config_path)
    
    # Use config defaults if not provided
    if start_page is None:
        start_page = config['download_settings']['default_start_page']
    if max_documents is None:
        max_documents = config['download_settings']['default_max_documents']
    
    # Get settings from config
    output_dir = Path(config['output']['directory'])
    concurrent_connections = config['download_settings']['concurrent_connections']
    delay_between_requests = config['download_settings']['delay_between_requests']
    
    # Build search params from config (filter out empty values)
    search_params = {}
    for key, value in config['search_params'].items():
        if value and str(value).strip():  # Only include non-empty values
            search_params[key] = value
    
    output_dir.mkdir(exist_ok=True)
    
    # Display configuration
    config_display = f"[bold cyan]Document Downloader[/bold cyan]\n"
    config_display += f"Starting from page: [yellow]{start_page}[/yellow]\n"
    config_display += f"Target documents: [yellow]{max_documents}[/yellow]\n"
    config_display += f"Output directory: [yellow]{output_dir}[/yellow]\n"
    config_display += f"Concurrent connections: [yellow]{concurrent_connections}[/yellow]\n"
    config_display += f"\n[dim]Search Parameters:[/dim]\n"
    for key, value in search_params.items():
        config_display += f"  [dim]{key}:[/dim] {value}\n"
    
    console.print(Panel.fit(
        config_display,
        title="Configuration",
        border_style="cyan"
    ))
    
    # Create a handler for navigation
    search_handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=delay_between_requests
        )
    )
    
    try:
        # Step 1: Perform search
        with console.status("[bold green]Performing search...", spinner="dots"):
            
            page = await search_handler.search(search_params, wait_for_results=True)
            
            if not page:
                console.print("[bold red]✗ Search failed[/bold red]")
                return
            
            await asyncio.sleep(2)
        
        # Step 2: Navigate to desired page
        if start_page > 1:
            with console.status(f"[bold green]Navigating to page {start_page}...", spinner="dots"):
                try:
                    page_link = await page.query_selector(f'a:has-text("{start_page}")')
                    if page_link:
                        await page_link.click()
                        await page.wait_for_load_state('networkidle', timeout=10000)
                        await asyncio.sleep(2)
                    else:
                        page_url = f"/Page/{start_page}"
                        await search_handler._rate_limit()
                        page = await search_handler.navigate(page_url)
                        if page:
                            await asyncio.sleep(2)
                except Exception:
                    page_url = f"/Page/{start_page}"
                    await search_handler._rate_limit()
                    page = await search_handler.navigate(page_url)
                    if page:
                        await asyncio.sleep(2)
        
        # Step 3: Extract document links
        with console.status("[bold green]Extracting document links...", spinner="dots"):
            all_document_links = []
            current_page = start_page
            
            while len(all_document_links) < max_documents:
                page_links = await search_handler.extract_document_links(max_links=None)
                
                if not page_links:
                    break
                
                remaining_needed = max_documents - len(all_document_links)
                links_to_add = page_links[:remaining_needed]
                all_document_links.extend(links_to_add)
                
                if len(all_document_links) >= max_documents:
                    break
                
                # Navigate to next page
                current_page += 1
                try:
                    next_page_link = await page.query_selector(f'a:has-text("{current_page}")')
                    if next_page_link:
                        await next_page_link.click()
                        await page.wait_for_load_state('networkidle', timeout=10000)
                        await asyncio.sleep(2)
                    else:
                        await search_handler._rate_limit()
                        page = await search_handler.navigate(f"/Page/{current_page}")
                        if not page:
                            break
                        await asyncio.sleep(2)
                except Exception:
                    await search_handler._rate_limit()
                    page = await search_handler.navigate(f"/Page/{current_page}")
                    if not page:
                        break
                    await asyncio.sleep(2)
        
        document_links = all_document_links[:max_documents]
        
        if not document_links:
            console.print("[bold red]✗ No documents found[/bold red]")
            return
        
        # Filter out documents that already have content in database (resume support)
        console.print(f"\n[bold cyan]Checking database for existing documents...[/bold cyan]")
        documents_to_download = []
        already_downloaded = []
        
        for doc_link in document_links:
            doc_id = doc_link.get('id', '')
            if doc_id and document_has_content_in_db(doc_id):
                already_downloaded.append(doc_id)
            else:
                documents_to_download.append(doc_link)
        
        if already_downloaded:
            console.print(f"[yellow]Skipping {len(already_downloaded)} already downloaded documents[/yellow]")
        
        if not documents_to_download:
            console.print("[bold green]✓ All documents already downloaded![/bold green]")
            return
        
        console.print(f"\n[bold green]✓ Found {len(document_links)} documents[/bold green]")
        console.print(f"[dim]Downloading {len(documents_to_download)} new documents with {concurrent_connections} concurrent connections...[/dim]\n")
        
        # Step 4: Download documents with progress bar
        semaphore = asyncio.Semaphore(concurrent_connections)
        
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
                "[bold cyan]Downloading documents...",
                total=len(documents_to_download)
            )
            
            # Process all documents concurrently
            tasks = [
                process_single_document(
                    doc_link=doc_link,
                    doc_index=i + 1,
                    total_docs=len(documents_to_download),
                    output_dir=output_dir,
                    semaphore=semaphore,
                    progress=progress,
                    task_id=task_id
                )
                for i, doc_link in enumerate(documents_to_download)
            ]
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
            
            # Add skipped documents to results
            for doc_id in already_downloaded:
                results.append({
                    'document_id': doc_id,
                    'reg_number': doc_id,
                    'success': True,
                    'skipped': True,
                    'reason': 'already_in_database'
                })
        
        # Step 5: Save summary
        summary_file = output_dir / "download_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_documents': len(document_links),
                'already_downloaded': len(already_downloaded),
                'new_downloads': len(documents_to_download),
                'successful': sum(1 for r in results if r.get('success')),
                'failed': sum(1 for r in results if not r.get('success')),
                'skipped': sum(1 for r in results if r.get('skipped')),
                'print_versions_saved': sum(1 for r in results if r.get('print_version_saved')),
                'text_extracted': sum(1 for r in results if r.get('text_extracted')),
                'db_saved': sum(1 for r in results if r.get('db_saved')),
                'db_content_records': sum(r.get('db_content_records', 0) for r in results),
                'metadata_extracted': sum(1 for r in results if r.get('metadata_extracted')),
                'metadata_updated': sum(1 for r in results if r.get('metadata_updated')),
                'results': results
            }, f, indent=2, ensure_ascii=False)
        
        # Step 6: Display summary table
        successful = sum(1 for r in results if r.get('success') and not r.get('skipped'))
        skipped = sum(1 for r in results if r.get('skipped'))
        print_versions = sum(1 for r in results if r.get('print_version_saved'))
        text_extracted = sum(1 for r in results if r.get('text_extracted'))
        db_saved = sum(1 for r in results if r.get('db_saved'))
        db_content_records = sum(r.get('db_content_records', 0) for r in results)
        metadata_extracted = sum(1 for r in results if r.get('metadata_extracted'))
        metadata_updated = sum(1 for r in results if r.get('metadata_updated'))
        failed = sum(1 for r in results if not r.get('success'))
        
        summary_table = Table(title="Download Summary", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        summary_table.add_column("Metric", style="cyan", no_wrap=True)
        summary_table.add_column("Value", style="magenta", justify="right")
        
        summary_table.add_row("Total Documents", str(len(document_links)))
        summary_table.add_row("Already Downloaded", f"[yellow]{len(already_downloaded)}[/yellow]" if already_downloaded else "0")
        summary_table.add_row("New Downloads", str(len(documents_to_download)))
        summary_table.add_row("Successful", f"[green]{successful}[/green]")
        summary_table.add_row("Skipped", f"[yellow]{skipped}[/yellow]" if skipped > 0 else "0")
        summary_table.add_row("Failed", f"[red]{failed}[/red]" if failed > 0 else "0")
        summary_table.add_row("Print Versions", str(print_versions))
        summary_table.add_row("Text Extracted", str(text_extracted))
        summary_table.add_row("Saved to Database", f"[green]{db_saved}[/green]" if db_saved > 0 else "[yellow]0[/yellow]")
        summary_table.add_row("DB Content Records", str(db_content_records))
        summary_table.add_row("Metadata Extracted", f"[green]{metadata_extracted}[/green]" if metadata_extracted > 0 else "[yellow]0[/yellow]")
        summary_table.add_row("Metadata Updated", f"[green]{metadata_updated}[/green]" if metadata_updated > 0 else "[yellow]0[/yellow]")
        
        console.print("\n")
        console.print(summary_table)
        console.print(f"\n[dim]All files saved to: [cyan]{output_dir}/[/cyan][/dim]")
        console.print(f"[dim]Summary saved to: [cyan]{summary_file}[/cyan][/dim]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await search_handler.close()


if __name__ == "__main__":
    import sys
    
    # Allow customization via command line
    start_page = None  # None = use config default
    max_docs = None    # None = use config default
    config_path = None
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--config' or arg == '-c':
            if i + 1 < len(sys.argv):
                config_path = Path(sys.argv[i + 1])
                i += 2
            else:
                console.print("[red]Error: --config requires a file path[/red]")
                sys.exit(1)
        elif arg.startswith('--'):
            console.print(f"[red]Unknown option: {arg}[/red]")
            sys.exit(1)
        else:
            # Positional arguments: start_page, max_documents
            if start_page is None:
                try:
                    start_page = int(arg)
                except ValueError:
                    console.print(f"[red]Error: Invalid start_page: {arg}[/red]")
                    sys.exit(1)
            elif max_docs is None:
                try:
                    max_docs = int(arg)
                except ValueError:
                    console.print(f"[red]Error: Invalid max_documents: {arg}[/red]")
                    sys.exit(1)
            i += 1
    
    asyncio.run(download_100_documents(
        start_page=start_page,
        max_documents=max_docs,
        config_path=config_path
    ))
