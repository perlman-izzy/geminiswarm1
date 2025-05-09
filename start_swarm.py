#!/usr/bin/env python3
"""
Startup script for the Multi-Agent Gemini AI Swarm system.
This script starts both proxy servers and provides a simple CLI.
"""
import os
import sys
import time
import signal
import logging
import argparse
import subprocess
import threading
import json
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("swarm_startup")

# Global processes
processes = []

def signal_handler(sig, frame):
    """Handle interruption signals gracefully."""
    logger.info("Shutting down all services...")
    for proc in processes:
        if proc and proc.poll() is None:
            proc.terminate()
    sys.exit(0)

def start_dual_proxies():
    """Start both proxy servers using the dual proxies script."""
    logger.info("Starting dual proxy servers...")
    
    try:
        process = subprocess.Popen(
            ["python", "run_proxies.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        processes.append(process)
        
        # Create a thread to read and log output
        def reader():
            if process.stdout is not None:
                for line in iter(process.stdout.readline, ''):
                    logger.info(f"PROXIES: {line.strip()}")
        
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        
        # Give the servers time to start
        time.sleep(2)
        
        logger.info("Proxy servers started successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to start proxy servers: {str(e)}")
        return False

def run_demo():
    """Run the demo script."""
    logger.info("Running multi-agent swarm demo...")
    try:
        result = subprocess.run(
            ["python", "run_demo.py"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            logger.error(f"Demo returned error: {result.stderr}")
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to run demo: {str(e)}")
        return False

def run_swarm_command(args):
    """Run a swarm controller command."""
    from swarm_controller import SwarmController, TaskType, TaskPriority
    
    try:
        controller = SwarmController()
        controller.start()
        
        if args.type == "prompt":
            # Handle simple prompt
            task_id = controller.add_prompt_task(
                args.input,
                priority=TaskPriority.HIGH if args.complex else TaskPriority.LOW
            )
        elif args.type == "web_search":
            # Handle web search
            task_id = controller.add_web_search_task(
                args.input,
                max_results=args.max_results
            )
        elif args.type == "code_fix":
            # Handle code fixing
            task_id = controller.add_code_fix_task(
                args.input,
                args.test_command or "python -m unittest"
            )
        else:
            logger.error(f"Unknown task type: {args.type}")
            return False
        
        logger.info(f"Submitted task: {task_id}")
        result = controller.wait_for_task(task_id)
        
        if result.get("success", False):
            print("\nRESULT:")
            print(result.get("result", "No result"))
            return True
        else:
            logger.error(f"Task failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"Failed to run swarm command: {str(e)}")
        return False
    finally:
        if 'controller' in locals():
            controller.stop()

def process_command(command_line):
    """Process a command from the user."""
    parts = command_line.strip().split(maxsplit=1)
    command = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    
    if command == "help":
        print("\nAvailable commands:")
        print("  help           - Show this help message")
        print("  demo           - Run the swarm controller demo")
        print("  test [name]    - Run tests (all or specific test)")
        print("  ask [prompt]   - Ask a question to Gemini")
        print("  search [query] - Perform a web search")
        print("  fix [file]     - Fix code in a file")
        print("  stats          - Show API key usage statistics")
        print("  exit/quit      - Exit the program")
        return True
    
    elif command == "demo":
        return run_demo()
    
    elif command == "test":
        test_name = args if args else None
        cmd = ["python", "escalation_test.py"]
        if test_name:
            cmd.extend(["--test", test_name])
        
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode == 0
    
    elif command == "ask":
        if not args:
            print("Please provide a prompt")
            return False
        
        parser = argparse.ArgumentParser()
        parser.add_argument("prompt", type=str, help="The prompt to send")
        parser.add_argument("--complex", "-c", action="store_true", 
                            help="Use more powerful model for complex tasks")
        
        try:
            cmd_args = parser.parse_args(["prompt", "--complex"] if args and "--complex" in args else ["prompt"])
            cmd_args.type = "prompt"
            cmd_args.input = args.replace("--complex", "").strip()
            cmd_args.max_results = 5
            cmd_args.test_command = None
            return run_swarm_command(cmd_args)
        except Exception as e:
            logger.error(f"Failed to parse args: {str(e)}")
            return False
    
    elif command == "search":
        if not args:
            print("Please provide a search query")
            return False
        
        parser = argparse.ArgumentParser()
        parser.add_argument("query", type=str, help="The search query")
        parser.add_argument("--max", "-m", type=int, default=5,
                            help="Maximum number of results")
        
        try:
            cmd_args = parser.parse_args(["query"])
            cmd_args.type = "web_search"
            cmd_args.input = args
            cmd_args.complex = False
            cmd_args.max_results = 5
            cmd_args.test_command = None
            return run_swarm_command(cmd_args)
        except Exception as e:
            logger.error(f"Failed to parse args: {str(e)}")
            return False
    
    elif command == "fix":
        if not args:
            print("Please provide a file to fix")
            return False
        
        parser = argparse.ArgumentParser()
        parser.add_argument("file", type=str, help="The file to fix")
        parser.add_argument("--test", "-t", type=str,
                            help="Test command to verify fix")
        
        try:
            cmd_args = parser.parse_args(["file"])
            cmd_args.type = "code_fix"
            cmd_args.input = args
            cmd_args.complex = True
            cmd_args.max_results = 0
            cmd_args.test_command = "python -m unittest"
            return run_swarm_command(cmd_args)
        except Exception as e:
            logger.error(f"Failed to parse args: {str(e)}")
            return False
    
    elif command == "stats":
        try:
            response = requests.get("http://localhost:5000/stats")
            data = response.json()
            print("\nAPI Key Usage Statistics:")
            for key, count in data.items():
                print(f"  Key ending in ...{key[-4:]}: {count} requests")
            return True
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return False
    
    elif command in ["exit", "quit"]:
        return "exit"
    
    else:
        print(f"Unknown command: {command}")
        print("Type 'help' for available commands")
        return False

def main():
    """Main function to start the swarm and handle user commands."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Start the Multi-Agent Gemini AI Swarm")
    parser.add_argument("--no-proxies", action="store_true", 
                        help="Don't start proxy servers (assume they're already running)")
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start proxy servers if needed
    if not args.no_proxies:
        if not start_dual_proxies():
            logger.error("Failed to start proxy servers. Exiting...")
            return 1
    
    # Welcome message
    print("\n" + "="*80)
    print(" Multi-Agent Gemini AI Swarm System ".center(80, "="))
    print("="*80)
    print("\nType 'help' for available commands, or 'exit' to quit\n")
    
    # Main command loop
    try:
        while True:
            try:
                command = input("> ")
                result = process_command(command)
                
                if result == "exit":
                    break
                
                print()  # Empty line for readability
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                logger.error(f"Error processing command: {str(e)}")
    finally:
        # Clean up
        logger.info("Shutting down...")
        for proc in processes:
            if proc and proc.poll() is None:
                proc.terminate()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())