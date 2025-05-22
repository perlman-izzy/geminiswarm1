#!/bin/bash
# Run the extended proxy server

# Ensure we have the main directory in Python path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Starting extended proxy server on port 3000..."
gunicorn --bind 0.0.0.0:3000 --workers 1 --reload flask_proxy_extended:app