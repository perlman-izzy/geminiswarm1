"""
Run all the direct search tests using the DirectAgent with mock LLM.
This demonstrates task completion validation without dependency on external APIs.
"""
import json
import os
import time
from typing import Dict, Any, List

from superagi_replit.agent.direct_agent import DirectAgent
from superagi_replit.tools.web_search_tool import WebSearchTool
from superagi_replit.tools.web_scraper_tool import WebScraperTool


def run_task_test(name: str, description: str, goals: List[str], query: str, max_iterations: int = 15) -> Dict[str, Any]:
    """
    Run a task test using the direct agent.
    
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
    agent = DirectAgent(
        name=name,
        description=description,
        goals=goals
    )
    
    # Add tools
    agent.add_tool(WebSearchTool())
    agent.add_tool(WebScraperTool())
    
    # Run the agent
    result = agent.run(query, max_iterations=max_iterations)
    
    # Print results
    print(f"\n{'=' * 60}")
    print(f"TEST RESULTS for {name}")
    print(f"{'=' * 60}")
    print(f"SUCCESS: {result['completed']}")
    print(f"EXECUTION TIME: {result['execution_time']:.2f} seconds")
    print(f"ITERATIONS: {result['iterations']}/{max_iterations}")
    print(f"REASON: {result['reason']}")
    print(f"CONFIDENCE: {result['confidence']:.2f}")
    
    # Print tool usages
    tool_usages = result.get("tool_uses", {})
    print("\nTOOL USAGES:")
    for tool, count in tool_usages.items():
        print(f"- {tool}: {count}")
    
    # Print response preview
    final_response = result.get("final_response", "")
    if final_response:
        preview = final_response[:500] + "..." if len(final_response) > 500 else final_response
        print(f"\nRESPONSE PREVIEW: {preview}")
    
    # Save result to file
    save_result(result, f"{name.lower().replace(' ', '_')}_result.json")
    
    return result


def save_result(result: Dict[str, Any], filename: str) -> None:
    """
    Save a result to a file.
    
    Args:
        result: Result dictionary
        filename: Filename to save to
    """
    # Ensure the test_results directory exists
    os.makedirs("test_results", exist_ok=True)
    filepath = os.path.join("test_results", filename)
    
    # Create a serializable version of the result
    serializable_result = {
        "task": result["task"],
        "goals": result["goals"],
        "completed": result["completed"],
        "reason": result["reason"],
        "confidence": result["confidence"],
        "iterations": result["iterations"],
        "max_iterations": result["max_iterations"],
        "execution_time": result["execution_time"],
        "tool_uses": {str(k): v for k, v in result.get("tool_uses", {}).items()},
        "final_response_preview": result.get("final_response", "")[:1000] + "..." if result.get("final_response", "") else ""
    }
    
    # Save to file
    with open(filepath, "w") as f:
        json.dump(serializable_result, f, indent=2)
    
    print(f"Result saved to {filepath}")


def run_all_tests():
    """Run all three test cases."""
    # Test 1: Venues with pianos in San Francisco
    venue_result = run_task_test(
        name="Venue Search Test",
        description="Finding venues with specific features and amenities",
        goals=["Find accurate venue information", "Provide detailed location data", "Verify amenities availability"],
        query="Find all the venues in San Francisco with pianos. Focus on places where pianos are available for use or performances.",
        max_iterations=5
    )
    
    # Test 2: Jazz club emails in NYC
    email_result = run_task_test(
        name="Jazz Club Email Test",
        description="Finding contact information for music venues",
        goals=["Find accurate email addresses", "Compile comprehensive contact lists", "Verify email validity"],
        query="Find me 20 email addresses of jazz clubs in New York City. Make sure they are current and valid addresses.",
        max_iterations=5
    )
    
    # Test 3: Clean public restrooms in San Francisco
    restroom_result = run_task_test(
        name="Public Restroom Test",
        description="Finding public facilities with specific criteria",
        goals=["Find public restrooms that meet specific criteria", "Evaluate cleanliness based on reviews", "Provide accurate location information"],
        query="Find me the cleanest public restroom in San Francisco that is not upstairs and that you don't have to purchase anything to use. Include specific locations and cleanliness ratings if available.",
        max_iterations=5
    )
    
    # Print overall results
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)
    print(f"Venue Search: {'✓' if venue_result['completed'] else '✗'} - {venue_result['reason']}")
    print(f"Email Search: {'✓' if email_result['completed'] else '✗'} - {email_result['reason']}")
    print(f"Restroom Search: {'✓' if restroom_result['completed'] else '✗'} - {restroom_result['reason']}")
    

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_num = int(sys.argv[1])
        if test_num == 1:
            run_task_test(
                name="Venue Search Test",
                description="Finding venues with specific features and amenities",
                goals=["Find accurate venue information", "Provide detailed location data", "Verify amenities availability"],
                query="Find all the venues in San Francisco with pianos. Focus on places where pianos are available for use or performances.",
                max_iterations=5
            )
        elif test_num == 2:
            run_task_test(
                name="Jazz Club Email Test",
                description="Finding contact information for music venues",
                goals=["Find accurate email addresses", "Compile comprehensive contact lists", "Verify email validity"],
                query="Find me 20 email addresses of jazz clubs in New York City. Make sure they are current and valid addresses.",
                max_iterations=5
            )
        elif test_num == 3:
            run_task_test(
                name="Public Restroom Test",
                description="Finding public facilities with specific criteria", 
                goals=["Find public restrooms that meet specific criteria", "Evaluate cleanliness based on reviews", "Provide accurate location information"],
                query="Find me the cleanest public restroom in San Francisco that is not upstairs and that you don't have to purchase anything to use. Include specific locations and cleanliness ratings if available.",
                max_iterations=5
            )
        else:
            print(f"Invalid test number: {test_num}")
    else:
        run_all_tests()