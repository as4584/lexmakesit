#!/bin/bash
# Start DonXEra Inventory Manager with automatic ngrok tunnel

echo "🚀 Starting DonXEra Inventory Manager..."
echo ""

cd "$(dirname "$0")/.."

# Load environment variables from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Set required environment
export PYTHONPATH=src
export DEMO_MODE=true
export ENABLE_NGROK=true

# Start the app (ngrok will start automatically)
python3 scripts/run_local.py
