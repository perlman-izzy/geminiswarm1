# Multi-Agent Gemini AI System

A powerful system that offers multiple AI agents with real-world capabilities through enhanced API interactions, web tools, and information retrieval.

## Features

### Core System
- **Dual Flask Servers**: Main application (port 5000) & Extended proxy (port 3000)
- **API Key Rotation**: Automatic load balancing across multiple Gemini API keys
- **Intelligent Model Selection**: Automatically selects appropriate Gemini model based on task complexity
- **Error Handling & Retries**: Built-in retry mechanism with fallback to different models

### Web Capabilities
- **Web Search**: Integration with DuckDuckGo for real-time information
- **Content Extraction**: Smart extraction of content from web pages
- **Knowledge Access**: Wikipedia integration for factual information
- **News & Trends**: Access to RSS feeds and Google Trends

### Text Analysis
- **Sentiment Analysis**: Analyze sentiment of text using TextBlob
- **Keyword Extraction**: Extract key topics from text using NLTK
- **Language Processing**: Natural language understanding capabilities

### System Tools
- **File Operations**: Read, write, and list files safely
- **System Commands**: Execute system commands in a controlled environment
- **Package Management**: Install Python packages as needed

### User Interfaces
- **Web Interface**: Bootstrap-based UI for interacting with all tools
- **API Endpoints**: REST API for programmatic access
- **Command Line**: Scripts for running various components

## Setup

### Prerequisites
- Python 3.9+
- Required packages (installed automatically using requirements):
  - flask
  - gunicorn
  - google-generativeai
  - requests
  - duckduckgo-search
  - textblob
  - nltk
  - wikipedia
  - pytrends
  - feedparser
  - beautifulsoup4
  - trafilatura

### Environment Variables
Set the following environment variables:
- `GOOGLE_API_KEY1`, `GOOGLE_API_KEY2`, `GOOGLE_API_KEY3`: Google/Gemini API keys for rotation
- `GEMINI_API_KEY`: Alternative way to specify a Gemini API key

## Running the System

### Full System (Both Servers)
Run both servers simultaneously:
```bash
python run_dual_servers.py
```

### Individual Components
Run the main application (port 5000):
```bash
python -m gunicorn --bind 0.0.0.0:5000 --workers 1 --reload main:app
```

Run the extended proxy (port 3000):
```bash
./run_extended_proxy_server.sh
```

## API Endpoints

### Main Server (port 5000)
- `GET /`: Web interface for the main application
- `GET /status`: Check system status
- `GET /proxy`: Redirect to the extended proxy

### Extended Proxy (port 3000)
- `POST /gemini`: Send prompts to Gemini AI
- `POST /web_search`: Perform web searches
- `POST /wikipedia`: Retrieve Wikipedia content
- `POST /scrape_text`: Extract text from websites
- `GET /trends`: Get trending topics
- `POST /news`: Get news from RSS feeds
- `POST /sentiment`: Analyze sentiment of text
- `POST /keywords`: Extract keywords from text
- `POST /list_files`: List files in a directory
- `POST /read_file`: Read a file
- `POST /write_file`: Write to a file
- `POST /execute`: Execute system commands
- `POST /install_package`: Install Python packages

## Architecture

The system uses a dual-server architecture:

1. **Main Application (port 5000)**:
   - Serves as the main entry point
   - Provides basic interface and status information
   - Redirects to extended functionality as needed

2. **Extended Proxy (port 3000)**:
   - Handles API interactions with Gemini
   - Provides all extended tools and capabilities
   - Manages web search, content extraction, and other tools

## Development

### Project Structure
- `main.py`: Main application entry point
- `flask_proxy_extended.py`: Extended proxy with all tools
- `ai_helper.py`: Helper functions for Gemini API interactions
- `config.py`: Configuration and environment settings
- `run_dual_servers.py`: Script to run both servers
- `templates/`: HTML templates for web interface
- `static/`: Static files for web interface
- `logs/`: Log files

### Adding New Features
1. For new tools: Add functions to `flask_proxy_extended.py`
2. For new API endpoints: Add routes to `flask_proxy_extended.py`
3. For UI changes: Modify templates in `templates/`

## Troubleshooting

- **API Key Issues**: Ensure API keys are set in environment variables
- **Import Errors**: Make sure the project root is in PYTHONPATH
- **Port Conflicts**: Ensure ports 5000 and 3000 are available
- **Logging**: Check logs in the `logs/` directory