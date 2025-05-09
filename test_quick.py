#!/usr/bin/env python3
"""
Quick test script for the autonomous researcher system with a simplified example.

This script provides a streamlined test of the system's core capabilities
with a smaller scope to run faster for demonstration purposes.
"""

import json
import time
import logging
from autonomous_researcher import AutonomousResearcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplifiedResearcher(AutonomousResearcher):
    """A simplified version of the autonomous researcher with faster execution."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """Initialize with a smaller max iterations value for quicker testing."""
        super().__init__(base_url)
        self.max_iterations = 3  # Limit to just 3 iterations for a quick test
    
    def _assess_progress(self):
        """Simplified assessment logic to complete after fixed iterations."""
        # Always complete after the max iterations
        if self.research_state["iterations"] >= self.max_iterations:
            return True, "Reached test iteration limit"
        
        # Basic check if we have some findings
        if len(self.research_state["findings"]) >= 2:
            return True, "Found at least 2 sources with relevant information"
            
        return False, "Still collecting basic information"

def run_quick_test():
    """Run a quick test of the autonomous researcher."""
    query = "Find piano bars in San Francisco"
    
    print(f"\n{'='*80}\nQuick Test of Autonomous Researcher\n{'='*80}")
    print(f"Query: {query}")
    
    researcher = SimplifiedResearcher()
    
    start_time = time.time()
    
    try:
        print("Starting simplified research...\n")
        results = researcher.research(query)
        
    except Exception as e:
        logger.error(f"Error during research: {e}")
        results = {"answer": f"Error during research: {e}", "limitations": ["Research encountered an error"]}
    
    elapsed_time = time.time() - start_time
    
    print(f"\n{'='*80}")
    print(f"Research completed in {elapsed_time:.2f} seconds")
    print(f"{'='*80}\n")
    
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
    
    return results

if __name__ == "__main__":
    run_quick_test()