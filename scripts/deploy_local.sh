#!/bin/bash

# Council Bot - Local Deploy Script
# This script deploys the bot to VPS from the project folder

echo "🚀 Deploying Council Bot to VPS..."

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "📁 Project directory: $PROJECT_ROOT"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if .env file exists in project root
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found in $PROJECT_ROOT"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Check if deploy_vps.sh exists
if [ ! -f "scripts/deploy_vps.sh" ]; then
    echo "❌ Error: scripts/deploy_vps.sh not found!"
    exit 1
fi

# Make deploy script executable
chmod +x scripts/deploy_vps.sh

# Run deployment
echo "📤 Starting deployment..."
./scripts/deploy_vps.sh

echo "✅ Deployment completed!" 