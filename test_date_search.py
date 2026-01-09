"""
Test script to search with RegDateBegin date field
"""

import asyncio
from bulk_requests_playwright import PlaywrightBulkHandler, PlaywrightConfig
from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()


async def test_date_search():
    """
    Test searching with RegDateBegin date field set to 01.01.2026
    Expected result: "За заданими параметрами пошуку знайдено документів: 11684"
    """
    console.print(Panel.fit(
        "[bold cyan]Date Search Test[/bold cyan]\n"
        "Searching with RegDateBegin = 01.01.2026\n"
        "Expected: 11684 documents found",
        title="Test Configuration",
        border_style="cyan"
    ))
    
    handler = PlaywrightBulkHandler(
        config=PlaywrightConfig(
            headless=True,
            delay_between_requests=2.0
        )
    )
    
    try:
        # Navigate to homepage
        with console.status("[bold green]Navigating to homepage...", spinner="dots"):
            page = await handler.navigate("/")
            if not page:
                console.print("[bold red]✗ Failed to navigate[/bold red]")
                return False
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(1)
        
        # Fill the RegDateBegin field
        with console.status("[bold green]Filling RegDateBegin field...", spinner="dots"):
            try:
                # Find the date input field
                reg_date_begin = page.locator('#RegDateBegin')
                await reg_date_begin.wait_for(state='visible', timeout=5000)
                
                # Clear and fill the date field
                await reg_date_begin.clear()
                await reg_date_begin.fill('01.01.2026')
                
                console.print("[green]✓[/green] Filled RegDateBegin with: [cyan]01.01.2026[/cyan]")
                
            except Exception as e:
                console.print(f"[bold red]✗ Error filling date field: {e}[/bold red]")
                return False
        
        # Submit the search form
        with console.status("[bold green]Submitting search form...", spinner="dots"):
            try:
                # Try multiple ways to submit the form
                submitted = False
                
                # Method 1: Try to find and click submit button
                submit_selectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'input[value*="Пошук"]',
                    'button:has-text("Пошук")'
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_button = page.locator(selector).first()
                        count = await submit_button.count()
                        if count > 0:
                            await submit_button.click()
                            console.print(f"[green]✓[/green] Clicked search button ({selector})")
                            submitted = True
                            break
                    except:
                        continue
                
                # Method 2: If no button found, try pressing Enter on the date field
                if not submitted:
                    await reg_date_begin.press('Enter')
                    console.print("[green]✓[/green] Submitted form (Enter key)")
                    submitted = True
                
                # Wait for results to load
                await page.wait_for_load_state('networkidle', timeout=15000)
                await asyncio.sleep(2)
                
            except Exception as e:
                console.print(f"[bold red]✗ Error submitting form: {e}[/bold red]")
                return False
        
        # Check for the expected result message
        with console.status("[bold green]Checking results...", spinner="dots"):
            try:
                # Wait for the results message to appear
                await asyncio.sleep(2)
                
                # Look for the span with the document count
                # The message format: "За заданими параметрами пошуку знайдено документів: 11684"
                page_content = await page.content()
                
                # Try to find the result message
                result_text = None
                document_count = None
                
                try:
                    result_span = page.locator('span:has-text("знайдено документів")')
                    count = await result_span.count()
                    if count > 0:
                        result_text = await result_span.first.inner_text()
                        # Extract the number from the text
                        import re
                        match = re.search(r'знайдено документів:\s*(\d+)', result_text)
                        if match:
                            document_count = int(match.group(1))
                except:
                    pass
                
                # Check if we got the expected count
                if document_count == 11684:
                    console.print("[bold green]✓ SUCCESS![/bold green]")
                    console.print("[green]Found expected result:[/green]")
                    console.print(f"[cyan]  {result_text}[/cyan]")
                    
                    # Take a screenshot for verification
                    screenshot_path = "test_date_search_result.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                    console.print(f"\n[dim]Screenshot saved to: [cyan]{screenshot_path}[/cyan][/dim]")
                    
                    return True
                elif document_count is not None:
                    # Got a different count
                    console.print("[yellow]⚠ Different document count found[/yellow]")
                    console.print(f"[cyan]Expected:[/cyan] 11,684 documents")
                    console.print(f"[cyan]Found:[/cyan] {document_count:,} documents")
                    console.print(f"[dim]Result message: {result_text}[/dim]")
                    
                    # Check for CAPTCHA
                    if 'captcha' in page_content.lower() or 'капча' in page_content.lower():
                        console.print("[bold yellow]⚠ CAPTCHA detected - this may affect results[/bold yellow]")
                    
                    # Take a screenshot anyway
                    screenshot_path = "test_date_search_result.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                    console.print(f"\n[dim]Screenshot saved to: [cyan]{screenshot_path}[/cyan][/dim]")
                    
                    return False
                else:
                    # No result message found
                    console.print("[yellow]⚠ No result message found[/yellow]")
                    
                    # Check for CAPTCHA
                    if 'captcha' in page_content.lower() or 'капча' in page_content.lower():
                        console.print("[bold red]⚠ CAPTCHA detected![/bold red]")
                    
                    # Save page content for debugging
                    with open("test_date_search_page.html", "w", encoding="utf-8") as f:
                        f.write(page_content)
                    console.print("[dim]Page content saved to: test_date_search_page.html[/dim]")
                    
                    return False
                    
            except Exception as e:
                console.print(f"[bold red]✗ Error checking results: {e}[/bold red]")
                return False
        
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        return False
    finally:
        await handler.close()


if __name__ == "__main__":
    success = asyncio.run(test_date_search())
    if success:
        console.print("\n[bold green]✓ Test passed![/bold green]")
    else:
        console.print("\n[bold red]✗ Test failed![/bold red]")
