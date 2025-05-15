"""
Task Manager module for handling task execution and saving results.
"""
import os
import json
import time
import datetime
from typing import Dict, Any, List

from superagi_replit.agent.direct_agent import DirectAgent
from superagi_replit.tools.web_search_tool import WebSearchTool
from superagi_replit.tools.web_scraper_tool import WebScraperTool

# Ensure the results directory exists
RESULTS_DIR = "search_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

def create_agent(name: str, description: str, goals: List[str]) -> DirectAgent:
    """
    Create a direct agent with the specified parameters.
    
    Args:
        name: Name of the agent
        description: Description of the agent
        goals: List of goals
        
    Returns:
        DirectAgent instance
    """
    agent = DirectAgent(
        name=name,
        description=description,
        goals=goals
    )
    
    # Add tools
    agent.add_tool(WebSearchTool())
    agent.add_tool(WebScraperTool())
    
    return agent

def run_task(task_type: str, query: str, max_iterations: int = 10) -> Dict[str, Any]:
    """
    Run a task with the appropriate agent configuration.
    
    Args:
        task_type: Type of task (venue, email, or facility)
        query: The search query
        max_iterations: Maximum iterations to run
        
    Returns:
        Results dictionary
    """
    # Set up agent based on task type
    if task_type == "venue":
        agent = create_agent(
            name="Venue Search Agent",
            description="Finding venues with specific features and amenities",
            goals=["Find accurate venue information", "Provide detailed location data", "Verify amenities availability"]
        )
    elif task_type == "email":
        agent = create_agent(
            name="Email Search Agent",
            description="Finding contact information for organizations",
            goals=["Find accurate email addresses", "Compile comprehensive contact lists", "Verify email validity"]
        )
    elif task_type == "facility":
        agent = create_agent(
            name="Facility Search Agent",
            description="Finding public facilities with specific criteria",
            goals=["Find facilities that meet specific criteria", "Evaluate quality based on reviews", "Provide accurate location information"]
        )
    else:
        agent = create_agent(
            name="General Search Agent",
            description="Finding detailed information on topics",
            goals=["Research thoroughly", "Gather accurate information", "Organize information clearly"]
        )
    
    # Run the agent
    result = agent.run(query, max_iterations=max_iterations)
    
    # Add timestamp and task info
    result["timestamp"] = datetime.datetime.now().isoformat()
    result["task_type"] = task_type
    result["query"] = query
    
    # Save the results
    save_path = save_results(result)
    result["saved_to"] = save_path
    
    return result

def save_results(result: Dict[str, Any]) -> str:
    """
    Save results to a file.
    
    Args:
        result: Results dictionary
        
    Returns:
        Path to the saved file
    """
    # Create a unique filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    task_type = result.get("task_type", "general")
    filename = f"{task_type}_{timestamp}.json"
    filepath = os.path.join(RESULTS_DIR, filename)
    
    # Also save a text version
    text_filename = f"{task_type}_{timestamp}.txt"
    text_filepath = os.path.join(RESULTS_DIR, text_filename)
    
    # Create a serializable version of the result
    serializable_result = {
        "task_type": result.get("task_type", "unknown"),
        "query": result.get("task", ""),
        "goals": result.get("goals", []),
        "completed": result.get("completed", False),
        "reason": result.get("reason", ""),
        "confidence": result.get("confidence", 0),
        "iterations": result.get("iterations", 0),
        "max_iterations": result.get("max_iterations", 0),
        "execution_time": result.get("execution_time", 0),
        "tool_uses": {str(k): v for k, v in result.get("tool_uses", {}).items()},
        "timestamp": result.get("timestamp", ""),
        "responses": result.get("responses", []),
        "final_response": result.get("final_response", "")
    }
    
    # Save JSON
    with open(filepath, "w") as f:
        json.dump(serializable_result, f, indent=2)
    
    # Save text version
    with open(text_filepath, "w") as f:
        f.write(f"SEARCH RESULTS: {result.get('task_type', 'general').upper()} SEARCH\n")
        f.write(f"Query: {result.get('task', '')}\n")
        f.write(f"Completed: {result.get('completed', False)}\n")
        f.write(f"Reason: {result.get('reason', '')}\n")
        f.write(f"Confidence: {result.get('confidence', 0)}\n")
        f.write(f"Iterations: {result.get('iterations', 0)}/{result.get('max_iterations', 0)}\n")
        f.write(f"Execution Time: {result.get('execution_time', 0):.2f} seconds\n\n")
        f.write("FINAL RESPONSE:\n")
        f.write(result.get("final_response", ""))
    
    return text_filepath

def list_saved_results() -> List[Dict[str, Any]]:
    """
    List all saved results.
    
    Returns:
        List of result summaries
    """
    results = []
    
    # Get all JSON files in results directory
    json_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.json')]
    
    for file in json_files:
        filepath = os.path.join(RESULTS_DIR, file)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            # Create a summary
            summary = {
                "filename": file,
                "task_type": data.get("task_type", "unknown"),
                "query": data.get("query", ""),
                "completed": data.get("completed", False),
                "timestamp": data.get("timestamp", ""),
                "iterations": data.get("iterations", 0),
                "text_file": file.replace(".json", ".txt")
            }
            results.append(summary)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    # Sort by timestamp (newest first)
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return results

def get_result_content(filename: str) -> Dict[str, Any]:
    """
    Get the content of a specific result file.
    
    Args:
        filename: Name of the result file
        
    Returns:
        Result dictionary
    """
    filepath = os.path.join(RESULTS_DIR, filename)
    
    if not os.path.exists(filepath):
        return {"error": "File not found"}
    
    try:
        with open(filepath, 'r') as f:
            if filepath.endswith('.json'):
                return json.load(f)
            else:
                return {"content": f.read()}
    except Exception as e:
        return {"error": f"Error loading file: {str(e)}"}