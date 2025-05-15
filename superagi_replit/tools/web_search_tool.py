"""
Web Search tool for SuperAGI.
"""
import json
import requests
import subprocess
import sys
import time
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field

from superagi_replit.lib.logger import logger
from superagi_replit.tools.base_tool import BaseTool


class WebSearchSchema(BaseModel):
    """Schema for Web Search tool inputs."""
    query: str = Field(..., description="The search query string")
    num_results: Optional[int] = Field(5, description="Number of search results to return (max 10)")


class WebSearchTool(BaseTool):
    """
    Tool for performing web searches using real search capability.
    """
    
    def __init__(self):
        """Initialize the Web Search tool."""
        super().__init__()
        self.name = "WebSearchTool"
        self.description = "A tool for searching the web for real-time information. Use this when you need to find current information on the internet."
        self.args_schema = WebSearchSchema
    
    def _direct_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a direct search using existing functions in the repo.
        
        This is a fallback if the proxy is not working.
        """
        try:
            # Try to import functions directly from main repo if available
            search_results = []
            
            # Use the library directly if available
            try:
                from duckduckgo_search import DDGS
                
                # Advanced search strategy with fallbacks and retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        with DDGS() as ddgs:
                            # Add site-specific search if query contains certain keywords
                            if any(keyword in query.lower() for keyword in ["venue", "restaurant", "location", "place"]):
                                # Try to get higher quality results from reliable sources
                                specialized_sites = ["yelp.com", "tripadvisor.com", "opentable.com", "timeout.com"]
                                
                                # Try site-specific searches first for specialized queries
                                for site in specialized_sites:
                                    site_results = []
                                    site_query = f"site:{site} {query}"
                                    logger.info(f"Specialized search attempt {attempt+1}/{max_retries} for site {site}")
                                    
                                    try:
                                        site_search = list(ddgs.text(site_query, max_results=3))
                                        for result in site_search:
                                            site_results.append({
                                                "title": result.get("title", ""),
                                                "url": result.get("href", ""),
                                                "snippet": result.get("body", "")
                                            })
                                    except Exception as site_err:
                                        logger.warning(f"Site-specific search failed for {site}: {str(site_err)}")
                                    
                                    search_results.extend(site_results)
                                    
                                    # If we have enough results, stop trying more sites
                                    if len(search_results) >= num_results:
                                        break
                            
                            # If we don't have enough results yet, do a general search
                            if len(search_results) < num_results:
                                logger.info(f"General search attempt {attempt+1}/{max_retries}")
                                general_results = list(ddgs.text(query, max_results=num_results))
                                
                                # Add results that aren't duplicates
                                existing_urls = {result.get("url", "") for result in search_results}
                                for result in general_results:
                                    if result.get("href", "") not in existing_urls:
                                        search_results.append({
                                            "title": result.get("title", ""),
                                            "url": result.get("href", ""),
                                            "snippet": result.get("body", "")
                                        })
                                        existing_urls.add(result.get("href", ""))
                            
                            # Truncate to requested number
                            search_results = search_results[:num_results]
                            
                            if search_results:
                                logger.info(f"Successfully got {len(search_results)} results from direct DDGS")
                                return search_results
                            
                            # If we got no results, we'll retry
                            logger.warning(f"No results on attempt {attempt+1}, will retry")
                            
                    except Exception as e:
                        logger.warning(f"Search attempt {attempt+1} failed: {str(e)}")
                        # Brief exponential backoff before retrying
                        time.sleep(1 * (attempt + 1))
                
                # If all retries failed but we have partial results, return those
                if search_results:
                    logger.warning(f"All retries failed but returning {len(search_results)} partial results")
                    return search_results
                    
                # If all retries completely failed, raise to try alternate method
                raise Exception("All DDGS search attempts failed")
            except ImportError:
                # If duckduckgo_search isn't available, use subprocess to run a simple curl to Google
                logger.info("DDGS import failed, trying subprocess method")
                
                # Sanitize the query
                safe_query = query.replace('"', '\\"')
                cmd = f'curl -s "https://www.google.com/search?q={safe_query.replace(" ", "+")}&num={num_results}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                # Extract basic results (this is a very simplified extractor)
                html = result.stdout
                
                # Very basic extraction - in a real implementation, this would use BeautifulSoup
                titles = []
                urls = []
                snippets = []
                
                # Find search result sections
                for line in html.split('\n'):
                    if '<h3' in line:
                        if '</h3>' in line:
                            title_start = line.find('>', line.find('<h3'))
                            title_end = line.find('</h3>', title_start)
                            if title_start > 0 and title_end > 0:
                                titles.append(line[title_start+1:title_end].strip())
                    
                    if 'class="iUh30' in line and 'http' in line:
                        url_start = line.find('http')
                        url_end = line.find('</div>', url_start)
                        if url_start > 0 and url_end > 0:
                            urls.append(line[url_start:url_end].strip())
                            
                    if 'class="st"' in line:
                        snippet_start = line.find('>', line.find('class="st"'))
                        snippet_end = line.find('</span>', snippet_start)
                        if snippet_start > 0 and snippet_end > 0:
                            snippets.append(line[snippet_start+1:snippet_end].strip())
                
                # Combine into results
                for i in range(min(len(titles), len(urls), len(snippets))):
                    search_results.append({
                        "title": titles[i],
                        "url": urls[i],
                        "snippet": snippets[i]
                    })
                
                if not search_results:
                    # Fallback to placeholder results with the query
                    search_results = [
                        {
                            "title": f"Search results for {query}",
                            "url": f"https://www.google.com/search?q={query.replace(' ', '+')}",
                            "snippet": "Direct search results were not able to be retrieved. Please try accessing the search URL directly."
                        }
                    ]
                    
                logger.info(f"Got {len(search_results)} results via subprocess")
                return search_results
        except Exception as e:
            logger.error(f"Error in direct search: {str(e)}")
            return [
                {
                    "title": f"Search query for: {query}",
                    "url": f"https://www.google.com/search?q={query.replace(' ', '+')}",
                    "snippet": f"Unable to retrieve search results directly. Error: {str(e)}"
                }
            ]
    
    def execute(self, *args, **kwargs) -> str:
        """
        Execute the web search tool.
        
        Args:
            query: The search query string
            num_results: Number of results to return (default: 5, max: 10)
            
        Returns:
            Search results as a formatted string
        """
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)
        try:
            # Ensure num_results is within bounds
            num_results = min(max(1, num_results), 10)
            
            # First try using the proxy
            search_url = "http://localhost:5000/search"
            
            payload = {
                "query": query,
                "num_results": num_results
            }
            
            logger.info(f"Attempting web search for: {query}")
            
            try:
                response = requests.post(
                    search_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10  # Shorter timeout to fall back to direct search if proxy is slow
                )
                
                response.raise_for_status()
                results = response.json()
                
                if "results" in results and results["results"]:
                    search_results = results["results"]
                    logger.info(f"Successfully got {len(search_results)} results from proxy")
                else:
                    logger.warning("No results from proxy, falling back to direct search")
                    search_results = self._direct_search(query, num_results)
            except (requests.RequestException, json.JSONDecodeError) as e:
                logger.warning(f"Error with search proxy: {str(e)}, falling back to direct search")
                search_results = self._direct_search(query, num_results)
            
            # Format the results
            formatted_results = f"Search results for: '{query}'\n\n"
            
            if search_results:
                for i, result in enumerate(search_results, 1):
                    title = result.get("title", "No title")
                    url = result.get("url", "No URL")
                    snippet = result.get("snippet", "No description")
                    
                    formatted_results += f"{i}. {title}\n"
                    formatted_results += f"   URL: {url}\n"
                    formatted_results += f"   Description: {snippet}\n\n"
            else:
                formatted_results += "No results found."
                
            return formatted_results
            
        except Exception as e:
            error_msg = f"Unexpected error in web search: {str(e)}"
            logger.error(error_msg)
            return error_msg