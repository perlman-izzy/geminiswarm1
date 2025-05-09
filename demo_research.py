#!/usr/bin/env python3
"""
Demo script for the autonomous researcher system concept.

This script demonstrates the key concepts of the autonomous researcher
in a simplified way that can run quickly for demonstration purposes.
"""

import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DemoResearcher:
    """A simplified demonstration of the autonomous researcher concept."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        Initialize the demo researcher.
        
        Args:
            base_url: Base URL for API endpoints
        """
        self.base_url = base_url
        self.findings = []
        self.visited_urls = []
        self.search_terms = []
        
    def call_gemini(self, prompt: str) -> Dict[str, Any]:
        """
        Call the Gemini API.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Response from Gemini API
        """
        try:
            url = f"{self.base_url}/gemini"
            response = requests.post(
                url,
                json={"prompt": prompt, "priority": "low"},
                headers={"Content-Type": "application/json"}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return {"status": "error", "response": str(e)}
    
    def web_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
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
            self.search_terms.append(query)
            logger.info(f"Web search for '{query}' found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []
    
    def scrape_url(self, url: str) -> str:
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
                self.visited_urls.append(url)
                logger.info(f"Successfully scraped URL: {url}")
                return content
            else:
                logger.warning(f"Failed to scrape URL: {url}")
                return ""
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {e}")
            return ""
    
    def analyze_content(self, content: str, context: str) -> Dict[str, Any]:
        """
        Analyze content in the given context.
        
        Args:
            content: Text content to analyze
            context: Context for analysis
            
        Returns:
            Analysis results
        """
        prompt = f"""
        Analyze the following content about {context}.
        
        CONTENT:
        {content[:1500]}...
        
        Extract the following information:
        1. Key facts about piano bars in San Francisco
        2. Names of specific piano bars mentioned
        3. Notable features of these bars (atmosphere, type of music, etc.)
        4. Any address information or location details
        
        Format your response as a JSON object with these fields:
        {{
            "key_facts": [list of facts],
            "venue_names": [list of venue names],
            "features": [list of notable features],
            "locations": [list of location details]
        }}
        """
        
        result = self.call_gemini(prompt)
        
        # Extract JSON from response
        if "response" in result:
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', result["response"])
                if json_match:
                    return json.loads(json_match.group(0))
            except Exception as e:
                logger.error(f"Error extracting JSON from analysis: {e}")
        
        # Return empty structure if we couldn't parse
        return {
            "key_facts": [],
            "venue_names": [],
            "features": [],
            "locations": []
        }
    
    def synthesize_results(self) -> Dict[str, Any]:
        """
        Synthesize findings into a final answer.
        
        Returns:
            Dictionary with synthesized results
        """
        if not self.findings:
            return {
                "answer": "No information found on piano bars in San Francisco",
                "venues": [],
                "limitations": ["Insufficient data collected"]
            }
        
        # Collect all venue names and facts
        all_venues = []
        all_facts = []
        all_features = []
        all_locations = []
        
        for finding in self.findings:
            # Make sure we only extend with properly formatted lists
            venue_names = finding.get("venue_names", [])
            if isinstance(venue_names, list):
                all_venues.extend(venue_names)
                
            key_facts = finding.get("key_facts", [])
            if isinstance(key_facts, list):
                all_facts.extend(key_facts)
                
            features = finding.get("features", [])
            if isinstance(features, list):
                all_features.extend(features)
                
            locations = finding.get("locations", [])
            if isinstance(locations, list):
                all_locations.extend(locations)
        
        # Make sure all items are hashable (strings)
        all_venues = [str(v) for v in all_venues if v is not None]
        all_facts = [str(f) for f in all_facts if f is not None]
        all_features = [str(feat) for feat in all_features if feat is not None]
        all_locations = [str(loc) for loc in all_locations if loc is not None]
        
        # Remove duplicates
        venues = list(set(all_venues))
        facts = list(set(all_facts))
        features = list(set(all_features))
        locations = list(set(all_locations))
        
        # Generate a summary
        venue_info = []
        for venue in venues:
            venue_dict = {"name": venue, "details": []}
            
            # Find features and locations related to this venue
            for feature in features:
                if venue.lower() in feature.lower():
                    venue_dict["details"].append(feature)
                    
            for location in locations:
                if venue.lower() in location.lower():
                    venue_dict["details"].append(location)
                    
            venue_info.append(venue_dict)
        
        # Create a simple answer
        if venues:
            answer = f"Found {len(venues)} piano bars in San Francisco including {', '.join(venues[:3])}"
            if len(venues) > 3:
                answer += f" and {len(venues) - 3} more"
            answer += ". "
            
            if facts:
                answer += f"Key information: {facts[0]}"
        else:
            answer = "Could not find specific piano bars in San Francisco based on the research."
        
        return {
            "answer": answer,
            "venues": venue_info,
            "facts": facts[:5],
            "limitations": ["Limited search scope for demonstration"]
        }
    
    def research(self, query: str) -> Dict[str, Any]:
        """
        Conduct a simplified research demonstration.
        
        Args:
            query: Research query
            
        Returns:
            Dictionary with research results
        """
        logger.info(f"Starting demo research on: {query}")
        
        # Step 1: Search for the query
        logger.info("Step 1: Initial web search")
        search_results = self.web_search(query)
        
        # Step 2: Visit a couple of URLs
        logger.info("Step 2: Exploring search results")
        urls_visited = 0
        
        for result in search_results[:3]:  # Limit to 3 URLs for demo
            url = result.get("href")
            if url:
                content = self.scrape_url(url)
                if content:
                    urls_visited += 1
                    analysis = self.analyze_content(content, query)
                    self.findings.append(analysis)
                    
                    # If we have 2 sources, that's enough for the demo
                    if urls_visited >= 2:
                        break
        
        # Step 3: Synthesize the results
        logger.info("Step 3: Synthesizing findings")
        results = self.synthesize_results()
        
        # Add metadata
        results["research_metadata"] = {
            "urls_visited": len(self.visited_urls),
            "search_terms_used": len(self.search_terms)
        }
        
        logger.info("Research demo complete")
        return results

def run_demo():
    """Run the research demonstration."""
    query = "Find piano bars in San Francisco"
    
    print(f"\n{'='*80}\nResearch System Demo\n{'='*80}")
    print(f"Query: {query}")
    
    researcher = DemoResearcher()
    
    start_time = time.time()
    
    try:
        print("Starting demonstration research...\n")
        results = researcher.research(query)
        
    except Exception as e:
        logger.error(f"Error during research: {e}")
        results = {"answer": f"Error during research: {e}"}
    
    elapsed_time = time.time() - start_time
    
    print(f"\n{'='*80}")
    print(f"Research completed in {elapsed_time:.2f} seconds")
    print(f"{'='*80}\n")
    
    print("ANSWER:")
    print(results.get("answer", "No answer generated"))
    
    print("\nVENUES FOUND:")
    for venue in results.get("venues", []):
        print(f"\n- {venue['name']}")
        for detail in venue.get("details", []):
            print(f"  * {detail}")
    
    print("\nKEY FACTS:")
    for fact in results.get("facts", []):
        print(f"- {fact}")
    
    print("\nLIMITATIONS:")
    for limitation in results.get("limitations", []):
        print(f"- {limitation}")
    
    print("\nRESEARCH METADATA:")
    metadata = results.get("research_metadata", {})
    print(f"- URLs visited: {metadata.get('urls_visited', 0)}")
    print(f"- Search terms used: {metadata.get('search_terms_used', 0)}")
    
    return results

if __name__ == "__main__":
    run_demo()