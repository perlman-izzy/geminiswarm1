#!/usr/bin/env python3
"""
Workflow script to start both proxy servers.
"""
import os
import sys
import time
import signal
import logging
import subprocess
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start_dual_proxies")

# Global processes to track
processes = []

def signal_handler(sig, frame):
    """Handle signals gracefully."""
    logger.info("Shutting down proxy servers...")
    for proc in processes:
        if proc and proc.poll() is None:
            proc.terminate()
    sys.exit(0)

def run_proxy(name, module_app, port):
    """Run a proxy server using Gunicorn."""
    cmd = [
        "gunicorn",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "1",
        "--reload",
        module_app
    ]
    logger.info(f"Starting {name} on port {port}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        processes.append(process)
        
        # Create a thread to log output
        def log_output():
            if process.stdout is not None:
                for line in iter(process.stdout.readline, ''):
                    logger.info(f"{name}: {line.strip()}")
        
        thread = threading.Thread(target=log_output, daemon=True)
        thread.start()
        
        return process
    except Exception as e:
        logger.error(f"Error starting {name}: {e}")
        return None

def check_ports_available(ports, timeout=30):
    """Check if ports are available."""
    import socket
    
    deadline = time.time() + timeout
    ports_status = {port: False for port in ports}
    
    while time.time() < deadline:
        for port in ports:
            if not ports_status[port]:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect(("localhost", port))
                    ports_status[port] = True
                except:
                    pass
                finally:
                    s.close()
        
        if all(ports_status.values()):
            return True
        
        # Wait before retrying
        time.sleep(1)
    
    # Timeout reached
    logger.error(f"Timed out waiting for ports: {[p for p, s in ports_status.items() if not s]}")
    return False

def main():
    """Start both proxy servers."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start main proxy on port 5000
    main_proxy = run_proxy("Main Proxy", "flask_proxy:app", 5000)
    
    # Start extended proxy on port 3000
    extended_proxy = run_proxy("Extended Proxy", "flask_proxy_extended:app", 3000)
    
    # Check if both proxies started successfully
    if main_proxy is None or extended_proxy is None:
        logger.error("Failed to start one or more proxy servers")
        signal_handler(None, None)
        return 1
    
    # Wait for ports to be available
    if not check_ports_available([5000, 3000]):
        logger.error("Proxy servers failed to start properly")
        signal_handler(None, None)
        return 1
    
    logger.info("All proxy servers running successfully")
    
    # Keep running
    try:
        while all(p.poll() is None for p in processes):
            time.sleep(1)
        
        # If we get here, a process died
        for i, p in enumerate(processes):
            if p.poll() is not None:
                logger.error(f"Process {i} exited with code {p.returncode}")
        
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        signal_handler(None, None)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())