#!/bin/bash
# Script to run the extended proxy server
gunicorn --bind 0.0.0.0:3000 --reuse-port --reload flask_proxy_extended:app