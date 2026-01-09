"""
Simple test script to make a few requests to reyestr.court.gov.ua
This helps verify the connection and understand the website's response patterns.
"""

import sys
from bulk_requests import BulkRequestHandler, RequestConfig
import logging

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_connection():
    """Test 1: Basic connection to homepage"""
    logger.info("=" * 60)
    logger.info("TEST 1: Basic Connection Test")
    logger.info("=" * 60)
    
    handler = BulkRequestHandler(
        config=RequestConfig(delay_between_requests=2.0)
    )
    
    try:
        response = handler.get_page("/")
        
        if response:
            logger.info(f"✓ Success! Status code: {response.status_code}")
            logger.info(f"  URL: {response.url}")
            logger.info(f"  Content length: {len(response.text)} bytes")
            
            # Check for CAPTCHA (informational only)
            if handler._has_captcha(response):
                logger.warning("⚠️  CAPTCHA challenge detected in response")
                logger.warning("  (This might be a blocking CAPTCHA or just informational)")
            else:
                logger.info("✓ No blocking CAPTCHA detected")
            
            # Check for CAPTCHA-related text (even if not blocking)
            content_lower = response.text.lower()
            if any(word in content_lower for word in ['суму цифр', 'арифметичного виразу']):
                logger.info("  ℹ️  CAPTCHA-related text found (may be informational)")
            
            # Save a sample of the response for inspection
            with open("test_response_sample.html", "w", encoding="utf-8") as f:
                f.write(response.text[:10000])  # First 10000 chars
            logger.info("  Saved sample response to test_response_sample.html")
            
            return True
        else:
            logger.error("✗ Failed to get response")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False
    finally:
        handler.close()


def test_multiple_pages():
    """Test 2: Request multiple pages with delays"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Multiple Page Requests")
    logger.info("=" * 60)
    
    handler = BulkRequestHandler(
        config=RequestConfig(delay_between_requests=3.0)
    )
    
    pages_to_test = [
        ("/", "Homepage"),
        ("/Help", "Help page"),
        ("/Rules", "Rules page"),
    ]
    
    results = []
    
    try:
        for endpoint, description in pages_to_test:
            logger.info(f"\nRequesting: {description} ({endpoint})")
            response = handler.get_page(endpoint)
            
            if response:
                logger.info(f"  ✓ Status: {response.status_code}")
                logger.info(f"  ✓ Length: {len(response.text)} bytes")
                
                if handler._has_captcha(response):
                    logger.warning(f"  ⚠️  CAPTCHA detected on {description}")
                
                results.append({
                    'endpoint': endpoint,
                    'status': response.status_code,
                    'success': True,
                    'has_captcha': handler._has_captcha(response)
                })
            else:
                logger.error(f"  ✗ Failed to get {description}")
                results.append({
                    'endpoint': endpoint,
                    'status': None,
                    'success': False
                })
        
        # Summary
        logger.info("\n" + "-" * 60)
        logger.info("Summary:")
        successful = sum(1 for r in results if r.get('success'))
        logger.info(f"  Successful requests: {successful}/{len(results)}")
        captcha_count = sum(1 for r in results if r.get('has_captcha'))
        if captcha_count > 0:
            logger.warning(f"  Pages with CAPTCHA: {captcha_count}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return results
    finally:
        handler.close()


def test_search_form_inspection():
    """Test 3: Inspect the search form structure"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Search Form Inspection")
    logger.info("=" * 60)
    
    handler = BulkRequestHandler(
        config=RequestConfig(delay_between_requests=2.0)
    )
    
    try:
        response = handler.get_page("/")
        
        if response and response.status_code == 200:
            # Look for form elements in the HTML
            html = response.text.lower()
            
            # Check for common form indicators
            form_indicators = {
                'form tags': '<form' in html,
                'input tags': '<input' in html,
                'select tags': '<select' in html,
                'search endpoint': '/search' in html or 'search' in html,
                'post method': 'method="post"' in html or "method='post'" in html,
            }
            
            logger.info("Form structure indicators found:")
            for indicator, found in form_indicators.items():
                status = "✓" if found else "✗"
                logger.info(f"  {status} {indicator}")
            
            # Try to find form action
            if '<form' in html:
                import re
                form_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
                if form_match:
                    logger.info(f"  Form action found: {form_match.group(1)}")
            
            return True
        else:
            logger.error("Failed to get homepage for form inspection")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    finally:
        handler.close()


def main():
    """Run all tests"""
    logger.info("Starting test suite for reyestr.court.gov.ua")
    logger.info("This will make a few test requests to understand the website behavior\n")
    
    results = {
        'connection': False,
        'multiple_pages': None,
        'form_inspection': False
    }
    
    # Test 1: Basic connection
    results['connection'] = test_basic_connection()
    
    if not results['connection']:
        logger.error("\n✗ Basic connection failed. Stopping tests.")
        return results
    
    # Test 2: Multiple pages
    results['multiple_pages'] = test_multiple_pages()
    
    # Test 3: Form inspection
    results['form_inspection'] = test_search_form_inspection()
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Basic connection: {'✓ PASS' if results['connection'] else '✗ FAIL'}")
    logger.info(f"Multiple pages: {'✓ PASS' if results['multiple_pages'] else '✗ FAIL'}")
    logger.info(f"Form inspection: {'✓ PASS' if results['form_inspection'] else '✗ FAIL'}")
    
    logger.info("\nNext steps:")
    logger.info("1. Check test_response_sample.html to see the actual HTML structure")
    logger.info("2. Inspect the form fields to understand search parameters")
    logger.info("3. Adjust search parameters in advanced_example.py based on findings")
    
    return results


if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0 if results['connection'] else 1)
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}")
        sys.exit(1)
