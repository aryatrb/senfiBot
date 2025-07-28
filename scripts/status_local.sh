#!/bin/bash

# Council Bot - Local Status Script
# This script checks the status of the bot and services

echo "📊 Council Bot Status Check"
echo "=========================="

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "📁 Project directory: $PROJECT_ROOT"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment exists"
else
    echo "❌ Virtual environment not found"
fi

# Check if .env file exists
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    
    # Check if bot token is configured
    if grep -q "your_bot_token_here" .env; then
        echo "⚠️  Bot token not configured (using placeholder)"
    else
        echo "✅ Bot token configured"
    fi
    
    # Check if admin user ID is configured
    if grep -q "your_admin_user_id_here" .env; then
        echo "⚠️  Admin user ID not configured (using placeholder)"
    else
        echo "✅ Admin user ID configured"
    fi
else
    echo "❌ .env file not found"
fi

# Check if database exists
if [ -f "bot_database.db" ]; then
    echo "✅ Database exists"
    
    # Check database size
    db_size=$(du -h bot_database.db | cut -f1)
    echo "📊 Database size: $db_size"
else
    echo "❌ Database not found"
fi

# Check if bot is running as systemd service
echo ""
echo "🖥️ Systemd Service Status:"
if systemctl is-active --quiet councilbot; then
    echo "✅ Bot service is running"
    
    # Check recent logs
    echo ""
    echo "📋 Recent Logs (last 5 lines):"
    sudo journalctl -u councilbot --no-pager -n 5
else
    echo "❌ Bot service is not running"
fi

echo ""
echo "🔧 Available Commands:"
echo "• ./run_bot.sh - Run bot locally"
echo "• ./test_local.sh - Test bot locally"
echo "• ./admin_panel_local.sh - Run admin panel"
echo "• ./deploy_local.sh - Deploy to VPS"
echo "• ./setup_local.sh - Setup development environment" 