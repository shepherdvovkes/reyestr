# Playwright Implementation Guide

## Overview

The Playwright implementation (`bulk_requests_playwright.py`) uses a headless browser to interact with the reyestr.court.gov.ua website. This is the **recommended approach** because:

1. ✅ Handles JavaScript-rendered content
2. ✅ Works with custom multi-select widgets
3. ✅ Better CAPTCHA detection
4. ✅ Can take screenshots for debugging
5. ✅ More reliable form interactions

## Installation

```bash
# Install Python package
pip install playwright

# Install browser binaries
playwright install chromium
```

## Basic Usage

```python
import asyncio
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig

async def main():
    # Create handler with configuration
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,  # Run in headless mode
            delay_between_requests=3.0,  # 3 seconds between requests
            timeout=30000  # 30 second timeout
        )
    )
    
    try:
        # Navigate to homepage
        page = await handler.navigate("/")
        
        # Perform a search
        search_params = {
            'CourtRegion': '11',  # Київська область
            'INSType': '1',  # Перша instance
        }
        
        result_page = await handler.search(search_params)
        
        if result_page:
            # Get the HTML content
            content = await handler.get_page_content()
            
            # Get text content
            text = await handler.get_page_text()
            
            # Take a screenshot
            await handler.take_screenshot("search_results.png")
            
            # Check for CAPTCHA
            has_captcha = await handler.check_for_captcha()
            if has_captcha:
                print("⚠️ CAPTCHA detected!")
        
    finally:
        await handler.close()

# Run the async function
asyncio.run(main())
```

## Search Parameters

The search form accepts the following parameters:

### Court Region (`CourtRegion`)
- Value: Region ID (string or list)
- Examples: `'11'` (Київська область), `'14'` (Львівська область)
- Can pass multiple: `['11', '14']`

### Instance Type (`INSType`)
- Value: Instance ID (string or list)
- Options:
  - `'1'` - Перша (First instance)
  - `'2'` - Апеляційна (Appeal)
  - `'3'` - Касаційна (Cassation)

### Judge Name (`ChairmenName`)
- Value: Full name of judge (string)
- Example: `'Іванов Іван Іванович'`

### Search Expression (`SearchExpression`)
- Value: Text to search for (string)
- Example: `'цивільна справа'`

### Date Fields
- `RegDateBegin` - Start date (format: DD.MM.YYYY)
- `RegDateEnd` - End date (format: DD.MM.YYYY)
- `ImportDateBegin` - Import start date
- `ImportDateEnd` - Import end date

## Bulk Searches

```python
async def bulk_search_example():
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(delay_between_requests=4.0)
    )
    
    try:
        # Define multiple search queries
        search_queries = [
            {
                'CourtRegion': '11',
                'INSType': '1',
            },
            {
                'CourtRegion': '14',
                'INSType': '2',
            },
            {
                'CourtRegion': '21',
                'INSType': '1',
            },
        ]
        
        # Execute all searches
        results = await handler.bulk_search(search_queries)
        
        # Process results
        for i, page in enumerate(results):
            if page:
                content = await handler.get_page_content()
                # Save or process content
                with open(f"result_{i}.html", "w", encoding="utf-8") as f:
                    f.write(content)
        
    finally:
        await handler.close()

asyncio.run(bulk_search_example())
```

## Configuration Options

```python
PlaywrightConfig(
    base_url="https://reyestr.court.gov.ua",
    delay_between_requests=3.0,  # Seconds between requests
    headless=True,  # Run browser in headless mode
    timeout=30000,  # Page load timeout (ms)
    viewport_width=1920,  # Browser viewport width
    viewport_height=1080,  # Browser viewport height
    user_agent="Mozilla/5.0..."  # Custom user agent
)
```

## Error Handling

The handler includes automatic error handling:
- Retries on timeouts
- Rate limiting enforcement
- CAPTCHA detection
- Screenshot on errors (saved to `error_screenshot.png`)

## Tips

1. **Start with small batches**: Test with 5-10 searches first
2. **Monitor rate limits**: Increase `delay_between_requests` if you get blocked
3. **Use screenshots**: Take screenshots to debug form interactions
4. **Check for CAPTCHA**: Always check `check_for_captcha()` after searches
5. **Save responses**: Save HTML content for later parsing

## Running Tests

```bash
# Run Playwright tests
python test_playwright.py
```

This will:
- Test basic navigation
- Test search functionality
- Test multiple searches
- Generate screenshots and HTML files for inspection
