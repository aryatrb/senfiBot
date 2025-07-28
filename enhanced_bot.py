import logging
import os
import sqlite3
import fcntl
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.constants import ParseMode

from database import Database
from config import Config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_ROLE, WAITING_FOR_MESSAGE = range(2)

class EnhancedCouncilBot:
    def __init__(self):
        self.db = Database(Config.DATABASE_PATH)
        self.user_states: Dict[int, Dict[str, Any]] = {}
        self.message_thread_map: Dict[int, int] = {}  # Maps telegram message_id to thread_id
        self.user_message_counts: Dict[int, Dict[str, int]] = {}  # Rate limiting: user_id -> {date -> count}
        self.user_last_message: Dict[int, datetime] = {}  # Rate limiting: user_id -> last_message_time
        
        # Lock file for preventing multiple instances
        self.lock_file_path = "bot.lock"
        self.lock_file = None
        
        # Load message mappings from database on startup
        self.load_message_mappings()
    
    def acquire_lock(self) -> bool:
        """Try to acquire a lock to prevent multiple instances"""
        try:
            self.lock_file = open(self.lock_file_path, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write current process info to lock file
            import psutil
            current_process = psutil.Process()
            lock_info = f"PID: {current_process.pid}\n"
            lock_info += f"Command: {' '.join(sys.argv)}\n"
            lock_info += f"Started: {datetime.now().isoformat()}\n"
            self.lock_file.write(lock_info)
            self.lock_file.flush()
            
            logger.info(f"Lock acquired successfully. PID: {current_process.pid}")
            return True
        except (IOError, OSError) as e:
            logger.error(f"Failed to acquire lock: {e}")
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            return False
    
    def release_lock(self):
        """Release the lock file"""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                os.unlink(self.lock_file_path)
                logger.info("Lock released successfully")
            except (IOError, OSError) as e:
                logger.error(f"Error releasing lock: {e}")
            finally:
                self.lock_file = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Add user to database
        self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Show role selection menu
        await self.show_role_menu(update, context)
        return CHOOSING_ROLE
    
    async def show_role_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the role selection menu"""
        roles = self.db.get_roles()
        
        keyboard = []
        for role in roles:
            keyboard.append([InlineKeyboardButton(
                role['role_name'], 
                callback_data=f"role_{role['role_id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("📋 گفتگوهای قبلی", callback_data="show_threads")])
        keyboard.append([InlineKeyboardButton("🆔 شناسه من", callback_data="get_user_id")])
        keyboard.append([InlineKeyboardButton("❓ راهنما", callback_data="help")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🤖 **بات شورای صنفی دانشجویی**

به بات شورای صنفی خوش آمدید! 

لطفاً مسئول مورد نظر خود را انتخاب کنید تا بتوانید با ایشان ارتباط برقرار کنید.

**نکات مهم:**
• تمام پیام‌ها با اطلاعات شما ارسال می‌شوند
• شناسه و اطلاعات شما برای مسئول ارسال می‌شود
• هر گفتگو در یک ترد جداگانه ذخیره می‌شود
• می‌توانید در هر زمان مسئول را تغییر دهید
        """
        
        # Always send message with inline keyboard
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Send new message with inline keyboard
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_role_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle role selection from inline keyboard"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "show_threads":
            await self.show_user_threads(update, context)
            return CHOOSING_ROLE
        
        elif query.data == "get_user_id":
            await self.get_user_id(update, context)
            return CHOOSING_ROLE
        
        elif query.data == "help":
            await self.show_help(update, context)
            return CHOOSING_ROLE
        
        elif query.data == "back_to_menu":
            await self.show_role_menu(update, context)
            return CHOOSING_ROLE
        
        elif query.data.startswith("continue_thread_"):
            thread_id = int(query.data.split("_")[2])
            await self.continue_thread(update, context, thread_id)
            return WAITING_FOR_MESSAGE
        
        elif query.data == "send_message":
            # Create reply keyboard for typing
            reply_keyboard = [
                [KeyboardButton("🔙 بازگشت")],
                [KeyboardButton("🏠 منوی اصلی")]
            ]
            reply_markup_keyboard = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
            
            # Edit the message to show typing interface
            await query.edit_message_text(
                text="📝 **ارسال پیام**\n\n"
                "💬 **حالا پیام خود را تایپ کنید:**\n\n"
                "برای لغو، روی دکمه «🔙 بازگشت» کلیک کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send a separate message with reply keyboard
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="⌨️ **دکمه‌های زیر را برای ناوبری استفاده کنید:**",
                reply_markup=reply_markup_keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            return WAITING_FOR_MESSAGE
        
        elif query.data == "new_thread":
            # Create new thread for current role
            user_id = query.from_user.id
            if user_id in self.user_states:
                role = self.user_states[user_id]['selected_role']
                thread_id = self.db.create_thread(user_id, role['role_id'])
                self.user_states[user_id]['thread_id'] = thread_id
                
                keyboard = [
                    [InlineKeyboardButton("📝 ارسال پیام", callback_data="send_message")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_role")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=f"✅ **گفتگوی جدید ایجاد شد!**\n\n"
                    f"مسئول: {role['role_name']}\n"
                    f"🆔 شناسه گفتگو: #{thread_id}\n\n"
                    f"برای ارسال پیام، روی «📝 ارسال پیام» کلیک کنید.",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                return WAITING_FOR_MESSAGE
            else:
                await query.edit_message_text("❌ خطا: لطفاً ابتدا مسئول را انتخاب کنید.")
                return CHOOSING_ROLE
        
        elif query.data == "back_to_role":
            # Go back to role selection for current role
            user_id = query.from_user.id
            if user_id in self.user_states:
                role = self.user_states[user_id]['selected_role']
                thread_id = self.user_states[user_id].get('thread_id')
                
                if thread_id:
                    keyboard = [
                        [InlineKeyboardButton("📝 ارسال پیام", callback_data="send_message")],
                        [InlineKeyboardButton("🆕 گفتگوی جدید", callback_data="new_thread")],
                        [InlineKeyboardButton("📋 گفتگوهای قبلی", callback_data="show_threads")],
                        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        text=f"✅ **گفتگوی فعال**\n\n"
                        f"مسئول: {role['role_name']}\n"
                        f"🆔 شناسه گفتگو: #{thread_id}\n\n"
                        f"برای ارسال پیام، روی «📝 ارسال پیام» کلیک کنید.",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    keyboard = [
                        [InlineKeyboardButton("📝 ارسال پیام", callback_data="send_message")],
                        [InlineKeyboardButton("📋 گفتگوهای قبلی", callback_data="show_threads")],
                        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        text=f"✅ **مسئول انتخاب شده**\n\n"
                        f"مسئول: {role['role_name']}\n\n"
                        f"برای ارسال پیام، روی «📝 ارسال پیام» کلیک کنید.",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                return CHOOSING_ROLE
            else:
                await self.show_role_menu(update, context)
                return CHOOSING_ROLE
        
        elif query.data.startswith("role_"):
            role_id = int(query.data.split("_")[1])
            role = self.db.get_role_by_id(role_id)
            
            if not role:
                await query.edit_message_text("❌ خطا: مسئول مورد نظر یافت نشد.")
                return ConversationHandler.END
            
            # Store selected role in user state
            user_id = query.from_user.id
            self.user_states[user_id] = {
                'selected_role': role,
                'thread_id': None
            }
            
            # Check if there's an active thread for this user and role
            thread_id = self.db.get_active_thread(user_id, role_id)
            if thread_id:
                self.user_states[user_id]['thread_id'] = thread_id
                
                # Show active thread with inline keyboard
                keyboard = [
                    [InlineKeyboardButton("📝 ارسال پیام", callback_data="send_message")],
                    [InlineKeyboardButton("🆕 گفتگوی جدید", callback_data="new_thread")],
                    [InlineKeyboardButton("📋 گفتگوهای قبلی", callback_data="show_threads")],
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=f"✅ **گفتگوی فعال یافت شد!**\n\n"
                    f"مسئول: {role['role_name']}\n"
                    f"🆔 شناسه گفتگو: #{thread_id}\n\n"
                    f"برای ارسال پیام، روی «📝 ارسال پیام» کلیک کنید.",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Show new conversation with inline keyboard
                keyboard = [
                    [InlineKeyboardButton("📝 ارسال پیام", callback_data="send_message")],
                    [InlineKeyboardButton("📋 گفتگوهای قبلی", callback_data="show_threads")],
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=f"✅ **مسئول انتخاب شد!**\n\n"
                    f"مسئول: {role['role_name']}\n\n"
                    f"برای ارسال پیام، روی «📝 ارسال پیام» کلیک کنید.\n\n"
                    f"⚠️ توجه: پیام‌ها ناشناس نیستند و اطلاعات شما برای مسئول ارسال می‌شود.",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            return CHOOSING_ROLE
    
    async def continue_thread(self, update: Update, context: ContextTypes.DEFAULT_TYPE, thread_id: int):
        """Continue an existing thread"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Get thread information
        threads = self.db.get_user_threads(user_id)
        thread_info = None
        for thread in threads:
            if thread['thread_id'] == thread_id:
                thread_info = thread
                break
        
        if not thread_info:
            await query.edit_message_text("❌ گفتگوی مورد نظر یافت نشد.")
            return CHOOSING_ROLE
        
        # Get role information
        role = self.db.get_role_by_id(thread_info['role_id'])
        if not role:
            await query.edit_message_text("❌ اطلاعات مسئول یافت نشد.")
            return CHOOSING_ROLE
        
        # Update user state
        self.user_states[user_id] = {
            'selected_role': role,
            'thread_id': thread_id
        }
        
        # Show recent messages
        messages = self.db.get_thread_messages(thread_id)
        if messages:
            text = f"📋 **ادامه گفتگو با {role['role_name']}**\n\n"
            text += "**آخرین پیام‌ها:**\n"
            for msg in messages[-3:]:  # Show last 3 messages
                sender = "👤 شما" if msg['sender_type'] == 'user' else "👨‍💼 مسئول"
                text += f"{sender}:\n{msg['message_text'][:100]}...\n\n"
        else:
            text = f"📋 **ادامه گفتگو با {role['role_name']}**\n\n"
            text += "هنوز پیامی در این گفتگو وجود ندارد."
        
        text += "\n📝 پیام خود را ارسال کنید یا از دستورات زیر استفاده کنید:\n"
        text += "📝 /new - شروع گفتگوی جدید\n"
        text += "📋 /history - مشاهده تاریخچه کامل گفتگو\n"
        text += "🔙 /back - بازگشت به منوی اصلی"
        
        # Create reply keyboard for continuing thread
        keyboard = [
            [KeyboardButton("🏠 منوی اصلی"), KeyboardButton("📋 گفتگوهای قبلی")],
            [KeyboardButton("🆕 گفتگوی جدید")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def show_user_threads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's previous threads with recent messages"""
        # Handle both callback_query and message
        if update.callback_query:
            query = update.callback_query
            user_id = query.from_user.id
        else:
            user_id = update.effective_user.id
        
        threads = self.db.get_user_threads(user_id)
        
        if not threads:
            if update.callback_query:
                keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📋 **هیچ گفتگوی قبلی یافت نشد.**\n\n"
                    "هنوز هیچ پیامی ارسال نکرده‌اید.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                back_to_menu_markup = self.create_back_to_menu_button()
                await update.message.reply_text(
                    "📋 **هیچ گفتگوی قبلی یافت نشد.**\n\n"
                    "هنوز هیچ پیامی ارسال نکرده‌اید.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=back_to_menu_markup
                )
            
            return CHOOSING_ROLE
        
        text = "📋 **گفتگوهای قبلی شما:**\n\n"
        keyboard = []
        
        for thread in threads[:10]:  # Show last 10 threads
            # Get recent messages for this thread
            recent_messages = self.db.get_thread_messages(thread['thread_id'])
            
            status = "🟢 فعال" if thread['is_active'] else "🔴 غیرفعال"
            text += f"**{thread['role_name']}** - {status}\n"
            text += f"🆔 شناسه: #{thread['thread_id']}\n"
            text += f"📅 آخرین فعالیت: {thread['last_activity'][:16]}\n"
            
            # Show last 3 messages
            if recent_messages:
                text += "📝 **آخرین پیام‌ها:**\n"
                for msg in recent_messages[-3:]:  # Last 3 messages
                    sender_icon = "👤" if msg['sender_type'] == 'user' else "👨‍💼"
                    message_preview = msg['message_text'][:50] + "..." if len(msg['message_text']) > 50 else msg['message_text']
                    text += f"{sender_icon} {message_preview}\n"
            
            text += "\n"
            
            keyboard.append([InlineKeyboardButton(
                f"📝 ادامه گفتگو با {thread['role_name']}", 
                callback_data=f"continue_thread_{thread['thread_id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Add back to menu button to the existing keyboard
            keyboard.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    

    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user messages"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_states:
            back_to_menu_markup = self.create_back_to_menu_button()
            await update.message.reply_text(
                "❌ لطفاً ابتدا مسئول مورد نظر خود را انتخاب کنید.\n"
                "از دستور /start استفاده کنید.",
                reply_markup=back_to_menu_markup
            )
            return CHOOSING_ROLE
        
        # Check rate limit
        if not self.check_rate_limit(user_id):
            back_to_menu_markup = self.create_back_to_menu_button()
            await update.message.reply_text(
                "⚠️ لطفاً کمی صبر کنید و دوباره تلاش کنید.\n"
                "برای جلوگیری از اسپم، محدودیت زمانی اعمال شده است.",
                reply_markup=back_to_menu_markup
            )
            return WAITING_FOR_MESSAGE
        
        user_state = self.user_states[user_id]
        role = user_state['selected_role']
        thread_id = user_state.get('thread_id')
        
        # If no active thread, create one
        if not thread_id:
            thread_id = self.db.create_thread(user_id, role['role_id'])
            self.user_states[user_id]['thread_id'] = thread_id
        
        message_text = update.message.text
        
        # Handle reply keyboard buttons
        if message_text == "🔙 بازگشت":
            # Remove reply keyboard
            remove_keyboard = ReplyKeyboardRemove()
            await context.bot.send_message(
                chat_id=user_id,
                text="🔙 بازگشت به منوی مسئول",
                reply_markup=remove_keyboard
            )
            # Go back to role view - create role view directly
            user_id = update.effective_user.id
            if user_id in self.user_states:
                role = self.user_states[user_id]['selected_role']
                thread_id = self.user_states[user_id].get('thread_id')
                
                if thread_id:
                    keyboard = [
                        [InlineKeyboardButton("📝 ارسال پیام", callback_data="send_message")],
                        [InlineKeyboardButton("🆕 گفتگوی جدید", callback_data="new_thread")],
                        [InlineKeyboardButton("📋 گفتگوهای قبلی", callback_data="show_threads")],
                        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ **گفتگوی فعال**\n\n"
                        f"مسئول: {role['role_name']}\n"
                        f"🆔 شناسه گفتگو: #{thread_id}\n\n"
                        f"برای ارسال پیام، روی «📝 ارسال پیام» کلیک کنید.",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    keyboard = [
                        [InlineKeyboardButton("📝 ارسال پیام", callback_data="send_message")],
                        [InlineKeyboardButton("📋 گفتگوهای قبلی", callback_data="show_threads")],
                        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ **مسئول انتخاب شده**\n\n"
                        f"مسئول: {role['role_name']}\n\n"
                        f"برای ارسال پیام، روی «📝 ارسال پیام» کلیک کنید.",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
            return CHOOSING_ROLE
        
        elif message_text == "🏠 منوی اصلی":
            # Remove reply keyboard
            remove_keyboard = ReplyKeyboardRemove()
            await context.bot.send_message(
                chat_id=user_id,
                text="🏠 بازگشت به منوی اصلی",
                reply_markup=remove_keyboard
            )
            # Go back to main menu
            await self.show_role_menu(update, context)
            return CHOOSING_ROLE
        
        # Store user message
        self.db.add_message(
            thread_id=thread_id,
            telegram_message_id=update.message.message_id,
            sender_type='user',
            message_text=message_text
        )
        
        # Send notification to admin
        admin_user_id = role['user_id']
        
        # Create admin notification message
        username = update.effective_user.username
        username_display = f"@{username}" if username else "بدون نام کاربری"
        
        admin_message = f"""
🔔 **پیام جدید از دانشجو**

🆔 **شناسه گفتگو:** #{thread_id}
👤 **نام کاربر:** {update.effective_user.first_name}
📝 **نام کاربری:** {username_display}
🆔 **شناسه کاربر:** {user_id}
📝 **پیام:** {message_text}

---
💬 برای پاسخ، روی این پیام ریپلای کنید.
        """
        
        try:
            sent_msg = await context.bot.send_message(
                chat_id=admin_user_id,
                text=admin_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Store the mapping between role message and thread
            self.message_thread_map[sent_msg.message_id] = thread_id
            
            # Add role message to database
            self.db.add_message(
                thread_id=thread_id,
                telegram_message_id=sent_msg.message_id,
                sender_type='admin',
                message_text=f"پیام کاربر (Thread #{thread_id}): {message_text}"
            )
            
            # Save the mapping to database for persistence
            self.save_message_mapping(sent_msg.message_id, thread_id)
            
            # Confirm to user
            keyboard = [
                [InlineKeyboardButton("📝 ارسال پیام دیگر", callback_data="send_message")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_role")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **پیام شما ارسال شد!**\n\n"
                f"مسئول: {role['role_name']}\n"
                f"🆔 شناسه گفتگو: #{thread_id}\n\n"
                f"پاسخ مسئول به شما ارسال خواهد شد.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Update rate limit
            self.update_rate_limit(user_id)
            
        except Exception as e:
            logger.error(f"Error sending message to admin: {e}")
            back_to_menu_markup = self.create_back_to_menu_button()
            await update.message.reply_text(
                "❌ خطا در ارسال پیام. لطفاً دوباره تلاش کنید.",
                reply_markup=back_to_menu_markup
            )
        
        return WAITING_FOR_MESSAGE
    
    async def handle_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
        """Handle user commands"""
        user_id = update.effective_user.id
        user_state = self.user_states[user_id]
        
        if command == '/new':
            # Create new thread
            selected_role = user_state['selected_role']
            thread_id = self.db.create_thread(user_id, selected_role['role_id'])
            user_state['thread_id'] = thread_id
            
            back_to_menu_markup = self.create_back_to_menu_button()
            await update.message.reply_text(
                f"🆕 **گفتگوی جدید شروع شد!**\n\n"
                f"مسئول: {selected_role['role_name']}\n"
                f"🆔 شناسه گفتگو: #{thread_id}\n\n"
                f"پیام خود را ارسال کنید.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_to_menu_markup
            )
        
        elif command == '/history':
            # Show thread history
            thread_id = user_state.get('thread_id')
            if thread_id:
                messages = self.db.get_thread_messages(thread_id)
                if messages:
                    text = f"📋 **تاریخچه گفتگو #{thread_id}:**\n\n"
                    for msg in messages[-10:]:  # Show last 10 messages
                        sender = "👤 شما" if msg['sender_type'] == 'user' else "👨‍💼 مسئول"
                        text += f"{sender}:\n{msg['message_text']}\n\n"
                    
                    back_to_menu_markup = self.create_back_to_menu_button()
                    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu_markup)
                else:
                    back_to_menu_markup = self.create_back_to_menu_button()
                    await update.message.reply_text("📋 هنوز پیامی در این گفتگو وجود ندارد.", reply_markup=back_to_menu_markup)
            else:
                back_to_menu_markup = self.create_back_to_menu_button()
                await update.message.reply_text("❌ گفتگوی فعالی یافت نشد.", reply_markup=back_to_menu_markup)
        
        elif command == '/back':
            # Return to role selection
            await self.show_role_menu(update, context)
            return CHOOSING_ROLE
    
    def create_back_to_menu_button(self) -> InlineKeyboardMarkup:
        """Create a back to main menu button"""
        keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_menu")]]
        return InlineKeyboardMarkup(keyboard)

    async def handle_admin_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle replies to admin messages (both from admins and regular users)"""
        logger.info(f"handle_admin_reply called for user {update.effective_user.id}")
        
        if not update.message.reply_to_message:
            logger.info("No reply_to_message found")
            return  # Not a reply
        
        user_id = update.effective_user.id
        is_admin = self.is_admin_user(user_id)
        
        # Log the reply attempt
        logger.info(f"Reply to admin message from user {user_id} (admin: {is_admin})")
        
        # Log admin action for security
        logger.info(f"Admin reply from user {user_id} for message {update.message.reply_to_message.message_id}")
        
        # Get the original message that was replied to
        original_message_id = update.message.reply_to_message.message_id
        admin_message = update.message.text
        
        # Debug: Log all message mappings
        logger.info(f"Message thread map contents: {self.message_thread_map}")
        logger.info(f"Looking for message ID: {original_message_id}")
        logger.info(f"Admin message: {admin_message}")
        logger.info(f"Reply message text: {update.message.text}")
        logger.info(f"Reply message ID: {update.message.message_id}")
        logger.info(f"Original message ID: {original_message_id}")
        
        # Find the thread for this message - try both direct mapping and database lookup
        thread_id = self.message_thread_map.get(original_message_id)
        
        # If not found in memory, try to find it in the database
        if not thread_id:
            try:
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                
                # Try multiple approaches to find the thread
                # 1. First try the message_mappings table
                cursor.execute('''
                    SELECT thread_id FROM message_mappings 
                    WHERE telegram_message_id = ?
                ''', (original_message_id,))
                result = cursor.fetchone()
                
                # 2. If not found, try the messages table for admin messages
                if not result:
                    cursor.execute('''
                        SELECT thread_id FROM messages 
                        WHERE telegram_message_id = ? AND sender_type = 'admin'
                    ''', (original_message_id,))
                    result = cursor.fetchone()
                
                # 3. If still not found, try the messages table for user messages
                if not result:
                    cursor.execute('''
                        SELECT thread_id FROM messages 
                        WHERE telegram_message_id = ? AND sender_type = 'user'
                    ''', (original_message_id,))
                    result = cursor.fetchone()
                
                # 4. If still not found, try to find by message text pattern (for admin notifications)
                if not result:
                    cursor.execute('''
                        SELECT thread_id FROM messages 
                        WHERE sender_type = 'admin' AND message_text LIKE ?
                        ORDER BY message_id DESC LIMIT 1
                    ''', (f'%Thread #{original_message_id}%',))
                    result = cursor.fetchone()
                
                # 5. Last resort: try to find any recent message in the same chat
                if not result:
                    cursor.execute('''
                        SELECT thread_id FROM messages 
                        WHERE telegram_message_id IN (
                            SELECT telegram_message_id FROM messages 
                            WHERE thread_id IN (
                                SELECT thread_id FROM threads WHERE user_id = ?
                            )
                            ORDER BY message_id DESC LIMIT 5
                        )
                        ORDER BY message_id DESC LIMIT 1
                    ''', (user_id,))
                    result = cursor.fetchone()
                
                conn.close()
                
                if result:
                    thread_id = result[0]
                    # Add to memory mapping for future use
                    self.message_thread_map[original_message_id] = thread_id
                    logger.info(f"Found thread {thread_id} for message {original_message_id} in database")
                else:
                    logger.warning(f"No thread found for message {original_message_id} in database")
                    logger.warning(f"Available message IDs: {list(self.message_thread_map.keys())}")
                    await update.message.reply_text("❌ پیام مورد نظر یافت نشد. لطفاً روی پیام اصلی ریپلای کنید.")
                    return
            except Exception as e:
                logger.error(f"Error looking up message in database: {e}")
                await update.message.reply_text("❌ خطا در یافتن پیام. لطفاً دوباره تلاش کنید.")
                return
        
        # Get thread information
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, role_id FROM threads WHERE thread_id = ?', (thread_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            logger.error(f"Thread {thread_id} not found in database")
            return
        
        student_user_id = result[0]
        role_id = result[1]
        reply_message = update.message.text
        
        # Get role information
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT role_name, user_id FROM roles WHERE role_id = ?', (role_id,))
        role_result = cursor.fetchone()
        conn.close()
        
        role_name = role_result[0] if role_result else "مسئول"
        admin_user_id = role_result[1] if role_result else None
        
        # Debug logging
        logger.info(f"Reply - Thread ID: {thread_id}, Student User ID: {student_user_id}, Reply User ID: {user_id}, Is Admin: {is_admin}")
        logger.info(f"Reply message text: {reply_message}")
        
        # Handle different scenarios
        if is_admin:
            # Admin is replying to user message
            logger.info(f"Admin reply - Will send reply to chat_id: {student_user_id}")
            
            # Check if user is blocked
            if self.db.is_user_blocked(user_id, student_user_id):
                await update.message.reply_text("❌ این کاربر توسط شما بلاک شده است.")
                return
        
            # Handle admin commands
            if reply_message.startswith('/block'):
                # Block the user
                reason = reply_message[7:].strip() if len(reply_message) > 7 else None
                self.db.block_user(user_id, student_user_id, reason)
                await update.message.reply_text(f"✅ کاربر بلاک شد.\nدلیل: {reason or 'بدون دلیل'}")
                return
            
            if reply_message.startswith('/unblock'):
                # Unblock the user
                self.db.unblock_user(user_id, student_user_id)
                await update.message.reply_text("✅ کاربر از بلاک خارج شد.")
                return
            
            if reply_message.startswith('/blocks'):
                # List blocked users
                blocked_users = self.db.get_blocked_users(user_id)
                if not blocked_users:
                    await update.message.reply_text("📋 هیچ کاربری بلاک نشده است.")
                    return
                
                text = "📋 **کاربران بلاک شده:**\n\n"
                for i, blocked in enumerate(blocked_users[:10], 1):  # Show first 10
                    text += f"{i}. شناسه: `{blocked['user_id']}`\n"
                    text += f"   تاریخ: {blocked['blocked_at'][:16]}\n"
                    if blocked['reason']:
                        text += f"   دلیل: {blocked['reason']}\n"
                    text += "\n"
                
                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                return
        else:
            # Regular user is replying to admin message
            logger.info(f"User reply - Will send reply to admin chat_id: {admin_user_id}")
            
            # Check if user is blocked by admin
            if admin_user_id and self.db.is_user_blocked(admin_user_id, user_id):
                await update.message.reply_text("❌ شما توسط این مسئول بلاک شده‌اید.")
                return
        
        # Add message to database
        sender_type = 'admin' if is_admin else 'user'
        self.db.add_message(
            thread_id=thread_id,
            telegram_message_id=update.message.message_id,
            sender_type=sender_type,
            message_text=reply_message
        )
        
        # Send reply
        try:
            if is_admin:
                # Admin sending reply to student
                reply_text = f"""
💬 **پاسخ از {role_name}**

🆔 **شناسه گفتگو:** #{thread_id}

{reply_message}

---
برای پاسخ، پیام خود را ارسال کنید.
                """
                
                target_user_id = student_user_id
                sender_name = role_name
            else:
                # Student sending reply to admin
                reply_text = f"""
💬 **پاسخ از دانشجو**

🆔 **شناسه گفتگو:** #{thread_id}

{reply_message}

---
برای پاسخ، روی این پیام ریپلای کنید.
                """
                
                target_user_id = admin_user_id
                sender_name = "دانشجو"
            
            # Find the original message to reply to
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            if is_admin:
                # Find the last user message to reply to
                cursor.execute('''
                    SELECT telegram_message_id FROM messages 
                    WHERE thread_id = ? AND sender_type = 'user' 
                    ORDER BY message_id DESC LIMIT 1
                ''', (thread_id,))
            else:
                # Find the last admin message to reply to
                cursor.execute('''
                    SELECT telegram_message_id FROM messages 
                    WHERE thread_id = ? AND sender_type = 'admin' 
                    ORDER BY message_id DESC LIMIT 1
                ''', (thread_id,))
            msg_result = cursor.fetchone()
            conn.close()
            
            # Send reply
            logger.info(f"Sending reply to {target_user_id} with text: {reply_text[:100]}...")
            
            try:
                # Create back to menu button
                back_to_menu_markup = self.create_back_to_menu_button()
                
                sent_message = None
                if msg_result:
                    sent_message = await context.bot.send_message(
                        chat_id=target_user_id,
                        text=reply_text,
                        reply_to_message_id=msg_result[0],
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=back_to_menu_markup
                    )
                else:
                    sent_message = await context.bot.send_message(
                        chat_id=target_user_id,
                        text=reply_text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=back_to_menu_markup
                    )
                
                # Save message mapping for future replies
                if sent_message:
                    self.save_message_mapping(sent_message.message_id, thread_id)
                    logger.info(f"Saved message mapping: {sent_message.message_id} -> {thread_id}")
                
                logger.info(f"Reply successfully forwarded to {target_user_id} for thread {thread_id}")
                
                # Send confirmation to sender
                if is_admin:
                    await update.message.reply_text(f"✅ پاسخ شما به دانشجو ارسال شد.\n🆔 شناسه گفتگو: #{thread_id}")
                else:
                    await update.message.reply_text(f"✅ پاسخ شما به {sender_name} ارسال شد.\n🆔 شناسه گفتگو: #{thread_id}")
                
            except Exception as send_error:
                logger.error(f"Error sending message to {target_user_id}: {send_error}")
                if is_admin:
                    await update.message.reply_text(f"❌ خطا در ارسال پاسخ به دانشجو: {str(send_error)}")
                else:
                    await update.message.reply_text(f"❌ خطا در ارسال پاسخ به {sender_name}: {str(send_error)}")
            
        except Exception as e:
            logger.error(f"Error forwarding reply: {e}")
            # Send error message to sender
            await update.message.reply_text(f"❌ خطا در ارسال پاسخ: {str(e)}")
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation and return to main menu"""
        user_id = update.effective_user.id
        
        # Clear user state
        if user_id in self.user_states:
            del self.user_states[user_id]
        
        # Return to main menu
        await self.show_role_menu(update, context)
        
        await update.message.reply_text("🔙 بازگشت به منوی اصلی")
        
        return CHOOSING_ROLE
    
    async def get_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user ID for configuration purposes"""
        user = update.effective_user
        
        # Simple text without Markdown to avoid parsing issues
        user_info_text = f"👤 اطلاعات کاربر:\n\n🆔 شناسه: {user.id}\n👤 نام: {user.first_name or 'بدون نام'}\n📝 نام کاربری: @{user.username or 'بدون نام کاربری'}"
        
        # Create back to menu button
        back_to_menu_markup = self.create_back_to_menu_button()
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text=user_info_text,
                reply_markup=back_to_menu_markup
            )
        else:
            await update.message.reply_text(
                text=user_info_text,
                reply_markup=back_to_menu_markup
            )
    
    async def test_admin_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test admin reply functionality"""
        user = update.effective_user
        
        if not self.is_admin_user(user.id):
            await update.message.reply_text("❌ این دستور فقط برای ادمین‌ها قابل استفاده است.")
            return
        
        # Show current message mappings
        mapping_info = f"📊 **اطلاعات نگاشت پیام‌ها:**\n\n"
        mapping_info += f"تعداد نگاشت‌های موجود: {len(self.message_thread_map)}\n\n"
        
        if self.message_thread_map:
            mapping_info += "**نگاشت‌های موجود:**\n"
            for msg_id, thread_id in list(self.message_thread_map.items())[:5]:  # Show first 5
                mapping_info += f"• پیام {msg_id} → ترد {thread_id}\n"
        else:
            mapping_info += "هیچ نگاشتی موجود نیست."
        
        # Also show recent threads
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.thread_id, t.user_id, r.role_name, t.created_at,
                       (SELECT COUNT(*) FROM messages m WHERE m.thread_id = t.thread_id) as message_count
                FROM threads t
                JOIN roles r ON t.role_id = r.role_id
                ORDER BY t.last_activity DESC
                LIMIT 3
            ''')
            threads = cursor.fetchall()
            conn.close()
            
            if threads:
                mapping_info += "\n\n**آخرین گفتگوها:**\n"
                for thread_id, user_id, role_name, created_at, msg_count in threads:
                    mapping_info += f"• ترد #{thread_id} - {role_name} (پیام‌ها: {msg_count})\n"
        except Exception as e:
            mapping_info += f"\n\nخطا در دریافت گفتگوها: {e}"
        
        back_to_menu_markup = self.create_back_to_menu_button()
        await update.message.reply_text(mapping_info, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu_markup)
    
    async def debug_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Debug information for troubleshooting"""
        user = update.effective_user
        
        debug_info = f"🔧 **اطلاعات دیباگ:**\n\n"
        debug_info += f"👤 کاربر: {user.id}\n"
        debug_info += f"🔑 ادمین: {self.is_admin_user(user.id)}\n"
        debug_info += f"📊 نگاشت‌های پیام: {len(self.message_thread_map)}\n"
        debug_info += f"🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Check if this is a reply
        if update.message.reply_to_message:
            debug_info += f"\n📝 **اطلاعات ریپلای:**\n"
            debug_info += f"پیام اصلی: {update.message.reply_to_message.message_id}\n"
            debug_info += f"پیام ریپلای: {update.message.message_id}\n"
            
            # Check if the original message is in our mapping
            original_id = update.message.reply_to_message.message_id
            thread_id = self.message_thread_map.get(original_id)
            debug_info += f"ترد یافت شده: {thread_id}\n"
        else:
            debug_info += f"\n❌ این پیام ریپلای نیست."
        
        back_to_menu_markup = self.create_back_to_menu_button()
        await update.message.reply_text(debug_info, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu_markup)
    
    async def handle_admin_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin messages for replying to students"""
        user = update.effective_user
        
        if not self.is_admin_user(user.id):
            return  # Not an admin, let other handlers deal with it
        
        message_text = update.message.text
        
        # Check if this is a reply command
        if message_text.startswith('/reply '):
            try:
                # Format: /reply <thread_id> <message>
                parts = message_text.split(' ', 2)
                if len(parts) >= 3:
                    thread_id = int(parts[1])
                    reply_text = parts[2]
                    
                    # Get thread information
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM threads WHERE thread_id = ?', (thread_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        user_id = result[0]
                        
                        # Get role information
                        conn = sqlite3.connect(self.db.db_path)
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT r.role_name FROM threads t
                            JOIN roles r ON t.role_id = r.role_id
                            WHERE t.thread_id = ?
                        ''', (thread_id,))
                        role_result = cursor.fetchone()
                        conn.close()
                        
                        role_name = role_result[0] if role_result else "مسئول"
                        
                        formatted_reply = f"""
💬 **پاسخ از {role_name}**

🆔 **شناسه گفتگو:** #{thread_id}

{reply_text}

---
برای پاسخ، پیام خود را ارسال کنید.
                        """
                        
                        # Send reply to student
                        back_to_menu_markup = self.create_back_to_menu_button()
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=formatted_reply,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=back_to_menu_markup
                        )
                        
                        # Add admin message to database
                        self.db.add_message(
                            thread_id=thread_id,
                            telegram_message_id=update.message.message_id,
                            sender_type='admin',
                            message_text=reply_text
                        )
                        
                        # Save message mapping for future replies
                        self.save_message_mapping(update.message.message_id, thread_id)
                        
                        await update.message.reply_text(f"✅ پاسخ شما به دانشجو ارسال شد.\n🆔 شناسه گفتگو: #{thread_id}")
                    else:
                        await update.message.reply_text(f"❌ ترد #{thread_id} یافت نشد.")
                else:
                    await update.message.reply_text("❌ فرمت صحیح: /reply <thread_id> <پیام>")
            except ValueError:
                await update.message.reply_text("❌ شناسه ترد باید عدد باشد.")
            except Exception as e:
                logger.error(f"Error in handle_admin_message: {e}")
                await update.message.reply_text(f"❌ خطا: {str(e)}")
        
        # Show recent threads for admin
        elif message_text == '/threads':
            try:
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT t.thread_id, t.user_id, r.role_name, t.created_at,
                           (SELECT COUNT(*) FROM messages m WHERE m.thread_id = t.thread_id) as message_count
                    FROM threads t
                    JOIN roles r ON t.role_id = r.role_id
                    ORDER BY t.last_activity DESC
                    LIMIT 10
                ''')
                threads = cursor.fetchall()
                conn.close()
                
                if threads:
                    threads_text = "📋 **آخرین گفتگوها:**\n\n"
                    for thread_id, user_id, role_name, created_at, msg_count in threads:
                        threads_text += f"🆔 **#{thread_id}** - {role_name}\n"
                        threads_text += f"👤 کاربر: {user_id}\n"
                        threads_text += f"📝 پیام‌ها: {msg_count}\n"
                        threads_text += f"📅 تاریخ: {created_at[:16]}\n"
                        threads_text += f"💬 پاسخ: `/reply {thread_id} پیام شما`\n\n"
                    
                    await update.message.reply_text(threads_text, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text("📋 هیچ گفتگویی یافت نشد.")
            except Exception as e:
                logger.error(f"Error showing threads: {e}")
                await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        query = update.callback_query
        
        help_text = """
❓ **راهنمای استفاده از بات**

**دستورات اصلی:**
• /start - شروع مجدد بات
• /cancel - لغو عملیات فعلی

**نحوه استفاده:**
1. مسئول مورد نظر خود را انتخاب کنید
2. روی «📝 ارسال پیام» کلیک کنید
3. پیام خود را تایپ کنید
4. پیام شما برای مسئول ارسال می‌شود

**نکات مهم:**
• پیام‌ها ناشناس نیستند
• هر گفتگو در یک ترد جداگانه ذخیره می‌شود
• می‌توانید در هر زمان مسئول را تغییر دهید
        """
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    def run(self):
        """Run the bot"""
        # Try to acquire lock to prevent multiple instances
        if not self.acquire_lock():
            logger.error("Another instance of the bot is already running!")
            logger.error("If you're sure no other instance is running, delete the 'bot.lock' file and try again.")
            sys.exit(1)
        
        try:
            # Validate configuration
            try:
                Config.validate_config()
            except ValueError as e:
                logger.error(f"Configuration error: {e}")
                return
            
            # Create application
            application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
            
            # Add conversation handler
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', self.start)],
                states={
                    CHOOSING_ROLE: [
                        CallbackQueryHandler(self.handle_role_selection),
                        CommandHandler('start', self.start)
                    ],
                    WAITING_FOR_MESSAGE: [
                        CallbackQueryHandler(self.handle_role_selection),
                        MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.REPLY, self.handle_message),
                        CommandHandler('cancel', self.cancel)
                    ]
                },
                fallbacks=[CommandHandler('cancel', self.cancel)]
            )
            
            application.add_handler(conv_handler, group=2)
            
            # Add command handler for getting user ID
            application.add_handler(CommandHandler('myid', self.get_user_id))
            
            # Add command handler for testing admin reply functionality
            application.add_handler(CommandHandler('testreply', self.test_admin_reply))
            
            # Add debug command
            application.add_handler(CommandHandler('debug', self.debug_info))
            
            # Add handler for admin replies (from any user) - with highest priority
            application.add_handler(
                MessageHandler(
                    filters.TEXT & filters.REPLY,
                    self.handle_admin_reply
                ),
                group=0  # Highest priority group
            )
            
            # Add handler for admin commands (alternative way to reply)
            application.add_handler(
                MessageHandler(
                    filters.TEXT & filters.ChatType.PRIVATE,
                    self.handle_admin_message
                ),
                group=1
            )
            
            # Start the bot
            logger.info("Starting Enhanced Council Bot...")
            # Clear any existing webhook
            application.bot.delete_webhook()
            # Start polling with specific offset
            application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES, close_loop=False)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Bot stopped due to error: {e}")
        finally:
            # Always release the lock when the bot stops
            self.release_lock()
    
    def is_admin_user(self, user_id: int) -> bool:
        """Check if user is an authorized admin"""
        admin_ids = [
            Config.ROLE_USERS['ROLE_SECRETARY_USER_ID'],
            Config.ROLE_USERS['ROLE_LEGAL_USER_ID'],
            Config.ROLE_USERS['ROLE_EDUCATIONAL_1_USER_ID'],
            Config.ROLE_USERS['ROLE_EDUCATIONAL_2_USER_ID'],
            Config.ROLE_USERS['ROLE_PUBLICATION_USER_ID'],
            Config.ADMIN_USER_ID
        ]
        return str(user_id) in admin_ids
    
    def check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limits"""
        now = datetime.now()
        
        # Check 10-minute message limit
        if user_id not in self.user_message_counts:
            self.user_message_counts[user_id] = {}
        
        # Remove old entries (older than 10 minutes)
        ten_minutes_ago = now.timestamp() - 600  # 10 minutes in seconds
        self.user_message_counts[user_id] = {
            timestamp: count for timestamp, count in self.user_message_counts[user_id].items()
            if float(timestamp) > ten_minutes_ago
        }
        
        # Count messages in last 10 minutes
        recent_count = sum(self.user_message_counts[user_id].values())
        if recent_count >= Config.MAX_MESSAGES_PER_10_MINUTES:
            return False
        
        # Check message frequency (minimum 10 seconds between messages)
        if user_id in self.user_last_message:
            time_diff = now - self.user_last_message[user_id]
            if time_diff.total_seconds() < 10:
                return False
        
        return True
    
    def load_message_mappings(self):
        """Load message mappings from database on startup"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT telegram_message_id, thread_id FROM message_mappings 
                ORDER BY created_at DESC
            ''')
            results = cursor.fetchall()
            conn.close()
            
            for telegram_message_id, thread_id in results:
                self.message_thread_map[telegram_message_id] = thread_id
            
            logger.info(f"Loaded {len(results)} message mappings from database")
            
        except Exception as e:
            logger.error(f"Error loading message mappings: {e}")
    
    def save_message_mapping(self, telegram_message_id: int, thread_id: int):
        """Save message mapping to database for persistence"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO message_mappings (telegram_message_id, thread_id)
                VALUES (?, ?)
            ''', (telegram_message_id, thread_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving message mapping: {e}")
    
    def update_rate_limit(self, user_id: int):
        """Update rate limiting counters"""
        now = datetime.now()
        timestamp = str(now.timestamp())
        
        if user_id not in self.user_message_counts:
            self.user_message_counts[user_id] = {}
        
        if timestamp not in self.user_message_counts[user_id]:
            self.user_message_counts[user_id][timestamp] = 0
        
        self.user_message_counts[user_id][timestamp] += 1
        self.user_last_message[user_id] = now

if __name__ == '__main__':
    bot = EnhancedCouncilBot()
    bot.run() 