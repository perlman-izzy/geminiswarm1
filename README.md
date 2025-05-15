# SuperAGI Simplified for Replit

This is a simplified version of SuperAGI designed to run in Replit without Docker or external services. The system uses Gemini as the LLM backend through a proxy.

## Features

- Simplified architecture that runs in a single process
- PostgreSQL database for persistent storage
- Gemini integration via a local proxy
- RESTful API for agent creation and execution
- Tool-using capabilities with a web search tool

## Architecture

The system consists of:

1. **Agent System**: Core agent logic for planning and executing tasks
2. **LLM Integration**: Gemini integration for language processing
3. **Tool System**: Extensible tool framework for agent capabilities
4. **Web API**: FastAPI endpoints for agent management

## Setup

1. The PostgreSQL database is automatically set up in Replit
2. The environment variables are loaded from the `.env` file
3. The Gemini proxy is expected to be running at `http://localhost:3000/gemini`

## Usage

### Starting the Application

To start the application, run:

```bash
python run.py
```

This will start the web server on port 5000.

### API Endpoints

#### Agents

- `GET /agents` - List all agents
- `POST /agents` - Create a new agent
- `GET /agents/{agent_id}` - Get agent details

#### Agent Execution

- `POST /agent-execution` - Execute an agent with a user query
- `GET /agent-execution/{execution_id}/feed` - Get the execution feed
- `POST /agent-query` - Send a follow-up query to an agent execution

### Example: Finding venues with pianos in San Francisco

To search for venues with pianos in San Francisco:

1. Create an agent:

```json
POST /agents
{
  "name": "VenueFinder",
  "description": "An agent that finds venue information based on specific criteria",
  "goals": ["Find venues with pianos in San Francisco"]
}
```

2. Execute the agent:

```json
POST /agent-execution
{
  "agent_id": 1,
  "user_input": "Find all venues with pianos in San Francisco"
}
```

3. Check the execution feed:

```
GET /agent-execution/1/feed
```

## Extending

### Adding New Tools

To add a new tool:

1. Create a new tool class that extends `BaseTool`
2. Implement the required methods
3. Add the tool to the agent during initialization

Example:

```python
from superagi_replit.tools.base_tool import BaseTool
from pydantic import BaseModel, Field

class MyToolSchema(BaseModel):
    param1: str = Field(..., description="Description of parameter 1")

class MyTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.name = "MyTool"
        self.description = "Description of my tool"
        self.args_schema = MyToolSchema
        
    def execute(self, *args, **kwargs):
        # Implementation
        param1 = kwargs.get("param1", "")
        return f"Result from MyTool using {param1}"
```

## Implementation Notes

- The system uses a simplified agent architecture
- Type annotations are used throughout the codebase
- Error handling is implemented for API endpoints
- Tools process inputs and return results as strings
- Agent executions are persisted in the database