#!/usr/bin/env python3
"""
Script to run both the main and extended proxy servers simultaneously.
"""
import os
import sys
import time
import threading
import subprocess
import logging
import signal
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dual_proxies")

# Global processes to track
processes = []

def signal_handler(sig, frame):
    """Handle termination signals gracefully."""
    logger.info("Received termination signal. Shutting down...")
    stop_processes()
    sys.exit(0)

def stop_processes():
    """Stop all running processes."""
    for proc in processes:
        if proc and proc.poll() is None:
            logger.info(f"Terminating process: {proc.pid}")
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()

def run_gunicorn(module, port, log_prefix):
    """Run a Flask app using Gunicorn."""
    cmd = [
        "gunicorn",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "1",
        f"{module}"
    ]
    logger.info(f"Starting {log_prefix} server on port {port}: {' '.join(cmd)}")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        processes.append(proc)
        
        # Create a thread to read and log output
        def log_output():
            for line in iter(proc.stdout.readline, ''):
                logger.info(f"{log_prefix}: {line.strip()}")
        
        thread = threading.Thread(target=log_output, daemon=True)
        thread.start()
        
        return proc
    except Exception as e:
        logger.error(f"Error starting {log_prefix} server: {str(e)}")
        return None

def is_port_in_use(port):
    """Check if a port is in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def wait_for_ports(ports, timeout=30):
    """Wait for ports to become available."""
    logger.info(f"Waiting for ports to become available: {ports}")
    start_time = time.time()
    all_available = False
    
    while not all_available and time.time() - start_time < timeout:
        available_ports = [port for port in ports if is_port_in_use(port)]
        if len(available_ports) == len(ports):
            all_available = True
            logger.info("All ports are available!")
            break
        
        unavailable = set(ports) - set(available_ports)
        logger.info(f"Waiting for ports: {unavailable}")
        time.sleep(1)
    
    if not all_available:
        logger.error(f"Timeout waiting for ports after {timeout} seconds")
    
    return all_available

def main():
    """Start both proxy servers and monitor them."""
    parser = argparse.ArgumentParser(description="Run both proxy servers")
    parser.add_argument("--timeout", type=int, default=30, 
                        help="Timeout in seconds to wait for services to start")
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start main proxy on port 5000
    main_proxy = run_gunicorn("flask_proxy:app", 5000, "MAIN PROXY")
    
    # Start extended proxy on port 3000
    extended_proxy = run_gunicorn("flask_proxy_extended:app", 3000, "EXTENDED PROXY")
    
    # Wait for both proxies to be available
    ports_ready = wait_for_ports([5000, 3000], timeout=args.timeout)
    
    if not ports_ready:
        logger.error("Failed to start proxy servers")
        stop_processes()
        return 1
    
    logger.info("Both proxy servers are running. Press Ctrl+C to stop.")
    
    # Keep the main thread alive
    try:
        while True:
            # Check if any process has died
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    logger.error(f"Process {i} (PID: {proc.pid}) terminated unexpectedly with exit code {proc.returncode}")
                    stop_processes()
                    return 1
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        stop_processes()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())