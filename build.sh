#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install system dependencies
apt-get update && apt-get install -y build-essential gfortran

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
