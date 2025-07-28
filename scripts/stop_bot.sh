#!/bin/bash

# Stop bot script
echo "🛑 Stopping Enhanced Council Bot..."

# Check if bot is running
if pgrep -f "python3 enhanced_bot.py" > /dev/null; then
    echo "📋 Found running bot processes:"
    ps aux | grep "python3 enhanced_bot.py" | grep -v grep
    
    echo ""
    echo "🔄 Stopping bot processes..."
    
    # Kill all bot processes
    pkill -f "python3 enhanced_bot.py"
    
    # Wait a moment for processes to stop
    sleep 2
    
    # Check if processes are still running
    if pgrep -f "python3 enhanced_bot.py" > /dev/null; then
        echo "⚠️  Some processes are still running. Force killing..."
        pkill -9 -f "python3 enhanced_bot.py"
        sleep 1
    fi
    
    # Check final status
    if pgrep -f "python3 enhanced_bot.py" > /dev/null; then
        echo "❌ Failed to stop all bot processes"
        exit 1
    else
        echo "✅ Bot stopped successfully"
        
        # Clean up lock file if it exists
        if [ -f "bot.lock" ]; then
            echo "🧹 Cleaning up lock file..."
            rm -f bot.lock
        fi
    fi
else
    echo "ℹ️  No bot processes found running"
    
    # Clean up orphaned lock file
    if [ -f "bot.lock" ]; then
        echo "🧹 Cleaning up orphaned lock file..."
        rm -f bot.lock
    fi
fi

echo ""
echo "📋 Bot status:"
./scripts/check_bot_status.sh 