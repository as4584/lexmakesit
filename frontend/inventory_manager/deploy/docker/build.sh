#!/bin/bash
# DonXEra Inventory Manager - Docker Build & Run Script

set -e

echo "🖤 DonXEra Inventory Manager - Docker Setup"
echo "============================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "📥 Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker found!"
echo ""

# Build the image
echo "🔨 Building Docker image..."
docker build -t donxera-inventory .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "🚀 To run the container:"
    echo "   docker run -p 8000:8000 donxera-inventory"
    echo ""
    echo "🌐 Then open: http://localhost:8000"
    echo ""
    echo "📖 For more options, see DOCKER_README.md"
else
    echo ""
    echo "❌ Build failed! Check the error messages above."
    exit 1
fi
