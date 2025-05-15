"""
Run direct search tests using the Agent class without going through the API.

This script tests the enhanced non-LLM task validator with complex search tasks.
"""
import json
import sys
import time
from typing import Dict, Any, List
import re

from superagi_replit.agent.agent import Agent
from superagi_replit.lib.logger import logger
from superagi_replit.tools.web_search_tool import WebSearchTool
from superagi_replit.tools.web_scraper_tool import WebScraperTool


def run_search_test(name: str, description: str, goals: List[str], query: str, max_iterations: int = 15) -> Dict[str, Any]:
    """
    Run a search test directly using the Agent class.
    
    Args:
        name: Name of the agent
        description: Description of the agent
        goals: List of goals
        query: Search query
        max_iterations: Maximum number of iterations
        
    Returns:
        Dictionary with test results
    """
    print(f"\n{'=' * 60}")
    print(f"RUNNING TEST: {name}")
    print(f"QUERY: {query}")
    print(f"MAX ITERATIONS: {max_iterations}")
    print(f"{'=' * 60}")
    
    # Create agent
    agent = Agent(
        name=name,
        description=description,
        goals=goals
    )
    
    # Add tools
    agent.add_tool(WebSearchTool())
    agent.add_tool(WebScraperTool())
    
    # Record start time
    start_time = time.time()
    
    # Run the agent
    try:
        response = agent.run(query, max_iterations=max_iterations)
        success = True
    except Exception as e:
        response = f"Error: {str(e)}"
        success = False
    
    # Record end time
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Get validation metrics
    validation_metrics = agent.task_validator.get_status_report()
    
    # Extract any URLs found in the response
    urls = re.findall(r'https?://[^\s\'"]+', response)
    
    # Print results
    print(f"\n{'=' * 60}")
    print(f"TEST RESULTS for {name}")
    print(f"{'=' * 60}")
    print(f"SUCCESS: {success}")
    print(f"EXECUTION TIME: {execution_time:.2f} seconds")
    print(f"ITERATIONS: {validation_metrics['iteration_count']}")
    print(f"TOOL USAGES: {validation_metrics['tool_usages']}")
    print(f"INFORMATION PATTERNS: {validation_metrics['information_patterns']}")
    
    # Print response (truncated if needed)
    if len(response) > 500:
        print(f"\nRESPONSE (truncated): {response[:500]}...[{len(response)} chars total]")
    else:
        print(f"\nRESPONSE: {response}")
    
    # Compile results
    result = {
        "name": name,
        "query": query,
        "success": success,
        "execution_time": execution_time,
        "validation_metrics": validation_metrics,
        "response": response,
        "urls_found": urls,
    }
    
    # Save to file
    filename = f"{name.replace(' ', '_').lower()}_results.json"
    with open(filename, "w") as f:
        try:
            json.dump({k: v for k, v in result.items() if not isinstance(v, set)}, f, indent=2)
            print(f"Results saved to {filename}")
        except:
            # Handle non-serializable objects
            simple_result = {
                "name": name,
                "query": query,
                "success": success,
                "execution_time": execution_time,
                "response": response,
                "urls_found": urls,
                "iterations": validation_metrics['iteration_count'],
                "tool_usages": str(validation_metrics['tool_usages']),
            }
            json.dump(simple_result, f, indent=2)
            print(f"Simplified results saved to {filename}")
    
    return result


def run_all_tests():
    """Run all the complex search tests."""
    # Test 1: Venues with pianos in San Francisco
    run_search_test(
        name="Venue Search Test",
        description="Finding venues with specific features and amenities",
        goals=["Find accurate venue information", "Provide detailed location data", "Verify amenities availability"],
        query="Find all the venues in San Francisco with pianos. Focus on places where pianos are available for use or performances.",
        max_iterations=20
    )
    
    # Test 2: Jazz club emails in NYC
    run_search_test(
        name="Jazz Club Email Test",
        description="Finding contact information for music venues",
        goals=["Find accurate email addresses", "Compile comprehensive contact lists", "Verify email validity"],
        query="Find me 20 email addresses of jazz clubs in New York City. Make sure they are current and valid addresses.",
        max_iterations=20
    )
    
    # Test 3: Clean public restrooms in San Francisco
    run_search_test(
        name="Public Restroom Test",
        description="Finding public facilities with specific criteria",
        goals=["Find public restrooms that meet specific criteria", "Evaluate cleanliness based on reviews", "Provide accurate location information"],
        query="Find me the cleanest public restroom in San Francisco that is not upstairs and that you don't have to purchase anything to use. Include specific locations and cleanliness ratings if available.",
        max_iterations=20
    )


def run_single_test(test_number: int):
    """Run a single test by number."""
    if test_number == 1:
        # Venues with pianos
        run_search_test(
            name="Venue Search Test",
            description="Finding venues with specific features and amenities",
            goals=["Find accurate venue information", "Provide detailed location data", "Verify amenities availability"],
            query="Find all the venues in San Francisco with pianos. Focus on places where pianos are available for use or performances.",
            max_iterations=20
        )
    elif test_number == 2:
        # Jazz club emails
        run_search_test(
            name="Jazz Club Email Test",
            description="Finding contact information for music venues",
            goals=["Find accurate email addresses", "Compile comprehensive contact lists", "Verify email validity"],
            query="Find me 20 email addresses of jazz clubs in New York City. Make sure they are current and valid addresses.",
            max_iterations=20
        )
    elif test_number == 3:
        # Clean public restrooms
        run_search_test(
            name="Public Restroom Test",
            description="Finding public facilities with specific criteria",
            goals=["Find public restrooms that meet specific criteria", "Evaluate cleanliness based on reviews", "Provide accurate location information"],
            query="Find me the cleanest public restroom in San Francisco that is not upstairs and that you don't have to purchase anything to use. Include specific locations and cleanliness ratings if available.",
            max_iterations=20
        )
    else:
        print(f"Invalid test number: {test_number}")


if __name__ == "__main__":
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) > 1:
        try:
            test_number = int(sys.argv[1])
            run_single_test(test_number)
        except ValueError:
            print("Please provide a valid test number (1, 2, or 3)")
    else:
        run_all_tests()