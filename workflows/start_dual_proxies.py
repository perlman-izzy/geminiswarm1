#!/usr/bin/env python3
"""
Script to start both the original and extended Gemini proxy servers simultaneously.
This allows for full functionality of the multi-agent swarm system.
"""
import os
import sys
import time
import logging
import subprocess
import threading
import signal

# Configure logging
logging.basicConfig(level=logging.INFO,
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define server info
SERVERS = [
    {
        "name": "Main Proxy",
        "module": "main:app",
        "port": 5000,
        "process": None,
    },
    {
        "name": "Extended Proxy",
        "script": "flask_proxy_extended.py",
        "port": 3000,
        "process": None,
    }
]

# Flag to indicate when shutdown is requested
shutdown_requested = False

def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals."""
    global shutdown_requested
    logger.info("Shutdown signal received, stopping servers...")
    shutdown_requested = True

def run_gunicorn(module, port, log_prefix):
    """Run a Flask app using Gunicorn."""
    cmd = [
        "gunicorn",
        "--bind", f"0.0.0.0:{port}",
        "--reuse-port",
        "--reload",
        module
    ]
    
    logger.info(f"Starting {log_prefix} on port {port} with command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Store the process in the server info
        for server in SERVERS:
            if server.get("module") == module:
                server["process"] = process
                break
        
        # Print output with prefix in real-time
        prefix = f"[{log_prefix}] "
        for line in process.stdout:
            if not shutdown_requested:
                print(prefix + line, end='')
            else:
                break
                
        # Process terminated
        return_code = process.wait()
        logger.info(f"{log_prefix} exited with code {return_code}")
    
    except Exception as e:
        logger.exception(f"Error running {log_prefix}: {e}")

def run_python_script(script_path, log_prefix):
    """Run a Python script directly."""
    cmd = [sys.executable, script_path]
    
    logger.info(f"Starting {log_prefix} with command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Store the process in the server info
        for server in SERVERS:
            if server.get("script") == os.path.basename(script_path):
                server["process"] = process
                break
        
        # Print output with prefix in real-time
        prefix = f"[{log_prefix}] "
        for line in process.stdout:
            if not shutdown_requested:
                print(prefix + line, end='')
            else:
                break
                
        # Process terminated
        return_code = process.wait()
        logger.info(f"{log_prefix} exited with code {return_code}")
    
    except Exception as e:
        logger.exception(f"Error running {log_prefix}: {e}")

def main():
    """Start both proxy servers and monitor them."""
    # Set up signal handling for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root
    root_dir = os.path.dirname(script_dir)
    
    # Start server threads
    threads = []
    
    # Start main proxy with gunicorn
    main_proxy_thread = threading.Thread(
        target=run_gunicorn,
        args=(SERVERS[0]["module"], SERVERS[0]["port"], SERVERS[0]["name"]),
        daemon=True
    )
    threads.append(main_proxy_thread)
    main_proxy_thread.start()
    
    # Start extended proxy directly with Python
    extended_proxy_path = os.path.join(root_dir, SERVERS[1]["script"])
    extended_proxy_thread = threading.Thread(
        target=run_python_script,
        args=(extended_proxy_path, SERVERS[1]["name"]),
        daemon=True
    )
    threads.append(extended_proxy_thread)
    extended_proxy_thread.start()
    
    # Wait a moment for servers to start
    time.sleep(3)
    
    logger.info("Both proxy servers should now be running.")
    logger.info(f"Main Proxy available at: http://localhost:{SERVERS[0]['port']}")
    logger.info(f"Extended Proxy available at: http://localhost:{SERVERS[1]['port']}")
    logger.info("Press Ctrl+C to shut down both servers.")
    
    # Keep the main thread alive until shutdown is requested
    try:
        while not shutdown_requested:
            # Check if any thread has exited unexpectedly
            if not all(thread.is_alive() for thread in threads):
                logger.error("One or more servers has stopped unexpectedly.")
                # Try to restart
                break
            time.sleep(1)
    except KeyboardInterrupt:
        # This should be caught by the signal handler, but just in case
        logger.info("Interrupt received, shutting down...")
    
    # Shut down all processes
    for server in SERVERS:
        if server.get("process") and server["process"].poll() is None:
            logger.info(f"Stopping {server['name']}...")
            server["process"].terminate()
            try:
                server["process"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"{server['name']} did not terminate gracefully, killing it.")
                server["process"].kill()
    
    logger.info("All servers stopped.")
    return 0

if __name__ == "__main__":
    sys.exit(main())