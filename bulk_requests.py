"""
Bulk request handler for reyestr.court.gov.ua

⚠️ WARNING: This script is for educational purposes only.
Ensure you comply with the website's terms of service and applicable laws.
"""

import time
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RequestConfig:
    """Configuration for bulk requests"""
    base_url: str = "https://reyestr.court.gov.ua"
    delay_between_requests: float = 2.0  # Minimum seconds between requests
    max_retries: int = 3
    timeout: int = 30
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class BulkRequestHandler:
    """
    Handles bulk requests to reyestr.court.gov.ua with rate limiting
    and error handling.
    """
    
    def __init__(self, config: Optional[RequestConfig] = None):
        self.config = config or RequestConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config.delay_between_requests:
            sleep_time = self.config.delay_between_requests - elapsed
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[requests.Response]:
        """
        Make a single HTTP request with retry logic and rate limiting
        """
        url = urljoin(self.config.base_url, endpoint)
        
        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                
                logger.info(f"Making {method} request to {url} (attempt {attempt + 1})")
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.config.timeout,
                    **kwargs
                )
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                # Check for CAPTCHA or blocking (but don't fail - just warn)
                if self._has_captcha(response):
                    logger.warning("CAPTCHA challenge detected in response. Proceeding anyway...")
                    # Don't return None - let the caller decide what to do
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.config.max_retries})")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Max retries exceeded for timeout")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
        
        return None
    
    def _has_captcha(self, response: requests.Response) -> bool:
        """
        Detect if the response contains a CAPTCHA challenge
        
        Note: This checks for CAPTCHA presence but doesn't necessarily mean
        the request was blocked. The page might just contain CAPTCHA elements
        that are shown conditionally.
        """
        if response.status_code != 200:
            return False
        
        # Check for common CAPTCHA indicators
        content_lower = response.text.lower()
        captcha_indicators = [
            'суму цифр',
            'арифметичного виразу',
            'малюнку',
            'перевірити'
        ]
        
        # More strict check: look for CAPTCHA-related form elements
        # The page might mention CAPTCHA but not require it for viewing
        has_captcha_form = any(indicator in content_lower for indicator in captcha_indicators)
        
        # Check if CAPTCHA is actually blocking (more specific patterns)
        is_blocked = (
            'введіть cуму цифр' in content_lower or
            'введіть в поле результат арифметичного виразу' in content_lower
        )
        
        return is_blocked  # Only return True if actually blocked
    
    def get_page(self, endpoint: str = "/", params: Optional[Dict] = None) -> Optional[requests.Response]:
        """GET request to a specific endpoint"""
        return self._make_request('GET', endpoint, params=params)
    
    def post_search(
        self,
        search_params: Dict,
        endpoint: str = "/Search"
    ) -> Optional[requests.Response]:
        """
        POST a search request
        
        Args:
            search_params: Dictionary of search parameters
            endpoint: Search endpoint (default: /Search)
        """
        return self._make_request('POST', endpoint, data=search_params)
    
    def bulk_search(
        self,
        search_queries: List[Dict],
        delay_multiplier: float = 1.0
    ) -> List[Optional[requests.Response]]:
        """
        Execute multiple search queries with rate limiting
        
        Args:
            search_queries: List of search parameter dictionaries
            delay_multiplier: Multiplier for delay between requests (default: 1.0)
        
        Returns:
            List of response objects (or None for failed requests)
        """
        results = []
        original_delay = self.config.delay_between_requests
        self.config.delay_between_requests = original_delay * delay_multiplier
        
        try:
            for i, query in enumerate(search_queries, 1):
                logger.info(f"Processing search query {i}/{len(search_queries)}")
                response = self.post_search(query)
                results.append(response)
                
                if response is None:
                    logger.warning(f"Query {i} failed")
                else:
                    logger.info(f"Query {i} completed with status {response.status_code}")
        finally:
            self.config.delay_between_requests = original_delay
        
        return results
    
    def close(self):
        """Close the session"""
        self.session.close()


# Example usage
if __name__ == "__main__":
    # Example search parameters (adjust based on actual form fields)
    example_searches = [
        {
            # Example: Search by court region
            'CourtRegion': 'Київська область',
            'Instance': 'Перша',
            # Add other search parameters as needed
        },
        # Add more search queries...
    ]
    
    handler = BulkRequestHandler(
        config=RequestConfig(
            delay_between_requests=3.0,  # 3 seconds between requests
            max_retries=3
        )
    )
    
    try:
        # Test connection
        logger.info("Testing connection...")
        response = handler.get_page("/")
        
        if response and response.status_code == 200:
            logger.info("Connection successful")
            
            # Check for CAPTCHA
            if handler._has_captcha(response):
                logger.warning("⚠️ CAPTCHA detected on homepage. Manual intervention may be required.")
            
            # Example: Execute bulk searches
            # results = handler.bulk_search(example_searches)
            
        else:
            logger.error("Failed to connect to website")
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        handler.close()
