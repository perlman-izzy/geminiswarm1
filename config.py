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
GEMINI_API_KEYS: List[str] = [
    os.environ.get("GOOGLE_API_KEY1", "AIzaSyAB7-BUnLe7HUElS1zRaQwf5jzOCSgHsh8"),
    os.environ.get("GOOGLE_API_KEY2", "AIzaSyCg2reIDH1OrR6TGNUCEycpAsz7XcZ0ckg"),
    os.environ.get("GOOGLE_API_KEY3", "AIzaSyB_BvGdX_M0pwhOa1-rHteRexm2pEG8y8I"),
    os.environ.get("GEMINI_API_KEY", ""),
    # Original keys that have been confirmed to work
    "AIzaSyDve6IOaFFD1VFEpm_Con-VA5ur37yYqC8",
    "AIzaSyCI5RP4-iCVOaC2MUYg-_mzJOpgXc7kvtY",
    "AIzaSyBEsgXakfjHf-tPaHwgAgfe4D3meMjQF-Y",
    "AIzaSyBHqfFs5E-8JCQIeVVbY92N4U7Su-Bv4vc",
    "AIzaSyDDonvk9pFqiB7H4Z9hovv77bv6tqc2Wi8",
    "AIzaSyDT7iUbxg6pXg-xRJ5hlhM2WxEmncZuoJA",
    "AIzaSyCUe2ug68aCGMYrNEnMqdyClnGJgzOb14U",
    "AIzaSyBkPwMNZHnvaXl2IyyRwyv6TjPn8skeYlk",
    "AIzaSyAIGisQwzXsxFNNYnOyic8WPZlAVLSk650",
    "AIzaSyAt_wwjCrCk1Se7BhY9N7yYovfT6rvV8_c",
    # New API keys provided by user
    "AIzaSyDHn4RAMfqCVEhlAtfX34I0nw-BW_fAQl4",
    "AIzaSyDwWFodtKdGDjTvqHkumPbQSwTCB3gSInA",
    "AIzaSyCw7uFkfZfu5xQ1faa9hAAUD9wQDJunE_Y",
    "AIzaSyAaqIIGMsVvjZdN99g9zBAHBYJv_qusn0c",
    "AIzaSyAAW4E_HF28MpDjL_51YcPfFEBBjHf_aOg",
    "AIzaSyD8oUFXwk34KQqzZHDWbW1NZ1omAX_NnQw",
    "AIzaSyDGgwtuxHLYJntaZE36XTioYU0pjhNT62E",
    "AIzaSyDFhlVIkR6-WFk5T7tuxyr43_VJvbSJdg8",
    "AIzaSyCP1DNOpxnTmP-Fsfs-D8m3kae7BRa7ZLA",
    "AIzaSyD4lcJJIOqtPpjBdcyJ4kMy6WMn400h10Q",
    "AIzaSyA9mwtQHobQEDD0RlBSOxWb2IIziQeBckQ",
    "AIzaSyAO5xmFONI5okR4EoB3y3sgwcs-AYfY85A",
    "AIzaSyCJTzumGYPLZ99G6Cp4SYZlDCdGv6Fe6gc",
    "AIzaSyDrwDIn11sAcLLQe5owwdOcoYEJYPDXf2Q",
    "AIzaSyCd49yfjbgmvSe-H2bCW9tChVuZZvBrgjI",
    # Additional keys provided May 16, 2025
    "AIzaSyCC3S7M-mBZV4Jip3cxl-3tU1kYV-weeJk",
    "AIzaSyCWA8VxHPb579N_8hNi1yM2VZhYm5uKctQ",
    "AIzaSyDk41aK9YLByXg63MgiGiynqW9L4WScVLU",
    "AIzaSyD0ftHRpL__zG3Ywl79ISVgzOEXkuBCbZg",
    "AIzaSyAIc3uUG6Om9k0GeSnfp-DrauEPub9AFv4",
    "AIzaSyACRKpNbJKgwZ6I9gzcKEuW3bHcKpmhe0k",
    "AIzaSyCb-RvK9qP07kB9gOfg1lcFs7nInQDAOmQ",
    "AIzaSyCxMazxBLsUxsX0iOiDsKp6Kc14WQJPoGg",
    "AIzaSyA0hgrI7bkxYBsnMQxBNHeJjGq_ACYLsUY",
    "AIzaSyDG3djs6Y1Rr0cOoKRu3ytmpssnUQgiA_E",
    "AIzaSyCwqzLegYcuZ4xr4z-1NUWbIn439qKCzcU",
    "AIzaSyDHgISrtBlEB3-SkxpUGjbIjJMajUg2vNQ"
]

