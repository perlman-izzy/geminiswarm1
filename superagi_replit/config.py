"""
Configuration module for the simplified SuperAGI system.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database
DATABASE_URL = os.environ.get("DATABASE_URL")

# Workspace directories
RESOURCES_INPUT_ROOT_DIR = "workspace/input/{agent_id}"
RESOURCES_OUTPUT_ROOT_DIR = "workspace/output/{agent_id}/{agent_execution_id}"

# LLM
GEMINI_PROXY_URL = "http://localhost:5000/gemini"

# App settings
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "superagi_encryption_key")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "superagi_jwt_secret_key")

# Default model parameters
DEFAULT_MODEL_TEMPERATURE = 0.7
DEFAULT_MODEL_MAX_TOKENS = 4096

def get_config(key, default=None):
    """Get a configuration value."""
    return globals().get(key, default)