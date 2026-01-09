"""
Extract document links from search results with RegDateBegin = 01.01.2026
and store directly to PostgreSQL database
"""

import asyncio
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, MofNCompleteColumn
from rich.table import Table
from rich import box
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from typing import Dict, List, Optional
import re
import os

console = Console()

# Database connection parameters
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 5433,  # Docker container port (mapped from 5432)
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
        return None


def create_search_session(conn, search_date: str) -> Optional[str]:
    """Create a search session in the database and return session ID"""
    try:
        cur = conn.cursor()
        parsed_date = parse_date(search_date)
        if not parsed_date:
            parsed_date = datetime.now().date()
        
        cur.execute("""
            INSERT INTO search_sessions (search_date, total_extracted)
            VALUES (%s, 0)
            RETURNING id
        """, (parsed_date,))
        
        session_id = cur.fetchone()[0]
        conn.commit()
        return str(session_id)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not create search session: {e}[/yellow]")
        conn.rollback()
        return None
    finally:
        cur.close()


def insert_documents_batch(conn, session_id: str, documents: List[Dict]) -> int:
    """Insert a batch of document links into the database (only URLs)"""
    if not documents:
        return 0
    
    try:
        cur = conn.cursor()
        
        # Prepare documents for bulk insert - only store URL and ID
        documents_data = []
        for doc in documents:
            # Extract just the URL and ID
            url = doc.get('url', '')
            doc_id = doc.get('id', '')
            # If no ID, extract from URL
            if not doc_id and url:
                doc_id = url.replace('/Review/', '') if '/Review/' in url else url.split('/')[-1]
            
            if url and doc_id:
                doc_data = (
                    doc_id,
                    session_id,
                    url,
                    doc.get('reg_number', doc_id),  # Use ID as reg_number if not provided
                    None,  # decision_type
                    None,  # decision_date
                    None,  # law_date
                    None,  # case_type
                    None,  # case_number
                    None,  # court_name
                    None   # judge_name
                )
                documents_data.append(doc_data)
        
        # Bulk insert with conflict handling
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
                updated_at = CURRENT_TIMESTAMP
            """,
            documents_data
        )
        
        # Update search session total
        cur.execute("""
            UPDATE search_sessions
            SET total_extracted = (
                SELECT COUNT(*) FROM documents WHERE search_session_id = %s
            )
            WHERE id = %s
        """, (session_id, session_id))
        
        conn.commit()
        inserted_count = len(documents_data)
        return inserted_count
    except Exception as e:
        console.print(f"[yellow]Warning: Error inserting documents batch: {e}[/yellow]")
        conn.rollback()
        return 0
    finally:
        cur.close()


def test_db_connection() -> bool:
    """Test database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        return True
    except Exception as e:
        console.print(f"[bold red]Database connection failed: {e}[/bold red]")
        console.print("[yellow]Make sure PostgreSQL container is running: docker-compose up -d[/yellow]")
        return False


async def extract_page_links(
    page_num: int,
    semaphore: asyncio.Semaphore,
    base_url: str,
    search_params: dict = None
) -> tuple[int, list]:
    """
    Extract links from a single page (used for concurrent processing)
    
    Args:
        page_num: Page number to extract
        semaphore: Semaphore to limit concurrent connections
        base_url: Base URL for navigation
    
    Returns:
        Tuple of (page_num, list of document links)
    """
    # Create a new handler for this task
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=1.0  # Reduced since we have concurrency control
        )
    )
    
    try:
        async with semaphore:
            # Build URL with search parameters if available
            if search_params:
                # Include search parameters in the URL
                from urllib.parse import urlencode
                params_str = urlencode(search_params, doseq=True)
                page_url = f"/Page/{page_num}?{params_str}"
            else:
                page_url = f"/Page/{page_num}"
            
            # Navigate to the page
            page = await handler.navigate(page_url)
            if not page:
                return (page_num, [])
            
            # Wait for page to fully load and document links to appear
            try:
                # Wait for document links to be visible
                await page.wait_for_selector('a.doc_text2[href^="/Review/"]', timeout=10000, state='attached')
            except:
                pass  # Continue even if selector not found immediately
            
            await asyncio.sleep(2)  # Additional wait for page to settle
            
            # Take screenshot of the page before extraction
            try:
                screenshot_path = f"screenshots/page_{page_num:04d}_before_extraction.png"
                await handler.take_screenshot(screenshot_path, full_page=True)
            except:
                pass
            
            # Extract document links
            page_links = await handler.extract_document_links(max_links=None)
            
            # Take screenshot after extraction
            try:
                if page_links and len(page_links) > 0:
                    screenshot_path = f"screenshots/page_{page_num:04d}_extracted_{len(page_links)}_links.png"
                else:
                    screenshot_path = f"screenshots/page_{page_num:04d}_no_links.png"
                await handler.take_screenshot(screenshot_path, full_page=True)
            except:
                pass
            
            if not page_links or len(page_links) == 0:
                # Debug: check if links exist on page
                try:
                    link_count = await page.locator('a.doc_text2[href^="/Review/"]').count()
                    if link_count > 0:
                        console.print(f"[yellow]⚠ Page {page_num}: Found {link_count} links but extraction returned 0[/yellow]")
                except:
                    pass
            
            return (page_num, page_links or [])
    except Exception as e:
        console.print(f"[dim]Error on page {page_num}: {e}[/dim]")
        return (page_num, [])
    finally:
        await handler.close()


