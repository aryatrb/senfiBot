#!/bin/bash

# Restart bot script
echo "🔄 Restarting Enhanced Council Bot..."

# Stop the bot first
echo "🛑 Stopping bot..."
./scripts/stop_bot.sh

# Wait a moment
sleep 2

# Start the bot
echo ""
echo "🚀 Starting bot..."
./scripts/start_bot.sh

echo ""
echo "✅ Bot restart completed!" 