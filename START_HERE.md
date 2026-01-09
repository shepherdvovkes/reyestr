# Getting Started with Small Batches

## Quick Start

### Step 1: Test with a Single Search

Start with just one search to verify everything works:

```bash
python small_batch_example.py single
```

This will:
- Make one search request
- Save the result to `single_search_result.html`
- Take a screenshot
- Check for CAPTCHA

### Step 2: Run a Small Batch (3 searches)

Once the single search works, try a small batch:

```bash
python small_batch_example.py
```

This will:
- Make 3 search requests
- Save all results to `batch_results/` directory
- Generate a summary JSON file
- Take screenshots for each search

### Step 3: Review Results

Check the generated files:
- `batch_results/*.html` - HTML responses
- `batch_results/*.png` - Screenshots
- `batch_results/*_summary.json` - Summary of all requests

### Step 4: Gradually Scale Up

Once you're comfortable with 3 searches:
1. Edit `small_batch_example.py`
2. Increase the number of queries in `search_queries` list
3. Try 5, then 10, then 20 searches
4. Monitor for any issues

## Configuration Tips

### For Very Small Batches (1-5 searches)
```python
PlaywrightConfig(
    delay_between_requests=3.0,  # 3 seconds
)
```

### For Small Batches (5-20 searches)
```python
PlaywrightConfig(
    delay_between_requests=4.0,  # 4 seconds (more conservative)
)
```

### For Medium Batches (20-50 searches)
```python
PlaywrightConfig(
    delay_between_requests=5.0,  # 5 seconds (very conservative)
)
```

## What to Watch For

1. **CAPTCHA Challenges**: If you see CAPTCHA warnings, slow down
2. **Rate Limiting**: If requests start failing, increase delays
3. **Timeouts**: If pages don't load, increase timeout
4. **Errors**: Check error screenshots in `batch_results/`

## Example: Custom Small Batch

Edit `small_batch_example.py` to customize your searches:

```python
search_queries = [
    {
        'name': 'My Custom Search 1',
        'CourtRegion': '11',
        'INSType': '1',
        'SearchExpression': 'some keyword',  # Optional
    },
    {
        'name': 'My Custom Search 2',
        'CourtRegion': '14',
        'INSType': '2',
    },
    # Add more queries here...
]
```

## Best Practices

1. ✅ **Start with 1 search** - Verify it works
2. ✅ **Then try 3 searches** - Test the batch system
3. ✅ **Review results carefully** - Make sure data is correct
4. ✅ **Increase gradually** - Don't jump from 3 to 100
5. ✅ **Monitor for issues** - Watch logs and check for CAPTCHA
6. ✅ **Save results** - Keep HTML files for later parsing
7. ✅ **Respect rate limits** - Don't overload the server

## Troubleshooting

### CAPTCHA Appears
- Slow down (increase `delay_between_requests`)
- Make fewer requests per session
- Consider manual intervention for CAPTCHA

### Requests Timeout
- Increase `timeout` in config
- Check your internet connection
- The website might be slow

### No Results in HTML
- Check the HTML file to see what the page actually contains
- The search might have returned no results
- Form might not have submitted correctly

## Next Steps

Once small batches work reliably:
1. Parse the HTML results to extract data
2. Build a data extraction pipeline
3. Scale up gradually
4. Consider database storage for results
