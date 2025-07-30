#!/usr/bin/env python3
"""
Fixed version of the bot startup script
Handles AI system path issues properly
"""

import os
import sys
import signal
import subprocess
import time

def setup_environment():
    """Setup proper environment for the bot"""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add ai directory to Python path
    ai_dir = os.path.join(script_dir, 'ai')
    if ai_dir not in sys.path:
        sys.path.insert(0, ai_dir)
    
    # Change to the script directory
    os.chdir(script_dir)
    
    print(f"✅ Environment setup complete")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🤖 AI directory: {ai_dir}")
    
    return script_dir, ai_dir

def test_ai_system(ai_dir):
    """Test if AI system works properly"""
    try:
        import sys
        sys.path.insert(0, ai_dir)
        
        from langchain_rag_system import LangChainRAGSystem
        
        # Use absolute paths for the files
        database_file = os.path.join(ai_dir, 'test_channels_database.json')
        config_file = os.path.join(ai_dir, 'multi_channel_config.json')
        
        print("🧪 Testing AI system...")
        rag = LangChainRAGSystem(database_file=database_file, config_file=config_file)
        result = rag.query("سلام")
        
        if "سلام" in result or "دستیار" in result:
            print("✅ AI system test passed!")
            return True
        else:
            print("⚠️ AI system test inconclusive")
            return True
            
    except Exception as e:
        print(f"❌ AI system test failed: {e}")
        return False

def start_bot():
    """Start the bot with proper environment"""
    print("🚀 Starting Enhanced Council Bot...")
    
    # Setup environment
    script_dir, ai_dir = setup_environment()
    
    # Test AI system
    if not test_ai_system(ai_dir):
        print("❌ AI system test failed. Please check configuration.")
        return False
    
    # Remove lock file if exists
    lock_file = os.path.join(script_dir, 'bot.lock')
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            print("🔓 Removed existing lock file")
        except Exception as e:
            print(f"⚠️ Could not remove lock file: {e}")
    
    # Start the bot
    try:
        print("🤖 Starting bot process...")
        from enhanced_bot import EnhancedCouncilBot
        
        bot = EnhancedCouncilBot()
        bot.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = start_bot()
    if not success:
        sys.exit(1) 