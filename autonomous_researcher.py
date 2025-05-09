#!/usr/bin/env python3
"""
Autonomous Researcher System

This module implements a self-guided research system that:
1. Creates a research plan based on the query
2. Executes research using available tools
3. Adaptively adjusts its strategy based on findings
4. Self-assesses progress and determines when to stop
5. Synthesizes results into a comprehensive answer
"""

import json
import time
import logging
import requests
import re
import os
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutonomousResearcher:
    """A self-guided research system that can plan, execute, and evaluate research."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        Initialize the autonomous researcher.
        
        Args:
            base_url: Base URL for API endpoints
        """
        self.base_url = base_url
        self.max_iterations = 15  # Safety limit to prevent infinite loops
        self.research_state = {
            "query": "",
            "plan": [],
            "findings": [],
            "searched_terms": [],
            "visited_urls": [],
            "categories": {},
            "iterations": 0,
            "complete": False
        }
    
    def _call_gemini(self, prompt: str, priority: str = "low") -> Dict[str, Any]:
        """
        Call the Gemini API with retry logic for rate limits and model fallback.
        
        Args:
            prompt: The prompt to send
            priority: Priority level (low or high)
            
        Returns:
            Response from Gemini API
        """
        max_retries = 3
        retry_delay = 3  # seconds
        
        # Define model tiers for fallback
        model_tiers = [
            {"model": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},  # Default, most capable
            {"model": "gemini-1.0-pro", "name": "Gemini 1.0 Pro"},  # Fallback 1
            {"model": "gemini-1.0-flash", "name": "Gemini 1.0 Flash"},  # Fallback 2
            {"model": "text-bison", "name": "PaLM 2 (text-bison)"}  # Last resort
        ]
        
        # Try each model tier until successful or all tiers exhausted
        for model_tier in model_tiers:
            model_name = model_tier["name"]
            model = model_tier["model"]
            
            logger.info(f"Attempting request with model: {model_name}")
            
            for attempt in range(max_retries):
                try:
                    url = f"{self.base_url}/gemini"
                    response = requests.post(
                        url,
                        json={
                            "prompt": prompt, 
                            "priority": priority,
                            "model": model  # Specify which model to use
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    result = response.json()
                    
                    # If successful response without quota error, return it
                    if "response" in result and not (
                        "error" in result.get("response", "").lower() and 
                        "quota" in result.get("response", "").lower()
                    ):
                        logger.info(f"Request successful with model: {model_name}")
                        # Add which model was used to the response
                        result["model_used"] = model_name
                        return result
                    
                    # If we hit a rate limit, try waiting before trying the same model again
                    if "error" in result.get("response", "").lower() and "quota" in result.get("response", "").lower():
                        logger.warning(f"API rate limit hit with {model_name}, attempt {attempt+1}/{max_retries}")
                        if attempt < max_retries - 1:
                            logger.info(f"Waiting {retry_delay} seconds before retry with same model")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            # After max retries with current model, break to try next tier
                            logger.warning(f"Max retries exceeded with {model_name}, trying next model tier")
                            break
                    
                except Exception as e:
                    logger.error(f"Error calling API with {model_name} (attempt {attempt+1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting {retry_delay} seconds before retry")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        # After max retries with current model, break to try next tier
                        logger.warning(f"Max retries exceeded with {model_name} due to errors, trying next model tier")
                        break
        
        # If we reach here, all model tiers have failed
        # Try anthropic fallback if available
        try:
            logger.info("All Google AI models failed, attempting fallback to Anthropic Claude")
            url = f"{self.base_url}/anthropic"
            response = requests.post(
                url,
                json={"prompt": prompt},
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            if "response" in result:
                logger.info("Request successful with Anthropic Claude fallback")
                result["model_used"] = "Anthropic Claude (fallback)"
                return result
        except Exception as e:
            logger.error(f"Error with Anthropic fallback: {e}")
            
        # If we reach here, all models including fallbacks have failed
        return {"status": "error", "response": "Failed after trying all model tiers", "model_used": "none"}
    
    def _web_search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """
        Perform a web search.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        try:
            url = f"{self.base_url}/web_search"
            response = requests.post(
                url,
                json={"query": query, "max_results": max_results},
                headers={"Content-Type": "application/json"}
            )
            results = response.json().get("results", [])
            self.research_state["searched_terms"].append(query)
            logger.info(f"Web search for '{query}' found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []
    
    def _scrape_url(self, url: str) -> str:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Scraped text content
        """
        try:
            api_url = f"{self.base_url}/scrape_text"
            response = requests.post(
                api_url,
                json={"url": url},
                headers={"Content-Type": "application/json"}
            )
            content = response.json().get("text", "")
            if "Error fetching URL" not in content:
                self.research_state["visited_urls"].append(url)
                logger.info(f"Successfully scraped URL: {url}")
                return content
            else:
                logger.warning(f"Failed to scrape URL: {url}")
                return ""
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {e}")
            return ""
    
    def _analyze_content(self, content: str, context: str) -> Dict[str, Any]:
        """
        Analyze content in the given context.
        
        Args:
            content: Text content to analyze
            context: Context for analysis
            
        Returns:
            Analysis results
        """
        prompt = f"""
        Analyze the following content in the context of {context}.
        
        CONTENT:
        {content}
        
        Extract the following information:
        1. Key facts relevant to {context}
        2. Any specific entities mentioned (places, organizations, people)
        3. Any numerical data or statistics
        4. What new information does this add to our research?
        
        Format your response as a JSON object with these fields:
        {{
            "key_facts": [list of facts],
            "entities": [list of entities],
            "numerical_data": [list of data points],
            "new_information": "description of what's new"
        }}
        """
        
        result = self._call_gemini(prompt, "low")
        if "response" in result:
            # Extract JSON from response
            try:
                json_match = re.search(r'\{[\s\S]*\}', result["response"])
                if json_match:
                    return json.loads(json_match.group(0))
            except Exception as e:
                logger.error(f"Error extracting JSON from analysis: {e}")
        
        # Return empty structure if we couldn't parse
        return {
            "key_facts": [],
            "entities": [],
            "numerical_data": [],
            "new_information": ""
        }
    
    def _create_research_plan(self, query: str) -> List[str]:
        """
        Create a research plan based on the query.
        
        Args:
            query: Research query
            
        Returns:
            List of research steps
        """
        prompt = f"""
        Create a step-by-step research plan to answer the following query:
        
        QUERY: {query}
        
        The plan should:
        1. Break down the query into key aspects to research
        2. Identify the most effective search terms to use
        3. Suggest how to categorize and organize findings
        4. Indicate when the research would be considered sufficient
        
        Format your response as a JSON array of steps, where each step is a string.
        """
        
        result = self._call_gemini(prompt, "low")
        plan = []
        
        if "response" in result:
            # Extract JSON array from response
            try:
                json_match = re.search(r'\[[\s\S]*\]', result["response"])
                if json_match:
                    plan = json.loads(json_match.group(0))
            except Exception as e:
                logger.error(f"Error extracting plan JSON: {e}")
                # Create a simple plan as fallback
                plan = [
                    "Search for general information about the topic",
                    "Identify key categories for organizing information",
                    "Gather specific details for each category",
                    "Synthesize findings into a comprehensive answer"
                ]
        
        logger.info(f"Created research plan with {len(plan)} steps")
        return plan
    
    def _generate_search_terms(self, query: str) -> List[str]:
        """
        Generate effective search terms based on the query.
        
        Args:
            query: Research query
            
        Returns:
            List of search terms
        """
        prompt = f"""
        Generate 5 effective search queries to find information about:
        
        QUERY: {query}
        
        The search queries should:
        1. Cover different aspects of the topic
        2. Use different phrasings and terminology
        3. Be specific enough to yield relevant results
        
        Format your response as a JSON array of search queries.
        """
        
        result = self._call_gemini(prompt, "low")
        search_terms = []
        
        if "response" in result:
            # Extract JSON array from response
            try:
                json_match = re.search(r'\[[\s\S]*\]', result["response"])
                if json_match:
                    search_terms = json.loads(json_match.group(0))
            except Exception as e:
                logger.error(f"Error extracting search terms JSON: {e}")
                # Create default search terms as fallback
                base_term = query.replace("Find", "").replace("find", "").strip()
                search_terms = [base_term, f"best {base_term}", f"{base_term} guide"]
        
        # Add the original query if empty
        if not search_terms:
            search_terms = [query]
            
        logger.info(f"Generated {len(search_terms)} search terms")
        return search_terms
    
    def _assess_progress(self) -> Tuple[bool, str]:
        """
        Assess research progress to determine if it's complete using an intuitive approach.
        
        This method evaluates whether the gathered information is sufficient to answer
        the original query, considering diminishing returns and information completeness
        rather than arbitrary metrics.
        
        Returns:
            Tuple of (is_complete, reason)
        """
        # Safety checks first
        if self.research_state["iterations"] >= self.max_iterations:
            return True, "Reached maximum iterations"
        
        if not self.research_state["findings"]:
            return False, "No findings yet"
            
        # Calculate coverage of different categories/aspects
        if not self.research_state["categories"]:
            self._categorize_findings()
            
        # Prepare a summary of what we've learned
        found_venues = []
        venue_types = []
        
        # Extract venue names and types from findings
        for finding in self.research_state["findings"]:
            new_info = finding.get("new_information", "")
            entities = finding.get("entities", [])
            
            # Look for venue names in entities
            for entity in entities:
                if any(keyword in entity.lower() for keyword in ["hall", "club", "lounge", "bar", "venue"]):
                    if entity not in found_venues:
                        found_venues.append(entity)
                        
            # Look for venue types/categories
            for entity in entities:
                if any(keyword in entity.lower() for keyword in ["jazz", "piano bar", "concert hall", "club"]):
                    if entity not in venue_types and not any(entity in vt for vt in venue_types):
                        venue_types.append(entity)
        
        # Prepare findings summary with what we know about piano venues
        findings_summary = self._summarize_findings(3)
        
        # Use Gemini to make an intuitive assessment
        prompt = f"""
        You are a researcher studying music venues in San Francisco with pianos. 
        Assess whether our research progress so far is sufficient to give a helpful answer.
        
        ORIGINAL QUERY: {self.research_state["query"]}
        
        RESEARCH CONTEXT:
        - We have investigated {len(self.research_state["visited_urls"])} sources
        - We have found information about approximately {len(found_venues)} venues
        - We have identified these types of venues: {", ".join(venue_types) if venue_types else "None yet"}
        - We've completed {self.research_state["iterations"]} research iterations
        
        KEY FINDINGS SO FAR:
        {findings_summary}
        
        Make a judgment similar to how a human would decide when they have "researched enough":
        
        1. Do we have enough information to provide a useful answer to someone asking about piano venues in SF?
        2. Would additional searching likely yield substantially new information, or mostly just confirm what we know?
        3. Do we have a reasonable diversity of venue types (piano bars, jazz clubs, concert halls, etc.)?
        4. Is our information specific enough to be helpful to someone looking for venues with pianos?
        
        Don't use rigid metrics - use your judgment about whether we've reached a point of diminishing returns.
        
        Respond with a JSON object:
        {{
            "is_complete": true/false,
            "reasoning": "Your intuitive assessment of completeness",
            "information_value": 0-10 (how valuable/complete our current information is),
            "diminishing_returns": 0-10 (how likely further research is to yield new insights),
            "venue_diversity": 0-10 (how well we've covered different types of venues),
            "next_direction": "If continuing, what specific aspect should we research next"
        }}
        """
        
        result = self._call_gemini(prompt, "low")
        assessment = {
            "is_complete": False,
            "reasoning": "Default assessment - continue research",
            "information_value": 3,
            "diminishing_returns": 2,
            "venue_diversity": 2,
            "next_direction": "Gather basic information about different venue types"
        }
        
        if "response" in result:
            # Extract JSON from response
            try:
                json_match = re.search(r'\{[\s\S]*\}', result["response"])
                if json_match:
                    assessment = json.loads(json_match.group(0))
            except Exception as e:
                logger.error(f"Error extracting assessment JSON: {e}")
                # Use text response as reasoning if JSON parsing fails
                if "response" in result:
                    assessment["reasoning"] = result["response"]
        
        # Make the final determination based on the intuitive assessment
        is_complete = assessment.get("is_complete", False)
        
        # Also consider our own heuristics for completeness
        info_value = int(assessment.get("information_value", 0))
        diminishing = int(assessment.get("diminishing_returns", 0))
        diversity = int(assessment.get("venue_diversity", 0))
        
        # Alternative completion check: good information value + diminishing returns
        if not is_complete and info_value >= 7 and diminishing >= 6:
            is_complete = True
            assessment["reasoning"] += " (System determined: Good information value with diminishing returns)"
        
        # Alternative completion check: enough iterations with moderate information
        if not is_complete and self.research_state["iterations"] >= 5 and info_value >= 5:
            is_complete = True
            assessment["reasoning"] += " (System determined: Sufficient iterations with adequate information)"
        
        reason = assessment.get("reasoning", "No reasoning provided")
        
        if is_complete:
            logger.info(f"Research assessed as complete: {reason}")
            logger.info(f"Final scores - Value: {info_value}/10, Diminishing Returns: {diminishing}/10, Diversity: {diversity}/10")
        else:
            next_direction = assessment.get("next_direction", "No specific direction provided")
            logger.info(f"Research continuing. Next focus: {next_direction}")
            logger.info(f"Current scores - Value: {info_value}/10, Diminishing Returns: {diminishing}/10, Diversity: {diversity}/10")
        
        return is_complete, reason
    
    def _summarize_findings(self, max_per_category: Optional[int] = None) -> str:
        """
        Summarize findings, optionally limiting items per category.
        
        Args:
            max_per_category: Maximum items to include per category
            
        Returns:
            Summary text
        """
        summary = []
        
        for category, items in self.research_state["categories"].items():
            category_summary = f"--- {category} ---\n"
            
            if max_per_category is not None and len(items) > max_per_category:
                items_subset = items[:max_per_category]
                category_summary += "\n".join(items_subset)
                category_summary += f"\n... and {len(items) - max_per_category} more items"
            else:
                category_summary += "\n".join(items)
                
            summary.append(category_summary)
            
        if not summary:
            for finding in self.research_state["findings"][:5]:
                summary.append(finding.get("new_information", ""))
                
        return "\n\n".join(summary)
    
    def _select_urls_to_visit(self, search_results: List[Dict[str, str]]) -> List[str]:
        """
        Select which URLs to visit from search results.
        
        Args:
            search_results: List of search results
            
        Returns:
            List of URLs to visit
        """
        urls_to_visit = []
        
        # Create a prompt with search results
        results_text = ""
        for i, result in enumerate(search_results):
            results_text += f"{i+1}. {result.get('title', 'No Title')}\n"
            results_text += f"   URL: {result.get('href', 'No URL')}\n"
            results_text += f"   Snippet: {result.get('body', 'No description')}\n\n"
        
        prompt = f"""
        Given these search results and our research query: "{self.research_state["query"]}"
        
        SELECT THE MOST PROMISING RESULTS TO INVESTIGATE FURTHER:
        
        {results_text}
        
        Select up to 3 of the most relevant and diverse results that would help answer our query.
        Consider which results would provide:
        1. The most specific information
        2. Information from different perspectives
        3. The most trustworthy sources
        
        Format your response as a JSON array of indices (1-based, matching the numbering above).
        For example: [2, 5, 7]
        """
        
        result = self._call_gemini(prompt, "low")
        
        if "response" in result:
            # Extract JSON array from response
            try:
                json_match = re.search(r'\[[\s\S]*\]', result["response"])
                if json_match:
                    selected_indices = json.loads(json_match.group(0))
                    
                    # Convert to 0-based indices and get URLs
                    for idx in selected_indices:
                        adjusted_idx = idx - 1
                        if 0 <= adjusted_idx < len(search_results):
                            url = search_results[adjusted_idx].get("href")
                            if url and url not in self.research_state["visited_urls"]:
                                urls_to_visit.append(url)
            except Exception as e:
                logger.error(f"Error extracting URL selection JSON: {e}")
        
        # Fallback: if no URLs selected, pick the first result
        if not urls_to_visit and search_results:
            first_url = search_results[0].get("href")
            if first_url and first_url not in self.research_state["visited_urls"]:
                urls_to_visit.append(first_url)
        
        logger.info(f"Selected {len(urls_to_visit)} URLs to visit")
        return urls_to_visit
    
    def _categorize_findings(self) -> None:
        """Categorize all findings into appropriate categories."""
        if not self.research_state["findings"]:
            return
            
        all_findings = [f.get("new_information", "") for f in self.research_state["findings"]]
        findings_text = "\n\n".join(all_findings)
        
        prompt = f"""
        Categorize the following research findings related to our query: "{self.research_state["query"]}"
        
        FINDINGS:
        {findings_text}
        
        Create appropriate categories and group the findings.
        
        Format your response as a JSON object where:
        - Keys are category names
        - Values are arrays of strings (individual findings in that category)
        
        For example:
        {{
            "Category 1": ["Finding 1", "Finding 2"],
            "Category 2": ["Finding 3", "Finding 4"]
        }}
        """
        
        result = self._call_gemini(prompt, "low")
        
        if "response" in result:
            # Extract JSON from response
            try:
                json_match = re.search(r'\{[\s\S]*\}', result["response"])
                if json_match:
                    categories = json.loads(json_match.group(0))
                    self.research_state["categories"] = categories
                    logger.info(f"Categorized findings into {len(categories)} categories")
            except Exception as e:
                logger.error(f"Error extracting categories JSON: {e}")
    
    def _synthesize_results(self) -> Dict[str, Any]:
        """
        Synthesize research results into a final answer.
        
        Returns:
            Dictionary with synthesized results
        """
        # Categorize findings first
        self._categorize_findings()
        
        # Create a summary of all research
        research_summary = {
            "query": self.research_state["query"],
            "iterations": self.research_state["iterations"],
            "search_terms_used": self.research_state["searched_terms"],
            "urls_visited": self.research_state["visited_urls"],
            "categories": self.research_state["categories"]
        }
        
        prompt = f"""
        Synthesize the research findings into a comprehensive answer to the original query.
        
        ORIGINAL QUERY: {self.research_state["query"]}
        
        RESEARCH FINDINGS BY CATEGORY:
        {json.dumps(self.research_state["categories"], indent=2)}
        
        Your answer should:
        1. Be comprehensive and address all aspects of the query
        2. Organize information logically by category
        3. Highlight the most important or relevant findings
        4. Note any significant limitations or gaps in the information
        
        Format your response as a JSON object:
        {{
            "answer": "detailed answer to the query",
            "categories": {{
                "category_name": [list of items in this category],
                ...
            }},
            "limitations": [list of limitations or gaps],
            "sources": [list of sources consulted]
        }}
        """
        
        result = self._call_gemini(prompt, "high")
        synthesis = {
            "answer": "Unable to synthesize results",
            "categories": {},
            "limitations": ["Failed to generate synthesis"],
            "sources": []
        }
        
        if "response" in result:
            # Extract JSON from response
            try:
                json_match = re.search(r'\{[\s\S]*\}', result["response"])
                if json_match:
                    synthesis = json.loads(json_match.group(0))
            except Exception as e:
                logger.error(f"Error extracting synthesis JSON: {e}")
                synthesis["answer"] = result.get("response", "Unable to synthesize results")
        
        # Add research metadata
        synthesis["research_metadata"] = {
            "iterations": self.research_state["iterations"],
            "search_terms_used": len(self.research_state["searched_terms"]),
            "urls_visited": len(self.research_state["visited_urls"])
        }
        
        logger.info("Research synthesis complete")
        return synthesis
    
    def _execute_research_step(self) -> bool:
        """
        Execute a single research step based on current state with adaptive strategy.
        
        This method intelligently decides what to research next based on:
        1. What we've already learned
        2. What gaps remain in our understanding
        3. What search strategies have been most effective so far
        
        Returns:
            True if research should continue, False if complete
        """
        self.research_state["iterations"] += 1
        iteration = self.research_state["iterations"]
        
        logger.info(f"Starting research iteration {iteration}")
        
        # PHASE 1: INITIAL DISCOVERY (Iteration 1)
        if iteration == 1:
            logger.info("PHASE 1: Initial discovery")
            search_terms = self._generate_search_terms(self.research_state["query"])
            
            # Use the first search term for broad exploration
            if search_terms:
                current_term = search_terms[0]
                logger.info(f"Using initial search term: {current_term}")
                search_results = self._web_search(current_term)
                
                # Select URLs to visit
                urls_to_visit = self._select_urls_to_visit(search_results)
                
                # Visit the URLs and gather content
                successful_scrapes = 0
                for url in urls_to_visit:
                    content = self._scrape_url(url)
                    if content:
                        successful_scrapes += 1
                        analysis = self._analyze_content(content, self.research_state["query"])
                        self.research_state["findings"].append(analysis)
                
                # If we didn't get any content, try an alternative search term immediately
                if successful_scrapes == 0 and len(search_terms) > 1:
                    logger.info("Initial search yielded no usable content, trying alternative term")
                    alt_term = search_terms[1]
                    logger.info(f"Using alternative search term: {alt_term}")
                    search_results = self._web_search(alt_term)
                    
                    urls_to_visit = self._select_urls_to_visit(search_results)
                    for url in urls_to_visit:
                        content = self._scrape_url(url)
                        if content:
                            analysis = self._analyze_content(content, self.research_state["query"])
                            self.research_state["findings"].append(analysis)
        
        # PHASE 2: CATEGORY EXPLORATION (Iterations 2-3)
        elif iteration <= 3:
            logger.info("PHASE 2: Category exploration")
            
            # First, identify venue categories from what we know
            venue_types = []
            for finding in self.research_state["findings"]:
                entities = finding.get("entities", [])
                for entity in entities:
                    if any(keyword in entity.lower() for keyword in ["jazz", "piano bar", "concert", "symphony", "club"]):
                        if entity not in venue_types:
                            venue_types.append(entity)
            
            # If we have venue types, search for specific types
            if venue_types and iteration - 2 < len(venue_types):
                venue_type = venue_types[iteration - 2]
                search_term = f"San Francisco {venue_type} piano"
                logger.info(f"Exploring venue category: {venue_type}")
                
                search_results = self._web_search(search_term)
                urls_to_visit = self._select_urls_to_visit(search_results)
                
                # Visit the URLs and gather content
                for url in urls_to_visit:
                    content = self._scrape_url(url)
                    if content:
                        analysis = self._analyze_content(content, search_term)
                        self.research_state["findings"].append(analysis)
            else:
                # No specific venue types found yet, use a general search term
                search_terms = self._generate_search_terms(self.research_state["query"])
                if len(search_terms) > iteration - 1:
                    current_term = search_terms[iteration - 1]
                    logger.info(f"Using general search term: {current_term}")
                    
                    search_results = self._web_search(current_term)
                    urls_to_visit = self._select_urls_to_visit(search_results)
                    
                    # Visit the URLs and gather content
                    for url in urls_to_visit:
                        content = self._scrape_url(url)
                        if content:
                            analysis = self._analyze_content(content, self.research_state["query"])
                            self.research_state["findings"].append(analysis)
        
        # PHASE 3: TARGETED RESEARCH (Iterations 4+)
        else:
            logger.info("PHASE 3: Targeted research based on gaps")
            
            # First, ensure we have categories
            if not self.research_state["categories"]:
                self._categorize_findings()
                
            # Determine what aspect needs more research
            assessment = self._get_research_direction()
            next_direction = assessment.get("next_direction", "")
            
            if next_direction:
                logger.info(f"Targeted research focus: {next_direction}")
                search_term = f"San Francisco piano venues {next_direction}"
                
                search_results = self._web_search(search_term)
                urls_to_visit = self._select_urls_to_visit(search_results)
                
                # Visit the URLs and gather content
                for url in urls_to_visit:
                    content = self._scrape_url(url)
                    if content:
                        analysis = self._analyze_content(content, search_term)
                        self.research_state["findings"].append(analysis)
            else:
                # Fallback: find the least-covered category
                least_covered = None
                min_items = float('inf')
                
                for category, items in self.research_state["categories"].items():
                    if len(items) < min_items:
                        min_items = len(items)
                        least_covered = category
                
                if least_covered:
                    logger.info(f"Researching least covered category: {least_covered}")
                    search_term = f"San Francisco piano venues {least_covered}"
                    
                    search_results = self._web_search(search_term)
                    urls_to_visit = self._select_urls_to_visit(search_results)
                    
                    # Visit the URLs and gather content
                    for url in urls_to_visit:
                        content = self._scrape_url(url)
                        if content:
                            analysis = self._analyze_content(content, search_term)
                            self.research_state["findings"].append(analysis)
        
        # After each iteration, check if we've gathered enough information
        is_complete, reason = self._assess_progress()
        
        # If complete or reached max iterations, stop
        if is_complete or iteration >= self.max_iterations:
            self.research_state["complete"] = True
            logger.info(f"Research complete after {iteration} iterations. Reason: {reason}")
            return False
        
        return True
        
    def _get_research_direction(self) -> Dict[str, Any]:
        """
        Determine the best direction for further research based on current findings.
        
        Returns:
            Dictionary with recommended research direction
        """
        # Prepare a summary of what we've learned
        found_venues = []
        venue_types = []
        
        # Extract venue names and types from findings
        for finding in self.research_state["findings"]:
            entities = finding.get("entities", [])
            
            # Look for venue names and types
            for entity in entities:
                if any(keyword in entity.lower() for keyword in ["hall", "club", "lounge", "bar", "venue"]):
                    if entity not in found_venues:
                        found_venues.append(entity)
                        
                if any(keyword in entity.lower() for keyword in ["jazz", "piano bar", "concert hall", "club"]):
                    if entity not in venue_types and not any(entity in vt for vt in venue_types):
                        venue_types.append(entity)
        
        # Prepare a prompt asking for research direction
        prompt = f"""
        You are a research director guiding a study on music venues in San Francisco with pianos.
        Based on what we've learned so far, suggest what specific aspect we should focus on next.
        
        ORIGINAL QUERY: {self.research_state["query"]}
        
        RESEARCH STATUS:
        - We have investigated {len(self.research_state["visited_urls"])} sources
        - We have found information about approximately {len(found_venues)} venues
        - We have identified these types of venues: {", ".join(venue_types) if venue_types else "None yet"}
        - We've completed {self.research_state["iterations"]} research iterations
        
        CURRENT FINDINGS BY CATEGORY:
        {self._summarize_findings()}
        
        Considering our current progress, what specific aspect of San Francisco piano venues
        should we research next to get the most valuable new information?
        
        Format your response as a JSON object:
        {{
            "next_direction": "specific focus area to research next",
            "reason": "why this direction will yield valuable information",
            "suggested_search_terms": ["term1", "term2"]
        }}
        """
        
        result = self._call_gemini(prompt, "low")
        direction = {
            "next_direction": "",
            "reason": "No specific direction determined",
            "suggested_search_terms": []
        }
        
        if "response" in result:
            # Extract JSON from response
            try:
                json_match = re.search(r'\{[\s\S]*\}', result["response"])
                if json_match:
                    direction = json.loads(json_match.group(0))
            except Exception as e:
                logger.error(f"Error extracting research direction JSON: {e}")
                # Use text response if JSON parsing fails
                if "response" in result:
                    direction["reason"] = result["response"]
                    # Try to extract a direction from the text
                    lines = result["response"].split('\n')
                    for line in lines:
                        if "should" in line.lower() and "research" in line.lower():
                            direction["next_direction"] = line
                            break
        
        return direction
    
    def save_results(self, results: Dict[str, Any], query: str, output_dir: str = "research_results") -> Tuple[str, str]:
        """
        Save research results to files in JSON and readable text formats.
        
        Args:
            results: Research results dictionary
            query: The original query
            output_dir: Directory to save results
            
        Returns:
            Tuple of (json_path, text_path)
        """
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create safe filename from query
        safe_filename = re.sub(r'[^\w\s-]', '', query).strip().lower()
        safe_filename = re.sub(r'[-\s]+', '-', safe_filename)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        base_filename = f"{safe_filename}-{timestamp}"
        
        # Save JSON file
        json_path = os.path.join(output_dir, f"{base_filename}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        # Save text file with readable format
        text_path = os.path.join(output_dir, f"{base_filename}.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("="*80 + "\n")
            f.write(f"Research Results: {query}\n")
            f.write("="*80 + "\n\n")
            
            # Write main answer
            f.write("ANSWER:\n")
            f.write(results.get("answer", "No answer generated") + "\n\n")
            
            # Write categories
            f.write("FINDINGS BY CATEGORY:\n")
            for category, items in results.get("categories", {}).items():
                f.write(f"\n{category.upper()}:\n")
                for i, item in enumerate(items, 1):
                    f.write(f"  {i}. {item}\n")
            
            # Write limitations
            if "limitations" in results and results["limitations"]:
                f.write("\nLIMITATIONS:\n")
                for limitation in results["limitations"]:
                    f.write(f"- {limitation}\n")
            
            # Write sources
            if "sources" in results and results["sources"]:
                f.write("\nSOURCES:\n")
                for source in results["sources"]:
                    f.write(f"- {source}\n")
            
            # Write research metadata
            if "research_metadata" in results:
                f.write("\nRESEARCH METADATA:\n")
                metadata = results["research_metadata"]
                f.write(f"- Iterations: {metadata.get('iterations', 0)}\n")
                f.write(f"- Search terms used: {metadata.get('search_terms_used', 0)}\n")
                f.write(f"- URLs visited: {metadata.get('urls_visited', 0)}\n")
        
        logger.info(f"Research results saved to {json_path} and {text_path}")
        return json_path, text_path
    
    def research(self, query: str, save_results_to_file: bool = True, output_dir: str = "research_results") -> Dict[str, Any]:
        """
        Conduct research on the given query.
        
        Args:
            query: Research query
            save_results_to_file: Whether to save results to files
            output_dir: Directory to save results if save_results_to_file is True
            
        Returns:
            Dictionary with research results
        """
        self.research_state = {
            "query": query,
            "plan": [],
            "findings": [],
            "searched_terms": [],
            "visited_urls": [],
            "categories": {},
            "iterations": 0,
            "complete": False
        }
        
        logger.info(f"Starting research on query: {query}")
        
        # Create a research plan
        self.research_state["plan"] = self._create_research_plan(query)
        
        # Execute research steps until complete
        continue_research = True
        while continue_research:
            continue_research = self._execute_research_step()
            
            # For safety, limit iterations
            if self.research_state["iterations"] >= self.max_iterations:
                logger.warning(f"Reached maximum iterations ({self.max_iterations})")
                break
        
        # Synthesize the results
        results = self._synthesize_results()
        
        # Save results to files if requested
        if save_results_to_file:
            json_path, text_path = self.save_results(results, query, output_dir)
            # Add file paths to results
            results["result_files"] = {
                "json": json_path,
                "text": text_path
            }
        
        logger.info(f"Research complete after {self.research_state['iterations']} iterations")
        return results

def main():
    """Main function to test the autonomous researcher."""
    researcher = AutonomousResearcher()
    query = "Find every music venue in San Francisco with a piano"
    
    print(f"Researching: {query}")
    print("This may take several minutes...")
    
    start_time = time.time()
    results = researcher.research(query)
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*80)
    print(f"Research completed in {elapsed_time:.2f} seconds")
    print("="*80 + "\n")
    
    print("ANSWER:")
    print(results.get("answer", "No answer generated"))
    
    print("\nCATEGORIES:")
    for category, items in results.get("categories", {}).items():
        print(f"\n{category}:")
        for item in items:
            print(f"- {item}")
    
    print("\nLIMITATIONS:")
    for limitation in results.get("limitations", []):
        print(f"- {limitation}")
    
    print("\nRESEARCH METADATA:")
    metadata = results.get("research_metadata", {})
    print(f"- Iterations: {metadata.get('iterations', 0)}")
    print(f"- Search terms used: {metadata.get('search_terms_used', 0)}")
    print(f"- URLs visited: {metadata.get('urls_visited', 0)}")

if __name__ == "__main__":
    main()