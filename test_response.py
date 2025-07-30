#!/usr/bin/env python3
"""
Test script for the improved bot response system
"""

import sys
import os

# Add ai directory to path
sys.path.append('ai')

def test_response():
    """Test the improved response system"""
    try:
        from langchain_rag_system import LangChainRAGSystem
        from enhanced_bot import EnhancedCouncilBot
        
        print("🤖 راه‌اندازی سیستم بهبود یافته...")
        rag = LangChainRAGSystem(database_file="ai/test_channels_database.json", config_file="ai/multi_channel_config.json")
        bot = EnhancedCouncilBot()
        
        # Test the exact scenario from user's message
        print("\n🔧 تست سناریوی کاربر (پاسخ با لینک‌های واقعی):")
        print("="*80)
        
        # Simulate the exact response that the user received
        test_response = """محمد شریفی مقدم• بر اساس اطلاعات موجود در کانال تلگرامی کانون یاریگران دانشگاه شریف:

**بخش‌های مرتبط:**
کانون یاریگران دانشگاه صنعتی شریف بیانیه‌ای در محکومیت حکم محمد شریفی مقدم صادر کرده است.
• این کانون از سال 1376 با هدف یاری‌رسانی به کودکان آسیب‌دیده و محروم از تحصیل تأسیس شده و تلاش می‌کند قشر دانشجو را با واقعیت‌های اجتماعی روبرو ساخته و درگیر مسائل اجتماعی کند.
• دانشجویان به عنوان قشری فرهیخته، همواره پیشگام تغییرات و تحولات مثبت اجتماعی و تلاش برای حل مسائل و معضلات جامعه بوده‌اند.

**مسائل مرتبط:**
محکومیت محمد شریفی مقدم.
• نقش دانشجویان و کانون یاریگران در مسائل و معضلات اجتماعی.

**منابع مرتبط:**
1. [کانون یاریگران](https://t.me/yarigaran_sharif/1001)
2. [کانون یاریگران](https://t.me/yarigaran_sharif/787)
3. [کانون یاریگران](https://t.me/yarigaran_sharif/863)
4. [کانون یاریگران](https://t.me/yarigaran_sharif/875)
5. [کانون یاریگران](https://t.me/yarigaran_sharif/1059)"""
        
        # Debug: Let's see what links are extracted
        import re
        link_pattern = r'https://t\.me/([^/\s]+)/(\d+)'
        links = re.findall(link_pattern, test_response)
        print("🔍 لینک‌های استخراج شده:")
        for channel, message_id in links:
            print(f"  - {channel}/{message_id}")
        
        processed = bot.post_process_ai_response(test_response, "محمد شریفی مقدم")
        print("\nپاسخ اصلی:")
        print(test_response)
        print("\n" + "="*80)
        print("پاسخ پس از پردازش:")
        print(processed)
        print("="*80)
        
        # Test different question types to verify general logic
        print("\n🧪 تست منطق عمومی برای سوالات مختلف:")
        print("="*80)
        
        # Test 1: Person question (should get boost)
        question1 = "احمد محمدی کیست؟"
        score1 = bot.calculate_relevance_score('sharif_senfi', question1)
        print(f"سوال شخص: '{question1}' -> امتیاز: {score1}")
        
        # Test 2: General question (no boost)
        question2 = "زمان ثبت‌نام ترم جدید چه زمانی است؟"
        score2 = bot.calculate_relevance_score('sharif_senfi', question2)
        print(f"سوال عمومی: '{question2}' -> امتیاز: {score2}")
        
        # Test 3: Another person question
        question3 = "بیوگرافی دکتر رضایی چیست؟"
        score3 = bot.calculate_relevance_score('sharifdaily', question3)
        print(f"سوال بیوگرافی: '{question3}' -> امتیاز: {score3}")
        
        print("="*80)
        
        # Test channel search functionality
        print("\n🔍 تست جستجو در کانال یاریگران:")
        print("="*80)
        
        # Test the specific case mentioned by user
        result = rag.search_messages_in_channel("یاریگران", "محمد شریفی مقدم")
        print("نتیجه جستجو:")
        print(result)
        print("="*80)
        
        # Test the specific case from logs: "yareegaran"
        print("\n🔍 تست مورد خاص از لاگ‌ها (yareegaran):")
        print("="*80)
        result2 = rag.search_messages_in_channel("yareegaran", "محمد شریفی مقدم")
        print("نتیجه جستجو:")
        print(result2)
        print("="*80)
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_response() 