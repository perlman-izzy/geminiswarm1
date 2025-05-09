#!/usr/bin/env python3
"""
Script to start all the necessary services for the multi-agent Gemini system.
This ensures all components are running before running tests.
"""
import os
import sys
import time
import logging
import subprocess
import threading
import argparse
import signal
import atexit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("services")

# Global list of processes to terminate at exit
processes = []

def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals."""
    logger.info("Received termination signal. Stopping all services...")
    stop_all_services()
    sys.exit(0)

def stop_all_services():
    """Stop all running services."""
    for process in processes:
        if process and process.poll() is None:  # If process exists and is running
            logger.info(f"Terminating process: {process.pid}")
            try:
                process.terminate()
                try:
                    process.wait(timeout=5)  # Wait for graceful termination
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process {process.pid} did not terminate gracefully. Killing...")
                    process.kill()
            except Exception as e:
                logger.error(f"Error terminating process: {str(e)}")

def run_service(command, name, cwd=None):
    """Run a service command and return the process."""
    logger.info(f"Starting {name}...")
    try:
        # Start the process
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Add to the global list for cleanup
        processes.append(process)
        
        # Create a thread to read and log output
        def log_output(process, name):
            for line in iter(process.stdout.readline, ''):
                logger.info(f"{name}: {line.strip()}")
        
        thread = threading.Thread(target=log_output, args=(process, name), daemon=True)
        thread.start()
        
        return process
    except Exception as e:
        logger.error(f"Error starting {name}: {str(e)}")
        return None

def is_port_in_use(port):
    """Check if a port is in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def wait_for_services(timeout=30):
    """Wait for all services to be available."""
    logger.info("Waiting for services to become available...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        main_proxy_available = is_port_in_use(5000)
        extended_proxy_available = is_port_in_use(3000)
        
        if main_proxy_available and extended_proxy_available:
            logger.info("All services are available!")
            return True
        
        # Check if any process has died
        for i, process in enumerate(processes):
            if process.poll() is not None:  # Process has terminated
                logger.error(f"Process {i} terminated unexpectedly with code {process.poll()}")
                return False
        
        logger.info(f"Waiting for services... Main proxy: {'✅' if main_proxy_available else '❌'}, "
                    f"Extended proxy: {'✅' if extended_proxy_available else '❌'}")
        time.sleep(2)
    
    logger.error(f"Timeout waiting for services after {timeout} seconds")
    return False

def main():
    """Start all the necessary services."""
    parser = argparse.ArgumentParser(description="Start all necessary services for testing")
    parser.add_argument("--timeout", type=int, default=30, 
                        help="Timeout in seconds to wait for services to start")
    parser.add_argument("--test-only", action="store_true",
                        help="Run tests immediately after services start")
    parser.add_argument("--test-script", default="test_escalating_prompts.py",
                        help="Test script to run if --test-only is specified")
    
    args = parser.parse_args()
    
    # Register signal handlers and atexit
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(stop_all_services)
    
    # Start the main proxy server
    main_proxy_process = run_service(
        ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "flask_proxy:app"],
        "Main Proxy"
    )
    
    # Start the extended proxy server
    extended_proxy_process = run_service(
        ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "1", "flask_proxy_extended:app"],
        "Extended Proxy"
    )
    
    # Wait for services to become available
    services_ready = wait_for_services(timeout=args.timeout)
    
    if not services_ready:
        logger.error("Failed to start all services. Exiting.")
        stop_all_services()
        return 1
    
    if args.test_only:
        # Run the test script
        logger.info(f"Running test script: {args.test_script}")
        
        # Split the test_script into command and arguments
        parts = args.test_script.split()
        test_script = parts[0]
        test_args = parts[1:] if len(parts) > 1 else []
        
        test_process = run_service(
            [sys.executable, test_script] + test_args,
            "Test Runner"
        )
        
        # Wait for test to complete
        if test_process:
            test_returncode = test_process.wait()
            logger.info(f"Test completed with return code: {test_returncode}")
            # Stop services and exit with test's return code
            stop_all_services()
            return test_returncode
        else:
            logger.error("Failed to start test process")
            stop_all_services()
            return 1
    else:
        # Keep services running until interrupted
        logger.info("All services started successfully. Press Ctrl+C to stop.")
        try:
            # Keep the main thread alive
            while True:
                # Check if any process has died
                for i, process in enumerate(processes):
                    if process.poll() is not None:
                        logger.error(f"Process {i} terminated unexpectedly with code {process.poll()}")
                        stop_all_services()
                        return 1
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
            stop_all_services()
            return 0

if __name__ == "__main__":
    sys.exit(main())