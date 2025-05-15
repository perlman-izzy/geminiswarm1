#!/bin/bash
# Run stealth proxy tests

echo "========================================="
echo "TESTING GEMINI STEALTH PROXY IMPLEMENTATION"
echo "========================================="

# Test the stealth proxy
echo -e "\n\n===== RUNNING BASIC TESTS ====="
python test_stealth_proxy.py

# Run example demonstration
echo -e "\n\n===== RUNNING EXAMPLE USAGE ====="
python gemini_stealth_example.py

echo -e "\n\nAll tests completed."
echo "========================================="