#!/usr/bin/env python3
"""
Test script for the multi-agent Gemini system with escalating complexity prompts.
This script will execute a series of prompts with increasing complexity to verify
that the system can handle tasks of various difficulties and delegate them appropriately.
"""

import os
import sys
import time
import json
import logging
import argparse
from typing import Dict, Any, List, Optional

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
logger = logging.getLogger("escalation_test")

# Define test prompts in increasing complexity order
TEST_PROMPTS = [
    {
        "name": "simple_weather",
        "prompt": "What's the weather like today?",
        "priority": TaskPriority.LOW,
        "description": "Basic question about today's weather - tests simple factual lookup"
    },
    {
        "name": "capital_cities",
        "prompt": "List the capital cities of 5 European countries and their populations.",
        "priority": TaskPriority.LOW,
        "description": "Medium complexity factual query - tests knowledge retrieval"
    },
    {
        "name": "explain_concept",
        "prompt": "Explain how quantum computing works in simple terms.",
        "priority": TaskPriority.HIGH,
        "description": "Concept explanation - tests ability to simplify complex topics"
    },
    {
        "name": "creative_writing",
        "prompt": "Write a short poem about artificial intelligence in the style of Shakespeare.",
        "priority": TaskPriority.HIGH,
        "description": "Creative task - tests language generation and stylistic mimicry"
    },
    {
        "name": "market_analysis",
        "prompt": "Analyze the current trends in renewable energy markets and predict future developments.",
        "priority": TaskPriority.HIGH,
        "description": "Analysis task - tests complex reasoning and synthesis of information"
    },
    {
        "name": "coding_task",
        "prompt": "Write a Python function that implements the Fibonacci sequence using recursion with memoization.",
        "priority": TaskPriority.HIGH,
        "description": "Coding task - tests ability to generate functional code"
    },
    {
        "name": "multi_step_search",
        "prompt": "Find popular music venues in San Francisco that have a piano. For the top 3 results, provide their address, rating, and a brief description.",
        "priority": TaskPriority.HIGH,
        "description": "Complex search - tests web search, filtering, and result synthesis"
    },
    {
        "name": "package_install",
        "prompt": "I need to analyze the sentiment of customer reviews. First install the necessary library (like NLTK or TextBlob), then write code to perform sentiment analysis on the following reviews: 'The service was excellent!', 'I would never come back to this place.', 'Average experience, nothing special.'",
        "priority": TaskPriority.HIGH,
        "description": "Resource acquisition + task - tests package installation and use"
    }
]


def execute_task(controller: SwarmController, prompt_data: Dict[str, Any], verbose: bool = True) -> Dict[str, Any]:
    """Execute a single task and wait for its completion."""
    prompt = prompt_data["prompt"]
    priority = prompt_data["priority"]
    name = prompt_data["name"]
    
    print("\n" + "="*80)
    print(f"EXECUTING TEST: {name}")
    print(f"PRIORITY: {priority.value}")
    print(f"DESCRIPTION: {prompt_data.get('description', 'No description')}")
    print("-"*80)
    print(f"PROMPT: {prompt}")
    print("="*80 + "\n")
    
    # Create and add task
    task = Task(
        task_type=TaskType.PROMPT,
        data={
            "prompt": prompt,
            "verbose": verbose
        },
        priority=priority
    )
    
    task_id = controller.add_task(task)
    logger.info(f"Added task with ID: {task_id}")
    
    # Wait for completion
    start_time = time.time()
    result = controller.wait_for_task(task_id)
    elapsed_time = time.time() - start_time
    
    # Process and display result
    success = "error" not in result
    
    print("\n" + "-"*80)
    print(f"TASK COMPLETED: {'SUCCESS' if success else 'FAILED'}")
    print(f"ELAPSED TIME: {elapsed_time:.2f} seconds")
    
    if success:
        response = result.get("result", {}).get("response", "")
        model_used = result.get("result", {}).get("model_used", "unknown")
        print(f"MODEL USED: {model_used}")
        print("-"*80)
        print("RESPONSE:")
        print(response)
    else:
        print(f"ERROR: {result.get('error', 'Unknown error')}")
    
    print("-"*80 + "\n")
    
    return {
        "name": name,
        "success": success,
        "elapsed_time": elapsed_time,
        "result": result
    }


def run_test_suite(controller: SwarmController, prompts: List[Dict[str, Any]], verbose: bool = True) -> List[Dict[str, Any]]:
    """Run the full test suite of prompts."""
    results = []
    
    for i, prompt_data in enumerate(prompts):
        print(f"\nRUNNING TEST {i+1}/{len(prompts)}")
        
        try:
            result = execute_task(controller, prompt_data, verbose)
            results.append(result)
            
            # Short pause between tests to avoid rate limiting
            if i < len(prompts) - 1:
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\nTest interrupted by user. Exiting.")
            break
        except Exception as e:
            logger.error(f"Error running test {prompt_data['name']}: {str(e)}", exc_info=True)
            results.append({
                "name": prompt_data["name"],
                "success": False,
                "error": str(e)
            })
    
    return results


def summarize_results(results: List[Dict[str, Any]]) -> None:
    """Print a summary of test results."""
    success_count = sum(1 for r in results if r.get("success", False))
    total_count = len(results)
    
    print("\n" + "="*80)
    print(f"TEST SUMMARY: {success_count}/{total_count} tests passed")
    print("="*80)
    
    for result in results:
        name = result.get("name", "unknown")
        success = result.get("success", False)
        elapsed = result.get("elapsed_time", 0)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {name} ({elapsed:.2f}s)")
    
    print("="*80 + "\n")


def main():
    """Main function to run the escalating test suite."""
    parser = argparse.ArgumentParser(description="Test the Gemini swarm with escalating complexity prompts")
    parser.add_argument("--main-proxy", default="http://localhost:5000/gemini", 
                        help="URL of the main Gemini proxy")
    parser.add_argument("--extended-proxy", default="http://localhost:3000/gemini", 
                        help="URL of the extended Gemini proxy")
    parser.add_argument("--workers", type=int, default=2, 
                        help="Number of worker threads")
    parser.add_argument("--verbose", action="store_true", default=True,
                        help="Enable verbose logging")
    parser.add_argument("--test", type=str, default=None,
                        help="Run a specific test by name")
    
    args = parser.parse_args()
    
    # Create and start the controller
    controller = SwarmController(
        main_proxy_url=args.main_proxy,
        extended_proxy_url=args.extended_proxy,
        worker_count=args.workers
    )
    controller.start()
    
    try:
        if args.test:
            # Run a single test if specified
            matching_tests = [t for t in TEST_PROMPTS if t["name"] == args.test]
            if matching_tests:
                results = run_test_suite(controller, matching_tests, args.verbose)
            else:
                logger.error(f"No test named '{args.test}' found.")
                print(f"Available tests: {', '.join(t['name'] for t in TEST_PROMPTS)}")
                return 1
        else:
            # Run all tests
            results = run_test_suite(controller, TEST_PROMPTS, args.verbose)
        
        # Summarize results
        summarize_results(results)
        
    finally:
        # Always stop the controller
        controller.stop()
    
    # Return 0 if all tests passed, 1 otherwise
    return 0 if all(r.get("success", False) for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())