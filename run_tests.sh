#!/bin/bash
# Script to run the escalating complexity tests

echo "=========================================================="
echo "Starting Gemini Multi-Agent System Test Suite"
echo "=========================================================="

# Stop any existing processes
pkill -f "python.*start_all_services.py" || true
pkill -f "gunicorn.*flask_proxy" || true
pkill -f "gunicorn.*flask_proxy_extended" || true

echo "Waiting for ports to be released..."
sleep 2

# 1. Start all necessary services with built-in testing
echo "Starting all services and running tests..."
python start_all_services.py --test-only --test-script test_escalating_prompts.py

# Capture exit code
EXIT_CODE=$?

echo "Test completed with exit code: $EXIT_CODE"

# Ensure all processes are stopped
pkill -f "python.*start_all_services.py" || true
pkill -f "gunicorn.*flask_proxy" || true
pkill -f "gunicorn.*flask_proxy_extended" || true

exit $EXIT_CODE