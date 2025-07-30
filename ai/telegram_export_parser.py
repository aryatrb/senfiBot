#!/usr/bin/env python3
"""
Telegram Export Parser
Parses Telegram Desktop export files to extract all messages
Supports both directory structure and direct JSON files
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramExportParser:
    def __init__(self, export_dir: str = "telegram_export"):
        """
        Initialize parser with export directory
        """
        self.export_dir = export_dir
    
    def parse_export(self) -> Dict[str, Any]:
        """
        Parse Telegram export directory or direct JSON files
        """
        try:
            if not os.path.exists(self.export_dir):
                logger.error(f"Export directory {self.export_dir} not found!")
                logger.info("Please export your Telegram data from Telegram Desktop")
                return {}
            
            channels = {}
            
            # Look for JSON files directly in the directory
            for item in os.listdir(self.export_dir):
                item_path = os.path.join(self.export_dir, item)
                
                if item.endswith('.json') and os.path.isfile(item_path):
                    # Direct JSON file
                    channel_name = os.path.splitext(item)[0]
                    channel_data = self.parse_json_file(channel_name, item_path)
                    if channel_data:
                        channels[channel_name] = channel_data
                elif os.path.isdir(item_path):
                    # Check if it's a channel directory (has messages.json)
                    messages_file = os.path.join(item_path, "messages.json")
                    if os.path.exists(messages_file):
                        channel_data = self.parse_channel(item, item_path)
                        if channel_data:
                            channels[item] = channel_data
            
            return channels
            
        except Exception as e:
            logger.error(f"Error parsing export: {e}")
            return {}
    
    def parse_channel(self, channel_name: str, channel_dir: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single channel directory
        """
        try:
            messages_file = os.path.join(channel_dir, "messages.json")
            
            with open(messages_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = []
            
            # Parse messages
            for msg in data.get('messages', []):
                if msg.get('type') == 'message' and msg.get('text'):
                    # Handle different text formats
                    text = msg['text']
                    if isinstance(text, list):
                        # Text is a list of text entities
                        text = ' '.join([item.get('text', '') for item in text if isinstance(item, dict)])
                    elif isinstance(text, str):
                        text = text.strip()
                    else:
                        continue
                    
                    if text and len(text) > 5:  # Filter out very short messages
                        messages.append({
                            "id": str(msg.get('id', 'unknown')),
                            "text": text,
                            "date": msg.get('date', datetime.now().isoformat()),
                            "from": msg.get('from', 'Channel'),
                            "views": msg.get('views', 0),
                            "type": "message"
                        })
            
            if messages:
                channel_data = {
                    "username": channel_name,
                    "name": channel_name,
                    "description": "",
                    "exported_at": datetime.now().isoformat(),
                    "total_messages": len(messages),
                    "messages": messages,
                    "source": "telegram_desktop_export"
                }
                
                logger.info(f"Parsed {channel_name}: {len(messages)} messages")
                return channel_data
            else:
                logger.warning(f"No messages found in {channel_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing channel {channel_name}: {e}")
            return None
    
    def parse_json_file(self, channel_name: str, json_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a direct JSON file (Telegram export format)
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = []
            
            # Parse messages
            for msg in data.get('messages', []):
                if msg.get('type') == 'message' and msg.get('text'):
                    # Handle different text formats
                    text = msg['text']
                    if isinstance(text, list):
                        # Text is a list of text entities
                        text = ' '.join([item.get('text', '') for item in text if isinstance(item, dict)])
                    elif isinstance(text, str):
                        text = text.strip()
                    else:
                        continue
                    
                    if text and len(text) > 5:  # Filter out very short messages
                        messages.append({
                            "id": str(msg.get('id', 'unknown')),
                            "text": text,
                            "date": msg.get('date', datetime.now().isoformat()),
                            "from": msg.get('from', 'Channel'),
                            "views": msg.get('views', 0),
                            "type": "message"
                        })
            
            if messages:
                channel_data = {
                    "username": channel_name,
                    "name": data.get('name', channel_name),
                    "description": "",
                    "exported_at": datetime.now().isoformat(),
                    "total_messages": len(messages),
                    "messages": messages,
                    "source": "telegram_desktop_export"
                }
                
                logger.info(f"Parsed {channel_name}: {len(messages)} messages")
                return channel_data
            else:
                logger.warning(f"No messages found in {channel_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing JSON file {channel_name}: {e}")
            return None
    
    def save_parsed_data(self, channels: Dict[str, Any], output_file: str = "parsed_telegram_export.json"):
        """
        Save parsed data to file
        """
        try:
            data = {
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "total_channels": len(channels),
                    "total_messages": sum(len(ch['messages']) for ch in channels.values()),
                    "source": "telegram_desktop_export"
                },
                "channels": channels
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Parsed data saved to {output_file}")
            return data
            
        except Exception as e:
            logger.error(f"Error saving parsed data: {e}")
            return None

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parse Telegram Desktop export")
    parser.add_argument("--export-dir", default="telegram_export", help="Export directory path")
    parser.add_argument("--output", default="parsed_telegram_export.json", help="Output file")
    
    args = parser.parse_args()
    
    parser = TelegramExportParser(args.export_dir)
    channels = parser.parse_export()
    
    if channels:
        data = parser.save_parsed_data(channels, args.output)
        
        if data:
            print(f"\n📊 Parse Summary:")
            print(f"Channels found: {data['metadata']['total_channels']}")
            print(f"Total messages: {data['metadata']['total_messages']}")
            
            for username, channel in channels.items():
                print(f"  @{username}: {len(channel['messages'])} messages")
    else:
        print("❌ No channels were parsed successfully")
        print("💡 Make sure you have exported your Telegram data from Telegram Desktop")

if __name__ == "__main__":
    main() 