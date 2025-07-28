#!/bin/bash

# Check bot status script
echo "🤖 Enhanced Council Bot Status Check"
echo "=================================="

# Check if bot process is running
if pgrep -f "python3 enhanced_bot.py" > /dev/null; then
    echo "✅ Bot is running"
    echo "Process details:"
    ps aux | grep "python3 enhanced_bot.py" | grep -v grep
    echo ""
    
    # Check lock file
    if [ -f "bot.lock" ]; then
        echo "🔒 Lock file exists:"
        cat bot.lock
    else
        echo "⚠️  Lock file missing (bot may not be properly locked)"
    fi
else
    echo "❌ Bot is not running"
    
    # Check if lock file exists (orphaned)
    if [ -f "bot.lock" ]; then
        echo "⚠️  Orphaned lock file found:"
        cat bot.lock
        echo ""
        echo "💡 To clean up, run: rm bot.lock"
    fi
fi

echo ""
echo "📋 Available commands:"
echo "  ./scripts/run_bot.sh      - Start the bot"
echo "  ./scripts/stop_bot.sh     - Stop the bot"
echo "  ./scripts/restart_bot.sh  - Restart the bot" 