#!/usr/bin/env python3
"""
Configuration module for the Multi-Agent Gemini AI system.
Loads environment variables and sets up system paths.
"""
import os
import sys
from dotenv import load_dotenv
from typing import List

# Load environment variables from .env file if present
load_dotenv()

# Directory paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT_DIR, "logs")
PROMPTS_DIR = os.path.join(ROOT_DIR, "prompts")
STATIC_DIR = os.path.join(ROOT_DIR, "static")
TEMPLATES_DIR = os.path.join(ROOT_DIR, "templates")

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Collect API keys from environment variables
API_KEYS: List[str] = [
    os.environ.get("GOOGLE_API_KEY1", ""),
    os.environ.get("GOOGLE_API_KEY2", ""),
    os.environ.get("GOOGLE_API_KEY3", ""),
    os.environ.get("GEMINI_API_KEY", "")
]

# API Endpoints
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta"

# Model names
GEMINI_MODELS = {
    "pro": "models/gemini-1.5-pro",
    "flash": "models/gemini-1.5-flash",
    "ultra": "models/gemini-1.5-pro-latest",  # May not be available in all regions
    "fallback": "models/gemini-1.0-pro"
}

# Port configurations
DEFAULT_PORT = 5000
EXTENDED_PORT = 3000

# Other configuration options
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
MAX_TOKENS = 8192
TEMPERATURE = 0.7

# Debug mode
DEBUG = os.environ.get("DEBUG", "False").lower() in ["true", "1", "yes"]

# Add repository root to Python path to allow imports from anywhere
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Print configuration status
if __name__ == "__main__":
    print(f"ROOT_DIR: {ROOT_DIR}")
    print(f"LOG_DIR: {LOG_DIR}")
    print(f"API Keys available: {len([k for k in API_KEYS if k])}")
    print(f"Debug mode: {DEBUG}")