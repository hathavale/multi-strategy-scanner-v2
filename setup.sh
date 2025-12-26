#!/bin/bash

# Multi-Strategy Options Scanner - Quick Setup Script
# This script automates the initial setup process

set -e  # Exit on error

echo "=================================================="
echo "Multi-Strategy Options Scanner - Quick Setup"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python 3 is installed
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed. Please install Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
echo ""

# Check if PostgreSQL is accessible
echo "Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠ psql not found. Make sure PostgreSQL is installed and accessible${NC}"
else
    echo -e "${GREEN}✓ PostgreSQL client found${NC}"
fi
echo ""

# Navigate to backend directory
cd "$(dirname "$0")/backend"

# Create virtual environment
echo "Creating Python virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create .env file if it doesn't exist
echo "Setting up environment configuration..."
if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file already exists${NC}"
else
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file from template${NC}"
    echo -e "${YELLOW}⚠ IMPORTANT: Edit .env file with your actual credentials!${NC}"
fi
echo ""

# Test imports
echo "Testing core modules..."
python3 -c "import config; print('✓ config.py')" 2>/dev/null || echo -e "${RED}✗ config.py failed - check .env file${NC}"
python3 -c "from utils import calculations; print('✓ calculations.py')" 2>/dev/null || echo -e "${RED}✗ calculations.py failed${NC}"
echo ""

echo "=================================================="
echo "Setup Complete!"
echo "=================================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Edit backend/.env with your credentials:"
echo "   - DATABASE_URL"
echo "   - ALPHAVANTAGE_API_KEY"
echo ""
echo "2. Set up the database:"
echo "   psql -U your_user -d your_database -f database/schema.sql"
echo ""
echo "3. Test the setup:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python config.py"
echo "   python database/connection.py"
echo ""
echo "4. Ready for Phase 2: Strategy Implementation!"
echo ""
echo -e "${GREEN}Happy Coding! 🚀${NC}"
