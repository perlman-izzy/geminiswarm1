"""
Entry point for the SuperAGI simplified application.

This script runs the SuperAGI application without Docker or external services,
using the Gemini proxy for LLM functionality.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    
    print("Starting SuperAGI simplified application...")
    print("Database URL:", os.environ.get("DATABASE_URL"))
    print("Gemini Proxy URL:", "http://localhost:3000/gemini")
    
    # Run FastAPI application
    uvicorn.run("superagi_replit.main:app", host="0.0.0.0", port=5000, reload=True)