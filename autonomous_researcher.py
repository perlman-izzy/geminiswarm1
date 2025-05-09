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
        Call the Gemini API with retry logic for rate limits.
        
        Args:
            prompt: The prompt to send
            priority: Priority level (low or high)
            
        Returns:
            Response from Gemini API
        """
        max_retries = 3
        retry_delay = 3  # seconds
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/gemini"
                response = requests.post(
                    url,
                    json={"prompt": prompt, "priority": priority},
                    headers={"Content-Type": "application/json"}
                )
                
                result = response.json()
                
                # Check if we hit a rate limit (based on error message)
                if "error" in result.get("response", "").lower() and "quota" in result.get("response", "").lower():
                    logger.warning(f"API rate limit hit, attempt {attempt+1}/{max_retries}")
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting {retry_delay} seconds before retry")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                
                return result
                
            except Exception as e:
                logger.error(f"Error calling Gemini API (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Waiting {retry_delay} seconds before retry")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                
        return {"status": "error", "response": "Failed after multiple attempts"}
    
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
        Assess research progress and determine if it's complete.
        
        Returns:
            Tuple of (is_complete, reason)
        """
        # Simple checks first
        if self.research_state["iterations"] >= self.max_iterations:
            return True, "Reached maximum iterations"
        
        if not self.research_state["findings"]:
            return False, "No findings yet"
        
        # Use Gemini to assess progress
        state_summary = json.dumps({
            "query": self.research_state["query"],
            "iterations": self.research_state["iterations"],
            "search_terms_used": self.research_state["searched_terms"],
            "urls_visited": len(self.research_state["visited_urls"]),
            "findings_count": len(self.research_state["findings"]),
            "categories": list(self.research_state["categories"].keys())
        })
        
        prompt = f"""
        Assess whether the following research progress is sufficient to answer the original query.
        
        ORIGINAL QUERY: {self.research_state["query"]}
        
        RESEARCH PROGRESS:
        {state_summary}
        
        FINDINGS SUMMARY:
        {self._summarize_findings(3)}
        
        Consider:
        1. Do we have enough information to provide a useful answer?
        2. Are there major gaps in our knowledge?
        3. Would additional research likely yield substantially new information?
        
        Respond with a JSON object:
        {{
            "is_complete": true/false,
            "reasoning": "explanation of your assessment",
            "gaps": ["list any significant gaps"],
            "next_steps": ["recommended next steps if not complete"]
        }}
        """
        
        result = self._call_gemini(prompt, "low")
        assessment = {
            "is_complete": False,
            "reasoning": "Default assessment - continue research",
            "gaps": ["No specific gaps identified yet"],
            "next_steps": ["Continue with research plan"]
        }
        
        if "response" in result:
            # Extract JSON from response
            try:
                json_match = re.search(r'\{[\s\S]*\}', result["response"])
                if json_match:
                    assessment = json.loads(json_match.group(0))
            except Exception as e:
                logger.error(f"Error extracting assessment JSON: {e}")
        
        is_complete = assessment.get("is_complete", False)
        reason = assessment.get("reasoning", "No reasoning provided")
        
        if is_complete:
            logger.info(f"Research assessed as complete: {reason}")
        else:
            gaps = ", ".join(assessment.get("gaps", ["None specified"]))
            logger.info(f"Research continuing. Gaps: {gaps}")
        
        return is_complete, reason
    
    def _summarize_findings(self, max_per_category: int = None) -> str:
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
        Execute a single research step based on current state.
        
        Returns:
            True if research should continue, False if complete
        """
        self.research_state["iterations"] += 1
        iteration = self.research_state["iterations"]
        
        logger.info(f"Starting research iteration {iteration}")
        
        # 1. If no search terms yet, generate them
        if not self.research_state["searched_terms"]:
            search_terms = self._generate_search_terms(self.research_state["query"])
            
            # Use the first search term
            if search_terms:
                current_term = search_terms[0]
                search_results = self._web_search(current_term)
                
                # Select URLs to visit
                urls_to_visit = self._select_urls_to_visit(search_results)
                
                # Visit the URLs and gather content
                for url in urls_to_visit:
                    content = self._scrape_url(url)
                    if content:
                        analysis = self._analyze_content(content, self.research_state["query"])
                        self.research_state["findings"].append(analysis)
                
            return True
            
        # 2. If we have searched but need more information
        elif iteration < len(self.research_state["searched_terms"]) + 3:
            # Try a different search term if available
            if iteration - 1 < len(self._generate_search_terms(self.research_state["query"])):
                search_terms = self._generate_search_terms(self.research_state["query"])
                current_term = search_terms[iteration - 1]
                
                # Check if we've already used this term
                if current_term in self.research_state["searched_terms"]:
                    current_term = f"{current_term} additional information"
                
                search_results = self._web_search(current_term)
                
                # Select URLs to visit
                urls_to_visit = self._select_urls_to_visit(search_results)
                
                # Visit the URLs and gather content
                for url in urls_to_visit:
                    content = self._scrape_url(url)
                    if content:
                        analysis = self._analyze_content(content, self.research_state["query"])
                        self.research_state["findings"].append(analysis)
            
            # Generate specialized search based on current findings if needed
            elif self.research_state["findings"]:
                # Identify what we need more information about
                categories = list(self.research_state["categories"].keys()) if self.research_state["categories"] else []
                if not categories and self.research_state["findings"]:
                    self._categorize_findings()
                    categories = list(self.research_state["categories"].keys())
                
                # Focus on areas with less information
                least_covered = None
                min_items = float('inf')
                
                for category, items in self.research_state["categories"].items():
                    if len(items) < min_items:
                        min_items = len(items)
                        least_covered = category
                
                if least_covered:
                    specialized_term = f"{self.research_state['query']} {least_covered}"
                    search_results = self._web_search(specialized_term)
                    
                    # Select URLs to visit
                    urls_to_visit = self._select_urls_to_visit(search_results)
                    
                    # Visit the URLs and gather content
                    for url in urls_to_visit:
                        content = self._scrape_url(url)
                        if content:
                            analysis = self._analyze_content(content, specialized_term)
                            self.research_state["findings"].append(analysis)
        
        # 3. Assess if we have enough information
        is_complete, reason = self._assess_progress()
        
        # If complete or reached max iterations, stop
        if is_complete or iteration >= self.max_iterations:
            self.research_state["complete"] = True
            logger.info(f"Research complete after {iteration} iterations. Reason: {reason}")
            return False
        
        return True
    
    def research(self, query: str) -> Dict[str, Any]:
        """
        Conduct research on the given query.
        
        Args:
            query: Research query
            
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