"""
Test script for demonstrating task completion with the agent.

This script uses a Mock LLM to simulate responses and tests the task validator
on three complex search tasks.
"""
import json
import time
from typing import Dict, Any, List, Tuple
import sys
import re
import os

from superagi_replit.agent.non_llm_task_validator import NonLLMTaskValidator
from superagi_replit.agent.mock_llm import MockLLM


class TaskCompletionTest:
    """Class for testing task completion."""
    
    def __init__(self):
        """Initialize the task completion test."""
        self.mock_llm = MockLLM()
        self.validator = NonLLMTaskValidator()
        self.responses = []
        self.tool_uses = {}
        
    def reset(self):
        """Reset the test state."""
        self.validator = NonLLMTaskValidator()
        self.responses = []
        self.tool_uses = {}
        
    def simulate_agent_interaction(self, task_description: str, max_iterations: int = 15) -> Dict[str, Any]:
        """
        Simulate an agent interaction and test task completion.
        
        Args:
            task_description: The task to complete
            max_iterations: Maximum number of iterations
            
        Returns:
            Result dictionary with task status and metrics
        """
        self.reset()
        
        print(f"\n{'=' * 60}")
        print(f"TASK: {task_description}")
        print(f"{'=' * 60}")
        
        iteration = 0
        start_time = time.time()
        final_response = ""
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\nIteration {iteration}/{max_iterations}")
            
            # Generate a response using the mock LLM
            if iteration == 1:
                prompt = task_description
            else:
                # In a real agent, previous responses would influence the next prompt
                prompt = f"{task_description}\n\nConsider what you've found so far and continue the search."
                
            response = self.mock_llm.generate(prompt)
            self.responses.append(response)
            
            # Extract and track tool usage
            tool_usage = self._extract_tool_usage(response)
            if tool_usage:
                tool_name, tool_args = tool_usage
                self.tool_uses[tool_name] = self.tool_uses.get(tool_name, 0) + 1
                self.validator.update_metrics(response, tool_name, tool_args)
            else:
                self.validator.update_metrics(response)
            
            # Print a summary of the response (trimmed)
            response_preview = response.strip()[:200] + "..." if len(response) > 200 else response.strip()
            print(f"Response: {response_preview}")
            
            # Check if task is complete
            is_complete, reason, confidence = self.validator.is_task_complete(task_description)
            print(f"Task status: Complete: {is_complete}, Reason: {reason}, Confidence: {confidence:.2f}")
            
            if is_complete:
                print(f"\nTask completed after {iteration} iterations!")
                final_response = response
                break
            
            # Small delay to simulate real-time interaction
            time.sleep(0.2)
            
        end_time = time.time()
        execution_time = end_time - start_time
        
        # If we didn't complete within the iterations, use the last response
        if not final_response:
            final_response = response
            
        # Get the status report
        status_report = self.validator.get_status_report()
        
        result = {
            "task": task_description,
            "completed": is_complete,
            "reason": reason,
            "confidence": confidence,
            "iterations": iteration,
            "execution_time": execution_time,
            "status_report": status_report,
            "final_response": final_response
        }
        
        # Print summary
        print(f"\n{'=' * 60}")
        print(f"TASK SUMMARY")
        print(f"{'=' * 60}")
        print(f"Task: {task_description}")
        print(f"Completed: {is_complete}")
        print(f"Reason: {reason}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Iterations: {iteration}/{max_iterations}")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Tool usages: {json.dumps(self.tool_uses, indent=2)}")
        print(f"Status report: {json.dumps(status_report, indent=2, default=str)}")
        
        return result
    
    def _extract_tool_usage(self, response: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract tool usage from a response.
        
        Args:
            response: Response string
            
        Returns:
            Tuple of (tool_name, tool_args) or (None, None) if no tool usage found
        """
        tool_pattern = r'```\s*{\s*"tool":\s*"([^"]+)",\s*"tool_input":\s*({[^}]+})'
        match = re.search(tool_pattern, response, re.DOTALL)
        
        if match:
            tool_name = match.group(1)
            tool_input_str = match.group(2)
            
            # Clean up the JSON string (this is simplified)
            # In real parsing, use a proper JSON parser with error handling
            tool_input_str = tool_input_str.replace("'", '"')
            try:
                tool_args = json.loads(tool_input_str)
                return tool_name, tool_args
            except json.JSONDecodeError:
                pass
                
        return None, None


def test_venue_search():
    """Test the venue search task."""
    tester = TaskCompletionTest()
    task = "Find all the venues in San Francisco with pianos. Focus on places where pianos are available for use or performances."
    return tester.simulate_agent_interaction(task)


def test_email_search():
    """Test the email search task."""
    tester = TaskCompletionTest()
    task = "Find me 20 email addresses of jazz clubs in New York City. Make sure they are current and valid addresses."
    return tester.simulate_agent_interaction(task)


def test_restroom_search():
    """Test the clean restroom search task."""
    tester = TaskCompletionTest()
    task = "Find me the cleanest public restroom in San Francisco that is not upstairs and that you don't have to purchase anything to use. Include specific locations and cleanliness ratings if available."
    return tester.simulate_agent_interaction(task)


def save_result(result: Dict[str, Any], filename: str = None):
    """
    Save a test result to a file.
    
    Args:
        result: Result dictionary
        filename: Optional filename (will be generated if not provided)
    """
    if not filename:
        task_prefix = result["task"][:20].replace(" ", "_").lower()
        filename = f"{task_prefix}_result.json"
    
    # Ensure the test_results directory exists
    os.makedirs("test_results", exist_ok=True)
    filepath = os.path.join("test_results", filename)
    
    # Save serializable version of the result
    serializable_result = {
        "task": result["task"],
        "completed": result["completed"],
        "reason": result["reason"],
        "confidence": result["confidence"],
        "iterations": result["iterations"],
        "execution_time": result["execution_time"],
        "tool_usages": str(result["status_report"]["tool_usages"]),
        "info_patterns": str(result["status_report"]["information_patterns"]),
        "final_response_preview": result["final_response"][:500] + "..."
    }
    
    with open(filepath, "w") as f:
        json.dump(serializable_result, f, indent=2)
    
    print(f"Result saved to {filepath}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("TASK COMPLETION TESTING")
    print("=" * 80)
    
    if len(sys.argv) > 1:
        test_num = int(sys.argv[1])
        if test_num == 1:
            print("\nRUNNING VENUE SEARCH TEST")
            result = test_venue_search()
            save_result(result, "venue_search_result.json")
        elif test_num == 2:
            print("\nRUNNING EMAIL SEARCH TEST")
            result = test_email_search()
            save_result(result, "email_search_result.json")
        elif test_num == 3:
            print("\nRUNNING RESTROOM SEARCH TEST")
            result = test_restroom_search()
            save_result(result, "restroom_search_result.json")
        else:
            print(f"Invalid test number: {test_num}")
    else:
        # Run all tests
        print("\nRUNNING VENUE SEARCH TEST")
        venue_result = test_venue_search()
        save_result(venue_result, "venue_search_result.json")
        
        print("\nRUNNING EMAIL SEARCH TEST")
        email_result = test_email_search()
        save_result(email_result, "email_search_result.json")
        
        print("\nRUNNING RESTROOM SEARCH TEST")
        restroom_result = test_restroom_search()
        save_result(restroom_result, "restroom_search_result.json")
    
    print("\nAll tests completed!")


if __name__ == "__main__":
    main()