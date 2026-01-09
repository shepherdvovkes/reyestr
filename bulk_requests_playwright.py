"""
Playwright-based bulk request handler for reyestr.court.gov.ua

Uses headless browser to handle JavaScript-rendered content and form interactions.
"""

import time
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PlaywrightConfig:
    """Configuration for Playwright bulk requests"""
    base_url: str = "https://reyestr.court.gov.ua"
    delay_between_requests: float = 3.0  # Minimum seconds between requests
    headless: bool = True
    timeout: int = 30000  # 30 seconds
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class PlaywrightBulkHandler:
    """
    Handles bulk requests using Playwright with headless browser.
    Better for JavaScript-heavy sites and form interactions.
    """
    
    def __init__(self, config: Optional[PlaywrightConfig] = None):
        self.config = config or PlaywrightConfig()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.last_request_time = 0
    
    async def _init_browser(self):
        """Initialize Playwright browser and context"""
        if self.browser is None:
            try:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=self.config.headless,
                    args=['--no-sandbox', '--disable-setuid-sandbox'] if self.config.headless else []
                )
                self.context = await self.browser.new_context(
                    viewport={'width': self.config.viewport_width, 'height': self.config.viewport_height},
                    user_agent=self.config.user_agent,
                    locale='uk-UA',
                    timezone_id='Europe/Kyiv'
                )
                self.page = await self.context.new_page()
                logger.info("Browser initialized")
            except Exception as e:
                logger.error(f"Failed to initialize browser: {e}")
                # Clean up on failure
                if self.browser:
                    try:
                        await self.browser.close()
                    except:
                        pass
                if self.playwright:
                    try:
                        await self.playwright.stop()
                    except:
                        pass
                self.browser = None
                self.playwright = None
                raise
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config.delay_between_requests:
            sleep_time = self.config.delay_between_requests - elapsed
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
        self.last_request_time = time.time()
    
    async def navigate(self, endpoint: str = "/", wait_until: str = "networkidle") -> Optional[Page]:
        """
        Navigate to a page with rate limiting
        
        Args:
            endpoint: URL endpoint to navigate to
            wait_until: When to consider navigation finished
                       Options: 'load', 'domcontentloaded', 'networkidle', 'commit'
        """
        await self._init_browser()
        await self._rate_limit()
        
        url = f"{self.config.base_url}{endpoint}"
        logger.info(f"Navigating to {url} (wait_until: {wait_until})")
        
        try:
            # Use shorter timeout for 'commit' and 'domcontentloaded' as they should be faster
            timeout = 10000 if wait_until in ['commit', 'domcontentloaded'] else self.config.timeout
            await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            logger.info(f"✓ Navigation successful: {self.page.url}")
            return self.page
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return None
    
    async def search(
        self,
        search_params: Dict,
        wait_for_results: bool = True,
        wait_selector: Optional[str] = None
    ) -> Optional[Page]:
        """
        Perform a search by filling out the form
        
        Args:
            search_params: Dictionary of search parameters
            wait_for_results: Whether to wait for results to load
            wait_selector: CSS selector to wait for (e.g., results table)
        """
        await self._init_browser()
        
        # First, navigate to homepage
        page = await self.navigate("/")
        if not page:
            return None
        
        # Wait for page to be fully loaded and JavaScript to execute
        await page.wait_for_load_state('networkidle', timeout=self.config.timeout)
        await asyncio.sleep(1)  # Additional wait for JavaScript widgets to initialize
        
        await self._rate_limit()
        
        logger.info("Filling search form...")
        
        try:
            # Fill search expression if provided
            if 'SearchExpression' in search_params and search_params['SearchExpression']:
                await page.fill('#SearchExpression', search_params['SearchExpression'])
                logger.info(f"  Filled SearchExpression: {search_params['SearchExpression']}")
            
            # Helper function to handle multi-select
            async def handle_multi_select(field_id, field_name, values):
                """Handle custom multi-select dropdown"""
                # Click to open the multi-select dropdown
                await page.click(f'#{field_id}', timeout=5000)
                await asyncio.sleep(0.8)  # Wait for dropdown to fully open
                
                # Check the checkboxes for selected values
                for val in values:
                    checkbox_selector = f'input[name="{field_name}[]"][value="{val}"]'
                    # Make sure checkbox is visible and check it
                    checkbox = page.locator(checkbox_selector)
                    await checkbox.wait_for(state='attached', timeout=5000)
                    await checkbox.check(timeout=5000)
                
                # Find and click the "Прийняти" (Accept) button for this specific dropdown
                # The button is in a div that follows the multiSelectOptions div for this field
                # Use JavaScript to find and click the visible one
                await page.evaluate(f"""
                    (function() {{
                        const field = document.getElementById('{field_id}');
                        if (field) {{
                            const optionsDiv = field.nextElementSibling;
                            if (optionsDiv && optionsDiv.classList.contains('multiSelectOptions')) {{
                                const afterDiv = optionsDiv.nextElementSibling;
                                if (afterDiv && afterDiv.classList.contains('afterSelectOptions')) {{
                                    const okButton = afterDiv.querySelector('.tdOk');
                                    if (okButton) {{
                                        okButton.style.visibility = 'visible';
                                        okButton.style.display = 'block';
                                        okButton.click();
                                    }}
                                }}
                            }}
                        }}
                    }})();
                """)
                await asyncio.sleep(0.5)  # Wait for selection to apply
            
            # Handle CourtRegion (custom multi-select with checkboxes)
            if 'CourtRegion' in search_params:
                region_value = search_params['CourtRegion']
                values = region_value if isinstance(region_value, list) else [region_value]
                await handle_multi_select('CourtRegion', 'CourtRegion', values)
                logger.info(f"  Selected CourtRegion: {values}")
            
            # Handle INSType (custom multi-select with checkboxes)
            if 'INSType' in search_params:
                instance_value = search_params['INSType']
                values = instance_value if isinstance(instance_value, list) else [instance_value]
                await handle_multi_select('INSType', 'INSType', values)
                logger.info(f"  Selected INSType: {values}")
            
            # Handle ChairmenName (judge name)
            if 'ChairmenName' in search_params and search_params['ChairmenName']:
                await page.fill('#ChairmenName', search_params['ChairmenName'])
                logger.info(f"  Filled ChairmenName: {search_params['ChairmenName']}")
            
            # Handle date fields if present
            if 'DateFrom' in search_params:
                await page.fill('input[name="DateFrom"]', search_params['DateFrom'])
            if 'DateTo' in search_params:
                await page.fill('input[name="DateTo"]', search_params['DateTo'])
            
            # Submit the form - look for submit button
            logger.info("Submitting search form...")
            # Try to find submit button - it might be an input or button
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'input[value*="Пошук"]',
                'button:has-text("Пошук")'
            ]
            
            submitted = False
            for selector in submit_selectors:
                try:
                    await page.click(selector, timeout=2000)
                    submitted = True
                    break
                except:
                    continue
            
            if not submitted:
                # Fallback: use form submission via JavaScript
                logger.warning("Could not find submit button, using form.submit()")
                await page.evaluate('document.querySelector("form").submit()')
            
            # Wait for navigation/results
            if wait_for_results:
                if wait_selector:
                    logger.info(f"Waiting for selector: {wait_selector}")
                    await page.wait_for_selector(wait_selector, timeout=self.config.timeout)
                else:
                    # Wait for page to load
                    await page.wait_for_load_state('networkidle', timeout=self.config.timeout)
            
            logger.info(f"✓ Search completed: {page.url}")
            return page
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Take screenshot for debugging
            if self.page:
                await self.page.screenshot(path="error_screenshot.png")
                logger.info("Screenshot saved to error_screenshot.png")
            return None
    
    async def get_page_content(self) -> Optional[str]:
        """Get the current page HTML content"""
        if self.page:
            return await self.page.content()
        return None
    
    async def get_page_text(self) -> Optional[str]:
        """Get the current page text content"""
        if self.page:
            return await self.page.inner_text('body')
        return None
    
    async def check_for_captcha(self) -> bool:
        """Check if CAPTCHA is present on the current page"""
        if not self.page:
            return False
        
        try:
            # Look for CAPTCHA modal or elements
            captcha_selectors = [
                '#modalcaptcha',
                'text=суму цифр',
                'text=арифметичного виразу',
                '[id*="captcha"]'
            ]
            
            for selector in captcha_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    is_visible = await element.is_visible()
                    if is_visible:
                        logger.warning(f"CAPTCHA detected via selector: {selector}")
                        return True
            
            # Check page text
            text = await self.get_page_text()
            if text:
                captcha_phrases = [
                    'введіть cуму цифр',
                    'введіть в поле результат арифметичного виразу'
                ]
                if any(phrase in text.lower() for phrase in captcha_phrases):
                    logger.warning("CAPTCHA-related text detected")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking for CAPTCHA: {e}")
            return False
    
    async def bulk_search(
        self,
        search_queries: List[Dict],
        delay_multiplier: float = 1.0
    ) -> List[Optional[Page]]:
        """
        Execute multiple search queries with rate limiting
        
        Args:
            search_queries: List of search parameter dictionaries
            delay_multiplier: Multiplier for delay between requests
        
        Returns:
            List of page objects (or None for failed requests)
        """
        results = []
        original_delay = self.config.delay_between_requests
        self.config.delay_between_requests = original_delay * delay_multiplier
        
        try:
            for i, query in enumerate(search_queries, 1):
                logger.info(f"Processing search query {i}/{len(search_queries)}")
                page = await self.search(query)
                results.append(page)
                
                if page is None:
                    logger.warning(f"Query {i} failed")
                else:
                    logger.info(f"Query {i} completed")
                    
                    # Check for CAPTCHA
                    if await self.check_for_captcha():
                        logger.warning(f"⚠️  CAPTCHA detected after query {i}")
        finally:
            self.config.delay_between_requests = original_delay
        
        return results
    
    async def take_screenshot(self, filename: str = "screenshot.png", full_page: bool = True):
        """Take a screenshot of the current page"""
        if self.page:
            try:
                await self.page.screenshot(path=filename, full_page=full_page)
                logger.info(f"Screenshot saved to {filename}")
                return filename
            except Exception as e:
                logger.error(f"Failed to take screenshot: {e}")
                return None
        return None
    
    async def extract_document_links(self, max_links: Optional[int] = None) -> List[Dict]:
        """
        Extract document links from search results page
        
        Args:
            max_links: Maximum number of links to extract (None for all)
        
        Returns:
            List of dictionaries with document info:
            [{'id': '101476997', 'url': '/Review/101476997', 'reg_number': '101476997', ...}, ...]
        """
        if not self.page:
            return []
        
        try:
            # Extract links using JavaScript - only collect URLs
            links_data = await self.page.evaluate("""
                () => {
                    const links = [];
                    const docLinks = document.querySelectorAll('a.doc_text2[href^="/Review/"]');
                    
                    docLinks.forEach(link => {
                        const href = link.getAttribute('href');
                        const id = href.replace('/Review/', '');
                        const regNumber = link.textContent.trim();
                        
                        // Only collect URL and basic info
                        const data = {
                            id: id,
                            url: href,
                            reg_number: regNumber || id
                        };
                        links.push(data);
                    });
                    
                    return links;
                }
            """)
            
            if max_links:
                links_data = links_data[:max_links]
            
            logger.info(f"Extracted {len(links_data)} document links")
            return links_data
            
        except Exception as e:
            logger.error(f"Error extracting document links: {e}")
            return []
    
    async def download_print_version(
        self,
        document_url: str,
        output_path: str,
        document_id: str
    ) -> Optional[str]:
        """
        Open a document, click print button, and save the print version
        
        Args:
            document_url: URL to the document page (e.g., '/Review/101476997')
            output_path: Path to save the print version HTML
            document_id: ID for naming files (e.g., '101476997')
        
        Returns:
            Path to saved file or None if failed
        """
        if not self.page:
            logger.error("No page available")
            return None
        
        try:
            full_url = f"{self.config.base_url}{document_url}"
            logger.info(f"Opening document for print version: {full_url}")
            
            await self._rate_limit()
            
            # Navigate to document page
            await self.page.goto(full_url, wait_until='networkidle', timeout=self.config.timeout)
            logger.info("Page loaded, waiting for print button...")
            await asyncio.sleep(3)  # Wait for page to fully load
            
            # Wait for print button
            print_button_selector = '#btnPrint'
            try:
                await self.page.wait_for_selector(print_button_selector, timeout=self.config.timeout)
                logger.info("Print button found")
            except Exception as e:
                logger.error(f"Print button not found: {e}")
                return None
            
            # The print button uses document.write() which replaces the page content
            # We need to capture the content after clicking
            # Set up a listener to capture the new content after document.write()
            
            # Click the print button - this will trigger document.write() and replace page content
            await self.page.click(print_button_selector)
            logger.info("Clicked print button, waiting for print version to load...")
            
            # Wait for the page content to be replaced by document.write()
            await asyncio.sleep(3)  # Give time for document.write() to complete
            
            # Get the new page content (after document.write() replaced it)
            content = await self.page.content()
            logger.info("Captured print version content")
            
            # Save the print version
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✓ Print version saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading print version: {e}", exc_info=True)
            return None
    
    async def screenshot_document_pages(
        self,
        document_url: str,
        output_dir: str,
        document_id: str,
        page_height: int = 1000,
        overlap: int = 100
    ) -> List[str]:
        """
        Open a document and take screenshots of every page
        
        Args:
            document_url: URL to the document page (e.g., '/Review/101476997')
            output_dir: Directory to save screenshots
            document_id: ID for naming files (e.g., '101476997')
            page_height: Height of each page screenshot in pixels
            overlap: Overlap between pages in pixels to avoid cutting content
        
        Returns:
            List of paths to saved screenshot files
        """
        if not self.page:
            logger.error("No page available")
            return []
        
        screenshot_paths = []
        
        try:
            full_url = f"{self.config.base_url}{document_url}"
            logger.info(f"Opening document: {full_url}")
            
            await self._rate_limit()
            
            # Navigate to document page
            await self.page.goto(full_url, wait_until='networkidle', timeout=self.config.timeout)
            logger.info("Page loaded, waiting for iframe...")
            await asyncio.sleep(4)  # Wait for iframe to load content and JavaScript to execute
            
            # Wait for iframe to be ready
            iframe_selector = '#divframe'
            try:
                await self.page.wait_for_selector(iframe_selector, timeout=self.config.timeout)
            except Exception as e:
                logger.error(f"Timeout waiting for iframe: {e}")
                return []
            
            # Try to get iframe - use simpler approach
            try:
                # First, try to screenshot the iframe directly
                iframe_locator = self.page.locator('#divframe')
                iframe_exists = await iframe_locator.count() > 0
                logger.info(f"Iframe exists: {iframe_exists}")
                
                if not iframe_exists:
                    logger.warning("Iframe not found, taking full page screenshot")
                    screenshot_path = f"{output_dir}/{document_id}_page_001.png"
                    await self.page.screenshot(path=screenshot_path, full_page=True)
                    screenshot_paths.append(screenshot_path)
                    logger.info(f"  Captured full page screenshot: {screenshot_path}")
                    return screenshot_paths
                
                # Get iframe frame
                frame = self.page.frame(name='divframe')
                if not frame:
                    # Try to get frame by URL
                    frames = self.page.frames
                    for f in frames:
                        if 'Review' in f.url or f.name == 'divframe':
                            frame = f
                            break
                
                if frame:
                    logger.info("Found iframe frame, getting document height...")
                    
                    # Wait a bit more for content to fully render
                    await asyncio.sleep(2)
                    
                    # Get document height from iframe - try multiple methods
                    total_height = await frame.evaluate("""
                        () => {
                            // Try to get the actual scrollable height
                            const body = document.body;
                            const html = document.documentElement;
                            
                            const heights = [
                                body.scrollHeight,
                                body.offsetHeight,
                                html.clientHeight,
                                html.scrollHeight,
                                html.offsetHeight,
                                body.getBoundingClientRect().height,
                                html.getBoundingClientRect().height
                            ];
                            
                            // Also check for content that might extend beyond
                            const allElements = document.querySelectorAll('*');
                            let maxBottom = 0;
                            allElements.forEach(el => {
                                const rect = el.getBoundingClientRect();
                                const bottom = rect.bottom + window.scrollY;
                                if (bottom > maxBottom) maxBottom = bottom;
                            });
                            
                            heights.push(maxBottom);
                            
                            return Math.max(...heights);
                        }
                    """)
                    logger.info(f"Initial document height: {total_height}px")
                    
                    # Scroll to bottom to ensure all content is loaded
                    await frame.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    
                    # Get updated height after scrolling (content might load dynamically)
                    total_height = await frame.evaluate("""
                        () => {
                            return Math.max(
                                document.body.scrollHeight,
                                document.body.offsetHeight,
                                document.documentElement.scrollHeight,
                                document.documentElement.offsetHeight
                            );
                        }
                    """)
                    logger.info(f"Final document height: {total_height}px")
                    
                    # Get viewport height to calculate pages properly
                    viewport_height = await frame.evaluate("window.innerHeight")
                    logger.info(f"Viewport height: {viewport_height}px")
                    
                    # Calculate pages - use viewport height as page height
                    effective_page_height = min(page_height, viewport_height)
                    scroll_height = effective_page_height - overlap
                    num_pages = max(1, int((total_height + scroll_height - 1) / scroll_height))
                    logger.info(f"Will capture {num_pages} page(s) (scroll height: {scroll_height}px)")
                    
                    # Scroll back to top
                    await frame.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(1)
                    
                    # Screenshot each page
                    for page_num in range(num_pages):
                        scroll_pos = page_num * scroll_height
                        
                        # Scroll to position
                        await frame.evaluate(f"window.scrollTo({{ top: {scroll_pos}, behavior: 'instant' }})")
                        await asyncio.sleep(1)  # Wait for scroll to complete and content to render
                        
                        # Take screenshot
                        screenshot_path = f"{output_dir}/{document_id}_page_{page_num + 1:03d}.png"
                        await iframe_locator.screenshot(path=screenshot_path)
                        screenshot_paths.append(screenshot_path)
                        logger.info(f"  Page {page_num + 1}/{num_pages} saved (scroll position: {scroll_pos}px)")
                    
                    logger.info(f"✓ Captured {len(screenshot_paths)} page(s) total")
                    return screenshot_paths
                else:
                    logger.warning("Could not access iframe frame, taking iframe screenshot")
                    screenshot_path = f"{output_dir}/{document_id}_page_001.png"
                    await iframe_locator.screenshot(path=screenshot_path)
                    screenshot_paths.append(screenshot_path)
                    return screenshot_paths
                    
            except Exception as e:
                logger.warning(f"Error with iframe method: {e}, trying full page screenshot")
                screenshot_path = f"{output_dir}/{document_id}_page_001.png"
                await self.page.screenshot(path=screenshot_path, full_page=True)
                screenshot_paths.append(screenshot_path)
                return screenshot_paths
            
            # Get iframe content frame - try different methods
            iframe_content = None
            try:
                # Method 1: Direct frame access
                frame = await iframe_element.frame_locator('iframe').first
                iframe_content = frame
            except:
                try:
                    # Method 2: Get frame by name
                    iframe_content = self.page.frame(name='divframe')
                except:
                    try:
                        # Method 3: Get frame by URL pattern
                        frames = self.page.frames
                        for frame in frames:
                            if 'Review' in frame.url or frame.name == 'divframe':
                                iframe_content = frame
                                break
                    except Exception as e:
                        logger.error(f"Could not access iframe content: {e}")
            
            if not iframe_content:
                logger.error("Could not access iframe content - trying alternative method")
                # Fallback: Screenshot the entire page
                screenshot_path = f"{output_dir}/{document_id}_page_001.png"
                await self.page.screenshot(path=screenshot_path, full_page=True)
                screenshot_paths.append(screenshot_path)
                logger.info(f"  Captured full page screenshot: {screenshot_path}")
                return screenshot_paths
            
            # Wait for iframe content to load
            try:
                if hasattr(iframe_content, 'wait_for_load_state'):
                    await iframe_content.wait_for_load_state('networkidle', timeout=self.config.timeout)
                await asyncio.sleep(2)  # Extra wait for content to render
            except Exception as e:
                logger.warning(f"Could not wait for iframe load state: {e}")
            
            # Get the total scroll height of the document
            try:
                if hasattr(iframe_content, 'evaluate'):
                    total_height = await iframe_content.evaluate("""
                        () => {
                            return Math.max(
                                document.body.scrollHeight,
                                document.body.offsetHeight,
                                document.documentElement.clientHeight,
                                document.documentElement.scrollHeight,
                                document.documentElement.offsetHeight
                            );
                        }
                    """)
                else:
                    # Fallback: Use page evaluate with iframe selector
                    total_height = await self.page.evaluate("""
                        () => {
                            const iframe = document.querySelector('#divframe');
                            if (iframe && iframe.contentDocument) {
                                return Math.max(
                                    iframe.contentDocument.body.scrollHeight,
                                    iframe.contentDocument.body.offsetHeight,
                                    iframe.contentDocument.documentElement.scrollHeight,
                                    iframe.contentDocument.documentElement.offsetHeight
                                );
                            }
                            return 1000; // Default height
                        }
                    """)
            except Exception as e:
                logger.warning(f"Could not get document height: {e}, using default")
                total_height = 2000  # Default height
            
            logger.info(f"Document height: {total_height}px")
            
            # Calculate number of pages
            scroll_height = page_height - overlap
            num_pages = int((total_height + scroll_height - 1) / scroll_height)
            logger.info(f"Will capture {num_pages} page(s)")
            
            # Scroll and screenshot each page
            for page_num in range(num_pages):
                scroll_position = page_num * scroll_height
                
                try:
                    # Scroll to position
                    if hasattr(iframe_content, 'evaluate'):
                        await iframe_content.evaluate(f"window.scrollTo(0, {scroll_position})")
                    else:
                        # Fallback: Scroll via page
                        await self.page.evaluate(f"""
                            () => {{
                                const iframe = document.querySelector('#divframe');
                                if (iframe && iframe.contentWindow) {{
                                    iframe.contentWindow.scrollTo(0, {scroll_position});
                                }}
                            }}
                        """)
                    await asyncio.sleep(0.8)  # Wait for scroll to complete
                except Exception as e:
                    logger.warning(f"Could not scroll to position {scroll_position}: {e}")
                
                # Take screenshot of iframe
                screenshot_path = f"{output_dir}/{document_id}_page_{page_num + 1:03d}.png"
                
                try:
                    # Screenshot the iframe element
                    await iframe_element.screenshot(path=screenshot_path, timeout=5000)
                    screenshot_paths.append(screenshot_path)
                    logger.info(f"  Page {page_num + 1}/{num_pages} saved: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Could not screenshot page {page_num + 1}: {e}")
                    # Fallback: Screenshot entire page
                    try:
                        await self.page.screenshot(path=screenshot_path, full_page=False, timeout=5000)
                        screenshot_paths.append(screenshot_path)
                        logger.info(f"  Page {page_num + 1}/{num_pages} (full page) saved: {screenshot_path}")
                    except:
                        pass
            
            logger.info(f"✓ Captured {len(screenshot_paths)} page(s) for document {document_id}")
            return screenshot_paths
            
        except Exception as e:
            logger.error(f"Error capturing document pages: {e}", exc_info=True)
            # Fallback: Take at least one full page screenshot
            if not screenshot_paths:
                try:
                    screenshot_path = f"{output_dir}/{document_id}_page_001.png"
                    await self.page.screenshot(path=screenshot_path, full_page=True)
                    screenshot_paths.append(screenshot_path)
                    logger.info(f"  Fallback: Captured full page screenshot: {screenshot_path}")
                except Exception as e2:
                    logger.error(f"Could not take fallback screenshot: {e2}")
            return screenshot_paths
    
    async def download_document(
        self,
        document_url: str,
        output_path: str,
        wait_for_download: bool = True
    ) -> Optional[str]:
        """
        Download a document from a document page
        
        Args:
            document_url: URL to the document page (e.g., '/Review/101476997')
            output_path: Path where to save the downloaded file
            wait_for_download: Whether to wait for download to complete
        
        Returns:
            Path to downloaded file or None if failed
        """
        if not self.page:
            return None
        
        try:
            full_url = f"{self.config.base_url}{document_url}"
            logger.info(f"Navigating to document: {full_url}")
            
            await self._rate_limit()
            
            # Navigate to document page
            await self.page.goto(full_url, wait_until='networkidle', timeout=self.config.timeout)
            await asyncio.sleep(1)  # Wait for page to fully load
            
            # Look for download link - could be PDF, DOC, or other format
            # Common patterns: download button, PDF link, document link
            download_selectors = [
                'a[href*=".pdf"]',
                'a[href*=".doc"]',
                'a[href*="Download"]',
                'a[href*="download"]',
                'a:has-text("Завантажити")',
                'a:has-text("Скачати")',
                'a:has-text("PDF")',
                'button[onclick*="download"]',
                'a[href*="/File/"]',
            ]
            
            download_url = None
            for selector in download_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        href = await element.get_attribute('href')
                        if href:
                            download_url = href
                            logger.info(f"Found download link: {href}")
                            break
                except:
                    continue
            
            # If no direct download link, try to get the document content
            if not download_url:
                # Check if document is embedded in iframe or directly in page
                # Try to find PDF viewer or document content
                logger.warning("No direct download link found, trying alternative methods...")
                
                # Method 1: Check for iframe with PDF
                iframe = await self.page.query_selector('iframe[src*=".pdf"]')
                if iframe:
                    src = await iframe.get_attribute('src')
                    if src:
                        download_url = src
                        logger.info(f"Found PDF in iframe: {src}")
                
                # Method 2: Check page source for PDF URL
                if not download_url:
                    content = await self.page.content()
                    import re
                    pdf_match = re.search(r'["\']([^"\']*\.pdf[^"\']*)["\']', content, re.IGNORECASE)
                    if pdf_match:
                        download_url = pdf_match.group(1)
                        logger.info(f"Found PDF URL in page source: {download_url}")
            
            if download_url:
                # Make download_url absolute if relative
                if download_url.startswith('/'):
                    download_url = f"{self.config.base_url}{download_url}"
                elif not download_url.startswith('http'):
                    download_url = f"{self.config.base_url}/{download_url}"
                
                # Download the file
                logger.info(f"Downloading from: {download_url}")
                await self._rate_limit()
                
                # Use Playwright's download functionality
                async with self.page.expect_download() as download_info:
                    await self.page.goto(download_url, wait_until='networkidle')
                
                download = await download_info.value
                
                # Save the file
                await download.save_as(output_path)
                logger.info(f"✓ Document saved to: {output_path}")
                return output_path
            else:
                # Fallback: Save the page HTML as document
                logger.warning("No download link found, saving page HTML instead")
                content = await self.page.content()
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✓ Page HTML saved to: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            return None
    
    async def close(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")


# Convenience functions for synchronous usage
def run_async(coro):
    """Run an async function synchronously"""
    return asyncio.run(coro)
