#!/bin/bash
# Start all services for the Multi-Agent Gemini AI System

# Create logs directory
mkdir -p logs

# Start main application (port 5000)
echo "Starting main application on port 5000..."
python3 -m gunicorn --bind 0.0.0.0:5000 --workers 1 --reload main:app > logs/main.log 2>&1 &
MAIN_PID=$!
echo "Main app started with PID: $MAIN_PID"

# Wait a moment to ensure first server starts correctly
sleep 2

# Start extended proxy (port 3000)
echo "Starting extended proxy on port 3000..."
python3 -m gunicorn --bind 0.0.0.0:3000 --workers 1 --reload flask_proxy_extended:app > logs/extended.log 2>&1 &
EXTENDED_PID=$!
echo "Extended proxy started with PID: $EXTENDED_PID"

echo "All services started."
echo "Main app:        http://localhost:5000"
echo "Extended proxy:  http://localhost:3000"
echo ""
echo "To view logs:"
echo "  Main app:       tail -f logs/main.log"
echo "  Extended proxy: tail -f logs/extended.log"
echo ""
echo "Press Ctrl+C to stop all services."

# Handle shutdown gracefully
trap "kill $MAIN_PID $EXTENDED_PID; echo 'Services stopped.'; exit 0" SIGINT SIGTERM

# Keep script running
while true; do
    sleep 1
done