# Bulk Requests to reyestr.court.gov.ua

## Important Considerations

⚠️ **Legal and Ethical Warnings:**

1. **Anti-Scraping Measures**: The website explicitly states (in Ukrainian):
   > "To prevent interference with the stable operation of the Register by making automatic or automated requests for search and copying ('downloading') of the database, an interactive system protection element has been introduced"

2. **Terms of Service**: Review the Rules page (`/Rules`) before bulk requests
3. **Rate Limiting**: Implement respectful rate limiting to avoid overloading the server
4. **Full Access**: Consider using the "Повний доступ" (Full Access) login if available for legitimate use cases

## Best Practices

### 1. **Use Official API (if available)**
   - Check if there's an official API endpoint
   - Contact the website administrators for bulk data access
   - Look for API documentation in the Help section

### 2. **Respectful Scraping**
   - Implement delays between requests (minimum 1-2 seconds)
   - Use proper User-Agent headers
   - Maintain session cookies
   - Handle CAPTCHA challenges appropriately
   - Don't exceed reasonable request volumes

### 3. **Technical Approach**
   - Use `requests` with session management
   - Implement retry logic with exponential backoff
   - Handle rate limiting responses (429 status codes)
   - Parse HTML carefully (site may use JavaScript rendering)
   - Consider using Selenium/Playwright for JavaScript-heavy pages

### 4. **CAPTCHA Handling**
   - The site uses image-based CAPTCHA (sum of digits)
   - For legitimate bulk access, consider:
     - Manual solving for small batches
     - CAPTCHA solving services (if legally compliant)
     - Requesting API access from administrators

## Implementation Examples

### Basic Implementation (`bulk_requests.py`)
Reference implementation using `requests` library:
- Session management
- Rate limiting
- Error handling
- CAPTCHA detection
- Respectful request patterns

### Playwright Implementation (`bulk_requests_playwright.py`) ⭐ RECOMMENDED
**Best for JavaScript-heavy sites** - Uses headless browser:
- Full JavaScript execution
- Handles custom multi-select widgets
- Better CAPTCHA handling
- Screenshot capabilities
- More reliable form interactions
- Rate limiting and error handling

### Advanced Implementation (`advanced_example.py`)
Extended example with:
- Form parsing
- Search parameter building
- HTML result parsing

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. **Playwright (Recommended)** - For JavaScript-heavy sites:
```python
import asyncio
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig

async def main():
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=3.0
        )
    )
    
    # Navigate to a page
    page = await handler.navigate("/")
    
    # Perform a search
    search_params = {
        'CourtRegion': '11',  # Київська область
        'INSType': '1',  # Перша
    }
    result_page = await handler.search(search_params)
    
    # Get content
    content = await handler.get_page_content()
    
    await handler.close()

asyncio.run(main())
```

3. **Basic requests** - For simple HTTP requests:
```python
from bulk_requests import BulkRequestHandler, RequestConfig

handler = BulkRequestHandler(
    config=RequestConfig(delay_between_requests=3.0)
)

# Make a request
response = handler.get_page("/")
handler.close()
```

## Important Notes

- **Start with small batches** to test your implementation
- **Monitor for CAPTCHA challenges** and handle them appropriately
- **Respect rate limits** - increase delays if you encounter 429 errors
- **Check the website's Help section** for official API documentation
- **Consider contacting administrators** for legitimate bulk access needs
