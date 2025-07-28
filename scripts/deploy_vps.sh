#!/bin/bash

# Council Bot - VPS Deployment Script
# This script deploys the bot to VPS using the project directory

set -e

echo "🚀 Deploying Council Bot to VPS..."

# Get the project root directory (parent of scripts directory)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "📁 Project directory: $PROJECT_DIR"

# Check if .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "❌ Error: .env file not found in $PROJECT_DIR"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

# Activate virtual environment and install/update dependencies
echo "📦 Installing/updating dependencies..."
source "$PROJECT_DIR/venv/bin/activate"
pip install -r "$PROJECT_DIR/requirements.txt"

# Create systemd service file
echo "📝 Creating systemd service..."
sudo tee /etc/systemd/system/councilbot.service > /dev/null <<EOF
[Unit]
Description=Council Bot Telegram Bot
After=network.target

[Service]
Type=simple
User=arya
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/enhanced_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Stop existing service if running
echo "⏹️ Stopping existing service..."
sudo systemctl stop councilbot || true

# Enable and start service
echo "▶️ Starting bot service..."
sudo systemctl enable councilbot
sudo systemctl start councilbot

# Wait a moment for service to start
sleep 3

# Check status
echo "📊 Checking service status..."
sudo systemctl status councilbot --no-pager

echo "✅ Deployment completed!"
echo ""
echo "🔧 Useful commands:"
echo "• sudo systemctl status councilbot"
echo "• sudo systemctl restart councilbot"
echo "• sudo journalctl -u councilbot -f"
echo "• sudo systemctl stop councilbot" 