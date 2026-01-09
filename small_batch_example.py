"""
Small batch example - Start with a few requests to test the system

This script demonstrates how to make small batch requests safely.
Start with 3-5 requests, then gradually increase.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig
import logging
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def small_batch_search():
    """
    Example: Small batch of 3 searches
    Start small to test the system before scaling up
    """
    logger.info("=" * 60)
    logger.info("Small Batch Search Example")
    logger.info("=" * 60)
    
    # Create output directory for results
    output_dir = Path("batch_results")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Configuration - conservative settings for small batches
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=4.0,  # 4 seconds between requests (conservative)
            timeout=30000
        )
    )
    
    # Define a small batch of search queries
    # Start with just 3 searches to test
    search_queries = [
        {
            'name': 'Київська область - Перша інстанція',
            'CourtRegion': '11',  # Київська область
            'INSType': '1',  # Перша
        },
        {
            'name': 'Львівська область - Апеляційна',
            'CourtRegion': '14',  # Львівська область
            'INSType': '2',  # Апеляційна
        },
        {
            'name': 'Одеська область - Перша інстанція',
            'CourtRegion': '16',  # Одеська область
            'INSType': '1',  # Перша
        },
    ]
    
    results_summary = []
    
    try:
        logger.info(f"Starting batch of {len(search_queries)} searches...")
        logger.info(f"Results will be saved to: {output_dir}/")
        logger.info("")
        
        for i, query in enumerate(search_queries, 1):
            query_name = query.pop('name', f'Query_{i}')
            logger.info(f"[{i}/{len(search_queries)}] Processing: {query_name}")
            logger.info(f"  Parameters: {query}")
            
            try:
                # Perform search
                page = await handler.search(query, wait_for_results=True)
                
                if page:
                    # Check for CAPTCHA
                    has_captcha = await handler.check_for_captcha()
                    if has_captcha:
                        logger.warning(f"  ⚠️  CAPTCHA detected for query {i}")
                        results_summary.append({
                            'query_number': i,
                            'name': query_name,
                            'status': 'captcha_detected',
                            'success': False
                        })
                        continue
                    
                    # Get content
                    content = await handler.get_page_content()
                    text_content = await handler.get_page_text()
                    
                    # Save results
                    result_file = output_dir / f"{timestamp}_query_{i}_{query_name.replace(' ', '_')}.html"
                    with open(result_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Take screenshot
                    screenshot_file = output_dir / f"{timestamp}_query_{i}_screenshot.png"
                    await handler.take_screenshot(str(screenshot_file))
                    
                    # Extract basic info
                    content_length = len(content)
                    has_results = 'результат' in text_content.lower() if text_content else False
                    
                    # Extract document links
                    document_links = await handler.extract_document_links(max_links=10)  # Limit to 10 for testing
                    logger.info(f"    Found {len(document_links)} document links")
                    
                    logger.info(f"  ✓ Success!")
                    logger.info(f"    Content length: {content_length:,} bytes")
                    logger.info(f"    Saved to: {result_file.name}")
                    logger.info(f"    Screenshot: {screenshot_file.name}")
                    logger.info(f"    Appears to have results: {has_results}")
                    logger.info(f"    Document links found: {len(document_links)}")
                    
                    # Download documents and take screenshots if requested
                    downloaded_count = 0
                    screenshots_count = 0
                    if document_links and len(document_links) > 0:
                        logger.info(f"    Processing documents...")
                        documents_dir = output_dir / f"{timestamp}_query_{i}_documents"
                        documents_dir.mkdir(exist_ok=True)
                        
                        for doc_idx, doc_link in enumerate(document_links[:3], 1):  # Limit to 3 for testing
                            try:
                                doc_id = doc_link['id']
                                reg_number = doc_link['reg_number']
                                
                                logger.info(f"      [{doc_idx}/{min(3, len(document_links))}] Processing {reg_number}...")
                                
                                # Download HTML
                                doc_filename = f"{doc_id}_{reg_number}.html"
                                doc_path = documents_dir / doc_filename
                                
                                downloaded_path = await handler.download_document(
                                    doc_link['url'],
                                    str(doc_path)
                                )
                                
                                if downloaded_path:
                                    downloaded_count += 1
                                
                                # Take screenshots of all pages
                                logger.info(f"        Taking screenshots of all pages...")
                                screenshot_paths = await handler.screenshot_document_pages(
                                    doc_link['url'],
                                    str(documents_dir),
                                    doc_id,
                                    page_height=1000,  # Height of each page screenshot
                                    overlap=100  # Overlap to avoid cutting content
                                )
                                
                                if screenshot_paths:
                                    screenshots_count += len(screenshot_paths)
                                    logger.info(f"        ✓ Captured {len(screenshot_paths)} page screenshot(s)")
                                
                                # Save document metadata
                                metadata_file = documents_dir / f"{doc_id}_metadata.json"
                                with open(metadata_file, 'w', encoding='utf-8') as f:
                                    json.dump(doc_link, f, indent=2, ensure_ascii=False)
                                
                            except Exception as e:
                                logger.warning(f"      Failed to process {doc_link.get('reg_number', 'unknown')}: {e}")
                        
                        if downloaded_count > 0 or screenshots_count > 0:
                            logger.info(f"    ✓ Processed {downloaded_count} documents, {screenshots_count} page screenshots")
                    
                    results_summary.append({
                        'query_number': i,
                        'name': query_name,
                        'status': 'success',
                        'success': True,
                        'content_length': content_length,
                        'has_results': has_results,
                        'file': str(result_file),
                        'screenshot': str(screenshot_file),
                        'document_links_found': len(document_links),
                        'documents_downloaded': downloaded_count,
                        'page_screenshots': screenshots_count
                    })
                else:
                    logger.error(f"  ✗ Search failed for query {i}")
                    results_summary.append({
                        'query_number': i,
                        'name': query_name,
                        'status': 'failed',
                        'success': False
                    })
                    
            except Exception as e:
                logger.error(f"  ✗ Error processing query {i}: {e}")
                results_summary.append({
                    'query_number': i,
                    'name': query_name,
                    'status': 'error',
                    'success': False,
                    'error': str(e)
                })
            
            # Small delay between queries (in addition to rate limiting)
            if i < len(search_queries):
                logger.info("  Waiting before next query...")
                await asyncio.sleep(1)
        
        # Save summary
        summary_file = output_dir / f"{timestamp}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'total_queries': len(search_queries),
                'successful': sum(1 for r in results_summary if r.get('success')),
                'failed': sum(1 for r in results_summary if not r.get('success')),
                'results': results_summary
            }, f, indent=2, ensure_ascii=False)
        
        # Print summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("BATCH SUMMARY")
        logger.info("=" * 60)
        successful = sum(1 for r in results_summary if r.get('success'))
        logger.info(f"Total queries: {len(search_queries)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {len(search_queries) - successful}")
        logger.info(f"Summary saved to: {summary_file}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Check the HTML files in batch_results/ to see actual results")
        logger.info("2. Review screenshots to verify form interactions")
        logger.info("3. If successful, gradually increase batch size")
        logger.info("4. Monitor for CAPTCHA or rate limiting issues")
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}", exc_info=True)
    finally:
        await handler.close()


async def single_search_example():
    """
    Even simpler: Just one search to start
    Use this to test before running batches
    """
    logger.info("=" * 60)
    logger.info("Single Search Test")
    logger.info("=" * 60)
    
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=3.0
        )
    )
    
    try:
        # Single search
        search_params = {
            'CourtRegion': '11',  # Київська область
            'INSType': '1',  # Перша
        }
        
        logger.info(f"Search parameters: {search_params}")
        page = await handler.search(search_params)
        
        if page:
            # Check for CAPTCHA
            has_captcha = await handler.check_for_captcha()
            if has_captcha:
                logger.warning("⚠️  CAPTCHA detected!")
            else:
                logger.info("✓ No CAPTCHA detected")
            
            # Save result
            content = await handler.get_page_content()
            with open("single_search_result.html", "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("✓ Result saved to single_search_result.html")
            
            # Screenshot
            await handler.take_screenshot("single_search_screenshot.png")
            logger.info("✓ Screenshot saved to single_search_screenshot.png")
            
        else:
            logger.error("✗ Search failed")
            
    finally:
        await handler.close()


if __name__ == "__main__":
    import sys
    
    # Choose which example to run
    if len(sys.argv) > 1 and sys.argv[1] == "single":
        # Run single search test
        asyncio.run(single_search_example())
    else:
        # Run small batch (default)
        asyncio.run(small_batch_search())
