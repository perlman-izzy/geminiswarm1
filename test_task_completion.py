"""
Test script for the task completion system.

This script helps test the task completion detection system by simulating
agent responses and checking if the system correctly identifies when a task
is complete.
"""
import json
import requests
import sys
import time
from typing import Dict, Any, List, Optional

# Configuration
API_BASE_URL = "http://localhost:5000"


def create_agent(name: str, description: str, goals: List[str]) -> Dict[str, Any]:
    """Create a new agent via the API."""
    print(f"Creating agent: {name}")
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


def execute_agent(agent_id: int, user_input: str, max_iterations: int = 10) -> Dict[str, Any]:
    """Execute an agent with a user query."""
    print(f"Executing agent {agent_id} with query: {user_input}")
    response = requests.post(
        f"{API_BASE_URL}/agent-execution",
        json={
            "agent_id": agent_id,
            "user_input": user_input,
            "max_iterations": max_iterations
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to execute agent: {response.text}")
    
    execution_data = response.json()
    print(f"Execution completed with ID: {execution_data['execution_id']}")
    return execution_data


def get_execution_feed(execution_id: int) -> List[Dict[str, Any]]:
    """Get the feed for an execution."""
    print(f"Getting feed for execution {execution_id}")
    response = requests.get(f"{API_BASE_URL}/agent-execution/{execution_id}/feed")
    
    if response.status_code != 200:
        raise Exception(f"Failed to get execution feed: {response.text}")
    
    feed_data = response.json()
    print(f"Retrieved {len(feed_data)} feed items")
    return feed_data


def test_simple_task():
    """Test a simple task that should complete quickly."""
    agent = create_agent(
        name="SimpleTaskAgent",
        description="An agent that performs simple tasks",
        goals=["Answer simple questions accurately"]
    )
    
    result = execute_agent(
        agent_id=agent["id"],
        user_input="What is the capital of France?",
        max_iterations=5
    )
    
    print("\nAgent Response:")
    print("=" * 50)
    print(result["response"])
    print("=" * 50)
    
    feed = get_execution_feed(result["execution_id"])
    return result, feed


def test_complex_task():
    """Test a more complex task that requires multiple iterations."""
    agent = create_agent(
        name="ResearchAgent",
        description="An agent that performs web research",
        goals=["Find detailed information on topics", "Provide comprehensive answers"]
    )
    
    result = execute_agent(
        agent_id=agent["id"],
        user_input="Find the latest developments in renewable energy technologies",
        max_iterations=15
    )
    
    print("\nAgent Response:")
    print("=" * 50)
    print(result["response"])
    print("=" * 50)
    
    feed = get_execution_feed(result["execution_id"])
    return result, feed


def count_tool_usages(feed: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count how many times each tool was used in the feed."""
    tool_counts = {}
    
    for item in feed:
        content = item.get("feed", "")
        if "tool" in content.lower():
            # Extract tool name - this is a simplistic approach, might need improvement
            if '"tool":' in content:
                try:
                    # Try to parse JSON if it's in that format
                    json_part = content.split('```')[1].strip() if '```' in content else content
                    if json_part.startswith('json'):
                        json_part = json_part[4:].strip()
                    data = json.loads(json_part)
                    tool_name = data.get("tool")
                    if tool_name:
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
                except (IndexError, json.JSONDecodeError):
                    pass
    
    return tool_counts


def analyze_feed(feed: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the execution feed for insights."""
    analysis = {
        "total_messages": len(feed),
        "user_messages": sum(1 for item in feed if item.get("role") == "user"),
        "assistant_messages": sum(1 for item in feed if item.get("role") == "assistant"),
        "system_messages": sum(1 for item in feed if item.get("role") == "system"),
        "tool_usages": count_tool_usages(feed),
        "completion_indicators": []
    }
    
    # Look for completion indicators
    completion_patterns = ["task complete", "goal achieved", "completed the task"]
    for item in feed:
        if item.get("role") == "assistant":
            content = item.get("feed", "").lower()
            for pattern in completion_patterns:
                if pattern in content:
                    analysis["completion_indicators"].append({
                        "message_id": item.get("id"),
                        "indicator": pattern
                    })
    
    return analysis


def main():
    """Run the main test script."""
    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        print("Running simple task test...")
        result, feed = test_simple_task()
    else:
        print("Running complex task test...")
        result, feed = test_complex_task()
    
    analysis = analyze_feed(feed)
    
    print("\nExecution Analysis:")
    print("=" * 50)
    print(f"Total messages: {analysis['total_messages']}")
    print(f"User messages: {analysis['user_messages']}")
    print(f"Assistant messages: {analysis['assistant_messages']}")
    print(f"System messages: {analysis['system_messages']}")
    print("\nTool usages:")
    for tool, count in analysis["tool_usages"].items():
        print(f"  - {tool}: {count}")
    print("\nCompletion indicators:")
    for indicator in analysis["completion_indicators"]:
        print(f"  - '{indicator['indicator']}' found in message {indicator['message_id']}")
    print("=" * 50)


if __name__ == "__main__":
    main()