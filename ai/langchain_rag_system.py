#!/usr/bin/env python3
"""
LangChain RAG System with Tools
Uses LangChain tools to search channels incrementally
"""

import os
import json
import re
from typing import List, Dict, Any, Tuple, Optional
import openai
from dotenv import load_dotenv
from datetime import datetime
import time

# Load environment variables
load_dotenv()

# Configure OpenAI client
openai.api_key = os.getenv('GEMINI_API_KEY')
openai.base_url = os.getenv('GEMINI_BASE_URL', 'https://api.gapgpt.app/v1')

class LangChainRAGSystem:
    def __init__(self, database_file: str = "test_channels_database.json", config_file: str = "multi_channel_config.json"):
        self.database_file = database_file
        self.config_file = config_file
        self.database = self.load_database()
        self.config = self.load_config()
        self.active_channels = [ch for ch in self.config['channels'] if ch['active']]
        self.embedding_cache = {}  # Cache for embeddings
        
        # Initialize LangChain components
        self.initialize_langchain()
        
    def initialize_langchain(self):
        """Initialize LangChain components"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain.tools import Tool
            from langchain.agents import AgentExecutor, create_openai_tools_agent
            from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
            from sentence_transformers import SentenceTransformer
            
            # Initialize sentence transformer for semantic search - using faster model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Initialize LLM
            self.llm = ChatOpenAI(
                model="gemini-2.5-flash",
                temperature=0.7,
                api_key=openai.api_key,
                base_url=openai.base_url
            )
            
            # Create tools
            self.tools = self.create_tools()
            
            # Create agent
            self.agent = self.create_agent()
            
            print("✅ LangChain system initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing LangChain: {e}")
            print("⚠️ Falling back to basic search")
            self.llm = None
            self.agent = None
    
    def create_tools(self) -> List:
        """Create LangChain tools for searching channels"""
        from langchain.tools import StructuredTool
        from pydantic import BaseModel, Field
        
        class SearchChannelsInput(BaseModel):
            query: str = Field(description="Query to search for relevant channels")
        
        class SearchMessagesInput(BaseModel):
            channel_username: str = Field(description="Username of the channel to search in")
            query: str = Field(description="Query to search for in the channel")
        
        class GetChannelInfoInput(BaseModel):
            channel_username: str = Field(description="Username of the channel to get info for")
        
        class ExpandSearchInput(BaseModel):
            current_channels: str = Field(description="Comma-separated list of current channels")
            query: str = Field(description="Query to expand search for")
        
        tools = [
            StructuredTool.from_function(
                func=self.search_relevant_channels,
                name="search_channels",
                description="Search for relevant channels based on a query. Returns list of channel usernames.",
                args_schema=SearchChannelsInput
            ),
            StructuredTool.from_function(
                func=self.search_messages_in_channel,
                name="search_messages_in_channel",
                description="Search for messages in a specific channel. Returns relevant messages.",
                args_schema=SearchMessagesInput
            ),
            StructuredTool.from_function(
                func=self.get_channel_info,
                name="get_channel_info",
                description="Get information about a specific channel. Returns channel details.",
                args_schema=GetChannelInfoInput
            ),
            StructuredTool.from_function(
                func=self.expand_search,
                name="expand_search",
                description="Expand search to more channels if current results are insufficient. Returns additional channels.",
                args_schema=ExpandSearchInput
            )
        ]
        
        return tools
    
    def create_agent(self):
        """Create LangChain agent"""
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain.agents import create_openai_tools_agent, AgentExecutor
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """شما یک دستیار هوشمند دانشگاه شریف هستید که بر اساس اطلاعات موجود در کانال‌های تلگرام دانشگاه پاسخ می‌دهید.

**اصول پاسخ‌دهی:**
- همیشه بی‌طرف، عینی و علمی باشید
- فقط بر اساس اطلاعات موجود در دیتابیس پاسخ دهید
- از اظهار نظر شخصی یا جانب‌داری پرهیز کنید
- اطلاعات را به صورت جامع و منظم ارائه دهید

**استراتژی جستجو:**
1. ابتدا کانال‌های اولویت‌دار را بررسی کنید: sharifdaily و sharif_senfi
2. سپس حداقل 2-3 کانال دیگر مرتبط را جستجو کنید
3. اگر اطلاعات کافی نیست، با expand_search کانال‌های بیشتری اضافه کنید
4. همیشه حداقل 3 کانال مختلف را بررسی کنید

**فرمت پاسخ:**
پاسخ خود را به این شکل ارائه دهید:

**عنوان اصلی** (نام شخص، موضوع یا رویداد)

