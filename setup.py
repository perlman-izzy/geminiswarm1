#!/usr/bin/env python3
"""
Setup script for the Multi-Agent Gemini AI System.
This script initializes the environment and checks for all dependencies.
"""
import os
import sys
import time
import signal
import logging
import argparse
import subprocess
import importlib
from typing import List, Dict, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup")

# Required dependencies
REQUIRED_PACKAGES = [
    'beautifulsoup4',
    'duckduckgo-search',
    'email-validator',
    'flask',
    'flask-sqlalchemy',
    'google-generativeai',
    'gunicorn',
    'psycopg2-binary',
    'python-dotenv',
    'requests',
    'trafilatura'
]

# Required API keys
REQUIRED_API_KEYS = [
    'GOOGLE_API_KEY1',
    'GOOGLE_API_KEY2',
    'GOOGLE_API_KEY3',
    'GEMINI_API_KEY'
]

def check_python_version() -> bool:
    """Check that we're running on Python 3.9 or newer."""
    major, minor = sys.version_info[:2]
    if major != 3 or minor < 9:
        logger.error(f"Python 3.9+ is required, but you have {major}.{minor}")
        return False
    else:
        logger.info(f"Python version check passed: {major}.{minor}")
        return True

def check_dependencies() -> Tuple[bool, List[str]]:
    """Check that all required packages are installed."""
    missing_packages = []
    
    for package in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package.replace('-', '_'))
            logger.debug(f"Found package: {package}")
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        return False, missing_packages
    else:
        logger.info("All required packages are installed")
        return True, []

def check_api_keys() -> Tuple[bool, List[str]]:
    """Check that all required API keys are set in the environment."""
    missing_keys = []
    
    # Load from .env if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    for key in REQUIRED_API_KEYS:
        if not os.environ.get(key):
            missing_keys.append(key)
    
    if missing_keys:
        logger.error(f"Missing required API keys: {', '.join(missing_keys)}")
        return False, missing_keys
    else:
        logger.info("All required API keys are set")
        return True, []

def install_missing_packages(packages: List[str]) -> bool:
    """Install missing packages."""
    if not packages:
        return True
    
    logger.info(f"Installing missing packages: {', '.join(packages)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
        logger.info("Package installation completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install packages: {e}")
        return False

def setup_environment() -> bool:
    """Set up the environment for the Gemini AI system."""
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
        logger.info("Created logs directory")
    
    # Create .env file if it doesn't exist
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            for key in REQUIRED_API_KEYS:
                f.write(f"# {key}=your_key_here\n")
        logger.info("Created .env file template")
    
    # Create config.py if it doesn't exist
    if not os.path.exists("config.py"):
        with open("config.py", "w") as f:
            f.write("""import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys (required)
API_KEYS = [
    os.environ.get("GOOGLE_API_KEY1", ""),
    os.environ.get("GOOGLE_API_KEY2", ""),
    os.environ.get("GOOGLE_API_KEY3", ""),
    os.environ.get("GEMINI_API_KEY", "")
]

# Proxy configuration
MAIN_PROXY_PORT = 5000
EXTENDED_PROXY_PORT = 3000
PROXY_URL = f"http://localhost:{MAIN_PROXY_PORT}/gemini"

# Logging configuration
LOG_DIR = "logs"

# Swarm configuration
WORKER_COUNT = 3
MAX_ATTEMPTS = 3

""")
        logger.info("Created config.py file")
    
    # Make scripts executable
    for script in ["start_swarm.py", "run_proxies.py", "escalation_test.py"]:
        if os.path.exists(script):
            try:
                os.chmod(script, 0o755)
                logger.info(f"Made {script} executable")
            except Exception as e:
                logger.error(f"Failed to make {script} executable: {e}")
    
    return True

def check_proxy_servers() -> bool:
    """Check if proxy servers are available."""
    import socket
    
    for port in [5000, 3000]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', port))
            if result == 0:
                logger.info(f"Port {port} is already in use")
                return True
    
    logger.info("Proxy servers are not running")
    return False

def start_proxy_servers() -> bool:
    """Start the proxy servers."""
    import threading
    
    logger.info("Starting proxy servers...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "run_proxies.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Create a thread to read and log output
        def read_output():
            if process.stdout is not None:
                for line in iter(process.stdout.readline, ''):
                    logger.info(f"PROXY: {line.strip()}")
        
        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()
        
        # Wait for servers to start
        time.sleep(3)
        
        # Check if they're running
        if check_proxy_servers():
            logger.info("Proxy servers started successfully")
            return True
        else:
            logger.error("Failed to start proxy servers")
            process.terminate()
            return False
    
    except Exception as e:
        logger.error(f"Error starting proxy servers: {e}")
        return False

def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="Set up the Multi-Agent Gemini AI System")
    parser.add_argument("--install", action="store_true", help="Install missing dependencies")
    parser.add_argument("--start", action="store_true", help="Start the system after setup")
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print(" Multi-Agent Gemini AI System Setup ".center(80, "="))
    print("="*80 + "\n")
    
    # Check Python version
    if not check_python_version():
        print("\nError: Python version check failed. Please use Python 3.9 or newer.")
        return 1
    
    # Check dependencies
    deps_ok, missing_packages = check_dependencies()
    if not deps_ok and args.install:
        if not install_missing_packages(missing_packages):
            print("\nError: Failed to install required packages.")
            return 1
        # Check again after installation
        deps_ok, missing_packages = check_dependencies()
    
    if not deps_ok:
        print("\nError: Missing required packages. Run with --install to install them.")
        return 1
    
    # Check API keys
    keys_ok, missing_keys = check_api_keys()
    if not keys_ok:
        print("\nWarning: Some API keys are missing. Please add them to your .env file.")
        print("Required API keys:", ", ".join(missing_keys))
        print("The system may not function correctly without these keys.")
    
    # Set up environment
    if not setup_environment():
        print("\nError: Failed to set up environment.")
        return 1
    
    # Start the system if requested
    if args.start:
        print("\nStarting the Multi-Agent Gemini AI System...")
        if not check_proxy_servers():
            if not start_proxy_servers():
                print("\nError: Failed to start proxy servers.")
                return 1
        
        try:
            subprocess.run([sys.executable, "start_swarm.py", "--no-proxies"])
        except KeyboardInterrupt:
            print("\nShutting down...")
    
    print("\n" + "="*80)
    print(" Setup Complete ".center(80, "="))
    print("="*80)
    print("\nTo start the system, run: python start_swarm.py")
    print("To run tests, run: python escalation_test.py")
    print("="*80 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())