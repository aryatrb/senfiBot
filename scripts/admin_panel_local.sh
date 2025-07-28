#!/bin/bash

# Council Bot - Local Admin Panel Script
# This script provides admin functionality locally

echo "👨‍💼 Council Bot Admin Panel"

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "📁 Project directory: $PROJECT_ROOT"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found in $PROJECT_ROOT"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Check database status
echo "🗄️ Checking database status..."
python3 -c "
from database import Database
try:
    db = Database()
    print('✅ Database connection successful')
    print('📊 Database file:', db.db_path)
except Exception as e:
    print('❌ Database error:', e)
"

# Check bot configuration
echo "🤖 Checking bot configuration..."
python3 -c "
import os
from config import Config
try:
    config = Config()
    print('✅ Configuration loaded successfully')
    print('🔑 Bot token configured:', 'Yes' if config.TELEGRAM_BOT_TOKEN else 'No')
    print('👤 Admin ID configured:', 'Yes' if config.ADMIN_USER_ID else 'No')
except Exception as e:
    print('❌ Configuration error:', e)
"

echo "✅ Admin panel check completed!" 