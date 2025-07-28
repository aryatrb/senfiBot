# ⚡ راهنمای سریع استقرار

## 🚀 استقرار فوری (انتخاب کنید)

### ۱. VPS (توصیه شده برای تولید)
```bash
# روی سرور خود اجرا کنید
git clone https://github.com/your-username/council-bot.git
cd council-bot
chmod +x scripts/deploy_vps.sh
./scripts/deploy_vps.sh
```

### ۲. استقرار محلی (توسعه و تست)
```bash
# نصب وابستگی‌ها
pip install -r requirements.txt

# تنظیم متغیرهای محیطی
cp .env.example .env
# فایل .env را ویرایش کنید

# اجرای بات
python enhanced_bot.py
```

### ۳. استقرار محلی با اسکریپت
```bash
# نصب خودکار
chmod +x scripts/setup_local.sh
./scripts/setup_local.sh

# اجرای بات
chmod +x scripts/run_bot.sh
./scripts/run_bot.sh
```

---

## ⚙️ تنظیمات ضروری

### ۱. دریافت توکن بات
1. به [@BotFather](https://t.me/BotFather) پیام دهید
2. `/newbot` را ارسال کنید
3. نام و username انتخاب کنید
4. توکن را کپی کنید

### ۲. دریافت شناسه کاربران مسئولین
برای هر مسئول نیاز به شناسه عددی کاربر دارید:
- مسئول حقوقی (@arya_t)
- مسئول آموزشی
- مسئول رفاهی
- مسئول فرهنگی
- مسئول ورزشی

### ۳. دریافت شناسه کاربران
```bash
# روش ۱: استفاده از @userinfobot
# به @userinfobot پیام دهید و /start ارسال کنید

# روش ۲: استفاده از بات خودتان
# کاربر پیامی به بات ارسال کند و دستور /myid استفاده کند

# روش ۳: استفاده از API
https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```

---

## 🔧 تنظیم متغیرهای محیطی

### فایل .env
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_USER_ID=123456789
ROLE_LEGAL_USER_ID=987654321
ROLE_EDUCATIONAL_USER_ID=456789123
ROLE_WELFARE_USER_ID=789123456
ROLE_CULTURAL_USER_ID=321654987
ROLE_SPORTS_USER_ID=654321987
```

---

## ✅ تست استقرار

### ۱. بررسی وضعیت بات
```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
```

### ۲. تست بات
1. در تلگرام بات را پیدا کنید
2. `/start` ارسال کنید
3. منوی انتخاب مسئول را ببینید

### ۳. بررسی لاگ‌ها
```bash
# محلی
python enhanced_bot.py

# VPS
sudo journalctl -u councilbot -f
```

---

## 🆘 مشکلات رایج

### بات پاسخ نمی‌دهد
- ✅ توکن صحیح است؟
- ✅ متغیرهای محیطی تنظیم شده‌اند؟
- ✅ بات در حال اجرا است؟

### خطای دیتابیس
- ✅ دسترسی فایل دیتابیس
- ✅ فضای کافی دیسک
- ✅ مجوزهای کاربر

### مشکل شبکه
- ✅ اتصال اینترنت
- ✅ فایروال
- ✅ پورت‌های باز

---

## 📞 پشتیبانی سریع

### لاگ‌ها را بررسی کنید
```bash
# محلی
python enhanced_bot.py

# VPS
sudo journalctl -u councilbot -n 50
```

### تست اتصال
```bash
# تست API تلگرام
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" | jq .

# تست دیتابیس
python3 -c "from database import Database; db = Database(); print('DB OK')"
```

### اسکریپت‌های کمکی
```bash
# بررسی وضعیت
./scripts/status_local.sh

# تست بات
./scripts/test_local.sh

# به‌روزرسانی متغیرهای محیطی
./scripts/update_env.sh
```

---

## 🎯 آماده برای استفاده

بعد از استقرار موفق:

1. **بات را تست کنید** - `/start` ارسال کنید
2. **گروه‌ها را بررسی کنید** - پیام‌ها می‌رسند؟
3. **پاسخ‌ها را تست کنید** - ریپلای کنید
4. **آمار را ببینید** - `./scripts/admin_panel_local.sh`

**🎉 بات شما آماده استفاده است!** 