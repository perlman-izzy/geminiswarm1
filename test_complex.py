#!/usr/bin/env python3
"""
Complex test script for the Gemini swarm system using the SwarmController
"""
import sys
import time
import logging
from typing import Dict, Any

# Import our swarm components
from swarm_controller import (
    SwarmController, 
    Task, 
    TaskType, 
    TaskPriority
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("complex_test")

def test_prompt(controller: SwarmController, prompt: str, priority: TaskPriority, verbose: bool = True) -> Dict[str, Any]:
    """Test a prompt with the SwarmController."""
    print(f"\nTesting prompt with {priority.value} priority: '{prompt[:100]}...'")
    
    # Create task
    task = Task(
        task_type=TaskType.PROMPT,
        data={
            "prompt": prompt,
            "verbose": verbose
        },
        priority=priority
    )
    
    # Add task and wait for completion
    task_id = controller.add_task(task)
    start_time = time.time()
    result = controller.wait_for_task(task_id)
    elapsed_time = time.time() - start_time
    
    # Process result
    success = "error" not in result
    
    print(f"Task completed: {'SUCCESS' if success else 'FAILED'}")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    
    if success:
        response = result.get("result", {}).get("response", "")
        model_used = result.get("result", {}).get("model_used", "unknown")
        print(f"Model used: {model_used}")
        print("\nResponse:")
        print(response)
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    return result

def test_complex_tasks():
    """Run tests for increasingly complex tasks to verify intelligent delegation."""
    # Create SwarmController
    controller = SwarmController()
    controller.start()
    
    try:
        # Simple task - should use the small model
        test_prompt(
            controller,
            "List 5 common fruits and their typical colors.",
            TaskPriority.LOW
        )
        
        # More complex task - should use the large model
        test_prompt(
            controller,
            "Find all music venues in San Francisco that have a piano. For the top 3 results, provide their address, rating, and a brief description.",
            TaskPriority.HIGH
        )
        
        # Test package installation requirement - complex reasoning
        test_prompt(
            controller,
            "I need to analyze the sentiment of customer reviews. First explain how to install the necessary library (like NLTK or TextBlob), then write code to perform sentiment analysis on the following reviews: 'The service was excellent!', 'I would never come back to this place.', 'Average experience, nothing special.'",
            TaskPriority.HIGH
        )
        
    finally:
        # Always stop the controller
        controller.stop()
    
def main():
    """Run the complex tests."""
    test_complex_tasks()
    return 0

if __name__ == "__main__":
    sys.exit(main())