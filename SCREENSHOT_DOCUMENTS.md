# Document Page Screenshot Guide

## Overview

The script can now automatically:
1. **Open documents** from search results
2. **Scroll through the document** page by page
3. **Take screenshots** of each page
4. **Save screenshots** with numbered filenames

## Features

- ✅ Automatic pagination detection
- ✅ Scrolls through long documents
- ✅ Captures each page as a separate screenshot
- ✅ Handles iframe-based documents
- ✅ Fallback to full-page screenshot if needed

## Usage

### Standalone Script

```bash
# Screenshot a single document
python screenshot_document_pages.py

# Screenshot multiple documents from search
python screenshot_document_pages.py multiple
```

### Integrated in Batch Script

The `small_batch_example.py` script now automatically:
- Downloads documents
- Takes screenshots of all pages for each document
- Saves screenshots in organized folders

```bash
python small_batch_example.py
```

## How It Works

1. **Opens document page** - Navigates to `/Review/{id}`
2. **Waits for iframe** - Documents are displayed in an iframe
3. **Calculates pages** - Determines how many pages based on document height
4. **Scrolls and screenshots** - For each page:
   - Scrolls to the page position
   - Takes a screenshot of the iframe
   - Saves with page number (001, 002, 003, etc.)

## Configuration

### Page Height
Controls how much content is captured per screenshot:
```python
page_height=1000  # pixels per page
```

### Overlap
Overlap between pages to avoid cutting content:
```python
overlap=100  # pixels of overlap
```

### Adjusting for Different Document Sizes

For longer documents, you might want to:
- **Increase page_height** - Capture more content per screenshot
- **Decrease overlap** - Reduce overlap if pages are too similar
- **Decrease page_height** - Capture more detailed screenshots

## Output Structure

```
document_screenshots/
├── 101476997_page_001.png
├── 101476997_page_002.png
└── 101476997_page_003.png

# Or in batch results:
batch_results/
└── 20260109_015901_query_1_documents/
    ├── 101476997_page_001.png
    ├── 101476997_page_002.png
    └── 101476997_metadata.json
```

## Example Output

```
Opening document: /Review/101476997
Page loaded, waiting for iframe...
Iframe exists: True
Found iframe frame, getting document height...
Document height: 856px
Will capture 1 page(s)
  Page 1/1 saved
✓ Successfully captured 1 page(s)
```

## Tips

1. **Short documents** - Will capture 1 screenshot
2. **Long documents** - Automatically splits into multiple screenshots
3. **Page numbering** - Files are numbered: `001`, `002`, `003`, etc.
4. **Rate limiting** - 4 seconds between document opens (configurable)

## Troubleshooting

### No Screenshots Captured
- Check if document page loaded correctly
- Verify iframe is present on the page
- Check error logs for specific issues

### Screenshots Are Empty
- Document might need more time to load
- Try increasing wait time in the script
- Check if document requires authentication

### Too Many/Few Pages
- Adjust `page_height` parameter
- Adjust `overlap` parameter
- Check document height calculation

## API Usage

```python
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig

handler = PlaywrightBulkHandler(config=PlaywrightConfig())

# Initialize browser
await handler.navigate("/")

# Screenshot document pages
screenshot_paths = await handler.screenshot_document_pages(
    document_url="/Review/101476997",
    output_dir="screenshots",
    document_id="101476997",
    page_height=1000,
    overlap=100
)

# screenshot_paths will contain: ['screenshots/101476997_page_001.png', ...]
```

## Integration with Batch Processing

When using `small_batch_example.py`, screenshots are automatically taken for each document:

- Up to 3 documents per search query (configurable)
- All pages of each document are screenshotted
- Screenshots saved alongside HTML and metadata
- Summary includes screenshot count
