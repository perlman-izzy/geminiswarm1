#!/usr/bin/env python3
"""
Script to start both the main application and extended proxy servers simultaneously.
"""
import os
import sys
import time
import signal
import logging
import threading
import subprocess
from config import LOG_DIR, DEFAULT_PORT, EXTENDED_PORT

# Configure logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "start_both_servers.log"))
    ]
)
logger = logging.getLogger("start_both_servers")

# Global process variables
main_process = None
extended_process = None

def signal_handler(sig, frame):
    """Handle termination signals gracefully."""
    logger.info("Shutting down all servers...")
    stop_processes()
    sys.exit(0)

def stop_processes():
    """Stop all running processes."""
    global main_process, extended_process
    
    if main_process:
        logger.info("Stopping main application...")
        try:
            main_process.terminate()
            main_process.wait(timeout=5)
        except:
            main_process.kill()
        logger.info("Main application stopped.")
    
    if extended_process:
        logger.info("Stopping extended proxy...")
        try:
            extended_process.terminate()
            extended_process.wait(timeout=5)
        except:
            extended_process.kill()
        logger.info("Extended proxy stopped.")

def run_gunicorn(module, port, log_prefix):
    """Run a Flask app using Gunicorn."""
    global main_process, extended_process
    
    cmd = [
        "gunicorn",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "1",
        "--reload",
        module
    ]
    
    logger.info(f"Starting {module} on port {port}...")
    
    # Create log file
    log_file = open(os.path.join(LOG_DIR, f"{log_prefix}.log"), "w")
    
    # Start the process
    process = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Store the process in the appropriate global variable
    if module == "main:app":
        main_process = process
    else:
        extended_process = process
    
    # Create a thread to log output
    def log_output():
        while process.poll() is None:
            time.sleep(1)
        logger.info(f"{module} process exited with code {process.returncode}")
    
    threading.Thread(target=log_output, daemon=True).start()
    
    return process

def is_port_in_use(port):
    """Check if a port is in use."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        s.close()
        return False
    except:
        return True

def wait_for_ports(ports, timeout=30):
    """Wait for ports to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not any(is_port_in_use(port) for port in ports):
            return True
        time.sleep(1)
    return False

def main():
    """Start both servers and monitor them."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for ports to be available
    if not wait_for_ports([DEFAULT_PORT, EXTENDED_PORT]):
        logger.error(f"Ports {DEFAULT_PORT} and {EXTENDED_PORT} not available after timeout")
        return 1
    
    try:
        # Start the main application
        run_gunicorn("main:app", DEFAULT_PORT, "main")
        
        # Wait a moment to ensure first server starts correctly
        time.sleep(2)
        
        # Start the extended proxy
        run_gunicorn("flask_proxy_extended:app", EXTENDED_PORT, "extended")
        
        # Print success message
        logger.info(f"All servers started successfully!")
        logger.info(f"Main application:  http://localhost:{DEFAULT_PORT}")
        logger.info(f"Extended proxy:    http://localhost:{EXTENDED_PORT}")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if main_process.poll() is not None:
                logger.error(f"Main application exited with code {main_process.returncode}")
                break
                
            if extended_process.poll() is not None:
                logger.error(f"Extended proxy exited with code {extended_process.returncode}")
                break
        
    except Exception as e:
        logger.error(f"Error starting servers: {e}")
        stop_processes()
        return 1
    
    finally:
        stop_processes()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())