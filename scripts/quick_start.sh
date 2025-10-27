#!/bin/bash

# Gmail AI Assistant - Quick Start Script
# This script helps you set up your Gmail AI Assistant

set -e

echo "=================================="
echo "Gmail AI Assistant - Quick Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"
echo ""

# Check if .env exists and has been configured
echo "Checking .env file..."
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please create .env file with your API keys."
    echo "See SETUP_GUIDE.md for details."
    exit 1
fi

# Check for placeholder values in .env
if grep -q "your_.*_api_key_here" .env; then
    echo "WARNING: .env file still contains placeholder values!"
    echo "Please edit .env and add your actual API keys:"
    echo "  - LANGSMITH_API_KEY"
    echo "  - OPENAI_API_KEY"
    echo "  - ANTHROPIC_API_KEY"
    echo ""
    read -p "Have you configured your .env file? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please configure .env first, then run this script again."
        exit 1
    fi
fi

# Load environment variables
echo "Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)
echo "✓ Environment variables loaded"
echo ""

# Check if config.yaml has been configured
echo "Checking config.yaml..."
if grep -q "your.email@gmail.com" eaia/main/config.yaml; then
    echo "WARNING: config.yaml still contains placeholder values!"
    echo "Please edit eaia/main/config.yaml with your personal information."
    echo ""
    read -p "Have you configured your config.yaml file? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please configure config.yaml first, then run this script again."
        exit 1
    fi
fi

# Check if secrets directory exists
if [ ! -d "eaia/.secrets" ]; then
    echo "Creating secrets directory..."
    mkdir -p eaia/.secrets
    echo "✓ Secrets directory created"
fi

# Check if OAuth credentials exist
if [ ! -f "eaia/.secrets/secrets.json" ]; then
    echo ""
    echo "=================================="
    echo "Google OAuth Setup Required"
    echo "=================================="
    echo ""
    echo "You need to set up Google OAuth credentials:"
    echo "1. Go to https://console.cloud.google.com/"
    echo "2. Create OAuth credentials (Desktop app)"
    echo "3. Download the credentials JSON file"
    echo "4. Move it to: eaia/.secrets/secrets.json"
    echo ""
    echo "See SETUP_GUIDE.md for detailed instructions."
    echo ""
    read -p "Have you placed the credentials at eaia/.secrets/secrets.json? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please set up OAuth credentials first, then run this script again."
        exit 1
    fi
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
echo "This may take a few minutes..."
pip install -e . -q
echo "✓ Dependencies installed"
echo ""

# Run Gmail setup script
echo "Setting up Gmail OAuth..."
echo "You may be redirected to your browser to authorize the app."
echo ""
python scripts/setup_gmail.py

echo ""
echo "=================================="
echo "✓ Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the development server:"
echo "   pip install -U \"langgraph-cli[inmem]\""
echo "   langgraph dev"
echo ""
echo "2. In a new terminal, ingest test emails:"
echo "   python scripts/run_ingest.py --minutes-since 120 --rerun 1 --early 0"
echo ""
echo "3. View results at:"
echo "   https://dev.agentinbox.ai/"
echo ""
echo "See SETUP_GUIDE.md for detailed usage instructions."
echo ""
