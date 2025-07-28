import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', './bot_database.db')
    
    # Admin Configuration
    ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')  # Changed from ADMIN_GROUP_ID
    
    # Role Configuration - User IDs for each role (individual accounts)
    ROLE_USERS = {
        'ROLE_SECRETARY_USER_ID': os.getenv('ROLE_SECRETARY_USER_ID'),      # دبیر
        'ROLE_LEGAL_USER_ID': os.getenv('ROLE_LEGAL_USER_ID'),              # نائب دبیر/مسئول حقوقی
        'ROLE_EDUCATIONAL_1_USER_ID': os.getenv('ROLE_EDUCATIONAL_1_USER_ID'), # مسئول آموزش ۱
        'ROLE_EDUCATIONAL_2_USER_ID': os.getenv('ROLE_EDUCATIONAL_2_USER_ID'), # مسئول آموزش ۲
        'ROLE_PUBLICATION_USER_ID': os.getenv('ROLE_PUBLICATION_USER_ID'),   # مسئول نشریه
    }
    
    # Bot Settings
    MAX_MESSAGE_LENGTH = 4096
    MAX_MESSAGES_PER_10_MINUTES = 5  # Limit messages per user per 10 minutes per role
    
    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        missing_configs = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            missing_configs.append('TELEGRAM_BOT_TOKEN')
        
        if not cls.ADMIN_USER_ID:
            missing_configs.append('ADMIN_USER_ID')
        
        # Check if at least one role user is configured
        role_users_configured = any(cls.ROLE_USERS.values())
        if not role_users_configured:
            missing_configs.append('At least one role user ID')
        
        if missing_configs:
            raise ValueError(f"Missing required configuration: {', '.join(missing_configs)}")
        
        return True
    
    @classmethod
    def get_role_user_id(cls, role_user_key: str) -> str:
        """Get the actual user ID for a role"""
        return cls.ROLE_USERS.get(role_user_key) 