# Document Download Guide

## Overview

The script now includes functionality to:
1. **Extract document links** from search results
2. **Download documents** from individual document pages
3. **Save metadata** for each document

## Features

### Document Link Extraction
- Automatically finds all document links in search results
- Extracts metadata: registration number, date, court name, judge, etc.
- Limits number of links extracted (configurable)

### Document Download
- Navigates to each document page
- Attempts to find PDF/download links
- Falls back to saving HTML page if no direct download available
- Saves document metadata as JSON

## Usage

### Integrated in Batch Script

The `small_batch_example.py` script now automatically:
- Extracts document links from search results
- Downloads up to 5 documents per search query (configurable)
- Saves documents in organized folders

```bash
python small_batch_example.py
```

### Standalone Download Script

Use `download_documents_example.py` for focused document downloading:

```bash
python download_documents_example.py
```

## Output Structure

```
batch_results/
├── 20260109_015901_query_1_Київська_область_-_Перша_інстанція.html
├── 20260109_015901_query_1_screenshot.png
└── 20260109_015901_query_1_documents/  # Documents folder
    ├── 101476997_101476997.html         # Document HTML
    ├── 101476997_metadata.json          # Document metadata
    ├── 107872773_107872773.html
    └── 107872773_metadata.json
```

## Document Metadata

Each document includes metadata saved as JSON:

```json
{
  "id": "101476997",
  "url": "/Review/101476997",
  "reg_number": "101476997",
  "decision_type": "Ухвала",
  "decision_date": "21.04.0211",
  "law_date": "26.04.2011",
  "case_type": "Адміністративне",
  "case_number": "2-а-2968/11",
  "court_name": "Києво-Святошинський районний суд Київської області",
  "judge_name": "Усатов Д. Д."
}
```

## Configuration

### Limit Document Links Extracted

In `small_batch_example.py`:
```python
document_links = await handler.extract_document_links(max_links=10)  # Change this number
```

### Limit Documents Downloaded

In `small_batch_example.py`:
```python
for doc_idx, doc_link in enumerate(document_links[:5], 1):  # Change 5 to desired limit
```

## How It Works

1. **Search**: Performs search and gets results page
2. **Extract Links**: Finds all `/Review/{id}` links in results table
3. **Extract Metadata**: Gets document info from table rows
4. **Download**: For each document:
   - Navigates to document page
   - Looks for PDF/download links
   - If found, downloads the file
   - If not found, saves the HTML page (which contains the document)
5. **Save**: Saves document and metadata to organized folders

## Notes

- Documents are saved as HTML files (the full document content is in the HTML)
- Rate limiting is applied between document downloads (4 seconds default)
- If a document page doesn't have a direct download link, the HTML page is saved instead
- Metadata is always saved as JSON for easy parsing later

## Customization

### Change Download Limit

Edit `small_batch_example.py`:
```python
# Change from 5 to your desired number
for doc_idx, doc_link in enumerate(document_links[:10], 1):  # Now downloads 10
```

### Download All Documents

Remove the limit:
```python
for doc_idx, doc_link in enumerate(document_links, 1):  # Downloads all
```

### Change Output Directory

```python
documents_dir = output_dir / f"{timestamp}_query_{i}_documents"
# Change to:
documents_dir = Path("my_custom_folder") / f"{timestamp}_query_{i}_documents"
```

## Troubleshooting

### No Documents Found
- Check if search returned results
- Verify the search parameters are correct
- The page might need more time to load

### Download Fails
- Check internet connection
- Verify rate limiting isn't too aggressive
- The document page might require authentication
- Check error logs for specific issues

### Documents Saved as HTML
- This is normal if no direct PDF link exists
- The HTML contains the full document text
- You can parse the HTML to extract text content later

## Next Steps

1. **Parse HTML Documents**: Extract text content from saved HTML files
2. **Convert to PDF**: Convert HTML documents to PDF format
3. **Database Storage**: Store document metadata in a database
4. **Bulk Processing**: Process all documents from multiple searches
