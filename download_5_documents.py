"""
Download documents from a specific page with concurrent connections
"""

import asyncio
from pathlib import Path
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig
import logging
import json
from extract_text_from_print import extract_text_from_html
from typing import Dict
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TaskID
from rich.table import Table
from rich.panel import Panel
from rich import box

# Configure logging to be less verbose (rich will handle display)
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


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
    
    async with semaphore:  # Limit concurrent connections
        try:
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
            
            result = {
                'document_id': doc_id,
                'reg_number': reg_number,
                'success': True,
                'print_version_saved': bool(print_version_path),
                'html_saved': bool(downloaded_path),
                'text_extracted': text_extracted
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


async def download_100_documents(start_page: int = 6, max_documents: int = 100):
    """
    Download documents from a specific page with concurrent connections
    
    Args:
        start_page: Page number to start from (default: 6)
        max_documents: Maximum number of documents to download (default: 100)
    """
    # Create output directory
    output_dir = Path("downloaded_100_documents")
    output_dir.mkdir(exist_ok=True)
    
    console.print(Panel.fit(
        f"[bold cyan]Document Downloader[/bold cyan]\n"
        f"Starting from page: [yellow]{start_page}[/yellow]\n"
        f"Target documents: [yellow]{max_documents}[/yellow]",
        title="Configuration",
        border_style="cyan"
    ))
    
    # Create a handler for navigation
    search_handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=2.0
        )
    )
    
    try:
        # Step 1: Perform search
        with console.status("[bold green]Performing search...", spinner="dots"):
            search_params = {
                'CourtRegion': '11',  # Київська область - to get results
                'INSType': '1',  # Перша instance
            }
            
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
        
        console.print(f"\n[bold green]✓ Found {len(document_links)} documents[/bold green]")
        console.print(f"[dim]Downloading with 5 concurrent connections...[/dim]\n")
        
        # Step 4: Download documents with progress bar
        semaphore = asyncio.Semaphore(5)
        
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
                total=len(document_links)
            )
            
            # Process all documents concurrently
            tasks = [
                process_single_document(
                    doc_link=doc_link,
                    doc_index=i + 1,
                    total_docs=len(document_links),
                    output_dir=output_dir,
                    semaphore=semaphore,
                    progress=progress,
                    task_id=task_id
                )
                for i, doc_link in enumerate(document_links)
            ]
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
        
        # Step 5: Save summary
        summary_file = output_dir / "download_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_documents': len(document_links),
                'successful': sum(1 for r in results if r.get('success')),
                'failed': sum(1 for r in results if not r.get('success')),
                'print_versions_saved': sum(1 for r in results if r.get('print_version_saved')),
                'text_extracted': sum(1 for r in results if r.get('text_extracted')),
                'results': results
            }, f, indent=2, ensure_ascii=False)
        
        # Step 6: Display summary table
        successful = sum(1 for r in results if r.get('success'))
        print_versions = sum(1 for r in results if r.get('print_version_saved'))
        text_extracted = sum(1 for r in results if r.get('text_extracted'))
        failed = len(document_links) - successful
        
        summary_table = Table(title="Download Summary", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        summary_table.add_column("Metric", style="cyan", no_wrap=True)
        summary_table.add_column("Value", style="magenta", justify="right")
        
        summary_table.add_row("Total Documents", str(len(document_links)))
        summary_table.add_row("Successful", f"[green]{successful}[/green]")
        summary_table.add_row("Failed", f"[red]{failed}[/red]" if failed > 0 else "0")
        summary_table.add_row("Print Versions", str(print_versions))
        summary_table.add_row("Text Extracted", str(text_extracted))
        
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
    start_page = 6
    max_docs = 100
    
    if len(sys.argv) > 1:
        start_page = int(sys.argv[1])
    if len(sys.argv) > 2:
        max_docs = int(sys.argv[2])
    
    asyncio.run(download_100_documents(start_page=start_page, max_documents=max_docs))