async def extract_document_links_from_date_search(
    reg_date_begin: str = "01.01.2026",
    extract_all: bool = True,
    concurrent_connections: int = 1
):
    """
    Extract ALL document links from search results with RegDateBegin date
    
    Args:
        reg_date_begin: Date to search from (format: DD.MM.YYYY)
        extract_all: If True, extract all documents from all pages
        concurrent_connections: Number of concurrent page extractions (default: 1 = sequential)
    
    Returns:
        List of document link dictionaries
    """
    console.print(Panel.fit(
        f"[bold cyan]Document Link Extractor[/bold cyan]\n"
        f"Search date: [yellow]{reg_date_begin}[/yellow]\n"
        f"Mode: [yellow]Extract ALL documents[/yellow]\n"
        f"Concurrent connections: [yellow]{concurrent_connections}[/yellow]\n"
        f"Database: [yellow]PostgreSQL (direct storage)[/yellow]",
        title="Configuration",
        border_style="cyan"
    ))
    
    # Test database connection
    if not test_db_connection():
        console.print("[bold red]Cannot proceed without database connection[/bold red]")
        return []
    
    # Connect to database and create search session
    try:
        db_conn = psycopg2.connect(**DB_CONFIG)
        session_id = create_search_session(db_conn, reg_date_begin)
        if not session_id:
            console.print("[bold red]Failed to create search session[/bold red]")
            db_conn.close()
            return []
        console.print(f"[green]✓[/green] Created search session: [cyan]{session_id}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]Database error: {e}[/bold red]")
        return []
    
    # Initialize handler with retry logic
    max_retries = 3
    handler = None
    for attempt in range(max_retries):
        try:
            handler = PlaywrightBulkHandler(
                config=PlaywrightConfig(
                    headless=True,
                    delay_between_requests=2.0,
                    timeout=60000  # Increase timeout to 60 seconds
                )
            )
            break
        except Exception as e:
            if attempt < max_retries - 1:
                console.print(f"[yellow]Browser initialization failed (attempt {attempt + 1}/{max_retries}), retrying...[/yellow]")
                await asyncio.sleep(2)
            else:
                console.print(f"[bold red]✗ Failed to initialize browser after {max_retries} attempts: {e}[/bold red]")
                return []
    
    if not handler:
        console.print("[bold red]✗ Could not initialize browser[/bold red]")
        return []
    
    all_document_links = []
    
    # Create screenshots directory
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    screenshot_counter = 0
    
    def get_screenshot_path(step_name: str) -> str:
        nonlocal screenshot_counter
        screenshot_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{screenshot_counter:03d}_{step_name}_{timestamp}.png"
        return str(screenshots_dir / filename)
    
    try:
        # Step 1: Navigate and fill search form
        with console.status("[bold green]Navigating to homepage...", spinner="dots"):
            # Try 'commit' first (fastest), then fallback to 'load' if needed
            page = None
            for wait_strategy in ['commit', 'domcontentloaded', 'load']:
                try:
                    console.print(f"[dim]Trying navigation with '{wait_strategy}' strategy...[/dim]")
                    page = await handler.navigate("/", wait_until=wait_strategy)
                    if page:
                        console.print(f"[green]✓[/green] Navigation successful with '{wait_strategy}'")
                        # Take screenshot after navigation
                        screenshot_path = get_screenshot_path("01_navigation_homepage")
                        await handler.take_screenshot(screenshot_path)
                        console.print(f"[dim]Screenshot: {screenshot_path}[/dim]")
                        break
                except Exception as e:
                    console.print(f"[yellow]Navigation with '{wait_strategy}' failed: {e}[/yellow]")
                    continue
            
            if not page:
                console.print("[bold red]✗ Failed to navigate with all strategies[/bold red]")
                # Take screenshot for debugging
                try:
                    if handler.page:
                        screenshot_path = get_screenshot_path("error_navigation_failed")
                        await handler.take_screenshot(screenshot_path)
                        console.print(f"[dim]Screenshot saved to: {screenshot_path}[/dim]")
                except:
                    pass
                return []
            
            # Wait for the search form to be visible (more reliable than networkidle)
            try:
                await page.wait_for_selector('#RegDateBegin', state='visible', timeout=10000)
                console.print("[green]✓[/green] Page loaded and form is ready")
                # Take screenshot of form ready
                screenshot_path = get_screenshot_path("02_form_ready")
                await handler.take_screenshot(screenshot_path)
                console.print(f"[dim]Screenshot: {screenshot_path}[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠ Form element not found, but continuing: {e}[/yellow]")
            
            await asyncio.sleep(1)  # Brief pause for page to settle
        
        # Fill RegDateBegin field
        with console.status("[bold green]Filling RegDateBegin field...", spinner="dots"):
            try:
                reg_date_begin_field = page.locator('#RegDateBegin')
                await reg_date_begin_field.wait_for(state='visible', timeout=5000)
                await reg_date_begin_field.clear()
                await reg_date_begin_field.fill(reg_date_begin)
                console.print(f"[green]✓[/green] Filled RegDateBegin with: [cyan]{reg_date_begin}[/cyan]")
                # Take screenshot after filling form
                screenshot_path = get_screenshot_path("03_form_filled")
                await handler.take_screenshot(screenshot_path)
                console.print(f"[dim]Screenshot: {screenshot_path}[/dim]")
            except Exception as e:
                console.print(f"[bold red]✗ Error filling date field: {e}[/bold red]")
                screenshot_path = get_screenshot_path("error_form_fill")
                await handler.take_screenshot(screenshot_path)
                return []
        
        # Submit search form
        with console.status("[bold green]Submitting search form...", spinner="dots"):
            try:
                submitted = False
                submit_selectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'input[value*="Пошук"]',
                    'button:has-text("Пошук")'
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_button = page.locator(selector).first()
                        count = await submit_button.count()
                        if count > 0:
                            await submit_button.click()
                            submitted = True
                            break
                    except:
                        continue
                
                if not submitted:
                    await reg_date_begin_field.press('Enter')
                
                # Use 'load' instead of 'networkidle' to avoid timeout
                await page.wait_for_load_state('load', timeout=20000)
                await asyncio.sleep(3)  # Increased wait time for results to load
                console.print("[green]✓[/green] Search submitted")
                # Take screenshot after search submission
                screenshot_path = get_screenshot_path("04_search_submitted")
                await handler.take_screenshot(screenshot_path)
                console.print(f"[dim]Screenshot: {screenshot_path}[/dim]")
                
                # Check for CAPTCHA (but don't block if documents are present)
                try:
                    page_content = await page.content()
                    has_captcha_text = 'captcha' in page_content.lower() or 'капча' in page_content.lower()
                    # Check if there are actual document links despite CAPTCHA text
                    doc_links_check = page.locator('a.doc_text2[href^="/Review/"]')
                    link_count = await doc_links_check.count()
                    
                    if has_captcha_text and link_count == 0:
                        console.print("[bold yellow]⚠ CAPTCHA detected and no documents found![/bold yellow]")
                        await page.screenshot(path="error_captcha_detected.png")
                        console.print("[dim]Screenshot saved to: error_captcha_detected.png[/dim]")
                    elif has_captcha_text and link_count > 0:
                        console.print(f"[yellow]⚠ CAPTCHA text found but {link_count} documents are visible - continuing[/yellow]")
                except:
                    pass
                
                # Verify we're on a results page (URL should contain search parameters or /Page/)
                current_url = page.url
                console.print(f"[dim]Current URL after search: {current_url}[/dim]")
                
                # Extract search parameters from URL for use in concurrent mode
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(current_url)
                search_params = parse_qs(parsed_url.query)
                # Store the base URL with search context for concurrent extraction
                search_context_url = current_url.split('?')[0] if '?' in current_url else current_url
                
                # Check if URL indicates we're on a results page
                if '/Page/' not in current_url and 'Search' not in current_url.lower():
                    # Try to wait a bit more and check again
                    console.print("[yellow]Waiting additional time for page to load...[/yellow]")
                    await asyncio.sleep(3)
                    current_url = page.url
                    console.print(f"[dim]URL after additional wait: {current_url}[/dim]")
                    parsed_url = urlparse(current_url)
                    search_params = parse_qs(parsed_url.query)
                    search_context_url = current_url.split('?')[0] if '?' in current_url else current_url
            except Exception as e:
                console.print(f"[bold red]✗ Error submitting form: {e}[/bold red]")
                # Take screenshot for debugging
                try:
                    await page.screenshot(path="error_form_submit.png")
                    console.print("[dim]Screenshot saved to: error_form_submit.png[/dim]")
                except:
                    pass
                return []
        
        # Check result count and calculate total pages
        total_documents = None
        last_page_num = None
        documents_per_page = 25  # Default, will be detected
        
        # Wait a bit more for results to fully render
        console.print("[dim]Waiting for results to load...[/dim]")
        await asyncio.sleep(2)
        
        # Try multiple methods to find result count
        result_text = None
        try:
            # Method 1: Look for span with "знайдено документів"
            # Wait for the span to appear
            try:
                result_span = page.locator('span:has-text("знайдено документів")')
                await result_span.first.wait_for(state='visible', timeout=5000)
            except:
                pass  # Continue even if wait times out
            
            result_span = page.locator('span:has-text("знайдено документів")')
            count = await result_span.count()
            if count > 0:
                result_text = await result_span.first.inner_text()
                console.print(f"[cyan]Search result (method 1):[/cyan] {result_text}")
            else:
                console.print("[yellow]⚠ Result span not found with method 1[/yellow]")
        except Exception as e:
            console.print(f"[dim]Method 1 failed: {e}[/dim]")
        
        # Method 2: Try to find result count in various text patterns
        if not result_text:
            try:
                page_content = await page.content()
                # Try multiple patterns
                patterns = [
                    r'знайдено\s+документів[:\s]*(\d+)',
                    r'всього\s+знайдено[:\s]*(\d+)',
                    r'(\d+)\s+документів',
                    r'(\d+)\s+результат',
                    r'знайдено[:\s]*(\d+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, page_content, re.IGNORECASE)
                    if match:
                        result_text = f"знайдено документів: {match.group(1)}"
                        console.print(f"[cyan]Search result (method 2, pattern '{pattern}'):[/cyan] {result_text}")
                        break
            except Exception as e:
                console.print(f"[dim]Method 2 failed: {e}[/dim]")
        
        # Method 3: Try to find pagination info to infer total
        if not result_text:
            try:
                # Look for pagination elements that might show total pages
                pagination = page.locator('.pagination, .pager, [class*="page"]')
                if await pagination.count() > 0:
                    pagination_text = await pagination.first.inner_text()
                    console.print(f"[cyan]Found pagination:[/cyan] {pagination_text}")
                    # Try to extract page numbers from pagination
                    page_numbers = re.findall(r'\b(\d+)\b', pagination_text)
                    if page_numbers:
                        max_page = max(int(p) for p in page_numbers if p.isdigit())
                        console.print(f"[yellow]Inferred max page from pagination: {max_page}[/yellow]")
                        # If we found a max page, we can estimate total_documents
                        if not total_documents and max_page > 0:
                            estimated_total = max_page * documents_per_page
                            total_documents = estimated_total
                            console.print(f"[yellow]Estimated total documents: {estimated_total} (from pagination)[/yellow]")
            except Exception as e:
                console.print(f"[dim]Method 3 failed: {e}[/dim]")
        
        # Debug: If we still don't have result_text, save page content for analysis
        if not result_text and not total_documents:
            try:
                # Save full page HTML for debugging
                page_content_full = await page.content()
                debug_file = Path("debug_page_content.html")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_content_full)
                console.print(f"[yellow]⚠ Debug: Saved full page content to {debug_file}[/yellow]")
                
                # Check for common issues in the page content
                if 'captcha' in page_content_full.lower() or 'капча' in page_content_full.lower():
                    console.print("[bold red]✗ CAPTCHA detected in page content![/bold red]")
                if 'error' in page_content_full.lower() or 'помилка' in page_content_full.lower():
                    console.print("[yellow]⚠ Error message detected in page content[/yellow]")
                
                # Also take a screenshot
                await page.screenshot(path="debug_search_results.png", full_page=True)
                console.print(f"[yellow]⚠ Debug: Screenshot saved to debug_search_results.png[/yellow]")
            except Exception as e:
                console.print(f"[dim]Could not save debug info: {e}[/dim]")
        
        # Extract total document count from result_text
        if result_text:
            try:
                # Try multiple regex patterns to extract number
                patterns = [
                    r'знайдено\s+документів[:\s]*(\d+)',
                    r'всього\s+знайдено[:\s]*(\d+)',
                    r'(\d+)\s+документів',
                    r'(\d+)\s+результат',
                    r'знайдено[:\s]*(\d+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, result_text, re.IGNORECASE)
                    if match:
                        total_documents = int(match.group(1))
                        console.print(f"[green]✓[/green] Extracted total documents: [cyan]{total_documents:,}[/cyan]")
                        break
            except Exception as e:
                console.print(f"[yellow]Could not parse document count: {e}[/yellow]")
        
        # Try to detect documents per page
        try:
            # Method 1: Check the dropdown for "Кількість записів на сторінці"
            records_per_page_select = page.locator('select[name*="page"], select[id*="page"], select[name*="PageSize"], select[id*="PageSize"]')
            if await records_per_page_select.count() > 0:
                selected_option = await records_per_page_select.first.input_value()
                if selected_option:
                    documents_per_page = int(selected_option)
                    console.print(f"[green]✓[/green] Detected documents per page from dropdown: [cyan]{documents_per_page}[/cyan]")
        except Exception as e:
            console.print(f"[dim]Could not detect from dropdown: {e}[/dim]")
        
        if documents_per_page == 25:  # Still default, try other methods
            try:
                # Method 2: Try to find the text "Кількість записів на сторінці: 25"
                page_text = await page.content()
                page_match = re.search(r'Кількість\s+записів\s+на\s+сторінці[:\s]*(\d+)', page_text, re.IGNORECASE)
                if page_match:
                    documents_per_page = int(page_match.group(1))
                    console.print(f"[green]✓[/green] Detected documents per page from text: [cyan]{documents_per_page}[/cyan]")
            except Exception as e:
                console.print(f"[dim]Could not detect from text: {e}[/dim]")
        
        # Method 3: Count actual documents on current page
        if documents_per_page == 25:
            try:
                doc_links = page.locator('a.doc_text2[href^="/Review/"]')
                actual_count = await doc_links.count()
                if actual_count > 0:
                    documents_per_page = actual_count
                    console.print(f"[green]✓[/green] Detected documents per page from current page: [cyan]{documents_per_page}[/cyan]")
            except Exception as e:
                console.print(f"[dim]Could not count documents on page: {e}[/dim]")
        
        # Calculate last page number if we have total_documents
        if total_documents and documents_per_page:
            last_page_num = (total_documents + documents_per_page - 1) // documents_per_page
            console.print(f"[green]✓[/green] Calculated last page number: [cyan]{last_page_num:,}[/cyan]")
        
        # Display extraction plan
        if total_documents and last_page_num:
            console.print("\n" + "=" * 60)
            console.print("[bold cyan]Extraction Plan[/bold cyan]")
            console.print("=" * 60)
            console.print(f"[cyan]Total documents found:[/cyan] [yellow]{total_documents:,}[/yellow]")
            console.print(f"[cyan]Documents per page:[/cyan] [yellow]{documents_per_page}[/yellow]")
            console.print(f"[cyan]Last page number:[/cyan] [yellow]{last_page_num:,}[/yellow]")
            console.print(f"[cyan]Total pages to process:[/cyan] [yellow]{last_page_num:,}[/yellow]")
            console.print("=" * 60 + "\n")
        else:
            console.print("\n" + "=" * 60)
            console.print("[bold yellow]⚠ Extraction Plan (Fallback Mode)[/bold yellow]")
            console.print("=" * 60)
            if total_documents:
                console.print(f"[cyan]Total documents found:[/cyan] [yellow]{total_documents:,}[/yellow]")
            else:
                console.print(f"[cyan]Total documents found:[/cyan] [yellow]Unknown[/yellow]")
            console.print(f"[cyan]Documents per page:[/cyan] [yellow]{documents_per_page}[/yellow]")
            console.print(f"[cyan]Last page number:[/cyan] [yellow]Unknown - will extract until no more results[/yellow]")
            console.print(f"[cyan]Mode:[/cyan] [yellow]Sequential extraction until empty page[/yellow]")
            console.print("=" * 60 + "\n")
        
        # Step 2: Extract links from all pages
        # If we don't know last_page_num, use fallback mode (sequential until empty)
        if not last_page_num:
            console.print("[yellow]⚠ Using fallback mode: will extract pages sequentially until no more documents found[/yellow]")
            # Set a reasonable maximum to prevent infinite loops
            last_page_num = 10000  # Very high limit, will break on empty page
            console.print("[dim]Maximum pages limit set to 10,000 (will stop earlier if no results found)[/dim]\n")
        
        # Verify we're on a results page before proceeding
        first_page_link_count = 0
        try:
            # Check if there are any document links on the current page
            doc_links_check = page.locator('a.doc_text2[href^="/Review/"]')
            first_page_link_count = await doc_links_check.count()
            if first_page_link_count == 0:
                console.print("[yellow]⚠ Warning: No document links found on current page[/yellow]")
                console.print("[yellow]This might indicate the search returned no results or the page structure changed[/yellow]")
                # Take a screenshot for debugging
                try:
                    await page.screenshot(path="error_no_results.png")
                    console.print("[dim]Screenshot saved to: error_no_results.png[/dim]")
                except:
                    pass
                
                # If we have no links and no total_documents, this is likely a failed search
                if not total_documents:
                    console.print("[bold red]✗ Search appears to have returned no results. Cannot proceed.[/bold red]")
                    console.print("[yellow]Possible reasons:[/yellow]")
                    console.print("  • CAPTCHA blocking the search")
                    console.print("  • Search form not submitted correctly")
                    console.print("  • No documents match the search criteria")
                    console.print("  • Page structure changed")
                    console.print("[dim]Check debug_search_results.png and debug_page_content.html for details[/dim]")
                    return []
            else:
                console.print(f"[green]✓[/green] Found [cyan]{first_page_link_count}[/cyan] document links on first page")
                # If we couldn't determine total_documents but found links, estimate from first page
                if not total_documents and first_page_link_count > 0:
                    # Use first page count as documents_per_page if not detected
                    if documents_per_page == 25:
                        documents_per_page = first_page_link_count
                        console.print(f"[yellow]Using first page count ({first_page_link_count}) as documents per page[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Could not verify results page: {e}[/yellow]")
            # If we can't verify but have no total_documents, be cautious
            if not total_documents:
                console.print("[yellow]⚠ Proceeding with caution - could not verify results page[/yellow]")
        
        # Extract links from the first page (current page after search)
        console.print("\n[bold cyan]Extracting links from first page...[/bold cyan]")
        # Take screenshot before extraction
        screenshot_path = get_screenshot_path("05_before_first_page_extraction")
        await handler.take_screenshot(screenshot_path)
        console.print(f"[dim]Screenshot: {screenshot_path}[/dim]")
        
        first_page_links = []
        try:
            first_page_links = await handler.extract_document_links(max_links=None)
            if first_page_links:
                console.print(f"[green]✓[/green] Found [cyan]{len(first_page_links)}[/cyan] document links on first page")
                # Insert first page links to database
                inserted = insert_documents_batch(db_conn, session_id, first_page_links)
                console.print(f"[green]✓[/green] Inserted [cyan]{inserted}[/cyan] links to database")
                all_document_links.extend(first_page_links)
                # Take screenshot after successful extraction
                screenshot_path = get_screenshot_path("06_first_page_extracted")
                await handler.take_screenshot(screenshot_path)
                console.print(f"[dim]Screenshot: {screenshot_path}[/dim]")
            else:
                console.print("[yellow]⚠ No links found on first page[/yellow]")
                # Take screenshot of empty page
                screenshot_path = get_screenshot_path("07_first_page_empty")
                await handler.take_screenshot(screenshot_path)
                console.print(f"[dim]Screenshot: {screenshot_path}[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠ Error extracting first page: {e}[/yellow]")
            screenshot_path = get_screenshot_path("error_first_page_extraction")
            await handler.take_screenshot(screenshot_path)
        
        # For concurrent processing, we need to know the last page number
        if concurrent_connections > 1 and not last_page_num:
            console.print(f"[yellow]⚠ Cannot use concurrent mode ({concurrent_connections} connections) without knowing last page number[/yellow]")
            console.print("[yellow]Falling back to sequential mode (1 connection)[/yellow]\n")
            concurrent_connections = 1
        
        # Create semaphore for concurrent connections
        semaphore = asyncio.Semaphore(concurrent_connections)
        
        # Create a dictionary to store results by page number
        page_results = {1: first_page_links}  # Store first page results
        
        # Determine progress total
        progress_total = last_page_num if last_page_num and last_page_num < 10000 else None
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%") if progress_total else TextColumn(""),
            TextColumn("•"),
            MofNCompleteColumn(),
            TextColumn("documents"),
            TextColumn("•"),
            TextColumn("[dim]Pages: {task.completed}" + ("/{task.total}" if progress_total else "") + "[/dim]"),
            TimeElapsedColumn(),
            console=console,
            expand=True
        ) as progress:
            
            task_id = progress.add_task(
                "[bold cyan]Extracting document links...",
                total=progress_total
            )
            
            if concurrent_connections == 1:
                # Sequential processing (original method)
                # Start from page 2 since we already extracted page 1
                current_page_num = 2
                consecutive_empty_pages = 0
                max_empty_pages = 2  # Stop after 2 consecutive empty pages
                
                while current_page_num <= last_page_num:
                    progress.update(
                        task_id,
                        description=f"[cyan]Extracting from page {current_page_num}...",
                        completed=current_page_num - 1
                    )
                    
                    try:
                        page_links = await handler.extract_document_links(max_links=None)
                        
                        # Check if page is empty
                        if not page_links or len(page_links) == 0:
                            consecutive_empty_pages += 1
                            console.print(f"[dim]Page {current_page_num}:[/dim] Found [cyan]0[/cyan] documents (empty page {consecutive_empty_pages}/{max_empty_pages})")
                            
                            # If we don't know the exact total, stop after consecutive empty pages
                            if not total_documents and consecutive_empty_pages >= max_empty_pages:
                                console.print(f"[yellow]Stopping: {max_empty_pages} consecutive empty pages detected[/yellow]")
                                break
                            
                            # If we know the total and have reached/exceeded it, stop
                            if total_documents and len(all_document_links) >= total_documents:
                                console.print(f"[green]Stopping: reached expected total of {total_documents} documents[/green]")
                                break
                        else:
                            consecutive_empty_pages = 0  # Reset counter on successful page
                            all_document_links.extend(page_links)
                            page_results[current_page_num] = page_links
                            
                            # Insert to database
                            inserted = insert_documents_batch(db_conn, session_id, page_links)
                            console.print(f"[dim]Page {current_page_num}:[/dim] Found [cyan]{len(page_links)}[/cyan] documents, "
                                        f"inserted [green]{inserted}[/green] to DB, total: [cyan]{len(all_document_links)}[/cyan]")
                        
                        progress.update(task_id, completed=current_page_num)
                        
                        # Navigate to next page
                        current_page_num += 1
                        if current_page_num <= last_page_num:
                            await handler._rate_limit()
                            next_page = await handler.navigate(f"/Page/{current_page_num}")
                            if not next_page:
                                console.print(f"[yellow]Failed to navigate to page {current_page_num}, stopping[/yellow]")
                                screenshot_path = get_screenshot_path(f"error_navigation_page_{current_page_num}")
                                await handler.take_screenshot(screenshot_path)
                                break
                            page = next_page
                            # Take screenshot after navigation to new page
                            screenshot_path = get_screenshot_path(f"page_{current_page_num}_navigated")
                            await handler.take_screenshot(screenshot_path)
                            await asyncio.sleep(1)
                    except Exception as e:
                        console.print(f"[bold red]Error on page {current_page_num}: {e}[/bold red]")
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= max_empty_pages:
                            console.print(f"[yellow]Stopping due to errors[/yellow]")
                            break
                        current_page_num += 1
                        continue
            else:
                # Concurrent processing
                console.print(f"[cyan]Processing {last_page_num} pages with {concurrent_connections} concurrent connections...[/cyan]\n")
                
                # Create tasks for all pages - pass search parameters to preserve context
                # Get search parameters from current URL if available
                current_url = page.url
                search_params_dict = None
                try:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(current_url)
                    params = parse_qs(parsed.query)
                    if params:
                        search_params_dict = params
                        console.print(f"[dim]Preserving search parameters: {list(params.keys())}[/dim]")
                except:
                    pass
                
                # Start from page 2 since we already extracted page 1
                tasks = [
                    extract_page_links(page_num, semaphore, handler.config.base_url, search_params_dict)
                    for page_num in range(2, last_page_num + 1)
                ]
                
                # Process pages in batches to update progress and avoid overwhelming the server
                batch_size = concurrent_connections * 3
                completed_pages = 0
                
                for batch_start in range(0, len(tasks), batch_size):
                    batch = tasks[batch_start:batch_start + batch_size]
                    
                    # Execute batch concurrently
                    results = await asyncio.gather(*batch, return_exceptions=True)
                    
                    # Process results
                    for i, result in enumerate(results):
                        # Page numbers start from 2 (since page 1 is already done)
                        page_num = batch_start + i + 2
                        if isinstance(result, Exception):
                            console.print(f"[yellow]Error on page {page_num}: {result}[/yellow]")
                            page_results[page_num] = []
                        else:
                            page_num_result, page_links = result
                            page_results[page_num_result] = page_links
                            completed_pages += 1
                            
                            # Insert to database
                            if page_links:
                                inserted = insert_documents_batch(db_conn, session_id, page_links)
                                console.print(f"[dim]Page {page_num_result}:[/dim] Found [cyan]{len(page_links)}[/cyan] documents, "
                                            f"inserted [green]{inserted}[/green] to DB")
                            else:
                                console.print(f"[dim]Page {page_num_result}:[/dim] Found [cyan]0[/cyan] documents")
                    
                    # Update progress (include page 1 in count)
                    total_collected = sum(len(links) for links in page_results.values())
                    completed_with_page1 = completed_pages + 1  # Include page 1
                    progress.update(
                        task_id,
                        description=f"[cyan]Extracted {completed_with_page1}/{last_page_num} pages...",
                        completed=completed_with_page1
                    )
                    
                    # Brief pause between batches
                    if batch_start + batch_size < len(tasks):
                        await asyncio.sleep(0.5)
                
                # Sort results by page number and combine
                all_document_links = []
                for page_num in sorted(page_results.keys()):
                    all_document_links.extend(page_results[page_num])
                
                current_page_num = last_page_num
        
        # Step 3: Save results to JSON (backup) and finalize database
        output_file = Path("extracted_document_links.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'search_date': reg_date_begin,
                'total_extracted': len(all_document_links),
                'documents': all_document_links
            }, f, indent=2, ensure_ascii=False)
        
        # Finalize search session
        try:
            cur = db_conn.cursor()
            cur.execute("""
                UPDATE search_sessions
                SET total_extracted = %s
                WHERE id = %s
            """, (len(all_document_links), session_id))
            db_conn.commit()
            cur.close()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not update search session: {e}[/yellow]")
        
        # Display summary
        summary_table = Table(title="Extraction Summary", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        summary_table.add_column("Metric", style="cyan", no_wrap=True)
        summary_table.add_column("Value", style="magenta", justify="right")
        
        # Get database statistics
        try:
            cur = db_conn.cursor()
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT court_name) as courts,
                    COUNT(DISTINCT judge_name) as judges,
                    COUNT(DISTINCT case_type) as case_types
                FROM documents
                WHERE search_session_id = %s
            """, (session_id,))
            db_stats = cur.fetchone()
            cur.close()
        except Exception as e:
            db_stats = None
            console.print(f"[yellow]Warning: Could not get database statistics: {e}[/yellow]")
        
        summary_table.add_row("Search Date", reg_date_begin)
        summary_table.add_row("Session ID", session_id[:8] + "...")
        summary_table.add_row("Total Documents Available", f"{total_documents:,}" if total_documents else "Unknown")
        summary_table.add_row("Documents Extracted", f"{len(all_document_links):,}")
        summary_table.add_row("Documents in Database", f"{db_stats[0]:,}" if db_stats else "N/A")
        summary_table.add_row("Unique Courts", f"{db_stats[1]:,}" if db_stats else "N/A")
        summary_table.add_row("Unique Judges", f"{db_stats[2]:,}" if db_stats else "N/A")
        summary_table.add_row("Unique Case Types", f"{db_stats[3]:,}" if db_stats else "N/A")
        summary_table.add_row("Last Page Number", f"{last_page_num:,}" if last_page_num else "Unknown")
        summary_table.add_row("Pages Processed", str(current_page_num - 1))
        summary_table.add_row("Documents Per Page", str(documents_per_page))
        summary_table.add_row("JSON Backup File", str(output_file))
        
        console.print("\n")
        console.print(summary_table)
        console.print(f"\n[dim]Links saved to: [cyan]{output_file}[/cyan][/dim]")
        console.print(f"[dim]Screenshots saved to: [cyan]{screenshots_dir}/[/cyan] ([yellow]{screenshot_counter}[/yellow] screenshots taken)[/dim]")
        
        # Show sample of first few links
        if all_document_links:
            console.print("\n[bold]Sample links (first 5):[/bold]")
            for i, doc in enumerate(all_document_links[:5], 1):
                console.print(f"  [cyan]{i}.[/cyan] {doc.get('reg_number', 'N/A')} - {doc.get('decision_type', 'N/A')}")
        
        return all_document_links
        
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        import traceback
        error_msg = f"Error: {e}\n{traceback.format_exc()}"
        console.print(f"[dim]{error_msg}[/dim]")
        # Save error to file for debugging
        try:
            with open("extraction_error.log", "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write(f"Search Date: {reg_date_begin}\n")
                f.write(f"Concurrent Connections: {concurrent_connections}\n")
                f.write(f"{error_msg}\n")
                f.write(f"{'='*60}\n")
            console.print("[dim]Error logged to extraction_error.log[/dim]")
        except:
            pass
        return []
    finally:
        try:
            await handler.close()
        except:
            pass
        # Close database connection
        try:
            if 'db_conn' in locals():
                db_conn.close()
                console.print("[dim]Database connection closed[/dim]")
        except:
            pass


if __name__ == "__main__":
    import sys
    
    # Default values
    reg_date = "01.01.2026"
    concurrent = 1  # Default: sequential
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        reg_date = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            concurrent = int(sys.argv[2])
            if concurrent < 1:
                concurrent = 1
        except ValueError:
            console.print(f"[yellow]Invalid concurrent value '{sys.argv[2]}', using default: 1[/yellow]")
            concurrent = 1
    
    links = asyncio.run(extract_document_links_from_date_search(
        reg_date_begin=reg_date,
        extract_all=True,
        concurrent_connections=concurrent
    ))
    
    if links:
        console.print(f"\n[bold green]✓ Successfully extracted {len(links)} document links![/bold green]")
    else:
        console.print("\n[bold red]✗ No links extracted[/bold red]")
