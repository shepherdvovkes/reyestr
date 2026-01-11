"""
Download Client - Client for distributed download system
Connects to download server and processes tasks
"""
import asyncio
import sys
import time
import socket
import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Import functions from downloader.py
from downloader import (
    download_100_documents,
    DB_CONFIG,
    document_has_content_in_db,
    ensure_document_in_db,
    save_document_content_to_db
)
from client.api_client import DownloadServerClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


def get_client_hostname() -> str:
    """Get client hostname"""
    try:
        return socket.gethostname()
    except:
        return "unknown"


async def process_task_from_server(
    api_client: DownloadServerClient,
    task: Dict[str, Any],
    output_dir: Path
) -> Dict[str, Any]:
    """
    Process a task received from server
    
    Args:
        api_client: API client instance
        task: Task configuration from server
        output_dir: Output directory for downloads
    
    Returns:
        Result summary dictionary
    """
    task_id = task['task_id']
    search_params = task['search_params']
    start_page = task['start_page']
    max_documents = task['max_documents']
    
    console.print(f"\n[bold cyan]Processing Task: {task_id}[/bold cyan]")
    console.print(f"  Start Page: [yellow]{start_page}[/yellow]")
    console.print(f"  Max Documents: [yellow]{max_documents}[/yellow]")
    console.print(f"  Search Params: [dim]{search_params}[/dim]\n")
    
    # Create temporary config for this task
    temp_config = {
        'search_params': search_params,
        'download_settings': {
            'default_start_page': start_page,
            'default_max_documents': max_documents,
            'concurrent_connections': 5,
            'delay_between_requests': 2.0
        },
        'output': {
            'directory': str(output_dir)
        },
        'database': {
            'enabled': True,
            'save_metadata': True,
            'extract_metadata_from_html': True
        }
    }
    
    # Save temp config
    temp_config_path = output_dir / f"task_{task_id}_config.json"
    with open(temp_config_path, 'w', encoding='utf-8') as f:
        json.dump(temp_config, f, indent=2, ensure_ascii=False)
    
    try:
        # Set server context for document registration
        try:
            from server_document_registry import set_server_context
            set_server_context(
                api_client=api_client,
                task_id=task_id,
                search_params=search_params,
                client_id=api_client.client_id
            )
            console.print(f"[dim]Server context set for document registration (client_id: {api_client.client_id})[/dim]")
        except ImportError:
            pass
        
        # Run the download
        await download_100_documents(
            start_page=start_page,
            max_documents=max_documents,
            config_path=temp_config_path
        )
        
        # Read summary file
        summary_file = output_dir / "download_summary.json"
        result_summary = {}
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                result_summary = json.load(f)
        
        # Extract statistics
        documents_downloaded = result_summary.get('successful', 0)
        documents_failed = result_summary.get('failed', 0)
        documents_skipped = result_summary.get('skipped', 0)
        
        return {
            'success': True,
            'documents_downloaded': documents_downloaded,
            'documents_failed': documents_failed,
            'documents_skipped': documents_skipped,
            'result_summary': result_summary,
            'error_message': None
        }
        
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
        return {
            'success': False,
            'documents_downloaded': 0,
            'documents_failed': 0,
            'documents_skipped': 0,
            'result_summary': None,
            'error_message': str(e)
        }
    finally:
        # Clean up temp config
        if temp_config_path.exists():
            temp_config_path.unlink()


