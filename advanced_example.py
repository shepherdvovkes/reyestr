"""
Advanced example for handling search forms and JavaScript-rendered content
on reyestr.court.gov.ua

This example shows:
1. Form field extraction
2. Search parameter construction
3. Handling JavaScript-rendered content (using Selenium/Playwright)
"""

from bulk_requests import BulkRequestHandler, RequestConfig
import logging
from bs4 import BeautifulSoup
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AdvancedSearchHandler(BulkRequestHandler):
    """
    Extended handler with form parsing and search capabilities
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize session by visiting homepage
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize session by loading homepage and setting cookies"""
        logger.info("Initializing session...")
        response = self.get_page("/")
        if response:
            logger.info("Session initialized successfully")
        else:
            logger.error("Failed to initialize session")
    
    def parse_search_form(self, html: str) -> Dict[str, list]:
        """
        Parse the search form to extract available options
        
        Returns:
            Dictionary with form field names and their options
        """
        soup = BeautifulSoup(html, 'html.parser')
        form_fields = {}
        
        # Example: Extract select options
        selects = soup.find_all('select')
        for select in selects:
            name = select.get('name', '')
            options = [opt.get('value', '') for opt in select.find_all('option')]
            if name and options:
                form_fields[name] = options
        
        return form_fields
    
    def build_search_params(
        self,
        court_region: Optional[str] = None,
        court_name: Optional[str] = None,
        instance: Optional[str] = None,
        judge_name: Optional[str] = None,
        case_number: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        case_type: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Build search parameters dictionary
        
        Args:
            court_region: Court region (e.g., 'Київська область')
            court_name: Court name
            instance: Instance type ('Перша', 'Апеляційна', 'Касаційна')
            judge_name: Judge full name
            case_number: Case number
            date_from: Start date (format: DD.MM.YYYY)
            date_to: End date (format: DD.MM.YYYY)
            case_type: Type of case
            **kwargs: Additional search parameters
        
        Returns:
            Dictionary of search parameters
        """
        params = {}
        
        if court_region:
            params['CourtRegion'] = court_region
        if court_name:
            params['CourtName'] = court_name
        if instance:
            params['Instance'] = instance
        if judge_name:
            params['JudgeName'] = judge_name
        if case_number:
            params['CaseNumber'] = case_number
        if date_from:
            params['DateFrom'] = date_from
        if date_to:
            params['DateTo'] = date_to
        if case_type:
            params['CaseType'] = case_type
        
        # Add any additional parameters
        params.update(kwargs)
        
        return params
    
    def search_and_parse_results(
        self,
        search_params: Dict,
        parse_html: bool = True
    ) -> Optional[Dict]:
        """
        Execute search and parse results
        
        Args:
            search_params: Search parameters dictionary
            parse_html: Whether to parse HTML response
        
        Returns:
            Dictionary with response and parsed data (if parse_html=True)
        """
        response = self.post_search(search_params)
        
        if not response:
            return None
        
        result = {
            'status_code': response.status_code,
            'url': response.url,
            'headers': dict(response.headers)
        }
        
        if parse_html and response.status_code == 200:
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract search results (adjust selectors based on actual HTML)
                results_table = soup.find('table', class_='results') or soup.find('table', id='results')
                if results_table:
                    rows = results_table.find_all('tr')
                    result['results_count'] = len(rows) - 1  # Exclude header
                    result['parsed_html'] = True
                else:
                    result['parsed_html'] = False
                    result['html'] = response.text[:1000]  # First 1000 chars
                    
            except Exception as e:
                logger.error(f"Error parsing HTML: {e}")
                result['parse_error'] = str(e)
        
        return result


# Example usage with Selenium/Playwright for JavaScript-heavy pages
def example_with_selenium():
    """
    Example using Selenium for JavaScript-rendered content
    
    Note: Requires selenium package and a WebDriver
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        import time
        
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get("https://reyestr.court.gov.ua/")
            time.sleep(2)  # Wait for page to load
            
            # Example: Fill search form
            # court_region_select = WebDriverWait(driver, 10).until(
            #     EC.presence_of_element_located((By.NAME, "CourtRegion"))
            # )
            # court_region_select.send_keys("Київська область")
            
            # Submit form
            # submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            # submit_button.click()
            
            # Wait for results
            # results = WebDriverWait(driver, 10).until(
            #     EC.presence_of_element_located((By.CLASS_NAME, "results"))
            # )
            
            html = driver.page_source
            return html
            
        finally:
            driver.quit()
            
    except ImportError:
        logger.warning("Selenium not installed. Install with: pip install selenium")
        return None


if __name__ == "__main__":
    # Example usage
    handler = AdvancedSearchHandler(
        config=RequestConfig(delay_between_requests=3.0)
    )
    
    try:
        # Example 1: Simple search
        search_params = handler.build_search_params(
            court_region="Київська область",
            instance="Перша",
            date_from="01.01.2023",
            date_to="31.12.2023"
        )
        
        logger.info(f"Search parameters: {search_params}")
        result = handler.search_and_parse_results(search_params)
        
        if result:
            logger.info(f"Search completed: {result.get('status_code')}")
            logger.info(f"Results found: {result.get('results_count', 'Unknown')}")
        
        # Example 2: Bulk searches with different parameters
        bulk_searches = [
            handler.build_search_params(
                court_region="Київська область",
                instance="Перша"
            ),
            handler.build_search_params(
                court_region="Львівська область",
                instance="Апеляційна"
            ),
        ]
        
        # Execute bulk searches
        # results = handler.bulk_search(bulk_searches, delay_multiplier=1.5)
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        handler.close()
