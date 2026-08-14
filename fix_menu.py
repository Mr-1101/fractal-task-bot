# fix_menu.py
import asyncio
from telegram import Bot, MenuButtonDefault
from config import Config


async def fix():
    bot = Bot(token=Config.TELEGRAM_TOKEN)

    # تنظیم منوی شیشه‌ای با روش ساده‌تر
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        print("✅ منوی شیشه‌ای (پیش‌فرض) تنظیم شد!")
    except Exception as e:
        print(f"❌ خطا: {e}")

    # چک کردن منوی فعلی
    try:
        menu = await bot.get_chat_menu_button()
        print(f"📋 منوی فعلی: {menu}")
    except Exception as e:
        print(f"❌ خطا: {e}")


asyncio.run(fix())