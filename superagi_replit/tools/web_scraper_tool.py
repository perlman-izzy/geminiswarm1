"""
Web Scraper tool for SuperAGI.
"""
import json
import requests
import time
from typing import Dict, Any, Optional, List

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from superagi_replit.lib.logger import logger
from superagi_replit.tools.base_tool import BaseTool


class WebScraperSchema(BaseModel):
    """Schema for Web Scraper tool inputs."""
    url: str = Field(..., description="The URL to scrape content from")
    max_depth: Optional[int] = Field(1, description="Maximum depth of page content to return (1-3)")
    elements: Optional[List[str]] = Field(None, description="Specific HTML elements to extract (e.g., ['h1', 'p', 'div.content'])")


class WebScraperTool(BaseTool):
    """
    Tool for scraping content from web pages.
    """
    
    def __init__(self):
        """Initialize the Web Scraper tool."""
        super().__init__()
        self.name = "WebScraperTool"
        self.description = "A tool for extracting content from web pages. Use this when you need to get detailed information from a specific webpage."
        self.args_schema = WebScraperSchema
    
    def execute(self, *args, **kwargs) -> str:
        """
        Execute the web scraper tool.
        
        Args:
            url: URL to scrape
            max_depth: Maximum depth of page content to return
            elements: Specific HTML elements to extract
            
        Returns:
            Extracted content as a string
        """
        url = kwargs.get("url", "")
        max_depth = min(max(1, kwargs.get("max_depth", 1)), 3)  # Between 1 and 3
        elements = kwargs.get("elements", None)
        
        try:
            # First try using the proxy if available
            try:
                logger.info(f"Attempting to scrape URL: {url}")
                proxy_url = "http://localhost:5000/fetch_url"
                
                payload = {
                    "url": url,
                    "max_depth": max_depth
                }
                
                response = requests.post(
                    proxy_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=20
                )
                
                response.raise_for_status()
                result = response.json()
                
                if "text" in result and result["text"]:
                    logger.info(f"Successfully scraped {url} via proxy")
                    return self._format_scraped_content(result["text"], url)
                elif "status_code" in result and "text" in result and result["text"]:
                    # Handle fetch_url endpoint format
                    logger.info(f"Successfully scraped {url} via proxy with status {result['status_code']}")
                    return self._format_scraped_content(result["text"], url)
                else:
                    logger.warning(f"No content returned from proxy for {url}, falling back to direct scraping")
            except (requests.RequestException, json.JSONDecodeError) as e:
                logger.warning(f"Error with scrape proxy: {str(e)}, falling back to direct scraping")
            
            # Fallback to direct scraping
            content = self._direct_scrape(url, max_depth, elements)
            return content
            
        except Exception as e:
            error_msg = f"Error scraping URL {url}: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _direct_scrape(self, url: str, max_depth: int = 1, elements: Optional[List[str]] = None) -> str:
        """
        Perform direct web scraping using requests and BeautifulSoup.
        
        Args:
            url: URL to scrape
            max_depth: Maximum depth of content to extract
            elements: Specific HTML elements to extract
            
        Returns:
            Extracted content as a string
        """
        try:
            # Set up proper headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/'
            }
            
            # Try to fetch the page with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    logger.warning(f"Scraping attempt {attempt+1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 * (attempt + 1))  # Exponential backoff
                    else:
                        raise
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unnecessary elements
            for script in soup(["script", "style", "iframe", "nav", "footer"]):
                script.decompose()
            
            # Extract content based on depth
            if elements:
                # Extract specific elements
                content = self._extract_elements(soup, elements)
            elif max_depth == 1:
                # Extract main content areas (basic)
                content = self._extract_main_content(soup)
            else:
                # Extract more detailed content
                content = self._extract_structured_content(soup, max_depth)
            
            return self._format_scraped_content(content, url)
        
        except Exception as e:
            logger.error(f"Error in direct scraping: {str(e)}")
            return f"Failed to scrape {url}: {str(e)}"
    
    def _extract_elements(self, soup: BeautifulSoup, elements: List[str]) -> str:
        """Extract specific elements from the page."""
        extracted = []
        
        for selector in elements:
            if '.' in selector:
                # Class selector (e.g., div.content)
                tag, class_name = selector.split('.')
                items = soup.find_all(tag, class_=class_name)
            elif '#' in selector:
                # ID selector (e.g., div#main)
                tag, id_name = selector.split('#')
                items = [soup.find(tag, id=id_name)]
            else:
                # Tag selector (e.g., h1)
                items = soup.find_all(selector)
            
            for item in items:
                if item and item.text.strip():
                    text = item.text.strip()
                    extracted.append(f"{selector}: {text}")
        
        return '\n\n'.join(extracted)
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from the page (basic version)."""
        # Try common content selectors
        main_selectors = [
            "main", "article", "div.content", "div.main", "div.article",
            "#content", "#main", "#article", ".post", ".entry"
        ]
        
        for selector in main_selectors:
            if '.' in selector:
                tag, class_name = selector.split('.')
                content = soup.find(tag, class_=class_name)
            elif '#' in selector:
                tag, id_name = selector.split('#')
                content = soup.find(tag, id=id_name)
            else:
                content = soup.find(selector)
                
            if content and content.text.strip():
                return content.text.strip()
        
        # If no main content found, extract title and paragraphs
        title = soup.find('title')
        title_text = title.text.strip() if title else "No title found"
        
        paragraphs = [p.text.strip() for p in soup.find_all('p') if p.text.strip()]
        paragraphs_text = '\n\n'.join(paragraphs[:10])  # Limit to first 10 paragraphs
        
        return f"{title_text}\n\n{paragraphs_text}"
    
    def _extract_structured_content(self, soup: BeautifulSoup, max_depth: int) -> str:
        """Extract structured content from the page."""
        content = []
        
        # Get title
        title = soup.find('title')
        if title:
            content.append(f"Title: {title.text.strip()}")
        
        # Get headings and their content
        for h_level in range(1, min(max_depth + 1, 4)):  # h1 to h3 depending on depth
            headings = soup.find_all(f'h{h_level}')
            for heading in headings:
                if heading.text.strip():
                    content.append(f"\nHeading (h{h_level}): {heading.text.strip()}")
                    
                    # Get content under this heading
                    next_sibling = heading.find_next_sibling()
                    sibling_content = []
                    
                    while next_sibling and next_sibling.name not in [f'h{h_level}', f'h{h_level-1}']:
                        if next_sibling.name in ['p', 'ul', 'ol'] and next_sibling.text.strip():
                            if next_sibling.name == 'ul' or next_sibling.name == 'ol':
                                list_items = [f"• {li.text.strip()}" for li in next_sibling.find_all('li') if li.text.strip()]
                                if list_items:
                                    sibling_content.append('\n'.join(list_items))
                            else:
                                sibling_content.append(next_sibling.text.strip())
                        next_sibling = next_sibling.find_next_sibling()
                    
                    if sibling_content:
                        content.append('\n'.join(sibling_content))
        
        # If no structured content found, fall back to paragraphs
        if len(content) <= 1:
            paragraphs = [p.text.strip() for p in soup.find_all('p') if p.text.strip()]
            content.extend(paragraphs[:20])  # Limit to first 20 paragraphs
        
        return '\n\n'.join(content)
    
    def _format_scraped_content(self, content: str, url: str) -> str:
        """Format the scraped content for readability."""
        # Clean up the text
        content = content.replace('\t', ' ').replace('\r', '')
        content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
        
        # Add source information
        header = f"Content scraped from: {url}\n{'='*50}\n\n"
        
        # If content is very long, truncate it with a note
        max_length = 10000
        if len(content) > max_length:
            truncated = content[:max_length]
            footer = f"\n\n[Content truncated. Total length: {len(content)} characters]"
            return header + truncated + footer
        
        return header + content