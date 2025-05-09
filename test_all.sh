#!/bin/bash
# Test script for the Gemini API proxy and Swarm debugger

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Testing Gemini API Proxy ===${NC}"
echo "Sending test request to API..."

# Test the API directly with a simple prompt
python test_api.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ API test passed!${NC}"
else
    echo -e "${RED}✗ API test failed!${NC}"
    exit 1
fi

echo -e "\n${YELLOW}=== Testing Direct Prompt from File ===${NC}"
# Test using a prompt from file
PROMPT=$(cat prompts/code_fix.txt)
curl -s -X POST http://localhost:5000/gemini \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"$PROMPT\"}" | jq

echo -e "\n${YELLOW}=== Testing Buggy Code with Swarm ===${NC}"
echo "Note: This will modify buggy_code.py"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Make a backup of the original file
    cp buggy_code.py buggy_code.py.bak
    
    # Try to run the tests (should fail)
    echo "Running tests on original code (should fail)..."
    python -m unittest test_buggy_code.py > /dev/null 2>&1 || {
        echo -e "${GREEN}✓ Original code fails tests as expected${NC}"
    }
    
    # Run swarm to fix the code
    echo "Running swarm to fix the code..."
    python swarm.py fix buggy_code.py --test-cmd "python -m unittest test_buggy_code.py"
    
    # Check if the fixed code passes tests
    echo "Testing fixed code..."
    if python -m unittest test_buggy_code.py; then
        echo -e "${GREEN}✓ Fixed code passes all tests!${NC}"
    else
        echo -e "${RED}✗ Fixed code still has issues${NC}"
    fi
    
    # Restore the backup
    echo "Restoring original buggy code"
    mv buggy_code.py.bak buggy_code.py
else
    echo "Skipping buggy code test"
fi

echo -e "\n${GREEN}All tests completed!${NC}"