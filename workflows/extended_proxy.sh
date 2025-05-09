#!/bin/bash
# Run the extended proxy server

# Set the environment PYTHONPATH to include the current directory
export PYTHONPATH=$(pwd)

# Run the server
echo "Starting extended proxy on port 3000..."
exec gunicorn --bind 0.0.0.0:3000 --workers 1 --reload flask_proxy_extended:app