async def client_loop(
    api_url: str,
    api_key: Optional[str] = None,
    client_name: Optional[str] = None,
    output_dir: str = "downloaded_documents",
    heartbeat_interval: int = 60,
    poll_interval: int = 5
):
    """
    Main client loop - continuously requests and processes tasks
    
    Args:
        api_url: Base URL of download server
        api_key: Optional API key for authentication
        client_name: Optional client name
        output_dir: Output directory for downloads
        heartbeat_interval: Interval for sending heartbeats (seconds)
        poll_interval: Interval for polling for new tasks (seconds)
    """
    # Initialize API client
    client_host = get_client_hostname()
    api_client = DownloadServerClient(
        base_url=api_url,
        api_key=api_key,
        client_name=client_name or f"client_{client_host}",
        client_host=client_host
    )
    
    # Check server health
    if not api_client.health_check():
        console.print(f"[bold red]✗ Server at {api_url} is not available[/bold red]")
        return
    
    console.print(f"[bold green]✓ Connected to server: {api_url}[/bold green]")
    if api_client.client_id:
        console.print(f"[dim]Client ID: {api_client.client_id}[/dim]")
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    last_heartbeat = time.time()
    task_count = 0
    
    console.print(f"\n[bold cyan]Starting client loop...[/bold cyan]")
    console.print(f"  Poll interval: [yellow]{poll_interval}s[/yellow]")
    console.print(f"  Heartbeat interval: [yellow]{heartbeat_interval}s[/yellow]")
    console.print(f"  Output directory: [yellow]{output_path}[/yellow]\n")
    
    try:
        while True:
            current_time = time.time()
            
            # Send heartbeat if needed
            if current_time - last_heartbeat >= heartbeat_interval:
                if api_client.send_heartbeat():
                    last_heartbeat = current_time
                    logger.debug("Heartbeat sent")
            
            # Request a task
            task = api_client.request_task()
            
            if task:
                task_count += 1
                console.print(f"\n[bold green]Task #{task_count} received[/bold green]")
                
                # Process the task
                result = await process_task_from_server(
                    api_client=api_client,
                    task=task,
                    output_dir=output_path
                )
                
                # Report results to server
                success = api_client.complete_task(
                    task_id=task['task_id'],
                    documents_downloaded=result['documents_downloaded'],
                    documents_failed=result['documents_failed'],
                    documents_skipped=result['documents_skipped'],
                    result_summary=result['result_summary'],
                    error_message=result['error_message']
                )
                
                if success:
                    console.print(f"[bold green]✓ Task {task['task_id']} completed and reported[/bold green]")
                else:
                    console.print(f"[bold yellow]⚠ Task {task['task_id']} completed but reporting failed[/bold yellow]")
                
                # Display summary
                if result['result_summary']:
                    summary = result['result_summary']
                    summary_table = Table(box=box.SIMPLE, show_header=False)
                    summary_table.add_column("Metric", style="cyan")
                    summary_table.add_column("Value", style="magenta", justify="right")
                    
                    summary_table.add_row("Downloaded", str(result['documents_downloaded']))
                    summary_table.add_row("Failed", str(result['documents_failed']))
                    summary_table.add_row("Skipped", str(result['documents_skipped']))
                    
                    console.print("\n")
                    console.print(summary_table)
            else:
                # No tasks available, wait before polling again
                logger.debug(f"No tasks available, waiting {poll_interval}s...")
                await asyncio.sleep(poll_interval)
            
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Client stopped by user[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]✗ Client error: {e}[/bold red]")
        logger.error(f"Client error: {e}", exc_info=True)
        raise


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download Client for Reyestr Distributed Download System"
    )
    parser.add_argument(
        "--api-url",
        required=True,
        help="Base URL of download server (e.g., https://gate-server.com)"
    )
    parser.add_argument(
        "--api-key",
        help="API key for authentication (optional if auth is disabled)"
    )
    parser.add_argument(
        "--client-name",
        help="Client name (default: auto-generated)"
    )
    parser.add_argument(
        "--output-dir",
        default="downloaded_documents",
        help="Output directory for downloads (default: downloaded_documents)"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Interval for polling for new tasks in seconds (default: 5)"
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=60,
        help="Interval for sending heartbeats in seconds (default: 60)"
    )
    parser.add_argument(
        "--db-host",
        help="Database host (overrides default from downloader.py)"
    )
    parser.add_argument(
        "--db-port",
        type=int,
        help="Database port (overrides default from downloader.py)"
    )
    
    args = parser.parse_args()
    
    # Override DB config if provided
    if args.db_host:
        from downloader import DB_CONFIG
        DB_CONFIG['host'] = args.db_host
    if args.db_port:
        from downloader import DB_CONFIG
        DB_CONFIG['port'] = args.db_port
    
    # Display configuration
    config_display = f"[bold cyan]Download Client[/bold cyan]\n"
    config_display += f"Server URL: [yellow]{args.api_url}[/yellow]\n"
    config_display += f"Client Name: [yellow]{args.client_name or 'auto'}[/yellow]\n"
    config_display += f"Output Directory: [yellow]{args.output_dir}[/yellow]\n"
    config_display += f"Poll Interval: [yellow]{args.poll_interval}s[/yellow]\n"
    config_display += f"Heartbeat Interval: [yellow]{args.heartbeat_interval}s[/yellow]\n"
    if args.api_key:
        config_display += f"API Key: [dim]***[/dim]\n"
    
    console.print(Panel.fit(
        config_display,
        title="Configuration",
        border_style="cyan"
    ))
    
    # Run client loop
    try:
        asyncio.run(client_loop(
            api_url=args.api_url,
            api_key=args.api_key,
            client_name=args.client_name,
            output_dir=args.output_dir,
            heartbeat_interval=args.heartbeat_interval,
            poll_interval=args.poll_interval
        ))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Client stopped[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]✗ Fatal error: {e}[/bold red]")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
