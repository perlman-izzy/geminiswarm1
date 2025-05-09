#!/usr/bin/env python3
"""
Test script for the autonomous researcher system.

This script tests the ability of the autonomous researcher to answer complex questions
by self-guiding its research process, determining when it has sufficient information,
and synthesizing findings into a comprehensive answer.
"""

import json
import time
import argparse
import logging
from autonomous_researcher import AutonomousResearcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test(query: str, base_url: str = "http://localhost:5000", max_time: int = 300):
    """
    Run a test of the autonomous researcher.
    
    Args:
        query: The research query to test
        base_url: API endpoint base URL
        max_time: Maximum time in seconds to allow the test to run
    """
    print(f"\n{'='*80}\nTesting Autonomous Researcher\n{'='*80}")
    print(f"Query: {query}")
    print(f"Base URL: {base_url}")
    print(f"Maximum time: {max_time} seconds\n")
    
    researcher = AutonomousResearcher(base_url=base_url)
    
    start_time = time.time()
    timeout = False
    
    # Set a timeout for the research
    def research_with_timeout():
        try:
            return researcher.research(query)
        except KeyboardInterrupt:
            print("\nResearch interrupted by user")
            return {"answer": "Research interrupted", "limitations": ["User interrupted the process"]}
    
    try:
        # Start a timer
        time_limit = start_time + max_time
        
        # Run the research
        print("Starting research... (press Ctrl+C to interrupt)\n")
        results = research_with_timeout()
        
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
    
    # Save results to file
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"research_results_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")
        print(f"\nFailed to save results: {e}")
    
    return results

def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description='Test the autonomous researcher system')
    parser.add_argument('query', nargs='?', default="Find every music venue in San Francisco with a piano", 
                      help='Research query to test')
    parser.add_argument('--base-url', default="http://localhost:5000",
                      help='API endpoint base URL')
    parser.add_argument('--max-time', type=int, default=300,
                      help='Maximum time in seconds to allow the test to run')
    
    args = parser.parse_args()
    
    run_test(args.query, args.base_url, args.max_time)

if __name__ == "__main__":
    main()