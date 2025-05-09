#!/usr/bin/env python3
"""
Direct runner for the extended proxy server
"""
import os
import sys
import flask_proxy_extended

# Run the app directly
if __name__ == "__main__":
    # Bind to all interfaces on port 3000
    flask_proxy_extended.app.run(host="0.0.0.0", port=3000, debug=True)