بر اساس اطلاعات موجود در کانال‌های تلگرامی دانشگاه شریف:

**بخش‌های مرتبط:**
• نکته اول
• نکته دوم
• نکته سوم

**مسائل مرتبط:**
• موضوع اول
• موضوع دوم

**منابع مرتبط:**
1. [نام کانال](https://t.me/channel_username/message_id)
2. [نام کانال](https://t.me/channel_username/message_id)

**نکات مهم:**
- از پیام‌های با امتیاز بالای 0.6 استفاده کنید
- حداکثر 15 پیام برتر از هر کانال را در نظر بگیرید
- لینک‌ها را به فرمت https://t.me/channel_username/message_id ارائه دهید
- پاسخ جامع و کامل بدهید
- اطلاعات را به بخش‌های منطقی تقسیم کنید

**لحن و سبک:**
- از لحن علمی و دانشگاهی استفاده کنید
- اطلاعات را به صورت منظم و ساختاریافته ارائه دهید
- از جملات کوتاه و واضح استفاده کنید
- همیشه منابع را ذکر کنید

ابزارهای موجود:
- search_channels: برای پیدا کردن کانال‌های مرتبط
- search_messages_in_channel: برای جستجو در پیام‌های یک کانال
- get_channel_info: برای دریافت اطلاعات کانال
- expand_search: برای گسترش جستجو

لطفاً به فارسی پاسخ دهید."""),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
        
        return agent_executor
    
    def search_relevant_channels(self, query: str) -> str:
        """Search for relevant channels based on query with priority channels"""
        try:
            # Priority channels that should always be checked first
            priority_channels = ['sharifdaily', 'sharif_senfi']
            
            # Use semantic search to find relevant channels
            query_embedding = self.embedding_model.encode(query)
            
            channel_scores = []
            priority_found = []
            
            # Batch encode channel texts for better performance
            channel_texts = []
            channel_names = []
            
            for channel in self.active_channels:
                channel_text = f"{channel['name']} {channel['description']}"
                channel_texts.append(channel_text)
                channel_names.append(channel['username'])
                
                # Check if it's a priority channel
                if channel['username'] in priority_channels:
                    priority_found.append(channel['username'])
            
            # Batch encode all channel texts at once
            if channel_texts:
                channel_embeddings = self.embedding_model.encode(channel_texts)
                
                for i, username in enumerate(channel_names):
                    similarity = self.cosine_similarity(query_embedding, channel_embeddings[i])
                    channel_scores.append((username, similarity))
            
            # Sort by similarity
            channel_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Start with priority channels, then add top semantic matches
            result_channels = []
            
            # Add priority channels first (if they exist in active channels)
            for priority_ch in priority_channels:
                if priority_ch in priority_found:
                    result_channels.append(priority_ch)
            
            # Add top semantic matches (excluding priority channels already added)
            for username, score in channel_scores:
                if username not in result_channels and len(result_channels) < 8:  # Keep total around 10
                    result_channels.append(username)
            
            return f"کانال‌های مرتبط (اولویت + معنایی): {', '.join(result_channels)}"
            
        except Exception as e:
            return f"خطا در جستجوی کانال‌ها: {e}"
    

    
    def search_messages_in_channel(self, channel_username: str, query: str) -> str:
        """Search for messages in a specific channel"""
        try:
            # Handle channel name variations and fuzzy matching
            if channel_username not in self.database['channels']:
                # Try to find similar channel names
                available_channels = list(self.database['channels'].keys())
                similar_channels = []
                
                # Check for common variations
                variations = {
                    'یاریگران': 'yarigaran_sharif',
                    'yaregaran': 'yarigaran_sharif',  # Common misspelling
                    'yareegaran': 'yarigaran_sharif',  # Another common misspelling
                    'yari': 'yarigaran_sharif',
                    'شریف': 'sharif_senfi',
                    'شورای صنفی': 'sharif_senfi',
                    'روزنامه': 'sharifdaily',
                    'daily': 'sharifdaily'
                }
                
                # Check if there's a direct variation match
                if channel_username in variations:
                    suggested_channel = variations[channel_username]
                    if suggested_channel in self.database['channels']:
                        # Automatically search in the suggested channel instead of just suggesting
                        print(f"🔄 Redirecting from '{channel_username}' to '{suggested_channel}'")
                        return self.search_messages_in_channel(suggested_channel, query)
                
                # Also check for partial matches in variations
                for variation, suggested_channel in variations.items():
                    if variation in channel_username or channel_username in variation:
                        if suggested_channel in self.database['channels']:
                            print(f"🔄 Redirecting from '{channel_username}' to '{suggested_channel}' (partial match)")
                            return self.search_messages_in_channel(suggested_channel, query)
                
                # Find similar channel names
                for available in available_channels:
                    if channel_username.lower() in available.lower() or available.lower() in channel_username.lower():
                        similar_channels.append(available)
                
                # Check if there's a very close match that we should automatically redirect to
                if similar_channels:
                    # If we have a very close match, automatically redirect
                    best_match = similar_channels[0]
                    if (channel_username.lower() in best_match.lower() or 
                        best_match.lower() in channel_username.lower() or
                        any(variation in channel_username.lower() for variation in ['یاریگران', 'yaregaran', 'yareegaran', 'yari'])):
                        print(f"🔄 Auto-redirecting from '{channel_username}' to '{best_match}'")
                        return self.search_messages_in_channel(best_match, query)
                
                # Only show error if no automatic redirect was possible
                error_msg = f"کانال '{channel_username}' در دیتابیس موجود نیست."
                
                if similar_channels:
                    error_msg += f"\n\nکانال‌های مشابه موجود:\n"
                    for ch in similar_channels[:5]:  # Show up to 5 suggestions
                        error_msg += f"• {ch}\n"
                
                error_msg += f"\n\nکانال‌های اصلی موجود:\n"
                main_channels = ['sharif_senfi', 'sharifdaily', 'yarigaran_sharif', 'sh_counseling']
                for ch in main_channels:
                    if ch in available_channels:
                        error_msg += f"• {ch}\n"
                
                return error_msg
            
            channel_data = self.database['channels'][channel_username]
            messages = channel_data.get('messages', [])
            
            # Search through ALL messages (no limit)
            print(f"🔍 جستجو در کل {len(messages)} پیام کانال {channel_username}...")
            
            if not messages:
                return f"هیچ پیامی در کانال {channel_username} یافت نشد"
            
            # Fast keyword search through ALL messages
            query_words = query.lower().split()
            message_scores = []
            
            print(f"🔍 جستجوی کلیدواژه در {len(messages)} پیام...")
            found_exact = 0
            found_all_words = 0
            
            for i, msg in enumerate(messages):
                if i % 2000 == 0:  # Progress indicator every 2000 messages
                    print(f"   پیشرفت: {i}/{len(messages)} ({i/len(messages)*100:.1f}%)")
                
                text = msg.get('text', '')
                if text and len(text) > 10:
                    text_lower = text.lower()
                    
                    # Check for exact phrase match first (highest priority)
                    if query.lower() in text_lower:
                        score = 0.95
                        message_scores.append((msg, score))
                        found_exact += 1
                        # Early termination if we have enough exact matches
                        if found_exact >= 20:
                            print(f"   ✅ {found_exact} تطبیق دقیق یافت شد - توقف زودهنگام")
                            break
                    # Check for all words present (medium priority)
                    elif all(word in text_lower for word in query_words if len(word) > 2):
                        score = 0.8
                        message_scores.append((msg, score))
                        found_all_words += 1
                        # Early termination if we have enough good matches
                        if found_all_words >= 50:
                            print(f"   ✅ {found_all_words} تطبیق خوب یافت شد - توقف زودهنگام")
                            break
                    # Check for partial matches (lower priority)
                    elif any(word in text_lower for word in query_words if len(word) > 2):
                        score = 0.6
                        message_scores.append((msg, score))
            
            # If still not enough results, do semantic search on ALL messages
            if len(message_scores) < 10:
                print("🔍 جستجوی معنایی در کل پیام‌ها...")
                query_embedding = self.embedding_model.encode(query)
                
                semantic_candidates = []
                for msg in messages:
                    text = msg.get('text', '')
                    if text and len(text) > 30:  # Only longer texts
                        semantic_candidates.append((msg, text[:200]))  # Limit text length
                
                if semantic_candidates:
                    print(f"   🔍 محاسبه embedding برای {len(semantic_candidates)} پیام...")
                    texts_to_encode = [text for _, text in semantic_candidates]
                    embeddings = self.embedding_model.encode(texts_to_encode)
                    
                    semantic_found = 0
                    for i, (msg, _) in enumerate(semantic_candidates):
                        similarity = self.cosine_similarity(query_embedding, embeddings[i])
                        if similarity > 0.4:  # Higher threshold
                            message_scores.append((msg, similarity))
                            semantic_found += 1
                            if semantic_found >= 20:  # Limit semantic results
                                break
                    
                    print(f"   ✅ {semantic_found} نتیجه معنایی یافت شد")
            
            # Sort by similarity
            message_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Check if we found relevant information (similarity > 0.3 for keyword matches, 0.5 for semantic)
            relevant_messages = [msg for msg, score in message_scores if score > 0.5 or (score > 0.3 and any(word in msg.get('text', '').lower() for word in query.lower().split()))]
            
            result = f"پیام‌های مرتبط در کانال {channel_username}:\n\n"
            
            if relevant_messages:
                # Limit to top 15 most relevant messages to avoid overwhelming responses
                top_messages = message_scores[:15]
                result += f"✅ اطلاعات مرتبط یافت شد! ({len(top_messages)} پیام از {len(relevant_messages)} پیام مرتبط)\n\n"
                
                for i, (msg, score) in enumerate(top_messages, 1):
                    text = msg.get('text', '')[:300]  # Show more text
                    date = msg.get('date', 'نامشخص')
                    msg_id = msg.get('id', 'نامشخص')
                    channel_username = msg.get('channel', msg.get('channel_name', channel_username))
                    
                    result += f"{i}. امتیاز: {score:.3f} | تاریخ: {date}\n"
                    result += f"   متن: {text}"
                    if len(msg.get('text', '')) > 300:
                        result += "..."
                    result += f"\n   🔗 لینک: https://t.me/{channel_username}/{msg_id}\n\n"
                
                # Add note about total results if there are more
                if len(relevant_messages) > 15:
                    result += f"📝 توجه: {len(relevant_messages) - 15} پیام مرتبط دیگر نیز یافت شد که برای خلاصگی نمایش داده نشد.\n\n"
            else:
                highest_score = message_scores[0][1] if message_scores else 0
                result += f"❌ اطلاعات مرتبط یافت نشد (بالاترین امتیاز: {highest_score:.3f})\n\n"
                # Show top 10 for debugging
                for i, (msg, score) in enumerate(message_scores[:10], 1):
                    text = msg.get('text', '')[:200]
                    date = msg.get('date', 'نامشخص')
                    msg_id = msg.get('id', 'نامشخص')
                    channel_username = msg.get('channel', msg.get('channel_name', channel_username))
                    
                    result += f"{i}. امتیاز: {score:.3f} | تاریخ: {date}\n"
                    result += f"   متن: {text}"
                    if len(msg.get('text', '')) > 200:
                        result += "..."
                    result += f"\n   🔗 لینک: https://t.me/{channel_username}/{msg_id}\n\n"
            
            return result
            
        except Exception as e:
            return f"خطا در جستجوی پیام‌ها: {e}"
    
    def get_channel_info(self, channel_username: str) -> str:
        """Get information about a specific channel"""
        try:
            if channel_username not in self.database['channels']:
                return f"کانال {channel_username} در دیتابیس موجود نیست"
            
            channel_data = self.database['channels'][channel_username]
            config_info = next((ch for ch in self.active_channels if ch['username'] == channel_username), None)
            
            result = f"اطلاعات کانال {channel_username}:\n"
            result += f"نام: {channel_data.get('name', 'نامشخص')}\n"
            result += f"تعداد پیام‌ها: {len(channel_data.get('messages', []))}\n"
            
            if config_info:
                result += f"توضیحات: {config_info.get('description', 'نامشخص')}\n"
                result += f"اولویت: {config_info.get('priority', 'نامشخص')}\n"
            
            return result
            
        except Exception as e:
            return f"خطا در دریافت اطلاعات کانال: {e}"
    
    def expand_search(self, current_channels: str, query: str) -> str:
        """Expand search to more channels - 5 at a time"""
        try:
            # Parse current channels
            current_list = [ch.strip() for ch in current_channels.split(',')]
            
            # Priority channels that should be checked if not already included
            priority_channels = ['sharifdaily', 'sharif_senfi']
            
            # Find more relevant channels
            query_embedding = self.embedding_model.encode(query)
            
            channel_scores = []
            additional_channels = []
            
            # First, add priority channels if not already checked
            for priority_ch in priority_channels:
                if priority_ch not in current_list and priority_ch in [ch['username'] for ch in self.active_channels]:
                    additional_channels.append(priority_ch)
                    if len(additional_channels) >= 5:
                        return f"کانال‌های اضافی (5 تا): {', '.join(additional_channels)}"
            
            # Then add semantic matches
            for channel in self.active_channels:
                if channel['username'] not in current_list and channel['username'] not in additional_channels:
                    channel_text = f"{channel['name']} {channel['description']}"
                    channel_embedding = self.embedding_model.encode(channel_text)
                    similarity = self.cosine_similarity(query_embedding, channel_embedding)
                    channel_scores.append((channel['username'], similarity))
            
            # Sort by similarity and add top matches
            channel_scores.sort(key=lambda x: x[1], reverse=True)
            
            for username, score in channel_scores:
                if len(additional_channels) < 5:
                    additional_channels.append(username)
                else:
                    break
            
            return f"کانال‌های اضافی (5 تا): {', '.join(additional_channels)}"
            
        except Exception as e:
            return f"خطا در گسترش جستجو: {e}"
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for better semantic search"""
        import re
        
        # Quick check for very short texts
        if len(text) < 10:
            return text
        
        # Remove URLs
        text = re.sub(r'http[s]?://[^\s]+', '', text)
        
        # Remove emojis and special characters but keep Persian text
        text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z0-9\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Only remove stop words for longer texts
        if len(text) > 50:
            stop_words = ['و', 'در', 'به', 'از', 'که', 'این', 'آن', 'با', 'برای', 'تا', 'را', 'یا', 'اما', 'اگر', 'چون', 'چرا', 'چگونه', 'کجا', 'کی', 'چه', 'چند', 'هم', 'نیز', 'همچنین', 'همه', 'هیچ', 'هر']
            words = text.split()
            words = [word for word in words if word not in stop_words and len(word) > 1]
            return ' '.join(words)
        
        return text
    
    def cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2)
    
    def load_database(self) -> Dict[str, Any]:
        """Load the local database"""
        try:
            with open(self.database_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Loaded database with {data['metadata']['total_channels']} channels and {data['metadata']['total_messages']} messages")
                return data
        except FileNotFoundError:
            print(f"⚠️ Database file {self.database_file} not found!")
            return {"metadata": {"total_channels": 0, "total_messages": 0}, "channels": {}}
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            return {"metadata": {"total_channels": 0, "total_messages": 0}, "channels": {}}
    
    def load_config(self, config_file: str = None) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if config_file is None:
            config_file = self.config_file
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {config_file} not found. Using default config.")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "channels": [],
            "llm_settings": {
                "model": "gemini-2.5-flash",
                "temperature": 0.7
            }
        }
    
    def query(self, question: str) -> str:
        """Main query function using LangChain agent"""
        try:
            if not self.agent:
                return "❌ LangChain system not initialized. Please check dependencies."
            
            print(f"🔍 جستجو برای: {question}")
            print("🤖 استفاده از LangChain Agent...")
            
            # Run agent
            result = self.agent.invoke({"input": question})
            
            return result.get('output', 'پاسخ یافت نشد')
            
        except Exception as e:
            print(f"❌ Error in LangChain query: {e}")
            return f"متأسفانه خطایی در پردازش سوال رخ داد: {e}"

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LangChain RAG System")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--query", type=str, help="Single query")
    
    args = parser.parse_args()
    
    rag = LangChainRAGSystem()
    
    print("🤖 سیستم LangChain RAG آماده است!")
    print("💾 دیتابیس:", rag.database_file)
    print("📊 تعداد کانال‌ها:", rag.database['metadata'].get('total_channels', 0))
    print("💬 تعداد پیام‌ها:", rag.database['metadata'].get('total_messages', 0))
    print()
    
    if args.query:
        # Single query
        result = rag.query(args.query)
        print("\n" + "="*60 + "\n")
        print("🤖 پاسخ:")
        print(result)
        return
    
    if args.daemon:
        # Interactive mode
        print("🚀 راه‌اندازی سیستم LangChain RAG...")
        print("🔄 برای خروج Ctrl+C را فشار دهید")
        print()
        
        while True:
            try:
                query = input("❓ سوال خود را بپرسید (یا 'quit' برای خروج): ")
                if query.lower() in ['quit', 'exit', 'خروج']:
                    break
                
                if query.strip():
                    print("\n" + "="*50)
                    result = rag.query(query)
                    print("\n🤖 پاسخ:")
                    print(result)
                    print("="*50 + "\n")
                    
            except KeyboardInterrupt:
                print("\n🛑 خروج از سیستم...")
                break
            except Exception as e:
                print(f"❌ خطا: {e}")
    
    # Default interactive mode
    while True:
        try:
            query = input("❓ سوال خود را بپرسید (یا 'quit' برای خروج): ")
            if query.lower() in ['quit', 'exit', 'خروج']:
                break
            
            if query.strip():
                print("\n" + "="*50)
                result = rag.query(query)
                print("\n🤖 پاسخ:")
                print(result)
                print("="*50 + "\n")
                
        except KeyboardInterrupt:
            print("\n🛑 خروج از سیستم...")
            break
        except Exception as e:
            print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main() 