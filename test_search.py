"""
Test script to try a simple search on reyestr.court.gov.ua
This will help understand how search requests work.
"""

import sys
from bulk_requests import BulkRequestHandler, RequestConfig
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_simple_search():
    """Test a simple search request"""
    logger.info("=" * 60)
    logger.info("Testing Simple Search")
    logger.info("=" * 60)
    
    handler = BulkRequestHandler(
        config=RequestConfig(delay_between_requests=3.0)
    )
    
    try:
        # First, get the homepage to establish session
        logger.info("Step 1: Loading homepage to establish session...")
        home_response = handler.get_page("/")
        
        if not home_response or home_response.status_code != 200:
            logger.error("Failed to load homepage")
            return False
        
        logger.info("✓ Homepage loaded successfully")
        
        # Try a simple search - empty search to see what happens
        logger.info("\nStep 2: Attempting simple search (empty form)...")
        
        # The form posts to "/" with method="post"
        # Let's try with minimal parameters
        search_params = {
            'SearchExpression': '',  # Empty search expression
            # Don't include other fields if empty to keep request minimal
        }
        
        response = handler.post_search(search_params, endpoint="/")
        
        if response:
            logger.info(f"✓ Search request completed")
            logger.info(f"  Status code: {response.status_code}")
            logger.info(f"  URL: {response.url}")
            logger.info(f"  Content length: {len(response.text)} bytes")
            
            # Check if we got results or an error
            if response.status_code == 200:
                # Save response to inspect
                with open("test_search_response.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info("  Saved response to test_search_response.html")
                
                # Check for common indicators
                content_lower = response.text.lower()
                if 'результат' in content_lower or 'знайдено' in content_lower:
                    logger.info("  ℹ️  Response appears to contain results")
                if 'помилка' in content_lower or 'error' in content_lower:
                    logger.warning("  ⚠️  Response may contain an error message")
                if handler._has_captcha(response):
                    logger.warning("  ⚠️  CAPTCHA challenge detected")
            
            return True
        else:
            logger.error("✗ Search request failed")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False
    finally:
        handler.close()


def test_search_with_params():
    """Test search with specific parameters"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Search with Parameters")
    logger.info("=" * 60)
    
    handler = BulkRequestHandler(
        config=RequestConfig(delay_between_requests=3.0)
    )
    
    try:
        # Load homepage first
        handler.get_page("/")
        
        # Try search with a specific region
        logger.info("Attempting search with Київська область, Перша instance...")
        
        search_params = {
            'CourtRegion': '11',  # Київська область (from the HTML we saw)
            'INSType': '1',  # Перша instance
            'SearchExpression': '',  # Empty text search
        }
        
        response = handler.post_search(search_params, endpoint="/")
        
        if response:
            logger.info(f"✓ Search completed")
            logger.info(f"  Status: {response.status_code}")
            logger.info(f"  Length: {len(response.text)} bytes")
            
            if response.status_code == 200:
                with open("test_search_with_params.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info("  Saved response to test_search_with_params.html")
            
            return True
        else:
            logger.error("✗ Search failed")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False
    finally:
        handler.close()


if __name__ == "__main__":
    logger.info("Starting search tests\n")
    
    # Test 1: Simple empty search
    result1 = test_simple_search()
    
    # Wait a bit before next test
    import time
    logger.info("\nWaiting 5 seconds before next test...")
    time.sleep(5)
    
    # Test 2: Search with parameters
    result2 = test_search_with_params()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"Simple search: {'✓ PASS' if result1 else '✗ FAIL'}")
    logger.info(f"Parameterized search: {'✓ PASS' if result2 else '✗ FAIL'}")
    
    logger.info("\nNext steps:")
    logger.info("1. Check test_search_response.html and test_search_with_params.html")
    logger.info("2. Inspect the HTML to see if searches are working")
    logger.info("3. Adjust search parameters based on findings")
