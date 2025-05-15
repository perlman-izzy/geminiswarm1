"""
Test script for complex search tasks with non-LLM validation.

This script tests the SuperAGI system with difficult search tasks
that require persistence, intelligent search strategies, and proper
stopping conditions.
"""
import json
import requests
import sys
import time
from typing import Dict, Any, List
import argparse

# Configuration
API_BASE_URL = "http://localhost:5000"
DEFAULT_MAX_ITERATIONS = 20  # Higher for complex tasks


def create_test_agent(name: str, description: str, goals: List[str]) -> Dict[str, Any]:
    """Create a new agent via the API."""
    print(f"\n=========== Creating Agent: {name} ===========")
    response = requests.post(
        f"{API_BASE_URL}/agents",
        json={
            "name": name,
            "description": description,
            "goals": goals
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to create agent: {response.text}")
    
    agent_data = response.json()
    print(f"Agent created with ID: {agent_data['id']}")
    return agent_data


def execute_search_task(agent_id: int, query: str, max_iterations: int = DEFAULT_MAX_ITERATIONS) -> Dict[str, Any]:
    """Execute a complex search task with an agent."""
    print(f"\n=========== Executing Search Task ===========")
    print(f"Query: {query}")
    print(f"Max iterations: {max_iterations}")
    print("Sending request...")
    
    start_time = time.time()
    response = requests.post(
        f"{API_BASE_URL}/agent-execution",
        json={
            "agent_id": agent_id,
            "user_input": query,
            "max_iterations": max_iterations
        }
    )
    
    execution_time = time.time() - start_time
    
    if response.status_code != 200:
        print(f"Error executing task: {response.text}")
        return {"error": response.text, "execution_time": execution_time}
    
    result = response.json()
    print(f"Execution completed in {execution_time:.2f} seconds")
    print(f"Execution ID: {result.get('execution_id')}")
    
    # Truncate the response for display if it's too long
    response_text = result.get('response', '')
    if len(response_text) > 500:
        print(f"Response (truncated): {response_text[:500]}...[{len(response_text)} chars total]")
    else:
        print(f"Response: {response_text}")
        
    result['execution_time'] = execution_time
    return result


def get_execution_feed(execution_id: int) -> List[Dict[str, Any]]:
    """Get the execution feed to analyze the search process."""
    print(f"\n=========== Getting Execution Feed ===========")
    print(f"Execution ID: {execution_id}")
    
    response = requests.get(f"{API_BASE_URL}/agent-execution/{execution_id}/feed")
    
    if response.status_code != 200:
        print(f"Error getting feed: {response.text}")
        return []
    
    feed = response.json()
    print(f"Retrieved {len(feed)} feed items")
    return feed


def analyze_search_process(feed: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """Analyze the search process to evaluate effectiveness."""
    print(f"\n=========== Analyzing Search Process ===========")
    
    analysis = {
        "total_messages": len(feed),
        "user_messages": sum(1 for item in feed if item.get("role") == "user"),
        "assistant_messages": sum(1 for item in feed if item.get("role") == "assistant"),
        "system_messages": sum(1 for item in feed if item.get("role") == "system"),
        "tool_usages": {},
        "iterations": 0,
        "information_sources": set(),
        "search_strategies_detected": [],
    }
    
    # Look for tool usages and search strategies
    for item in feed:
        content = item.get("feed", "").lower()
        
        # Count tool usages
        if "tool" in content and item.get("role") == "assistant":
            analysis["iterations"] += 1
            
            # Try to parse JSON in the content
            try:
                if '```' in content:
                    json_str = content.split('```')[1].strip()
                    if json_str.startswith('json'):
                        json_str = json_str[4:].strip()
                    data = json.loads(json_str)
                    
                    if "tool" in data:
                        tool_name = data["tool"]
                        analysis["tool_usages"][tool_name] = analysis["tool_usages"].get(tool_name, 0) + 1
                        
                        # Track search strategies
                        if tool_name == "WebSearchTool" and "tool_input" in data:
                            query_terms = data["tool_input"].get("query", "").lower()
                            if "site:" in query_terms:
                                analysis["search_strategies_detected"].append("site-specific search")
                            if "email" in query_terms and "contact" in query_terms:
                                analysis["search_strategies_detected"].append("contact information search")
                            if "review" in query_terms or "rating" in query_terms:
                                analysis["search_strategies_detected"].append("review-based search")
                            if "location" in query_terms or "address" in query_terms:
                                analysis["search_strategies_detected"].append("location-based search")
            except:
                pass
                
        # Extract URLs (information sources)
        urls = re.findall(r'https?://[^\s\'"]+', content)
        for url in urls:
            analysis["information_sources"].add(url)
    
    # Remove duplicates from strategies
    analysis["search_strategies_detected"] = list(set(analysis["search_strategies_detected"]))
    analysis["information_sources"] = list(analysis["information_sources"])
    
    # Print summary
    print(f"Iterations: {analysis['iterations']}")
    print(f"Tool usages: {dict(analysis['tool_usages'])}")
    print(f"Search strategies: {analysis['search_strategies_detected']}")
    print(f"Information sources: {len(analysis['information_sources'])}")
    
    return analysis


def run_venue_search_test():
    """Test finding venues with pianos in San Francisco."""
    agent = create_test_agent(
        name="VenueSearchAgent",
        description="An agent that specializes in finding venue information based on specific criteria",
        goals=["Find accurate information about venues", "Provide detailed and specific venue information"]
    )
    
    result = execute_search_task(
        agent_id=agent["id"],
        query="Find all the venues in San Francisco with pianos. Focus on places where pianos are available for use or performances.",
        max_iterations=25  # More iterations for this complex task
    )
    
    if "execution_id" in result:
        feed = get_execution_feed(result["execution_id"])
        analysis = analyze_search_process(feed, "venues with pianos")
        
        # Save results
        with open("venue_search_results.json", "w") as f:
            json.dump({
                "query": "Find all the venues in San Francisco with pianos",
                "result": result,
                "analysis": {k: v for k, v in analysis.items() if isinstance(v, (str, int, float, bool, list, dict))}
            }, f, indent=2)
    
    return result


def run_email_search_test():
    """Test finding 20 emails of NYC jazz clubs."""
    agent = create_test_agent(
        name="JazzClubEmailAgent",
        description="An agent that specializes in finding contact information for music venues",
        goals=["Find accurate email addresses", "Compile comprehensive contact lists"]
    )
    
    result = execute_search_task(
        agent_id=agent["id"],
        query="Find me 20 email addresses of jazz clubs in New York City. Make sure they are current and valid addresses.",
        max_iterations=25  # More iterations for this complex task
    )
    
    if "execution_id" in result:
        feed = get_execution_feed(result["execution_id"])
        analysis = analyze_search_process(feed, "jazz club emails")
        
        # Save results
        with open("jazz_club_email_results.json", "w") as f:
            json.dump({
                "query": "Find me 20 email addresses of jazz clubs in New York City",
                "result": result,
                "analysis": {k: v for k, v in analysis.items() if isinstance(v, (str, int, float, bool, list, dict))}
            }, f, indent=2)
    
    return result


def run_restroom_search_test():
    """Test finding the cleanest public restroom in San Francisco with specific constraints."""
    agent = create_test_agent(
        name="RestroomSearchAgent",
        description="An agent that specializes in finding location-based information with specific criteria",
        goals=["Find accurate and current information about public facilities", "Evaluate quality of facilities based on reviews and criteria"]
    )
    
    result = execute_search_task(
        agent_id=agent["id"],
        query="Find me the cleanest public restroom in San Francisco that is not upstairs and that you don't have to purchase anything to use. Include specific locations and cleanliness ratings if available.",
        max_iterations=25  # More iterations for this complex task
    )
    
    if "execution_id" in result:
        feed = get_execution_feed(result["execution_id"])
        analysis = analyze_search_process(feed, "clean public restroom")
        
        # Save results
        with open("restroom_search_results.json", "w") as f:
            json.dump({
                "query": "Find me the cleanest public restroom in San Francisco with specific constraints",
                "result": result,
                "analysis": {k: v for k, v in analysis.items() if isinstance(v, (str, int, float, bool, list, dict))}
            }, f, indent=2)
    
    return result


def main():
    """Run the test suite or a specific test."""
    parser = argparse.ArgumentParser(description="Test complex search tasks")
    parser.add_argument("--test", choices=["venues", "emails", "restrooms", "all"], 
                        default="all", help="Which test to run")
    
    args = parser.parse_args()
    
    try:
        import re  # Import here to avoid global namespace pollution
        
        print("\n===================================================")
        print("  COMPLEX SEARCH TASK TEST SUITE")
        print("===================================================\n")
        
        if args.test == "venues" or args.test == "all":
            print("\n\n========== TEST 1: VENUES WITH PIANOS ==========\n")
            run_venue_search_test()
            
        if args.test == "emails" or args.test == "all":
            print("\n\n========== TEST 2: JAZZ CLUB EMAILS ==========\n")
            run_email_search_test()
            
        if args.test == "restrooms" or args.test == "all":
            print("\n\n========== TEST 3: CLEAN PUBLIC RESTROOMS ==========\n")
            run_restroom_search_test()
            
        print("\n\n===================================================")
        print("  TEST SUITE COMPLETED")
        print("===================================================\n")
        
    except Exception as e:
        print(f"\nError in test execution: {str(e)}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main()