# Gemini AI Proxy with Swarm Debugger

A system for debugging code automatically using Google's Gemini AI models with API key rotation and parallel worker support.

## Components

### Flask Proxy Server

The `flask_proxy.py` file creates a web server that:
- Provides an API endpoint for Gemini AI access
- Implements key rotation across multiple API keys
- Handles rate limiting with automatic retries
- Provides a stats endpoint for monitoring usage

### Swarm Debugger

The swarm system allows:
- Parallel debugging of multiple files
- Automatic error detection and code fixing
- API key distribution across workers
- Robust error handling and logging

## Installation

1. Install dependencies:
```
pip install flask google-generativeai requests python-dotenv
```

2. Configure API keys:
   - Get API keys from [Google AI Studio](https://ai.google.dev/)
   - Add keys to environment variables or use directly in the code
   - For better security, use environment variables or the .env file

## Usage

### Starting the Proxy Server

```
python flask_proxy.py
```

This starts a server on http://localhost:5000 with:
- `/` - Web interface for testing
- `/gemini` - API endpoint for AI requests
- `/stats` - Usage statistics

### Command-Line Client

```
python main.py "Your prompt here"
```

### Swarm Debugger

```
python swarm.py fix file1.py file2.py --test-cmd "python -m unittest tests.py"
```

Options:
- `--proxy` - URL of the proxy server
- `--attempts` - Maximum fix attempts per file
- `--workers` - Number of parallel workers

## Configuration

Environment variables (or .env file):
- `PROXY_URL` - URL of the Gemini proxy server
- `MAX_ATTEMPTS` - Maximum fix attempts per file
- `WORKER_COUNT` - Number of parallel workers
- `LOG_DIR` - Directory for log files
- `GEMINI_API_KEYS` - Comma-separated list of API keys

## Testing

Run the test script to verify the system:

```
./test_all.sh
```

This tests:
1. API functionality with simple prompts
2. Code fixing with the sample buggy code
3. Various error handling scenarios

## Architecture

```
┌───────────────┐     ┌──────────────┐     ┌───────────────┐
│   Swarm.py    │────▶│ flask_proxy.py│────▶│  Gemini API   │
│ (Parallel     │     │ (Key rotation)│     │  (Google AI)  │
│  Workers)     │◀────│               │◀────│               │
└───────────────┘     └──────────────┘     └───────────────┘
       │                                           ▲
       │                                           │
       ▼                                           │
┌───────────────┐     ┌──────────────┐             
│ loop_controller│────▶│ gemini_client │           
│ (Fix logic)    │     │ (API handling)│──────────▶
└───────────────┘     └──────────────┘            
```

## Files

- `flask_proxy.py` - API proxy server with key rotation
- `main.py` - Command-line client
- `swarm.py` - Parallel debugging controller
- `loop_controller.py` - Fix attempt logic
- `gemini_client.py` - Gemini API client
- `file_agent.py` - Safe file operations
- `runner.py` - Command execution utilities
- `logger.py` - Logging configuration
- `config.py` - Central configuration
- `.env` - Environment variables

## License

Open source - use as needed!