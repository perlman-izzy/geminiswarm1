#!/usr/bin/env python3
"""
Startup script for the Multi-Agent Gemini AI Swarm system.
This script starts both proxy servers and provides a simple CLI.
"""

import os
import sys
import time
import argparse
import subprocess
import threading
import logging
import signal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("swarm_startup")

# Control flags
running = True
processes = []

def signal_handler(sig, frame):
    """Handle interruption signals gracefully."""
    global running
    logger.info("Shutdown signal received, cleaning up...")
    running = False
    # Kill all child processes
    for proc in processes:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
    sys.exit(0)

def start_dual_proxies():
    """Start both proxy servers using the dual proxies script."""
    script_path = os.path.join("workflows", "start_dual_proxies.py")
    
    if not os.path.exists(script_path):
        logger.error(f"Could not find {script_path}")
        return None
    
    try:
        logger.info("Starting dual proxy servers...")
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        processes.append(process)
        
        # Start a thread to read and display the output
        def reader():
            for line in process.stdout:
                if running:
                    print(line, end='')
                else:
                    break
        
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        
        # Wait a moment for servers to start
        time.sleep(3)
        return process
    except Exception as e:
        logger.exception(f"Error starting proxy servers: {e}")
        return None

def run_demo():
    """Run the demo script."""
    try:
        logger.info("Running demonstration...")
        demo_process = subprocess.Popen(
            [sys.executable, "run_demo.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        processes.append(demo_process)
        
        # Display output in real-time
        for line in demo_process.stdout:
            if running:
                print(line, end='')
            else:
                break
        
        return_code = demo_process.wait()
        if return_code != 0:
            logger.warning(f"Demo exited with code {return_code}")
        else:
            logger.info("Demo completed successfully")
    except Exception as e:
        logger.exception(f"Error running demo: {e}")

def run_swarm_command(args):
    """Run a swarm controller command."""
    try:
        cmd = [sys.executable, "swarm_controller.py"] + args
        logger.info(f"Running command: {' '.join(cmd)}")
        
        swarm_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        processes.append(swarm_process)
        
        # Display output in real-time
        for line in swarm_process.stdout:
            if running:
                print(line, end='')
            else:
                break
        
        return_code = swarm_process.wait()
        if return_code != 0:
            logger.warning(f"Command exited with code {return_code}")
        else:
            logger.info("Command completed successfully")
    except Exception as e:
        logger.exception(f"Error running command: {e}")

def process_command(command_line):
    """Process a command from the user."""
    if not command_line.strip():
        return
    
    args = command_line.strip().split()
    command = args[0].lower()
    
    if command == "exit" or command == "quit":
        logger.info("Exiting...")
        return False
    elif command == "help":
        print("\nAvailable commands:")
        print("  demo              - Run the demo script")
        print("  prompt <text>     - Send a prompt to Gemini")
        print("  fix <file> <cmd>  - Fix a file using the test command")
        print("  search <query>    - Search the web")
        print("  help              - Show this help message")
        print("  exit              - Exit the program")
    elif command == "demo":
        run_demo()
    elif command == "prompt":
        if len(args) < 2:
            print("Usage: prompt <text> [--priority high/low]")
        else:
            # Extract prompt and any additional arguments
            prompt_text = " ".join(args[1:])
            
            # Check for priority flag
            priority = "--priority low"
            if "--priority" in prompt_text:
                parts = prompt_text.split("--priority")
                prompt_text = parts[0].strip()
                priority_value = parts[1].strip()
                priority = f"--priority {priority_value}"
            
            run_swarm_command(["prompt", prompt_text, priority])
    elif command == "fix":
        if len(args) < 3:
            print("Usage: fix <file> <test_command>")
        else:
            file_path = args[1]
            test_cmd = " ".join(args[2:])
            run_swarm_command(["fix", file_path, test_cmd])
    elif command == "search":
        if len(args) < 2:
            print("Usage: search <query>")
        else:
            query = " ".join(args[1:])
            run_swarm_command(["search", query])
    else:
        print(f"Unknown command: {command}")
        print("Type 'help' for a list of commands")
    
    return True

def main():
    """Main function to start the swarm and handle user commands."""
    parser = argparse.ArgumentParser(description="Multi-Agent Gemini AI Swarm")
    parser.add_argument("--demo", action="store_true", help="Run the demo after starting")
    args = parser.parse_args()
    
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the proxy servers
    proxy_process = start_dual_proxies()
    if not proxy_process:
        logger.error("Failed to start proxy servers. Exiting.")
        return 1
    
    # Run the demo if requested
    if args.demo:
        run_demo()
    
    # Interactive command loop
    print("\nMulti-Agent Gemini AI Swarm")
    print("Type 'help' for a list of commands")
    
    try:
        while running:
            command = input("\nswarm> ")
            should_continue = process_command(command)
            if should_continue is False:
                break
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down...")
    finally:
        # Clean up
        for proc in processes:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except:
                    proc.kill()
    
    logger.info("Shutdown complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())