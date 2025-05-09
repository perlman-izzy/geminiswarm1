#!/usr/bin/env python3
"""
Entry point for running the extended proxy server on its own.
"""
from flask_proxy_extended import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)