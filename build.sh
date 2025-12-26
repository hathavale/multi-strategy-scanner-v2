#!/usr/bin/env bash
# Exit on error and print each command
set -o errexit
set -o xtrace

echo "=== Starting build ==="
echo "Current directory: $(pwd)"
echo "Listing files:"
ls -la

echo "=== Python version ==="
python --version

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Build complete ==="
