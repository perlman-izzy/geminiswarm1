# Multi-Agent Gemini AI System

A powerful system that offers multiple AI agents with real-world capabilities through enhanced API interactions, web tools, and information retrieval. Features autonomous research, job application optimization, and intelligent form filling capabilities.

## Features

### Core System
- **Consolidated Architecture**: Single server approach consolidating all capabilities
- **API Key Rotation**: Automatic load balancing across multiple Gemini API keys
- **Intelligent Model Selection**: Automatically selects appropriate Gemini model based on task complexity
- **Error Handling & Retries**: Built-in retry mechanism with exponential backoff and fallbacks

### Autonomous Research Capabilities
- **Self-Guided Research**: Intelligently determines research strategy without human guidance
- **Adaptive Learning**: Changes research focus based on previously discovered information
- **Intuitive Assessment**: Determines when sufficient information has been gathered without rigid metrics
- **Information Synthesis**: Combines findings from multiple sources into comprehensive answers

### Job Application Capabilities
- **Resume Analysis**: Extracts relevant information from resumes in various formats
- **Intelligent Form Filling**: Automatically maps resume data to job application fields
- **Experience Optimization**: Tailors work experience to emphasize relevance to job postings
- **Multi-Stage Processing**: Handles complex application workflows across multiple pages

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

### Main Application Server
Run the main application server:
```bash
python -m gunicorn --bind 0.0.0.0:5000 --workers 1 --reload main:app
```

### Using the Autonomous Researcher
Run a research query:
```bash
python test_research_capability.py "Your research query here"
```

For a quick demo with limited iterations:
```bash
python test_quick.py
```

For a simple demonstration of core functionality:
```bash
python demo_research.py
```

### Running Resume Analysis Tests
Test the resume analysis and form filling capabilities:
```bash
python test_resume_analysis.py
```

### Testing Form Filling
Test job application form filling functionality:
```bash
python test_form_filling.py
```

## API Endpoints

### Application Server (port 5000)
- `GET /`: Web interface for the application
- `GET /status`: Check system status
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

### Autonomous Researcher API
The autonomous researcher can be used programmatically by importing it into your Python code:

```python
from autonomous_researcher import AutonomousResearcher

# Initialize the researcher
researcher = AutonomousResearcher()

# Conduct research on a query
results = researcher.research("Your research question here")

# Access the structured results
answer = results["answer"]
categories = results["categories"]
```

## Architecture

The system uses a consolidated single-server architecture:

1. **Main Application Server (port 5000)**:
   - Serves as the main entry point
   - Handles API interactions with Gemini, Claude, and OpenAI
   - Provides all tools and capabilities (web search, content extraction, etc.)
   - Hosts the web interface and API endpoints
   
2. **Core Components**:
   - **Autonomous Researcher**: Self-guided research system
   - **Resume Analysis & Form Filling**: Automated job application system
   - **AI Model Integrations**: Support for multiple AI models with fallbacks
   - **Web Tools**: Search, scraping, content analysis, etc.

## Development

### Project Structure
- `main.py`: Main application entry point
- `flask_proxy_extended.py`: Extended proxy with all tools
- `ai_helper.py`: Helper functions for Gemini API interactions
- `autonomous_researcher.py`: Self-guided research system
- `anthropic_helper.py`: Fallback to Anthropic's Claude models
- `openai_helper.py`: Integration with OpenAI models
- `test_research_capability.py`: Tests for autonomous research
- `test_resume_analysis.py`: Tests for resume analysis and form filling
- `config.py`: Configuration and environment settings
- `templates/`: HTML templates for web interface
- `static/`: Static files for web interface
- `logs/`: Log files

### Key Components

#### Autonomous Researcher
The `autonomous_researcher.py` module implements a self-guided research system that:
1. Creates a research plan based on the user's query
2. Executes research using web search and content scraping
3. Adaptively adjusts its strategy based on what it discovers
4. Assesses progress using an intuitive approach to determine completeness
5. Synthesizes findings into a comprehensive, categorized answer

#### Resume Analysis System
The resume analysis functionality provides:
1. Extraction of work experience, skills, education, and contact details
2. Mapping of resume data to job application fields
3. Optimization of descriptions to match job requirements
4. Handling of varied resume formats and structures

### Adding New Features
1. For new tools: Add functions to `flask_proxy_extended.py`
2. For new API endpoints: Add routes to `flask_proxy_extended.py`
3. For UI changes: Modify templates in `templates/`

## Troubleshooting

- **API Key Issues**: Ensure API keys are set in environment variables
- **Import Errors**: Make sure the project root is in PYTHONPATH
- **Port Conflicts**: Ensure port 5000 is available
- **Logging**: Check logs in the `logs/` directory
- **Web Scraping Issues**: Some websites like Yelp block scraping. Try different sources if you encounter 403 errors
- **Rate Limiting**: If you encounter rate limits, the system will retry with exponential backoff
- **Model Selection**: For complex queries, the system will automatically select more capable models