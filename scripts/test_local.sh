#!/bin/bash

# Council Bot - Local Test Script
# This script tests the bot functionality locally

echo "🧪 Testing Council Bot locally..."

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

# Test database functionality
echo "🗄️ Testing database functionality..."
python3 -c "
from database import Database
try:
    db = Database()
    print('✅ Database initialization successful')
    
    # Test basic operations
    db.init_database()
    print('✅ Database tables created successfully')
    
    # Test role operations
    roles = db.get_all_roles()
    print(f'✅ Found {len(roles)} roles in database')
    
except Exception as e:
    print('❌ Database test failed:', e)
"

# Test configuration
echo "⚙️ Testing configuration..."
python3 -c "
from config import Config
try:
    config = Config()
    print('✅ Configuration loaded successfully')
    print(f'🔑 Bot token: {config.TELEGRAM_BOT_TOKEN[:10]}...' if config.TELEGRAM_BOT_TOKEN else '❌ Bot token not configured')
    print(f'👤 Admin ID: {config.ADMIN_USER_ID}' if config.ADMIN_USER_ID else '❌ Admin ID not configured')
except Exception as e:
    print('❌ Configuration test failed:', e)
"

# Test bot imports
echo "🤖 Testing bot imports..."
python3 -c "
try:
    from enhanced_bot import CouncilBot
    print('✅ Bot module imports successfully')
except Exception as e:
    print('❌ Bot import failed:', e)
"

echo "✅ All tests completed!" 