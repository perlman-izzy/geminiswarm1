import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Proxy and swarm settings
PROXY_URL = os.getenv("PROXY_URL", "http://localhost:5000")
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "3"))
WORKER_COUNT = int(os.getenv("WORKER_COUNT", "2"))
LOG_DIR = os.getenv("LOG_DIR", "logs")

# Flask proxy keys (optional override)
API_KEYS = os.getenv("GEMINI_API_KEYS", "").split(",") if os.getenv("GEMINI_API_KEYS") else []