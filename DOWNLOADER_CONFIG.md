# Downloader Configuration Guide

## Overview

The `downloader.py` script now supports configuration via `downloader.config.json`. This allows you to customize search parameters, download settings, and output options without modifying the code.

## Configuration File

The configuration file `downloader.config.json` contains the following sections:

### Search Parameters (`search_params`)

Configure what documents to search for:

```json
{
  "search_params": {
    "CourtRegion": "11",        // Court region ID
    "INSType": "1",             // Instance type
    "ChairmenName": "",         // Judge name (optional)
    "SearchExpression": "",     // Text search (optional)
    "RegDateBegin": "",         // Registration date from (DD.MM.YYYY)
    "RegDateEnd": "",           // Registration date to (DD.MM.YYYY)
    "DateFrom": "",             // Alternative date from
    "DateTo": ""                // Alternative date to
  }
}
```

#### Court Region IDs

Common region IDs:
- `"11"` - Київська область (Kyiv region)
- `"14"` - Львівська область (Lviv region)
- `"21"` - Запорізька область (Zaporizhzhia region)
- See the reyestr website for full list

#### Instance Types

- `"1"` - Перша інстанція (First instance)
- `"2"` - Апеляційна (Appeal)
- `"3"` - Касаційна (Cassation)

### Download Settings (`download_settings`)

Configure download behavior:

```json
{
  "download_settings": {
    "default_start_page": 6,           // Default page to start from
    "default_max_documents": 100,      // Default max documents to download
    "concurrent_connections": 5,        // Number of parallel downloads
    "delay_between_requests": 2.0      // Seconds between requests
  }
}
```

### Output Settings (`output`)

Configure where files are saved:

```json
{
  "output": {
    "directory": "downloaded_100_documents"  // Output directory name
  }
}
```

### Database Settings (`database`)

Configure database behavior:

```json
{
  "database": {
    "enabled": true,                      // Enable database saving
    "save_metadata": true,                // Save metadata to database
    "extract_metadata_from_html": true    // Extract metadata from HTML
  }
}
```

## Usage Examples

### Basic Usage (Uses Config Defaults)

```bash
# Uses all defaults from downloader.config.json
python3 downloader.py
```

### Override Start Page and Max Documents

```bash
# Start from page 1, download 50 documents
python3 downloader.py 1 50
```

### Use Custom Config File

```bash
# Use a different config file
python3 downloader.py --config my_custom_config.json

# Or with overrides
python3 downloader.py --config my_custom_config.json 1 50
```

## Example Configurations

### Search by Date Range

```json
{
  "search_params": {
    "CourtRegion": "11",
    "INSType": "1",
    "RegDateBegin": "01.01.2026",
    "RegDateEnd": "31.01.2026"
  }
}
```

### Search by Judge Name

```json
{
  "search_params": {
    "CourtRegion": "11",
    "INSType": "1",
    "ChairmenName": "Іванов Іван Іванович"
  }
}
```

### Search with Text

```json
{
  "search_params": {
    "CourtRegion": "11",
    "INSType": "1",
    "SearchExpression": "цивільна справа"
  }
}
```

### Multiple Regions

Note: The current implementation supports single region. For multiple regions, you may need to run multiple downloads or modify the code.

## Configuration Priority

1. **Command line arguments** (highest priority)
   - `start_page` and `max_documents` override config defaults
   
2. **Config file values**
   - Used if not overridden by command line
   
3. **Hardcoded defaults** (lowest priority)
   - Used if config file doesn't exist

## Notes

- Empty string values in `search_params` are automatically filtered out
- If `downloader.config.json` doesn't exist, defaults are used
- Config file is loaded once at startup
- Changes to config file require restarting the script

## Troubleshooting

### Config File Not Found

If the config file doesn't exist, the script will use hardcoded defaults and log:
```
Config file downloader.config.json not found, using defaults
```

### Invalid JSON

If the config file has invalid JSON, the script will use defaults and log a warning.

### Missing Fields

Missing fields in the config file will use default values from the code.
