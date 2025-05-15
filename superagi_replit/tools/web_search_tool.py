"""
Web Search tool for SuperAGI.
"""
import json
import requests
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

from superagi_replit.lib.logger import logger
from superagi_replit.tools.base_tool import BaseTool


class WebSearchSchema(BaseModel):
    """Schema for Web Search tool inputs."""
    query: str = Field(..., description="The search query string")
    num_results: Optional[int] = Field(5, description="Number of search results to return (max 10)")


class WebSearchTool(BaseTool):
    """
    Tool for performing web searches using the Gemini proxy.
    """
    
    def __init__(self):
        """Initialize the Web Search tool."""
        super().__init__()
        self.name = "WebSearchTool"
        self.description = "A tool for searching the web. Use this when you need to find information on the internet."
        self.args_schema = WebSearchSchema
    
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
            
            # In a real implementation, we would call an actual search API
            # For this simplified version, we'll use a mock response
            search_url = "http://localhost:3000/search"
            
            payload = {
                "query": query,
                "num_results": num_results
            }
            
            response = requests.post(
                search_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()
            results = response.json()
            
            # Format the results
            formatted_results = f"Search results for: '{query}'\n\n"
            
            if "results" in results and results["results"]:
                for i, result in enumerate(results["results"], 1):
                    title = result.get("title", "No title")
                    url = result.get("url", "No URL")
                    snippet = result.get("snippet", "No description")
                    
                    formatted_results += f"{i}. {title}\n"
                    formatted_results += f"   URL: {url}\n"
                    formatted_results += f"   Description: {snippet}\n\n"
            else:
                formatted_results += "No results found."
                
            return formatted_results
            
        except requests.RequestException as e:
            error_msg = f"Error performing web search: {str(e)}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error in web search: {str(e)}"
            logger.error(error_msg)
            return error_msg