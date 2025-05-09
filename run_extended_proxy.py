#!/usr/bin/env python3
"""
Script to run the extended proxy server on port 3000.
"""
import os
import sys
import subprocess
import time
import signal
import logging
from config import LOG_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "extended_proxy.log"))
    ]
)
logger = logging.getLogger("run_extended_proxy")

def main():
    """Run the extended proxy server."""
    # Get the path to gunicorn
    gunicorn_path = subprocess.check_output("which gunicorn", shell=True).decode().strip()
    logger.info(f"Using gunicorn at: {gunicorn_path}")
    
    # Run the extended proxy server
    cmd = [
        gunicorn_path,
        "--bind", "0.0.0.0:3000",
        "--reuse-port",
        "--reload",
        "flask_proxy_extended:app"
    ]
    
    logger.info(f"Starting extended proxy server with command: {' '.join(cmd)}")
    
    # Execute the server
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        raise

if __name__ == "__main__":
    main()