"""
Example: Open a document and take screenshots of every page
"""

import asyncio
from pathlib import Path
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def screenshot_document_example():
    """
    Example: Open a document and screenshot every page
    """
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=3.0
        )
    )
    
    # Create output directory
    output_dir = Path("document_screenshots")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Initialize browser by navigating to homepage first
        await handler.navigate("/")
        
        # Example document URL (from search results)
        document_url = "/Review/101476997"
        document_id = "101476997"
        
        logger.info(f"Opening document: {document_url}")
        logger.info(f"Output directory: {output_dir}/")
        
        # Take screenshots of all pages
        screenshot_paths = await handler.screenshot_document_pages(
            document_url=document_url,
            output_dir=str(output_dir),
            document_id=document_id,
            page_height=1000,  # Height of each page in pixels
            overlap=100  # Overlap between pages to avoid cutting content
        )
        
        if screenshot_paths:
            logger.info(f"\n✓ Successfully captured {len(screenshot_paths)} page(s)")
            logger.info("Screenshots saved:")
            for path in screenshot_paths:
                logger.info(f"  - {path}")
        else:
            logger.warning("No screenshots were captured")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await handler.close()


async def screenshot_multiple_documents():
    """
    Example: Screenshot multiple documents from search results
    """
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=4.0
        )
    )
    
    output_dir = Path("document_screenshots")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # First, perform a search
        search_params = {
            'CourtRegion': '11',
            'INSType': '1',
        }
        
        logger.info("Performing search...")
        page = await handler.search(search_params)
        
        if not page:
            logger.error("Search failed")
            return
        
        # Extract document links
        logger.info("Extracting document links...")
        document_links = await handler.extract_document_links(max_links=3)  # Limit to 3 for testing
        
        if not document_links:
            logger.warning("No documents found")
            return
        
        logger.info(f"Found {len(document_links)} documents")
        
        # Screenshot each document
        total_screenshots = 0
        for i, doc_link in enumerate(document_links, 1):
            logger.info(f"\n[{i}/{len(document_links)}] Processing document {doc_link['reg_number']}")
            
            doc_dir = output_dir / doc_link['id']
            doc_dir.mkdir(exist_ok=True)
            
            screenshot_paths = await handler.screenshot_document_pages(
                document_url=doc_link['url'],
                output_dir=str(doc_dir),
                document_id=doc_link['id'],
                page_height=1000,
                overlap=100
            )
            
            if screenshot_paths:
                total_screenshots += len(screenshot_paths)
                logger.info(f"  ✓ Captured {len(screenshot_paths)} page(s)")
        
        logger.info(f"\n✓ Total: {total_screenshots} page screenshots across {len(document_links)} documents")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await handler.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "multiple":
        asyncio.run(screenshot_multiple_documents())
    else:
        asyncio.run(screenshot_document_example())
