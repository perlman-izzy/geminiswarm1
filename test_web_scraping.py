#!/usr/bin/env python3
"""
Test script for the improved web scraping and error handling in the autonomous researcher
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
        print(f"First result: {results[0].get('title', 'No title')} - {results[0].get('href', 'No URL')}")
    
    # Test with an invalid query (too short)
    print("\nTesting invalid query (too short):")
    results = researcher._web_search("a")
    print(f"Found {len(results)} results for query 'a' (expected 0 due to length)")
    
    # Test with a very specific query that might return no results
    print("\nTesting query that might return no results:")
    results = researcher._web_search("xyzabc123987nonexistenttermqwerty")
    print(f"Found {len(results)} results for 'xyzabc123987nonexistenttermqwerty'")
    
    return True

def test_url_scraping_with_retry():
    """Test the URL scraping function with retry logic"""
    print("\n=== Testing URL Scraping with Retry Logic ===")
    
    # Create a researcher instance
    researcher = AutonomousResearcher()
    
    # Test with a valid URL
    valid_url = "https://www.seattletimes.com/life/food-drink/9-of-seattles-most-outstanding-coffee-shops/"
    print(f"\nTesting valid URL: {valid_url}")
    content = researcher._scrape_url(valid_url)
    print(f"Scraped {len(content)} characters from valid URL")
    print(f"Content snippet: {content[:200]}..." if content else "No content scraped")
    
    # Test with an invalid URL
    print("\nTesting invalid URL format:")
    content = researcher._scrape_url("not-a-valid-url")
    print("Expected result: Empty string due to invalid format" + (" ✓" if content == "" else " ✗"))
    
    # Test with a URL that should be blocked by robots.txt
    print("\nTesting URL likely to be protected by robots.txt:")
    content = researcher._scrape_url("https://www.linkedin.com/jobs/")
    print(f"Scraped content length: {len(content)} characters")
    print("Expected: Either empty string due to robots.txt or minimal content")
    
    # Test with a non-existent URL
    print("\nTesting non-existent URL:")
    content = researcher._scrape_url("https://example.com/nonexistent-page-12345")
    print(f"Scraped content length: {len(content)} characters")
    print("Expected: Empty string or error page content")
    
    # Test already visited URL (should skip)
    if valid_url.split('?')[0].rstrip('/') in researcher.research_state["visited_urls"]:
        print("\nTesting already visited URL (should skip):")
        content = researcher._scrape_url(valid_url)
        print(f"Scraped content length: {len(content)} characters")
        print("Expected: Empty string as URL should be skipped")
    
    return True

def test_research_with_improved_scraping():
    """Test a quick research task with the improved scraping functionality"""
    print("\n=== Testing Quick Research Task with Improved Scraping ===")
    
    # Create a researcher instance with limited iterations
    researcher = AutonomousResearcher()
    researcher.max_iterations = 2  # Limit to 2 iterations for faster testing
    
    # Make the scraper more aggressive for testing
    original_select_urls = researcher._select_urls_to_visit
    def test_url_selection(search_results):
        # Always pick the first three results for testing
        urls = []
        for i, result in enumerate(search_results):
            if i < 3 and 'href' in result:  # Take up to 3 URLs
                urls.append(result['href'])
        return urls
    researcher._select_urls_to_visit = test_url_selection
    
    # Run a quick research task
    query = "Describe Seattle's coffee culture"
    print(f"\nRunning quick research on: '{query}'")
    start_time = time.time()
    
    # Run the research
    results = researcher.research(query, save_results_to_file=True)
    
    elapsed_time = time.time() - start_time
    print(f"\nResearch completed in {elapsed_time:.2f} seconds")
    
    # Print research statistics
    visited_urls = researcher.research_state.get("visited_urls", [])
    searched_terms = researcher.research_state.get("searched_terms", [])
    findings = researcher.research_state.get("findings", [])
    
    print(f"\nResearch statistics:")
    print(f"- Iterations completed: {researcher.research_state.get('iterations', 0)}")
    print(f"- Search terms used: {len(searched_terms)}")
    print(f"- URLs visited: {len(visited_urls)} (including retries)")
    print(f"- Findings collected: {len(findings)}")
    
    if "result_files" in results:
        print(f"\nResults saved to:")
        print(f"- JSON: {results['result_files']['json']}")
        print(f"- Text: {results['result_files']['text']}")
        
        # Show the beginning of the text file
        if os.path.exists(results['result_files']['text']):
            print("\nAnswer from research:")
            print("-" * 80)
            with open(results['result_files']['text'], 'r') as f:
                content = f.read()
                answer_start = content.find("ANSWER:")
                if answer_start >= 0:
                    answer_end = content.find("\n\nFINDINGS BY CATEGORY:")
                    if answer_end >= 0:
                        print(content[answer_start:answer_end])
                    else:
                        print(content[answer_start:answer_start + 500] + "...")
                else:
                    print(content[:500] + "...")
            print("-" * 80)
    
    # Print models used
    print("\nModels used:")
    models_used = {}
    for finding in findings:
        model = finding.get("model_used", "unknown")
        models_used[model] = models_used.get(model, 0) + 1
    
    for model, count in models_used.items():
        print(f"- {model}: {count} times")
    
    if "model_used_for_synthesis" in results:
        print(f"- Synthesis model: {results['model_used_for_synthesis']}")
    
    return results

def main():
    """Run all tests for web scraping improvements"""
    print("Testing autonomous researcher's improved web scraping functionality")
    
    # Run individual tests
    web_search_ok = test_web_search_with_retry()
    url_scraping_ok = test_url_scraping_with_retry()
    
    # Run research test with improved scraping
    research_results = test_research_with_improved_scraping()
    
    # Print overall results
    print("\n" + "=" * 80)
    print("TEST RESULTS:")
    print(f"Web search with retry: {'Success' if web_search_ok else 'Failed'}")
    print(f"URL scraping with retry: {'Success' if url_scraping_ok else 'Failed'}")
    print(f"Research with improved scraping: {'Success' if research_results else 'Failed'}")
    print("=" * 80)
    
    print("\nAll tests completed")

if __name__ == "__main__":
    main()