#!/usr/bin/env python3
"""
Workflow script to start the extended proxy server.
"""
import os
import sys
import signal
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("extended_proxy")

def signal_handler(sig, frame):
    """Handle signals gracefully."""
    logger.info("Shutting down extended proxy server...")
    sys.exit(0)

def main():
    """Start the extended proxy server."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting extended proxy server on port 3000")
    
    # Command to start the server
    cmd = [
        "gunicorn",
        "--bind", "0.0.0.0:3000",
        "--workers", "1",
        "--reload",
        "flask_proxy_extended:app"
    ]
    
    # Run the command
    try:
        process = subprocess.run(cmd)
        return process.returncode
    except Exception as e:
        logger.error(f"Error starting extended proxy server: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())