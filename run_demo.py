#!/usr/bin/env python3
"""
Demonstration script for the Multi-Agent Gemini Swarm system.
This script shows how to use the swarm_controller to coordinate
multiple Gemini agents working together on different tasks.
"""

import os
import sys
import time
import logging
import threading
import argparse

from swarm_controller import (
    SwarmController, Task, TaskType, TaskPriority
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("demo")

def format_result(result):
    """Format a result dictionary in a readable way."""
    if isinstance(result, dict):
        return '\n'.join(f"  {k}: {format_result(v)}" for k, v in result.items())
    elif isinstance(result, list):
        return '\n'.join(f"  - {format_result(item)}" for item in result)
    else:
        return str(result)

def execute_task_demo(controller, task_type, data, priority=TaskPriority.LOW, wait=True):
    """Execute a task and optionally wait for the result."""
    logger.info(f"Executing {task_type.value} task with priority {priority.value}")
    
    task = Task(
        task_type=task_type,
        data=data,
        priority=priority
    )
    
    task_id = controller.add_task(task)
    logger.info(f"Task added with ID: {task_id}")
    
    if wait:
        logger.info("Waiting for task to complete...")
        result = controller.wait_for_task(task_id)
        if "error" in result:
            logger.error(f"Task error: {result['error']}")
            return None
        
        logger.info("Task completed successfully")
        return result.get("result")
    
    return task_id

def run_demo():
    """Run a demonstration of the swarm controller capabilities."""
    # Create and start the swarm controller
    controller = SwarmController(worker_count=2)
    controller.start()
    
    try:
        print("\n" + "="*80)
        print("MULTI-AGENT GEMINI SWARM DEMONSTRATION")
        print("="*80 + "\n")
        
        print("Starting demonstration of parallel task processing...\n")
        
        # 1. Low priority prompt task
        print("\n--- LOW PRIORITY PROMPT (Simple Task) ---")
        result = execute_task_demo(
            controller,
            TaskType.PROMPT,
            {"prompt": "Write a short poem about artificial intelligence."},
            TaskPriority.LOW
        )
        if result:
            print("\nResult:")
            print(result.get("response", "No response"))
        
        # 2. High priority prompt task
        print("\n--- HIGH PRIORITY PROMPT (Complex Task) ---")
        result = execute_task_demo(
            controller,
            TaskType.PROMPT,
            {"prompt": "Explain the concept of multi-agent systems in AI and how they can collaborate to solve complex problems. Include specific advantages and potential challenges."},
            TaskPriority.HIGH
        )
        if result:
            print("\nResult:")
            print(result.get("response", "No response"))
        
        # 3. Web search task
        print("\n--- WEB SEARCH TASK ---")
        result = execute_task_demo(
            controller,
            TaskType.WEB_SEARCH,
            {"query": "multi agent AI systems", "max_results": 3}
        )
        if result:
            print("\nSearch Results:")
            for i, item in enumerate(result.get("results", [])):
                print(f"{i+1}. {item.get('title', 'No title')}")
                print(f"   URL: {item.get('url', 'No URL')}")
                print(f"   {item.get('snippet', 'No snippet')}")
                print()
        
        # 4. Execute a system command
        print("\n--- SYSTEM COMMAND EXECUTION ---")
        result = execute_task_demo(
            controller,
            TaskType.EXECUTE,
            {"cmd": "ls -la"}
        )
        if result:
            print("\nCommand Output:")
            print(result.get("stdout", "No output"))
        
        # 5. Parallel tasks with different priorities
        print("\n--- PARALLEL TASK PROCESSING ---")
        print("Starting multiple tasks with different priorities simultaneously...")
        
        # Start tasks without waiting
        task1_id = execute_task_demo(
            controller,
            TaskType.PROMPT,
            {"prompt": "List 5 benefits of distributed computing systems."},
            TaskPriority.LOW,
            wait=False
        )
        
        task2_id = execute_task_demo(
            controller,
            TaskType.PROMPT,
            {"prompt": "Compare and contrast supervised, unsupervised, and reinforcement learning with examples of each."},
            TaskPriority.HIGH,
            wait=False
        )
        
        # Wait for both tasks to complete
        results = []
        for task_id in [task1_id, task2_id]:
            result = controller.wait_for_task(task_id)
            results.append(result)
        
        # Display results
        for i, result in enumerate(results):
            print(f"\nTask {i+1} Result:")
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(result.get("result", {}).get("response", "No response"))
        
        print("\n" + "="*80)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
        
    finally:
        # Stop the controller
        controller.stop()

def main():
    """Main function to parse arguments and run the demo."""
    parser = argparse.ArgumentParser(description="Multi-Agent Gemini Swarm Demo")
    parser.add_argument("--no-demo", action="store_true", help="Skip running the demo")
    args = parser.parse_args()
    
    if not args.no_demo:
        run_demo()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())