"""
Extract Ukrainian text from print version HTML files
"""

import re
from pathlib import Path
from bs4 import BeautifulSoup
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_text_from_html(html_path: Path) -> str:
    """
    Extract clean Ukrainian text from print version HTML file
    
    Args:
        html_path: Path to the HTML file
    
    Returns:
        Cleaned text content
    """
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up the text
        # Remove extra whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        
        # Join lines with proper spacing
        cleaned_text = '\n'.join(lines)
        
        # Fix common HTML entity issues
        cleaned_text = cleaned_text.replace('&nbsp;', ' ')
        cleaned_text = cleaned_text.replace('&amp;', '&')
        cleaned_text = cleaned_text.replace('&lt;', '<')
        cleaned_text = cleaned_text.replace('&gt;', '>')
        cleaned_text = cleaned_text.replace('&quot;', '"')
        
        # Remove multiple spaces
        cleaned_text = re.sub(r' +', ' ', cleaned_text)
        
        # Remove multiple newlines (keep max 2)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text from {html_path}: {e}")
        return ""


def extract_all_print_versions(directory: Path = None):
    """
    Extract text from all print version HTML files in a directory
    
    Args:
        directory: Directory containing document folders (default: downloaded_5_documents)
    """
    if directory is None:
        directory = Path("downloaded_5_documents")
    
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return
    
    logger.info(f"Extracting text from print versions in: {directory}")
    
    # Find all print version HTML files
    print_files = list(directory.glob("**/*_print.html"))
    
    if not print_files:
        logger.warning("No print version files found")
        return
    
    logger.info(f"Found {len(print_files)} print version file(s)")
    
    extracted_count = 0
    
    for print_file in print_files:
        try:
            # Extract text
            text = extract_text_from_html(print_file)
            
            if not text:
                logger.warning(f"No text extracted from {print_file.name}")
                continue
            
            # Save as .txt file
            txt_file = print_file.with_suffix('.txt')
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Count lines and characters
            lines = text.split('\n')
            char_count = len(text)
            word_count = len(text.split())
            
            logger.info(f"✓ Extracted: {print_file.name}")
            logger.info(f"  Saved to: {txt_file.name}")
            logger.info(f"  Lines: {len(lines)}, Words: {word_count}, Characters: {char_count}")
            
            extracted_count += 1
            
        except Exception as e:
            logger.error(f"Error processing {print_file.name}: {e}")
    
    logger.info(f"\n✓ Extracted text from {extracted_count}/{len(print_files)} file(s)")


def extract_single_file(html_path: str):
    """
    Extract text from a single print version HTML file
    
    Args:
        html_path: Path to the HTML file
    """
    file_path = Path(html_path)
    
    if not file_path.exists():
        logger.error(f"File not found: {html_path}")
        return
    
    logger.info(f"Extracting text from: {file_path.name}")
    
    text = extract_text_from_html(file_path)
    
    if not text:
        logger.warning("No text extracted")
        return
    
    # Save as .txt file
    txt_file = file_path.with_suffix('.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text)
    
    # Show preview
    preview = text[:500] + "..." if len(text) > 500 else text
    logger.info(f"✓ Text extracted and saved to: {txt_file.name}")
    logger.info(f"\nPreview (first 500 chars):\n{preview}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Extract from single file
        extract_single_file(sys.argv[1])
    else:
        # Extract from all files in directory
        extract_all_print_versions()
