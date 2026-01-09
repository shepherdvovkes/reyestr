"""
Test script using Playwright with headless browser
"""

import asyncio
import sys
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_basic_navigation():
    """Test 1: Basic navigation"""
    logger.info("=" * 60)
    logger.info("TEST 1: Basic Navigation with Playwright")
    logger.info("=" * 60)
    
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=2.0
        )
    )
    
    try:
        # Navigate to homepage
        page = await handler.navigate("/")
        
        if page:
            logger.info(f"✓ Navigation successful")
            logger.info(f"  URL: {page.url}")
            
            # Get page title
            title = await page.title()
            logger.info(f"  Title: {title}")
            
            # Check for CAPTCHA
            has_captcha = await handler.check_for_captcha()
            if has_captcha:
                logger.warning("⚠️  CAPTCHA detected")
            else:
                logger.info("✓ No blocking CAPTCHA detected")
            
            # Take screenshot
            await handler.take_screenshot("test_homepage.png")
            logger.info("  Screenshot saved to test_homepage.png")
            
            # Save HTML
            content = await handler.get_page_content()
            if content:
                with open("test_playwright_homepage.html", "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info("  HTML saved to test_playwright_homepage.html")
            
            return True
        else:
            logger.error("✗ Navigation failed")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False
    finally:
        await handler.close()


async def test_search():
    """Test 2: Search functionality"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Search with Playwright")
    logger.info("=" * 60)
    
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=3.0
        )
    )
    
    try:
        # Test search with parameters
        search_params = {
            'CourtRegion': '11',  # Київська область
            'INSType': '1',  # Перша
        }
        
        logger.info(f"Search parameters: {search_params}")
        page = await handler.search(search_params, wait_for_results=True)
        
        if page:
            logger.info(f"✓ Search completed")
            logger.info(f"  URL: {page.url}")
            
            # Check for CAPTCHA
            has_captcha = await handler.check_for_captcha()
            if has_captcha:
                logger.warning("⚠️  CAPTCHA detected after search")
            
            # Take screenshot
            await handler.take_screenshot("test_search_results.png")
            logger.info("  Screenshot saved to test_search_results.png")
            
            # Save HTML
            content = await handler.get_page_content()
            if content:
                with open("test_playwright_search.html", "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info("  HTML saved to test_playwright_search.html")
            
            # Try to find results table or content
            try:
                # Look for common result indicators
                text_content = await handler.get_page_text()
                if text_content:
                    if 'результат' in text_content.lower() or 'знайдено' in text_content.lower():
                        logger.info("  ℹ️  Response appears to contain results")
            except Exception as e:
                logger.warning(f"  Could not extract text: {e}")
            
            return True
        else:
            logger.error("✗ Search failed")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False
    finally:
        await handler.close()


async def test_multiple_searches():
    """Test 3: Multiple searches"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Multiple Searches")
    logger.info("=" * 60)
    
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=4.0  # Longer delay for bulk
        )
    )
    
    try:
        # Define multiple search queries
        search_queries = [
            {
                'CourtRegion': '11',  # Київська область
                'INSType': '1',  # Перша
            },
            {
                'CourtRegion': '14',  # Львівська область
                'INSType': '2',  # Апеляційна
            },
        ]
        
        logger.info(f"Executing {len(search_queries)} searches...")
        results = await handler.bulk_search(search_queries, delay_multiplier=1.0)
        
        successful = sum(1 for r in results if r is not None)
        logger.info(f"\nSummary: {successful}/{len(search_queries)} searches successful")
        
        return successful == len(search_queries)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False
    finally:
        await handler.close()


async def main():
    """Run all tests"""
    logger.info("Starting Playwright tests for reyestr.court.gov.ua")
    logger.info("Using headless browser\n")
    
    results = {
        'navigation': False,
        'search': False,
        'multiple_searches': False
    }
    
    # Test 1: Basic navigation
    results['navigation'] = await test_basic_navigation()
    
    if not results['navigation']:
        logger.error("\n✗ Basic navigation failed. Stopping tests.")
        return results
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Test 2: Search
    results['search'] = await test_search()
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Test 3: Multiple searches
    results['multiple_searches'] = await test_multiple_searches()
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Navigation: {'✓ PASS' if results['navigation'] else '✗ FAIL'}")
    logger.info(f"Search: {'✓ PASS' if results['search'] else '✗ FAIL'}")
    logger.info(f"Multiple searches: {'✓ PASS' if results['multiple_searches'] else '✗ FAIL'}")
    
    logger.info("\nGenerated files:")
    logger.info("  - test_homepage.png")
    logger.info("  - test_search_results.png")
    logger.info("  - test_playwright_homepage.html")
    logger.info("  - test_playwright_search.html")
    
    return results


if __name__ == "__main__":
    try:
        results = asyncio.run(main())
        sys.exit(0 if all(results.values()) else 1)
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}")
        sys.exit(1)
