#!/bin/bash

# Start bot script
echo "🚀 Starting Enhanced Council Bot..."

# Check if bot is already running
if pgrep -f "python3 enhanced_bot.py" > /dev/null; then
    echo "⚠️  Bot is already running!"
    echo "📋 Current bot processes:"
    ps aux | grep "python3 enhanced_bot.py" | grep -v grep
    echo ""
    echo "💡 Use './scripts/stop_bot.sh' to stop the bot first"
    exit 1
fi

# Check for orphaned lock file
if [ -f "bot.lock" ]; then
    echo "⚠️  Found orphaned lock file. Cleaning up..."
    rm -f bot.lock
fi

# Check if enhanced_bot.py exists
if [ ! -f "enhanced_bot.py" ]; then
    echo "❌ enhanced_bot.py not found in current directory"
    exit 1
fi

# Start the bot
echo "🔄 Starting bot process..."
nohup python3 enhanced_bot.py > bot.log 2>&1 &

# Wait a moment for the bot to start
sleep 3

# Check if bot started successfully
if pgrep -f "python3 enhanced_bot.py" > /dev/null; then
    echo "✅ Bot started successfully!"
    echo "📋 Process details:"
    ps aux | grep "python3 enhanced_bot.py" | grep -v grep
    
    if [ -f "bot.lock" ]; then
        echo ""
        echo "🔒 Lock file created:"
        cat bot.lock
    fi
    
    echo ""
    echo "📝 Logs are being written to: bot.log"
    echo "💡 Use './scripts/check_bot_status.sh' to check status"
else
    echo "❌ Failed to start bot"
    echo "📝 Check bot.log for error details:"
    if [ -f "bot.log" ]; then
        tail -10 bot.log
    fi
    exit 1
fi 