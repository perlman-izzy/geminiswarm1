#!/usr/bin/env python3
"""
Run both the main application and the extended proxy server.
"""
import os
import sys
import time
import signal
import logging
import threading
import subprocess
from config import LOG_DIR

# Configure logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "dual_servers.log"))
    ]
)
logger = logging.getLogger("dual_servers")

# Global variables
main_process = None
extended_process = None
running = True

def signal_handler(sig, frame):
    """Handle termination signals."""
    global running
    logger.info("Shutting down servers...")
    running = False
    stop_processes()
    logger.info("All servers stopped.")
    sys.exit(0)

def stop_processes():
    """Stop all processes."""
    global main_process, extended_process
    
    if main_process:
        try:
            main_process.terminate()
            main_process.wait(timeout=5)
        except:
            if main_process.poll() is None:
                main_process.kill()
        logger.info("Main application stopped.")
    
    if extended_process:
        try:
            extended_process.terminate()
            extended_process.wait(timeout=5)
        except:
            if extended_process.poll() is None:
                extended_process.kill()
        logger.info("Extended proxy stopped.")

def start_server(cmd, name, log_file):
    """Start a server process."""
    logger.info(f"Starting {name}...")
    
    # Open log file
    log_fd = open(log_file, 'w')
    
    # Start process
    process = subprocess.Popen(
        cmd,
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    return process

def monitor_process(process, name):
    """Monitor a process and restart it if it fails."""
    global running
    
    while running:
        if process.poll() is not None:
            logger.error(f"{name} exited with code {process.returncode}")
            return
        time.sleep(1)

def main():
    """Main function."""
    global main_process, extended_process, running
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start main application
        main_cmd = [
            "gunicorn",
            "--bind", "0.0.0.0:5000",
            "--workers", "1",
            "--reload",
            "main:app"
        ]
        main_log = os.path.join(LOG_DIR, "main_app.log")
        main_process = start_server(main_cmd, "Main application", main_log)
        
        # Start monitoring thread for main app
        main_thread = threading.Thread(target=monitor_process, args=(main_process, "Main application"))
        main_thread.daemon = True
        main_thread.start()
        
        # Wait a moment to ensure first server starts correctly
        time.sleep(2)
        
        # Start extended proxy
        extended_cmd = [
            "gunicorn",
            "--bind", "0.0.0.0:3000",
            "--workers", "1",
            "--reload",
            "flask_proxy_extended:app"
        ]
        extended_log = os.path.join(LOG_DIR, "extended_proxy.log")
        extended_process = start_server(extended_cmd, "Extended proxy", extended_log)
        
        # Start monitoring thread for extended proxy
        extended_thread = threading.Thread(target=monitor_process, args=(extended_process, "Extended proxy"))
        extended_thread.daemon = True
        extended_thread.start()
        
        logger.info("All servers started.")
        logger.info("Main application: http://localhost:5000")
        logger.info("Extended proxy:   http://localhost:3000")
        
        # Keep running until interrupted
        while running:
            time.sleep(1)
            
            # Check if processes are still running
            if not main_thread.is_alive() or not extended_thread.is_alive():
                logger.error("One or more servers failed.")
                running = False
                break
    
    except Exception as e:
        logger.error(f"Error starting servers: {e}")
    
    finally:
        stop_processes()

if __name__ == "__main__":
    main()