# Other provider API keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# For backward compatibility
API_KEYS = GEMINI_API_KEYS

# API Endpoints
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta"

# Model names and configurations

# Gemini Models
GEMINI_MODELS = {
    # Pro-level models (complex reasoning)
    "pro": "models/gemini-2.5-pro",  # Using Gemini 2.5 as primary model
    "pro_alt1": "models/gemini-2.5-pro-latest",
    "pro_alt2": "models/gemini-2.5-flash",
    "pro_alt3": "models/gemini-2.5-flash-latest",
    "pro_alt4": "models/gemini-1.5-pro",
    "pro_alt5": "models/gemini-1.5-pro-latest",
    "pro_alt6": "models/gemini-1.5-pro-vision",
    "pro_old": "models/gemini-1.0-pro",
    
    # Flash models (faster, less complex reasoning)
    "flash": "models/gemini-1.5-flash",
    "flash_alt1": "models/gemini-1.5-flash-latest",
    "flash_alt2": "models/gemini-1.5-flash-001",
    "flash_alt3": "models/gemini-1.5-flash-002",
    "flash_alt4": "models/gemini-1.5-flash-8b",
    
    # Fallback models
    "fallback": "models/gemini-1.0-pro",
    "fallback_alt": "models/gemini-1.0-pro-vision-latest",
    "fallback_alt2": "models/gemini-pro-vision"
}

# OpenAI Models Configuration (for fallback)
OPENAI_MODELS = {
    "primary": "gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    "secondary": "gpt-4-turbo",
    "economy": "gpt-3.5-turbo",
    "vision": "gpt-4-vision-preview"
}

# Anthropic Models Configuration (for fallback)
ANTHROPIC_MODELS = {
    "primary": "claude-3-5-sonnet-20241022", # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
    "secondary": "claude-3-opus-20240229",
    "economy": "claude-3-haiku-20240307"
}

# Port configurations
DEFAULT_PORT = 5000
EXTENDED_PORT = 3000

# Other configuration options
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
MAX_TOKENS = 8192
TEMPERATURE = 0.7

# Default models to try in sequence (prioritizing Gemini 2.5)
DEFAULT_MODELS = [
    GEMINI_MODELS["pro"],         # gemini-2.5-pro
    GEMINI_MODELS["pro_alt1"],    # gemini-2.5-pro-latest
    GEMINI_MODELS["pro_alt2"],    # gemini-2.5-flash
    GEMINI_MODELS["pro_alt4"],    # gemini-1.5-pro (fallback)
    GEMINI_MODELS["fallback"]     # gemini-1.0-pro (last resort)
]

# Safety settings to reduce refusals
SAFETY_SETTINGS = {
    "harassment": "block_none",
    "hate": "block_none",
    "sexual": "block_none",
    "dangerous": "block_none"
}

# Generation configuration
GENERATION_CONFIG = {
    "temperature": TEMPERATURE,
    "max_output_tokens": MAX_TOKENS,
    "top_p": 0.95,
    "top_k": 64
}

# Logging format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Main proxy port
MAIN_PROXY_PORT = DEFAULT_PORT

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