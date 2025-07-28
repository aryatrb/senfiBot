#!/bin/bash

# Update .env file with correct configuration
sudo tee /opt/councilbot/.env > /dev/null <<EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=xxxx

# Database Configuration
DATABASE_PATH=./bot_database.db

# Admin Configuration
ADMIN_USER_ID=xxxx

# Role Configuration - Individual User IDs
ROLE_LEGAL_USER_ID=your_legal_user_id_here
ROLE_EDUCATIONAL_USER_ID=your_educational_user_id_here
ROLE_WELFARE_USER_ID=your_welfare_user_id_here
ROLE_CULTURAL_USER_ID=your_cultural_user_id_here
ROLE_SPORTS_USER_ID=your_sports_user_id_here
EOF

# Set correct permissions
sudo chown councilbot:councilbot /opt/councilbot/.env
sudo chmod 600 /opt/councilbot/.env

echo "✅ .env file updated successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Update the user IDs in /opt/councilbot/.env"
echo "2. Restart the bot: sudo systemctl restart councilbot"
echo "3. Check status: sudo systemctl status councilbot" 