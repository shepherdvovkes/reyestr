#!/usr/bin/env python3
"""
Check database contents and identify errors
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

# Database connection - using correct port 5433
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 5433,  # Docker container port
    'database': 'reyestr_db',
    'user': 'reyestr_user',
    'password': 'reyestr_password'
}

console = Console()

def check_database():
    """Check database contents and identify issues"""
    
    try:
        console.print(Panel.fit("[bold cyan]Connecting to database...[/bold cyan]", border_style="cyan"))
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check search sessions
        console.print("\n[bold cyan]Search Sessions:[/bold cyan]")
        cur.execute("""
            SELECT 
                id,
                search_date,
                total_extracted,
                created_at,
                updated_at
            FROM search_sessions
            ORDER BY created_at DESC
            LIMIT 10
        """)
        sessions = cur.fetchall()
        
        if sessions:
            table = Table(title="Recent Search Sessions", box=box.ROUNDED, show_header=True, header_style="bold cyan")
            table.add_column("Session ID", style="cyan", no_wrap=False)
            table.add_column("Search Date", style="green")
            table.add_column("Total Extracted", style="yellow", justify="right")
            table.add_column("Created At", style="dim")
            
            for session in sessions:
                table.add_row(
                    str(session['id'])[:8] + "...",
                    str(session['search_date']),
                    str(session['total_extracted']),
                    str(session['created_at'])[:19]
                )
            console.print(table)
        else:
            console.print("[yellow]No search sessions found[/yellow]")
        
        # Check documents
        console.print("\n[bold cyan]Documents Summary:[/bold cyan]")
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT search_session_id) as sessions,
                COUNT(DISTINCT court_name) as courts,
                COUNT(DISTINCT judge_name) as judges,
                COUNT(DISTINCT case_type) as case_types,
                MIN(created_at) as first_doc,
                MAX(created_at) as last_doc
            FROM documents
        """)
        doc_stats = cur.fetchone()
        
        table = Table(title="Documents Statistics", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta", justify="right")
        
        table.add_row("Total Documents", str(doc_stats['total']))
        table.add_row("Search Sessions", str(doc_stats['sessions']))
        table.add_row("Unique Courts", str(doc_stats['courts']))
        table.add_row("Unique Judges", str(doc_stats['judges']))
        table.add_row("Unique Case Types", str(doc_stats['case_types']))
        if doc_stats['first_doc']:
            table.add_row("First Document", str(doc_stats['first_doc'])[:19])
        if doc_stats['last_doc']:
            table.add_row("Last Document", str(doc_stats['last_doc'])[:19])
        
        console.print(table)
        
        # Show sample documents
        if doc_stats['total'] > 0:
            console.print("\n[bold cyan]Sample Documents (first 5):[/bold cyan]")
            cur.execute("""
                SELECT 
                    id,
                    reg_number,
                    decision_type,
                    court_name,
                    decision_date,
                    created_at
                FROM documents
                ORDER BY created_at DESC
                LIMIT 5
            """)
            sample_docs = cur.fetchall()
            
            table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
            table.add_column("ID", style="cyan", no_wrap=False)
            table.add_column("Reg Number", style="green")
            table.add_column("Decision Type", style="yellow")
            table.add_column("Court", style="magenta", no_wrap=False)
            table.add_column("Decision Date", style="dim")
            
            for doc in sample_docs:
                table.add_row(
                    str(doc['id'])[:20] + "..." if len(str(doc['id'])) > 20 else str(doc['id']),
                    str(doc['reg_number'])[:30] if doc['reg_number'] else "N/A",
                    str(doc['decision_type'])[:30] if doc['decision_type'] else "N/A",
                    str(doc['court_name'])[:40] + "..." if doc['court_name'] and len(str(doc['court_name'])) > 40 else (str(doc['court_name']) if doc['court_name'] else "N/A"),
                    str(doc['decision_date']) if doc['decision_date'] else "N/A"
                )
            console.print(table)
        
        # Check document_content
        console.print("\n[bold cyan]Document Content:[/bold cyan]")
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT document_id) as documents_with_content,
                COUNT(DISTINCT content_type) as content_types,
                SUM(file_size_bytes) as total_size_bytes
            FROM document_content
        """)
        content_stats = cur.fetchone()
        
        table = Table(title="Document Content Statistics", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta", justify="right")
        
        table.add_row("Total Content Records", str(content_stats['total']))
        table.add_row("Documents with Content", str(content_stats['documents_with_content']))
        table.add_row("Content Types", str(content_stats['content_types']))
        if content_stats['total_size_bytes']:
            size_mb = content_stats['total_size_bytes'] / (1024 * 1024)
            table.add_row("Total Size", f"{size_mb:.2f} MB")
        else:
            table.add_row("Total Size", "0 MB")
        
        console.print(table)
        
        # Check content types breakdown
        if content_stats['total'] > 0:
            cur.execute("""
                SELECT 
                    content_type,
                    COUNT(*) as count,
                    SUM(file_size_bytes) as total_size
                FROM document_content
                GROUP BY content_type
                ORDER BY count DESC
            """)
            content_types = cur.fetchall()
            
            table = Table(title="Content by Type", box=box.ROUNDED, show_header=True, header_style="bold cyan")
            table.add_column("Content Type", style="cyan")
            table.add_column("Count", style="magenta", justify="right")
            table.add_column("Total Size", style="yellow", justify="right")
            
            for ct in content_types:
                size_mb = (ct['total_size'] or 0) / (1024 * 1024)
                table.add_row(
                    str(ct['content_type']),
                    str(ct['count']),
                    f"{size_mb:.2f} MB"
                )
            console.print(table)
        
        # Check for documents without content
        console.print("\n[bold cyan]Documents Without Content:[/bold cyan]")
        cur.execute("""
            SELECT COUNT(*) as count
            FROM documents d
            LEFT JOIN document_content dc ON d.id = dc.document_id
            WHERE dc.id IS NULL
        """)
        no_content = cur.fetchone()
        if no_content['count'] > 0:
            console.print(f"[yellow]Warning: {no_content['count']} documents have no content stored[/yellow]")
        else:
            console.print("[green]✓ All documents have content[/green]")
        
        # Check for errors - documents with NULL required fields
        console.print("\n[bold cyan]Data Quality Check:[/bold cyan]")
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE url IS NULL OR url = '') as missing_url,
                COUNT(*) FILTER (WHERE reg_number IS NULL OR reg_number = '') as missing_reg_number,
                COUNT(*) FILTER (WHERE search_session_id IS NULL) as missing_session
            FROM documents
        """)
        quality = cur.fetchone()
        
        issues = []
        if quality['missing_url'] > 0:
            issues.append(f"{quality['missing_url']} documents missing URL")
        if quality['missing_reg_number'] > 0:
            issues.append(f"{quality['missing_reg_number']} documents missing registration number")
        if quality['missing_session'] > 0:
            issues.append(f"{quality['missing_session']} documents missing session ID")
        
        if issues:
            console.print("[red]Data Quality Issues Found:[/red]")
            for issue in issues:
                console.print(f"  [yellow]• {issue}[/yellow]")
        else:
            console.print("[green]✓ No data quality issues found[/green]")
        
        # Check for orphaned content (content without document)
        cur.execute("""
            SELECT COUNT(*) as count
            FROM document_content dc
            LEFT JOIN documents d ON dc.document_id = d.id
            WHERE d.id IS NULL
        """)
        orphaned = cur.fetchone()
        if orphaned['count'] > 0:
            console.print(f"\n[yellow]Warning: {orphaned['count']} content records are orphaned (no parent document)[/yellow]")
        
        cur.close()
        conn.close()
        console.print("\n[bold green]✓ Database check complete[/bold green]")
        
    except psycopg2.OperationalError as e:
        console.print(f"[bold red]✗ Database connection failed: {e}[/bold red]")
        console.print("\n[yellow]Possible fixes:[/yellow]")
        console.print("  1. Make sure Docker container is running: [cyan]docker-compose up -d[/cyan]")
        console.print("  2. Check if port 5433 is correct (should match docker-compose.yml)")
        console.print("  3. Verify database credentials")
        console.print("\n[dim]To check container status: docker ps | grep reyestr_db[/dim]")
        return False
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False
    
    return True

if __name__ == "__main__":
    check_database()
