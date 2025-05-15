"""
Enhanced Agentic Search module for SuperAGI.

This module implements a more powerful, tool-using agentic search capability that:
1. Combines multiple search tools to find comprehensive results
2. Uses iterative refinement to improve search specificity
3. Self-validates results to ensure completeness and accuracy
4. Provides specific, actionable results with full details
"""
import re
import time
import json
import random
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple, Set, Union, cast

from superagi_replit.lib.logger import logger
from superagi_replit.agent.non_llm_task_validator import NonLLMTaskValidator


# Class name differentiated to avoid conflict in import
class SearchAPIClient:
    """
    Simple API client interface for the AgenticSearch class.
    Handles communication with various endpoints in the main application.
    """
    
    def __init__(self, base_url: str):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for API endpoints
        """
        self.base_url = base_url
        
    def call_gemini(self, prompt: str, priority: str = "low", max_retries: int = 3) -> Dict[str, Any]:
        """
        Call the Gemini API with retry mechanism for rate limits.
        
        Args:
            prompt: The prompt to send
            priority: Priority level (low or high)
            max_retries: Maximum number of retries for rate-limited requests
            
        Returns:
            Response from the API
        """
        retry_count = 0
        base_delay = 2  # Base delay in seconds for exponential backoff
        
        while retry_count <= max_retries:
            try:
                logger.info(f"Making Gemini API call (attempt {retry_count+1}/{max_retries+1})")
                
                # Try using anthropic as fallback if this is a retry
                use_fallback = retry_count > 0
                
                response = requests.post(
                    f"{self.base_url}/gemini",
                    json={
                        "prompt": prompt, 
                        "priority": priority,
                        "use_fallback": use_fallback
                    },
                    timeout=30  # Set a timeout to avoid hanging indefinitely
                )
                
                # Handle rate limiting specifically
                if response.status_code == 429:
                    retry_count += 1
                    if retry_count <= max_retries:
                        # Exponential backoff with jitter
                        delay = base_delay * (2 ** retry_count) + random.uniform(0, 1)
                        logger.warning(f"Rate limit hit, retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("Max retries exceeded for rate limit")
                        return {
                            "status": "error", 
                            "response": "Rate limit exceeded. Please try again later.",
                            "fallback_response": "The system is currently experiencing high demand. Please try a simpler search or try again later."
                        }
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timed out (attempt {retry_count+1})")
                retry_count += 1
                delay = base_delay * (2 ** retry_count)
                time.sleep(delay)
                
                # If we've exhausted retries for timeouts
                if retry_count > max_retries:
                    return {
                        "status": "error",
                        "response": "Request timed out repeatedly",
                        "fallback_response": "The system is taking too long to respond. Please try a simpler query."
                    }
                continue
                
            except Exception as e:
                logger.error(f"Error calling Gemini API: {e}")
                
                # If it's a rate limit error, retry with backoff
                if "429" in str(e) or "rate limit" in str(e).lower():
                    retry_count += 1
                    if retry_count <= max_retries:
                        delay = base_delay * (2 ** retry_count)
                        logger.warning(f"Rate limit hit, retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        continue
                
                return {
                    "status": "error", 
                    "response": str(e),
                    "fallback_response": "An error occurred while processing your request. Please try again with a simpler query."
                }
        
        # This should never be reached, but adding as a fallback for the type checker
        return {
            "status": "error",
            "response": "Unknown error occurred",
            "fallback_response": "An unexpected error occurred. Please try again."
        }
        
    def web_search(self, query: str, max_results: int = 10, max_retries: int = 2) -> Dict[str, Any]:
        """
        Perform a web search with retry logic.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            max_retries: Maximum number of retries
            
        Returns:
            Dictionary with search results
        """
        retry_count = 0
        base_delay = 1  # Base delay in seconds
        
        while retry_count <= max_retries:
            try:
                logger.info(f"Making web search call (attempt {retry_count+1}/{max_retries+1})")
                
                response = requests.post(
                    f"{self.base_url}/web_search",
                    json={"query": query, "max_results": max_results, "agentic": False},
                    timeout=20
                )
                
                # Handle specific rate limiting
                if response.status_code == 429:
                    retry_count += 1
                    if retry_count <= max_retries:
                        delay = base_delay * (2 ** retry_count)
                        logger.warning(f"Search rate limit hit, retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        continue
                    else:
                        # Return empty results with a warning
                        return {
                            "status": "warning", 
                            "results": [],
                            "message": "Search rate limit exceeded. Using fallback information."
                        }
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                logger.warning(f"Web search request timed out (attempt {retry_count+1})")
                retry_count += 1
                if retry_count <= max_retries:
                    delay = base_delay * (2 ** retry_count)
                    time.sleep(delay)
                    continue
                    
            except Exception as e:
                logger.error(f"Error performing web search: {e}")
                
                # If it's a rate limit error, retry
                if "429" in str(e) or "rate limit" in str(e).lower() or "ratelimit" in str(e).lower():
                    retry_count += 1
                    if retry_count <= max_retries:
                        delay = base_delay * (2 ** retry_count)
                        logger.warning(f"Search rate limit hit, retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        continue
                
                # For other errors, return empty results
                return {
                    "status": "error", 
                    "results": [],
                    "message": f"Search failed: {str(e)}"
                }
        
        # If we've exhausted retries
        return {"status": "error", "results": [], "message": "Maximum retries exceeded"}
        
    def scrape_text(self, url: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Scrape text from a URL with retry logic.
        
        Args:
            url: URL to scrape
            max_retries: Maximum number of retries
            
        Returns:
            Dictionary with scraped content
        """
        retry_count = 0
        base_delay = 1  # Base delay in seconds
        
        while retry_count <= max_retries:
            try:
                logger.info(f"Making scrape request (attempt {retry_count+1}/{max_retries+1})")
                
                response = requests.post(
                    f"{self.base_url}/scrape_text",
                    json={"url": url},
                    timeout=25  # Longer timeout for scraping
                )
                
                if response.status_code == 429:
                    retry_count += 1
                    if retry_count <= max_retries:
                        delay = base_delay * (2 ** retry_count)
                        logger.warning(f"Scrape rate limit hit, retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                logger.warning(f"Scrape request timed out (attempt {retry_count+1})")
                retry_count += 1
                if retry_count <= max_retries:
                    delay = base_delay * (2 ** retry_count)
                    time.sleep(delay)
                    continue
                
            except Exception as e:
                logger.error(f"Error scraping text: {e}")
                
                # If it's a rate limit error, retry
                if "429" in str(e) or "rate limit" in str(e).lower():
                    retry_count += 1
                    if retry_count <= max_retries:
                        delay = base_delay * (2 ** retry_count)
                        logger.warning(f"Scrape rate limit hit, retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        continue
                
                # Extract domain from URL for the message
                try:
                    domain = url.split("//")[1].split("/")[0]
                except:
                    domain = url
                    
                return {
                    "status": "error", 
                    "content": f"Unable to retrieve content from {domain}. The site may be unavailable or have restrictions."
                }
        
        # If we've exhausted retries
        return {"status": "error", "content": "Failed to retrieve content after multiple attempts"}


class SearchSource:
    """Represents a source of information used in search results."""
    def __init__(self, url: str, title: str):
        self.url = url
        self.title = title
        
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {
            "url": self.url,
            "title": self.title
        }


class SearchResultSection:
    """Represents a section of search results with specific content and sources."""
    def __init__(self, title: str, content: str, sources: Optional[List[SearchSource]] = None):
        self.title = title
        self.content = content
        self.sources = sources if sources is not None else []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "title": self.title,
            "content": self.content,
            "sources": [source.to_dict() for source in self.sources]
        }


class AgenticSearch:
    """
    Enhanced search agent that uses multiple tools and strategies to find
    comprehensive, accurate and specific results for user queries.
    """
    
    def __init__(self, api_client, validator=None):
        """
        Initialize the agentic search.
        
        Args:
            api_client: Client for making API calls (to Gemini, tools, etc.)
            validator: Optional validator instance to use
        """
        self.api_client = api_client
        self.validator = validator or NonLLMTaskValidator()
        self.search_state = {
            "query": "",
            "search_iterations": 0,
            "tool_uses": {},
            "searches_performed": [],
            "urls_visited": [],
            "raw_results": [],
            "refined_results": [],
            "validation_score": 0.0,
            "validation_feedback": "",
            "start_time": 0,
            "end_time": 0
        }
    
    def reset(self):
        """Reset the search state."""
        self.validator.reset()
        self.search_state = {
            "query": "",
            "search_iterations": 0,
            "tool_uses": {},
            "searches_performed": [],
            "urls_visited": [],
            "raw_results": [],
            "refined_results": [],
            "validation_score": 0.0,
            "validation_feedback": "",
            "start_time": 0,
            "end_time": 0
        }
    
    def search(self, query: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Perform an agentic search for the given query.
        
        Args:
            query: The search query
            max_iterations: Maximum number of search iterations
            
        Returns:
            Dictionary with search results and metadata
        """
        # Reset state and initialize
        self.reset()
        self.search_state["query"] = query
        self.search_state["start_time"] = time.time()
        
        logger.info(f"Starting agentic search for query: {query}")
        
        # Phase 1: Initial search planning
        search_plan = self._create_search_plan(query)
        logger.info(f"Created search plan with {len(search_plan)} steps")
        
        # Phase 2: Execute the search plan with adaptive refinement
        for i in range(max_iterations):
            self.search_state["search_iterations"] += 1
            
            # Determine what to search for in this iteration
            if i == 0:
                # Initial searches from the plan
                current_searches = search_plan[:2]  # Start with first 2 planned searches
            else:
                # Generate refinement searches based on what we've found so far
                refinement = self._generate_search_refinement()
                current_searches = refinement.get("next_searches", [])
                
                # If we have enough specific results and validation passes, we can stop
                if refinement.get("is_complete", False):
                    logger.info(f"Search refinement indicates completion after {i+1} iterations")
                    break
            
            # Execute current batch of searches
            for search_query in current_searches:
                if search_query in self.search_state["searches_performed"]:
                    continue  # Skip duplicate searches
                
                results = self._execute_search(search_query)
                self.search_state["searches_performed"].append(search_query)
                self.search_state["raw_results"].extend(results)
                
                # Visit top URLs from results to get specific details
                urls_to_visit = self._select_urls_to_visit(results)
                for url in urls_to_visit:
                    if url in self.search_state["urls_visited"]:
                        continue  # Skip already visited URLs
                    
                    content = self._scrape_url(url)
                    if content:
                        # Extract specific information
                        extracted_info = self._extract_specific_info(content, query)
                        if extracted_info:
                            self.search_state["refined_results"].append({
                                "source": url,
                                "extracted_info": extracted_info
                            })
                        self.search_state["urls_visited"].append(url)
            
            # After each iteration, check if we have enough specific information
            validation_result = self._validate_results()
            
            if validation_result["is_valid"]:
                logger.info(f"Search results validated as complete after {i+1} iterations")
                break
                
            # Update the validator with our progress
            self.validator.update_metrics(
                latest_response=json.dumps(self.search_state["refined_results"]),
                used_tool="AgenticSearch",
                tool_args={"query": query, "iteration": i+1}
            )
            
        # Phase 3: Final result synthesis and validation
        synthesized_results = self._synthesize_results()
        self.search_state["end_time"] = time.time()
        
        # Package the final results
        execution_time = self.search_state["end_time"] - self.search_state["start_time"]
        result = {
            "query": query,
            "iterations": self.search_state["search_iterations"],
            "execution_time": execution_time,
            "searches_performed": self.search_state["searches_performed"],
            "urls_visited": self.search_state["urls_visited"],
            "result_count": len(synthesized_results),
            "results": synthesized_results,
            "validation_score": self.search_state["validation_score"],
            "validation_feedback": self.search_state["validation_feedback"]
        }
        
        return result
    
    def _create_search_plan(self, query: str) -> List[str]:
        """
        Create a search plan based on the query.
        
        Args:
            query: The search query
            
        Returns:
            List of planned search queries
        """
        # Call the API to generate a search plan
        prompt = f"""
        Create a detailed search plan for finding comprehensive information about:
        "{query}"
        
        Generate a list of 5-7 specific search queries that would help gather complete information.
        These queries should:
        1. Start with broad searches to map the territory
        2. Include specific detail-oriented searches
        3. Include searches for opposing viewpoints or alternatives
        4. Cover different aspects/dimensions of the request
        
        Format your response as a JSON array of search queries.
        """
        
        try:
            response = self.api_client.call_gemini(prompt, "high")
            # Extract the JSON array from the response
            search_plan = self._extract_json_array(response.get("response", "[]"))
            
            # Ensure we have some search queries
            if not search_plan:
                # Fallback: generate some basic searches
                search_plan = self._generate_fallback_searches(query)
                
            return search_plan
        except Exception as e:
            logger.error(f"Error creating search plan: {e}")
            # Fallback plan
            return self._generate_fallback_searches(query)
    
    def _generate_fallback_searches(self, query: str) -> List[str]:
        """Generate fallback search queries when the API fails."""
        # Basic fallback search plan
        base_query = query.replace("Find", "").replace("find", "").strip()
        searches = [
            base_query,  # Direct search
            f"best {base_query}",  # Quality search
            f"{base_query} location specific details",  # Specific details
            f"{base_query} reviews ratings",  # Reviews and ratings
            f"{base_query} alternatives",  # Alternatives
        ]
        return searches
    
    def _extract_json_array(self, text: str) -> List[str]:
        """Extract a JSON array from text."""
        try:
            # Find JSON array pattern
            match = re.search(r'\[.*?\]', text, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            return []
        except json.JSONDecodeError:
            logger.error(f"Error parsing JSON array from: {text}")
            return []
    
    def _execute_search(self, search_query: str) -> List[Dict[str, str]]:
        """
        Execute a search with the given query.
        
        Args:
            search_query: The search query
            
        Returns:
            List of search results
        """
        try:
            # Call the search API
            response = self.api_client.web_search(search_query)
            self.search_state["tool_uses"]["WebSearchTool"] = self.search_state["tool_uses"].get("WebSearchTool", 0) + 1
            
            # Process and return results
            if "results" in response and isinstance(response["results"], list):
                return response["results"]
            return []
        except Exception as e:
            logger.error(f"Error executing search: {e}")
            return []
    
    def _select_urls_to_visit(self, search_results: List[Dict[str, str]]) -> List[str]:
        """
        Select which URLs to visit from search results.
        
        Args:
            search_results: List of search results
            
        Returns:
            List of URLs to visit
        """
        urls = []
        for result in search_results:
            if "href" in result and result["href"]:
                # Basic URL filtering
                url = result["href"]
                
                # Skip already visited URLs
                if url in self.search_state["urls_visited"]:
                    continue
                    
                # Skip certain URL patterns (e.g., social media, pdfs)
                if any(pattern in url for pattern in [".pdf", "facebook.com", "twitter.com", "instagram.com"]):
                    continue
                    
                urls.append(url)
                
                # Limit to top 3 most relevant URLs per search
                if len(urls) >= 3:
                    break
                    
        return urls
    
    def _scrape_url(self, url: str) -> str:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Scraped text content
        """
        try:
            # Call the scraping API
            response = self.api_client.scrape_text(url)
            self.search_state["tool_uses"]["WebScraperTool"] = self.search_state["tool_uses"].get("WebScraperTool", 0) + 1
            
            if "content" in response and response["content"]:
                return response["content"]
            return ""
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {e}")
            return ""
    
    def _extract_specific_info(self, content: str, query: str) -> Dict[str, Any]:
        """
        Extract specific information from scraped content.
        
        Args:
            content: Scraped content
            query: Original search query
            
        Returns:
            Dictionary with extracted information
        """
        # Call the API to extract specific information
        prompt = f"""
        Based on the following text content and the original query:
        
        QUERY: {query}
        
        CONTENT:
        {content[:5000]}  # Limit content to avoid token limits
        
        Extract the most relevant and specific information related to the query.
        Focus on extracting:
        1. Specific locations with addresses (if applicable)
        2. Quality indicators, ratings, or reviews
        3. Specific details about facilities/services
        4. Requirements for use (cost, memberships, restrictions)
        5. Contact information
        
        Format your response as a concise, focused summary with specific details only.
        Do not include generic information or speculation.
        """
        
        try:
            response = self.api_client.call_gemini(prompt, "low")
            return {
                "extracted_text": response.get("response", "No relevant information found"),
                "model_used": response.get("model_used", "unknown")
            }
        except Exception as e:
            logger.error(f"Error extracting specific info: {e}")
            return {
                "extracted_text": "Error extracting specific information",
                "error": str(e)
            }
    
    def _generate_search_refinement(self) -> Dict[str, Any]:
        """
        Generate refinement searches based on current results.
        
        Returns:
            Dictionary with next searches and completion status
        """
        # Package current state for analysis
        current_results = self.search_state["refined_results"]
        current_searches = self.search_state["searches_performed"]
        
        # Generate a summary of what we've found so far
        results_summary = "\n".join([
            f"- {result.get('source', 'Unknown source')}: {result.get('extracted_info', {}).get('extracted_text', 'No text')[:200]}..."
            for result in current_results[:5]  # Limit to top 5 results
        ])
        
        # Call the API to generate refinement
        prompt = f"""
        Based on the original query and search results so far, determine what additional
        searches are needed to complete the task.
        
        ORIGINAL QUERY: {self.search_state["query"]}
        
        SEARCHES ALREADY PERFORMED:
        {", ".join(current_searches)}
        
        CURRENT RESULTS SUMMARY:
        {results_summary}
        
        Evaluate whether the current results provide:
        1. Specific locations and addresses
        2. Quality information (cleanliness, ratings, etc.)
        3. Complete details on requirements/restrictions
        4. Sufficient number of options/alternatives
        
        Provide your response as a JSON object with these fields:
        - is_complete: boolean indicating if the search has found sufficient information
        - missing_aspects: list of aspects still missing from results
        - next_searches: list of 2-3 additional search queries that would fill gaps
        - completion_percentage: estimated percentage of completion (0-100)
        """
        
        try:
            response = self.api_client.call_gemini(prompt, "high")
            
            # Extract the JSON object from the response
            refinement_text = response.get("response", "{}")
            refinement = self._extract_json_object(refinement_text)
            
            # Ensure we have required fields
            if "is_complete" not in refinement:
                refinement["is_complete"] = False
                
            if "next_searches" not in refinement or not refinement["next_searches"]:
                # Generate some fallback refinement searches
                refinement["next_searches"] = [
                    f"{self.search_state['query']} best rated locations",
                    f"{self.search_state['query']} specific details",
                    f"{self.search_state['query']} exact information verified"
                ]
                
            return refinement
            
        except Exception as e:
            logger.error(f"Error generating search refinement: {e}")
            # Return a basic refinement
            return {
                "is_complete": False,
                "missing_aspects": ["specific details", "quality information", "requirements"],
                "next_searches": [
                    f"{self.search_state['query']} best rated locations",
                    f"{self.search_state['query']} specific details",
                    f"{self.search_state['query']} exact information verified"
                ]
            }
    
    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        """Extract a JSON object from text."""
        try:
            # Find JSON object pattern
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            
            # If no JSON object was found, return an empty object
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error parsing JSON object from: {text}")
            return {}
    
    def _validate_results(self) -> Dict[str, Any]:
        """
        Validate the search results using a high-quality LLM.
        
        Returns:
            Dictionary with validation results
        """
        # Check if we have enough results to validate
        if len(self.search_state["refined_results"]) < 3:
            return {"is_valid": False, "score": 0.2, "feedback": "Not enough results yet"}
            
        # Get all the extracted information we've gathered
        all_info = "\n\n".join([
            f"Source: {result.get('source', 'Unknown')}\n"
            f"Information: {result.get('extracted_info', {}).get('extracted_text', 'No information')}"
            for result in self.search_state["refined_results"][:5]  # Limit to 5 results
        ])
        
        # Call the API to validate the results
        prompt = f"""
        As an expert validator, assess the completeness, specificity, and accuracy of 
        the search results for this query:
        
        QUERY: {self.search_state["query"]}
        
        SEARCH RESULTS:
        {all_info}
        
        Evaluate the results on these criteria:
        1. COMPLETENESS: Do the results fully address the query? Are there missing aspects?
        2. SPECIFICITY: Do the results include specific details like exact locations, addresses, etc.?
        3. QUALITY: Do the results include relevant quality indicators (e.g., ratings, reviews)?
        4. ACTIONABILITY: Based on these results, could someone take clear action?
        
        Provide your assessment as a JSON object with these fields:
        - is_valid: boolean indicating if the results are adequate
        - score: number from 0.0 to 1.0 rating the overall quality
        - feedback: detailed feedback explaining the assessment
        - missing_aspects: list of any key missing information
        """
        
        try:
            response = self.api_client.call_gemini(prompt, "high")
            
            # Extract the validation result
            result_text = response.get("response", "{}")
            result = self._extract_json_object(result_text)
            
            # Store the validation results in the search state
            self.search_state["validation_score"] = result.get("score", 0.0)
            self.search_state["validation_feedback"] = result.get("feedback", "")
            
            # Ensure basic fields are present
            if "is_valid" not in result:
                result["is_valid"] = result.get("score", 0.0) >= 0.7
                
            return result
            
        except Exception as e:
            logger.error(f"Error validating results: {e}")
            return {
                "is_valid": False,
                "score": 0.5,
                "feedback": "Unable to validate results due to an error"
            }
    
    def _synthesize_results(self) -> List[Dict[str, Any]]:
        """
        Synthesize final results from all collected information.
        
        Returns:
            List of synthesized results (as dictionaries)
        """
        if not self.search_state["refined_results"]:
            return []
            
        # Prepare all the information we've gathered
        all_extracted_info = [
            result.get("extracted_info", {}).get("extracted_text", "")
            for result in self.search_state["refined_results"]
            if "extracted_info" in result and "extracted_text" in result.get("extracted_info", {})
        ]
        
        # Generate a comprehensive final synthesis
        # Join the first 5 sources with newlines
        collected_info = "\n\n".join(all_extracted_info[:5])
        
        prompt = f"""
        Based on the following collected information, synthesize a complete, detailed
        and specific response to the original query:
        
        ORIGINAL QUERY: {self.search_state["query"]}
        
        COLLECTED INFORMATION:
        {collected_info}
        
        Synthesize a comprehensive answer that:
        1. Directly addresses the query with specific, actionable information
        2. Includes specific locations, addresses, and contact details when available
        3. Organizes information in a clear, structured format
        4. Prioritizes the most relevant and specific information
        5. Cites sources for key information
        
        Format your response as detailed sections, each covering a specific aspect.
        """
        
        try:
            response = self.api_client.call_gemini(prompt, "high")
            synthesis_text = response.get("response", "")
            
            # Split into logical sections
            raw_sections = self._split_into_sections(synthesis_text)
            
            # Convert raw dictionaries to proper SearchResultSection objects
            # Create source objects from refined results
            sources = [
                SearchSource(
                    url=result.get("source", "Unknown"),
                    title=f"Source {i+1}"
                )
                for i, result in enumerate(self.search_state["refined_results"][:5])
            ]
            
            # Create proper section objects
            sections = []
            if raw_sections:
                for raw_section in raw_sections:
                    if isinstance(raw_section, dict) and "title" in raw_section and "content" in raw_section:
                        section = SearchResultSection(
                            title=raw_section["title"],
                            content=raw_section["content"],
                            sources=sources
                        )
                        sections.append(section)
            
            # If we couldn't extract any valid sections, create a default one
            if not sections:
                sections = [
                    SearchResultSection(
                        title="Results",
                        content=synthesis_text,
                        sources=sources
                    )
                ]
                
            # Convert to dictionaries for the API response
            return [section.to_dict() for section in sections]
            
        except Exception as e:
            logger.error(f"Error synthesizing results: {e}")
            # Create a fallback section if synthesis fails
            fallback_sources = [
                SearchSource(
                    url=result.get("source", "Unknown"),
                    title=f"Source {i+1}"
                )
                for i, result in enumerate(self.search_state["refined_results"][:3])
            ]
            
            fallback_section = SearchResultSection(
                title="Search Results",
                content="\n\n".join(all_extracted_info[:3]),
                sources=fallback_sources
            )
            
            return [fallback_section.to_dict()]
    
    def _split_into_sections(self, text: str) -> List[Dict[str, str]]:
        """Split synthesized text into logical sections."""
        sections = []
        
        # Try to split by headings
        heading_pattern = r"(?:^|\n)#+\s+(.*?)(?:\n|$)"
        headings = re.finditer(heading_pattern, text, re.MULTILINE)
        
        last_pos = 0
        current_title = "Introduction"
        
        for match in headings:
            heading_pos = match.start()
            heading_title = match.group(1).strip()
            
            # If we have content before this heading, add it as a section
            if heading_pos > last_pos:
                section_content = text[last_pos:heading_pos].strip()
                if section_content:
                    sections.append({
                        "title": current_title,
                        "content": section_content
                    })
            
            current_title = heading_title
            last_pos = match.end()
        
        # Add the final section
        if last_pos < len(text):
            final_content = text[last_pos:].strip()
            if final_content:
                sections.append({
                    "title": current_title,
                    "content": final_content
                })
        
        # If no headings were found, try to split by newlines
        if not sections:
            paragraphs = text.split("\n\n")
            if len(paragraphs) > 1:
                # Use the first paragraph as an introduction
                sections.append({
                    "title": "Introduction",
                    "content": paragraphs[0]
                })
                
                # Group the rest into a results section
                sections.append({
                    "title": "Results",
                    "content": "\n\n".join(paragraphs[1:])
                })
            else:
                # Just use the whole text as one section
                sections.append({
                    "title": "Results",
                    "content": text
                })
                
        return sections


class APIClient:
    """
    Simple API client interface for the AgenticSearch class.
    This can be replaced with the actual API client implementation.
    """
    
    def __init__(self, base_url: str):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for API endpoints
        """
        self.base_url = base_url
        
    def call_gemini(self, prompt: str, priority: str = "low") -> Dict[str, Any]:
        """
        Call the Gemini API.
        
        Args:
            prompt: The prompt to send
            priority: Priority level (low or high)
            
        Returns:
            Response from the API
        """
        import requests
        try:
            url = f"{self.base_url}/gemini"
            response = requests.post(
                url,
                json={
                    "prompt": prompt,
                    "priority": priority,
                    "verbose": False
                },
                headers={"Content-Type": "application/json"}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return {"status": "error", "response": str(e)}
    
    def web_search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Perform a web search.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            Dictionary with search results
        """
        import requests
        try:
            url = f"{self.base_url}/web_search"
            response = requests.post(
                url,
                json={
                    "query": query,
                    "max_results": max_results
                },
                headers={"Content-Type": "application/json"}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            return {"status": "error", "error": str(e), "results": []}
    
    def scrape_text(self, url: str) -> Dict[str, Any]:
        """
        Scrape text from a URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Dictionary with scraped content
        """
        import requests
        try:
            api_url = f"{self.base_url}/scrape_text"
            response = requests.post(
                api_url,
                json={"url": url},
                headers={"Content-Type": "application/json"}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error scraping URL: {e}")
            return {"status": "error", "error": str(e), "content": ""}