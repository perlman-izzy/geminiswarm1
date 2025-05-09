#!/usr/bin/env python3
"""
Test script for the improved web search error handling in the autonomous researcher
"""

import os
import sys
import time
from autonomous_researcher import AutonomousResearcher

def test_web_search_with_retry():
    """Test the web search function with retry logic"""
    print("\n=== Testing Web Search with Retry Logic ===")
    
    # Create a researcher instance
    researcher = AutonomousResearcher()
    
    # Test with a valid query
    print("\nTesting valid web search query:")
    results = researcher._web_search("best coffee shops in Seattle")
    print(f"Found {len(results)} results for 'best coffee shops in Seattle'")
    
    # Print the first result if available
    if results:
        print(f"First result: {results[0].get('title', 'No title')}")
        print(f"URL: {results[0].get('href', 'No URL')}")
    
    # Test with an invalid query (too short)
    print("\nTesting invalid query (too short):")
    results = researcher._web_search("a")
    print(f"Found {len(results)} results for query 'a' (expected 0 due to length)")
    
    return True

def test_quick_research():
    """Test a single research step with the improved error handling"""
    print("\n=== Testing Quick Research with Improved Error Handling ===")
    
    # Create a researcher instance with very limited execution
    researcher = AutonomousResearcher()
    
    # Override to limit to exactly one iteration
    researcher.max_iterations = 1
    
    # Override url selection to pick just one URL to visit
    original_select_urls = researcher._select_urls_to_visit
    def select_single_url(search_results):
        if search_results and len(search_results) > 0 and 'href' in search_results[0]:
            return [search_results[0]['href']]
        return []
    researcher._select_urls_to_visit = select_single_url
    
    # Run a simple research and time it
    query = "What is Seattle's best coffee shop"
    print(f"\nResearching: '{query}'")
    
    start_time = time.time()
    results = researcher.research(query, save_results_to_file=True)
    elapsed_time = time.time() - start_time
    
    print(f"\nResearch completed in {elapsed_time:.2f} seconds")
    
    # Show research statistics
    print(f"\nResearch statistics:")
    print(f"- Search terms: {researcher.research_state['searched_terms']}")
    print(f"- URLs visited: {researcher.research_state['visited_urls']}")
    print(f"- Findings count: {len(researcher.research_state['findings'])}")
    
    # Show model usage summary
    print("\nModels used:")
    models = {}
    for finding in researcher.research_state["findings"]:
        model = finding.get("model_used", "unknown")
        models[model] = models.get(model, 0) + 1
    
    for model, count in models.items():
        print(f"- {model}: {count} times")
    
    # Show result file paths
    if "result_files" in results:
        print(f"\nResults saved to:")
        print(f"- JSON: {results['result_files']['json']}")
        print(f"- Text: {results['result_files']['text']}")
    
    return results

def main():
    """Run the test script"""
    print("Testing autonomous researcher's improved web search error handling")
    
    # Run the test
    success = test_web_search_with_retry()
    
    # Run a quick research
    results = test_quick_research()
    
    # Print overall results
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY:")
    print(f"- Web search with retry: {'Success' if success else 'Failed'}")
    print(f"- Quick research test: {'Success' if results else 'Failed'}")
    
    # If we have results with a text file, show the answer
    if results and "result_files" in results and "text" in results["result_files"]:
        text_path = results["result_files"]["text"]
        if os.path.exists(text_path):
            print("\nRESEARCH ANSWER:")
            print("-" * 80)
            with open(text_path, 'r') as f:
                content = f.read()
                # Find and display just the answer portion
                answer_start = content.find("ANSWER:")
                if answer_start >= 0:
                    answer_end = content.find("\n\nFINDINGS")
                    if answer_end > 0:
                        print(content[answer_start:answer_end])
                    else:
                        print(content[answer_start:answer_start+500] + "...")
                else:
                    print(content[:500] + "...")
            print("-" * 80)
    
    print("\nTest completed")

if __name__ == "__main__":
    main()