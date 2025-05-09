# Multi-Agent Gemini AI System

A sophisticated multi-agent system leveraging Google's Gemini AI to work on a variety of tasks with intelligent task delegation and coordination.

## Features

- **Dual Proxy Architecture**: Main proxy (port 5000) and extended proxy (port 3000) to handle different types of requests
- **Intelligent Task Delegation**: Routes tasks to appropriate models based on complexity
- **Swarm Controller**: Coordinates multiple AI agents working together on different tasks
- **Web Search Capability**: Search the web and retrieve information
- **Advanced Code Debugging**: Automatically debug and fix code issues
- **Real-time Resource Management**: On-the-fly package installation when needed
- **Transparent Reasoning**: Detailed logs of the AI's "thinking" process

## Getting Started

### Prerequisites

- Python 3.9+
- Google Gemini API keys

### Installation

1. Clone this repository
2. Run the setup script:

```bash
python setup.py --install
```

3. Add your API keys to the `.env` file:

```
GOOGLE_API_KEY1=your_key_here
GOOGLE_API_KEY2=your_key_here
GOOGLE_API_KEY3=your_key_here
GEMINI_API_KEY=your_key_here
```

### Running the System

Start the system using:

```bash
python start_swarm.py
```

This will start both proxy servers and provide a command-line interface to interact with the system.

## Available Commands

When the system is running, you can use the following commands:

- `help` - Show available commands
- `demo` - Run a demonstration of the system's capabilities
- `test [name]` - Run specific tests or all tests if no name is provided
- `ask [prompt]` - Ask a question to Gemini
- `search [query]` - Perform a web search
- `fix [file]` - Fix code in a file
- `stats` - Show API key usage statistics
- `exit` or `quit` - Exit the program

## Testing

Run the escalation tests to verify functionality:

```bash
python escalation_test.py
```

This will run a series of tests with increasing complexity to validate the system's capabilities.

## System Components

- **flask_proxy.py**: Main proxy server for Gemini API
- **flask_proxy_extended.py**: Enhanced proxy with intelligent model selection
- **swarm_controller.py**: Coordinates multiple AI agents
- **task_queue.py**: Thread-safe task queue implementation
- **loop_controller.py**: Loops for debugging and fixing code
- **gemini_client.py**: Client for interacting with Gemini API
- **ai_helper.py**: Helper module for different versions of the Gemini API
- **config.py**: Centralized configuration

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.