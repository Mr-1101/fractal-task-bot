# handlers/keyboard.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import Config


def get_main_keyboard():
    """کیبورد اصلی Inline"""
    keyboard = [
        [InlineKeyboardButton("📝 ثبت تسک جدید", callback_data="new_task")],
        [InlineKeyboardButton("📊 مشاهده وضعیت", callback_data="view_status")],
        [InlineKeyboardButton("📋 لیست تسک‌ها", callback_data="my_tasks")],
        [InlineKeyboardButton("📄 گزارش کامل من", callback_data="my_report")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")],
        [InlineKeyboardButton("🔄 تغییر موضوع", callback_data="change_topic")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reply_keyboard():
    """کیبورد Reply ثابت"""
    keyboard = [
        ["📝 تسک جدید", "📊 وضعیت"],
        ["📋 تسک‌های من", "📄 گزارش من"],
        ["🔄 تغییر موضوع", "❓ راهنما"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_topic_keyboard(topics=None):
    """کیبورد انتخاب موضوع"""
    if topics is None:
        topics = Config.load_topics()

    keyboard = []
    for key, topic in topics.items():
        if topic.get('is_active', True):
            keyboard.append([InlineKeyboardButton(
                f"{topic['emoji']} {topic['name']} ({topic['tasks_needed']} تسک)",
                callback_data=f"topic_{key}"
            )])
    keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)


def get_task_count_keyboard():
    """کیبورد انتخاب تعداد تسک‌ها"""
    keyboard = [
        [InlineKeyboardButton("📊 ۱۰۰ تسک - شروع", callback_data="count_100")],
        [InlineKeyboardButton("📊 ۲۰۰ تسک - متوسط", callback_data="count_200")],
        [InlineKeyboardButton("📊 ۵۰۰ تسک - حرفه‌ای", callback_data="count_500")],
        [InlineKeyboardButton("📊 ۱۰۰۰ تسک - فوق‌حرفه‌ای", callback_data="count_1000")],
        [InlineKeyboardButton("✏️ سفارشی - هر عددی", callback_data="count_custom")],
        [InlineKeyboardButton("❌ انصراف", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_status_keyboard():
    """کیبورد وضعیت"""
    keyboard = [
        [InlineKeyboardButton("📊 همه تسک‌ها", callback_data="all_tasks")],
        [InlineKeyboardButton("✅ تکمیل شده", callback_data="approved_tasks")],
        [InlineKeyboardButton("⏳ در انتظار", callback_data="pending_tasks")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard():
    """کیبورد تایید"""
    keyboard = [
        [
            InlineKeyboardButton("✅ بله", callback_data="confirm"),
            InlineKeyboardButton("❌ نه", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)