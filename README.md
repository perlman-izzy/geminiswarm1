# Multi-Agent Gemini AI Swarm

A powerful and efficient multi-agent system that leverages Google's Gemini AI with API key rotation and model delegation capabilities. The system enables multiple AI agents to collaborate on complex tasks, browse the web, use tools, and interact with the computer.

## Features

- **Dual Proxy Architecture**: Main proxy (port 5000) and Extended proxy (port 3000) for greater flexibility
- **API Key Rotation**: Automatically cycles through multiple API keys to handle rate limiting
- **Model Delegation**: Intelligently routes tasks to appropriate models based on priority and complexity
- **Web Capabilities**: Search, fetch, and scrape content from the web
- **File System Operations**: Read, write, and manage files
- **Script Execution**: Run commands and capture their output
- **Swarm Debugging**: Fix issues in multiple Python files concurrently
- **Priority-Based Queuing**: High-priority tasks are processed before low-priority ones

## Components

- **Main Proxy (`flask_proxy.py`)**: Core API proxy with key rotation
- **Extended Proxy (`flask_proxy_extended.py`)**: Enhanced proxy with model delegation
- **AI Helper (`ai_helper.py`)**: Utilities for working with various versions of the Gemini API
- **Swarm Controller (`swarm_controller.py`)**: Coordinates multiple agents and distributes tasks
- **Task Queue (`task_queue.py`)**: Thread-safe queue for managing tasks
- **Loop Controller (`loop_controller.py`)**: Iteratively fixes code until tests pass
- **File Agent (`file_agent.py`)**: Safely reads and writes files with backups
- **Runner (`runner.py`)**: Executes commands and captures output
- **Logger (`logger.py`)**: Configures logging with file and console output

## Models Used

- **Small Model (`gemini-1.5-flash`)**: Fast, efficient model for simple tasks
- **Large Model (`gemini-1.5-pro`)**: More powerful model for complex reasoning tasks

## Getting Started

### Quick Start

The easiest way to get started is to use the all-in-one starter script:

```bash
# Start the system with interactive CLI
python start_swarm.py

# Start the system and run the demo
python start_swarm.py --demo
```

This will start both proxies and provide an interactive command line interface where you can run various commands:

```
swarm> help

Available commands:
  demo              - Run the demo script
  prompt <text>     - Send a prompt to Gemini
  fix <file> <cmd>  - Fix a file using the test command
  search <query>    - Search the web
  help              - Show this help message
  exit              - Exit the program

swarm> prompt Tell me a joke about AI
```

### Manual Startup

Alternatively, you can start each component separately:

1. Start both proxy servers:
   ```bash
   python workflows/start_dual_proxies.py
   ```

2. Run the demonstration script:
   ```bash
   python run_demo.py
   ```

3. Use the swarm controller for specific tasks:
   ```bash
   # Send a prompt with high priority
   python swarm_controller.py prompt "Explain quantum computing" --priority high
   
   # Fix a Python file
   python swarm_controller.py fix buggy_code.py "python -m pytest test_buggy_code.py"
   
   # Search the web
   python swarm_controller.py search "multi-agent AI systems"
   ```

## Extensibility

The system is designed to be easily extendable for local machine use:

1. Use the centralized `config.py` to customize settings
2. Add new task types to the `TaskType` enum in `swarm_controller.py`
3. Implement new handler methods in the `SwarmController` class
4. Update the safety settings in `ai_helper.py` if needed

## Optimization Features

- **Parallel Processing**: Multiple worker threads handle tasks simultaneously
- **Error Handling**: Robust error handling with automatic retries
- **Logging**: Comprehensive logging for debugging and monitoring
- **Resource Management**: Efficiently manages API keys to avoid rate limiting
- **Security**: Safety settings and proper error handling to prevent issues

## Command Line Arguments

The swarm controller supports various command line arguments:

```
usage: swarm_controller.py [-h] [--main-proxy MAIN_PROXY] [--extended-proxy EXTENDED_PROXY] [--workers WORKERS] {prompt,fix,search} ...

Gemini Swarm Controller

positional arguments:
  {prompt,fix,search}   Command to run
    prompt              Send a prompt to Gemini
    fix                 Fix code issues
    search              Search the web

options:
  -h, --help            show this help message and exit
  --main-proxy MAIN_PROXY
                        URL of the main Gemini proxy
  --extended-proxy EXTENDED_PROXY
                        URL of the extended Gemini proxy
  --workers WORKERS     Number of worker threads
```