#!/usr/bin/env python3
"""
Script to run the extended proxy server on port 3000.
"""
from flask_proxy_extended import app

if __name__ == "__main__":
    print("Starting Extended Gemini API Proxy server on port 3000")
    app.run(host='0.0.0.0', port=3000, debug=True)