"""
Standalone example for downloading documents from search results
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


async def download_documents_from_search():
    """
    Example: Search and download documents
    """
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=4.0
        )
    )
    
    # Create output directory
    output_dir = Path("downloaded_documents")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Perform a search
        search_params = {
            'CourtRegion': '11',  # Київська область
            'INSType': '1',  # Перша
        }
        
        logger.info("Performing search...")
        page = await handler.search(search_params)
        
        if not page:
            logger.error("Search failed")
            return
        
        # Extract document links
        logger.info("Extracting document links...")
        document_links = await handler.extract_document_links(max_links=5)  # Limit to 5 for testing
        
        if not document_links:
            logger.warning("No document links found")
            return
        
        logger.info(f"Found {len(document_links)} documents")
        
        # Download each document
        for i, doc_link in enumerate(document_links, 1):
            logger.info(f"\n[{i}/{len(document_links)}] Processing document {doc_link['reg_number']}")
            logger.info(f"  Type: {doc_link.get('decision_type', 'N/A')}")
            logger.info(f"  Date: {doc_link.get('decision_date', 'N/A')}")
            logger.info(f"  Court: {doc_link.get('court_name', 'N/A')[:50]}...")
            
            # Create filename
            safe_reg_number = doc_link['reg_number'].replace('/', '_')
            filename = f"{doc_link['id']}_{safe_reg_number}.html"
            filepath = output_dir / filename
            
            # Download document
            downloaded_path = await handler.download_document(
                doc_link['url'],
                str(filepath)
            )
            
            if downloaded_path:
                logger.info(f"  ✓ Saved to: {filename}")
            else:
                logger.warning(f"  ✗ Failed to download")
        
        logger.info(f"\n✓ Download complete! Files saved to: {output_dir}/")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await handler.close()


if __name__ == "__main__":
    asyncio.run(download_documents_from_search())
