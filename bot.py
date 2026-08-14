#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مدیریت تسک‌های شخصی - نسخه نهایی
"""

import os
import logging
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    MenuButtonCommands
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

from config import Config
from models import get_session, User, TaskSubmission, UserProgress
from utils.helpers import (
    get_progress_bar, validate_email, format_date
)


# ============================================
# کیبوردها - فقط Inline
# ============================================

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 ثبت تسک جدید", callback_data="new_task")],
        [InlineKeyboardButton("📊 وضعیت من", callback_data="view_status")],
        [InlineKeyboardButton("📋 تسک‌های من", callback_data="my_tasks")],
        [InlineKeyboardButton("📄 گزارش کامل", callback_data="my_report")],
        [InlineKeyboardButton("🔄 تغییر موضوع", callback_data="change_topic")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_topic_keyboard(topics=None):
    if topics is None:
        topics = Config.load_topics()

    keyboard = []
    for key, topic in topics.items():
        if topic.get('is_active', True):
            keyboard.append([InlineKeyboardButton(
                f"{topic['emoji']} {topic['name']} ({topic['tasks_needed']} تسک)",
                callback_data=f"topic_{key}"
            )])
    keyboard.append([InlineKeyboardButton("➕ موضوع جدید", callback_data="add_new_topic")])
    keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)


# ============================================
# وضعیت‌های مکالمه
# ============================================
(WAITING_FOR_EMAIL, WAITING_FOR_TOPIC, WAITING_FOR_TASK_COUNT,
 WAITING_FOR_TASK_CODE, WAITING_FOR_SCREENSHOT, WAITING_FOR_VOICE,
 WAITING_FOR_NEW_TOPIC_NAME, WAITING_FOR_NEW_TOPIC_TASKS) = range(8)

# ============================================
# تنظیمات لاگینگ
# ============================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL),
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================
# دستورات اصلی
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # تنظیم منوی شیشه‌ای
    try:
        await context.bot.set_chat_menu_button(
            chat_id=user_id,
            menu_button=MenuButtonCommands()
        )
        print(f"✅ منوی شیشه‌ای برای کاربر {user_id} تنظیم شد")
    except Exception as e:
        print(f"⚠️ خطا در تنظیم منوی شیشه‌ای: {e}")

    session = get_session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if user and user.is_active:
        progress_bar = get_progress_bar(user)

        await update.message.reply_text(
            f"✅ **خوش برگشتی {user.full_name}!**\n\n"
            f"📚 **موضوع:** {user.topic}\n"
            f"📊 **تسک‌های باقی‌مانده:** {user.remaining_tasks} از {user.total_tasks}\n"
            f"📈 **پیشرفت:** {progress_bar} {user.get_progress_percentage():.1f}%\n\n"
            "از دکمه‌های زیر استفاده کنید:",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        session.close()
        return

    # کاربر جدید
    context.user_data['registration'] = {}
    await update.message.reply_text(
        "🆕 **ثبت‌نام در ربات**\n\n"
        "📧 **ایمیل خود را وارد کنید:**",
        parse_mode='Markdown'
    )
    session.close()
    return WAITING_FOR_EMAIL


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


# ============================================
# ثبت‌نام
# ============================================

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text
    if email == "/cancel":
        await cancel(update, context)
        return ConversationHandler.END
    if not validate_email(email):
        await update.message.reply_text("❌ ایمیل نامعتبر! دوباره وارد کنید:")
        return WAITING_FOR_EMAIL

    context.user_data['registration']['email'] = email

    topics = Config.load_topics()
    active_topics = {k: v for k, v in topics.items() if v.get('is_active', True)}
    await update.message.reply_text(
        "📚 **موضوع خود را انتخاب کنید:**\n\n"
        "⚠️ اگر موضوع مورد نظر را پیدا نکردید، روی دکمه ➕ موضوع جدید کلیک کنید.",
        reply_markup=get_topic_keyboard(active_topics),
        parse_mode='Markdown'
    )
    return WAITING_FOR_TOPIC


async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ ثبت‌نام لغو شد.")
        return ConversationHandler.END

    if query.data == "add_new_topic":
        await query.edit_message_text(
            "➕ **افزودن موضوع جدید**\n\n"
            "📝 **نام موضوع را وارد کنید:**",
            parse_mode='Markdown'
        )
        return WAITING_FOR_NEW_TOPIC_NAME

    topic_key = query.data.split('_')[1]
    topics = Config.load_topics()
    topic_info = topics.get(topic_key)

    if not topic_info or not topic_info.get('is_active', True):
        await query.edit_message_text("❌ موضوع نامعتبر!")
        return ConversationHandler.END

    context.user_data['registration']['topic_key'] = topic_key
    context.user_data['registration']['topic_info'] = topic_info
    context.user_data['telegram_id'] = update.effective_user.id
    context.user_data['full_name'] = query.from_user.full_name

    await query.edit_message_text(
        f"✅ موضوع **{topic_info['name']}** انتخاب شد.\n\n"
        "✏️ **تعداد تسک‌ها را وارد کنید:**\n"
        "(مثلاً: ۱۰۰، ۲۰۰، ۵۰۰، ۱۰۰۰)",
        parse_mode='Markdown'
    )
    return WAITING_FOR_TASK_COUNT


async def handle_new_topic_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if name == "/cancel":
        await update.message.reply_text("❌ لغو شد.")
        return ConversationHandler.END

    context.user_data['new_topic_name'] = name
    await update.message.reply_text(
        f"✅ نام **{name}** ثبت شد.\n\n"
        "📊 **تعداد تسک‌های این موضوع را وارد کنید:**",
        parse_mode='Markdown'
    )
    return WAITING_FOR_NEW_TOPIC_TASKS


async def handle_new_topic_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = update.message.text
    if tasks == "/cancel":
        await update.message.reply_text("❌ لغو شد.")
        return ConversationHandler.END

    try:
        tasks_needed = int(tasks)
        if tasks_needed <= 0:
            raise ValueError
    except:
        await update.message.reply_text("❌ عدد نامعتبر!")
        return WAITING_FOR_NEW_TOPIC_TASKS

    topics = Config.load_topics()
    max_id = max([int(k) for k in topics.keys() if k.isdigit()] or [0])
    new_id = str(max_id + 1)

    topics[new_id] = {
        'name': context.user_data['new_topic_name'],
        'tasks_needed': tasks_needed,
        'emoji': '📌',
        'is_active': True
    }
    Config.save_topics(topics)
    Config.TOPICS = topics

    topic_info = topics[new_id]
    context.user_data['registration']['topic_key'] = new_id
    context.user_data['registration']['topic_info'] = topic_info
    context.user_data['telegram_id'] = update.effective_user.id
    context.user_data['full_name'] = update.effective_user.full_name

    await update.message.reply_text(
        f"✅ **موضوع جدید اضافه شد!** 🎉\n\n"
        f"🔹 {topic_info['emoji']} {topic_info['name']}\n"
        f"📊 {topic_info['tasks_needed']} تسک\n\n"
        "✏️ **تعداد تسک‌های مورد نظر خود را وارد کنید:**",
        parse_mode='Markdown'
    )
    return WAITING_FOR_TASK_COUNT


async def handle_task_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "/cancel":
        await update.message.reply_text("❌ لغو شد.")
        return ConversationHandler.END

    try:
        tasks_needed = int(text)
        if tasks_needed < 1 or tasks_needed > 10000:
            raise ValueError
    except:
        await update.message.reply_text("❌ عدد نامعتبر! (۱ تا ۱۰۰۰۰)")
        return WAITING_FOR_TASK_COUNT

    registration = context.user_data.get('registration', {})
    telegram_id = context.user_data.get('telegram_id') or update.effective_user.id
    full_name = context.user_data.get('full_name') or update.effective_user.full_name

    topic_info = registration.get('topic_info')
    if not topic_info:
        await update.message.reply_text("❌ اطلاعات ثبت‌نام ناقص است. /start کنید.")
        return ConversationHandler.END

    session = get_session()

    existing = session.query(User).filter_by(telegram_id=telegram_id).first()
    if existing:
        session.delete(existing)
        session.commit()

    user = User(
        telegram_id=telegram_id,
        username=update.effective_user.username or "کاربر",
        full_name=full_name,
        phone="-",
        email=registration.get('email', ''),
        topic=topic_info['name'],
        topic_key=registration.get('topic_key'),
        remaining_tasks=tasks_needed,
        total_tasks=tasks_needed,
        is_active=True
    )
    session.add(user)
    session.commit()

    progress = UserProgress(user_id=user.id)
    session.add(progress)
    session.commit()

    user_data = {
        'full_name': user.full_name,
        'topic': user.topic,
        'total': user.total_tasks
    }
    session.close()

    context.user_data.clear()

    msg = f"✅ **ثبت‌نام کامل شد!** 🎉\n\n👤 {user_data['full_name']}\n📚 {user_data['topic']}\n📊 {user_data['total']} تسک\n\nاز دکمه‌های زیر استفاده کنید:"

    await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    return ConversationHandler.END


# ============================================
# ثبت تسک جدید
# ============================================

async def new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    session = get_session()
    user = session.query(User).filter_by(telegram_id=user_id, is_active=True).first()

    if not user:
        msg = "❌ ثبت‌نام نکرده‌اید. /start کنید."
        if update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(msg, reply_markup=get_main_keyboard())
        session.close()
        return

    if user.remaining_tasks <= 0:
        msg = "🎉 **تبریک!** تمام تسک‌ها را کامل کردید!"
        if update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        session.close()
        return

    context.user_data['task_user_id'] = user.id
    progress_bar = get_progress_bar(user)
    user_topic = user.topic
    user_remaining = user.remaining_tasks
    session.close()

    msg = (
        f"📝 **ثبت تسک جدید**\n\n"
        f"📚 {user_topic}\n"
        f"📊 {user_remaining} تسک باقی‌مانده\n"
        f"📈 {progress_bar}\n\n"
        "🔢 **کد تسک را وارد کنید:**"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, parse_mode='Markdown')

    return WAITING_FOR_TASK_CODE


async def handle_task_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_code = update.message.text.strip()

    if task_code == "/cancel":
        await cancel(update, context)
        return ConversationHandler.END

    context.user_data['task_code'] = task_code

    await update.message.reply_text(
        f"✅ کد **{task_code}** ثبت شد.\n\n"
        "📸 **لطفاً اسکرین‌شات ارسال کنید:**",
        parse_mode='Markdown'
    )

    return WAITING_FOR_SCREENSHOT


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً یک تصویر ارسال کنید:")
        return WAITING_FOR_SCREENSHOT

    photo = update.message.photo[-1]
    context.user_data['screenshot_file_id'] = photo.file_id

    await update.message.reply_text(
        "✅ **اسکرین‌شات دریافت شد.**\n\n"
        "🎤 **ویس توضیحی ارسال کنید:**",
        parse_mode='Markdown'
    )
    return WAITING_FOR_VOICE


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.voice:
        await update.message.reply_text("❌ لطفاً یک پیام صوتی ارسال کنید:")
        return WAITING_FOR_VOICE

    voice = update.message.voice

    user_id = context.user_data.get('task_user_id')
    if not user_id:
        await update.message.reply_text("❌ خطا! دوباره /newtask بزنید.")
        return ConversationHandler.END

    session = get_session()
    user = session.query(User).filter_by(id=user_id, is_active=True).first()

    if not user:
        await update.message.reply_text("❌ کاربر یافت نشد!")
        session.close()
        return

    # ایجاد تسک جدید
    task = TaskSubmission(
        user_id=user.id,
        task_code=context.user_data.get('task_code', 'UNKNOWN'),
        screenshot_file_id=context.user_data.get('screenshot_file_id', ''),
        voice_file_id=voice.file_id,
        voice_duration=voice.duration,
        submission_date=datetime.now(),
        status='approved'
    )
    session.add(task)
    user.remaining_tasks -= 1
    user.last_activity = datetime.now()
    session.commit()

    # به‌روزرسانی پیشرفت
    progress = session.query(UserProgress).filter_by(user_id=user.id).first()
    if progress:
        progress.total_submissions += 1
        progress.approved_count += 1
        progress.last_submission_date = datetime.now()
        session.commit()

    remaining = user.remaining_tasks
    total = user.total_tasks
    progress_bar = get_progress_bar(user)
    progress_pct = user.get_progress_percentage()
    task_code = task.task_code
    task_screenshot = task.screenshot_file_id
    task_voice = task.voice_file_id
    task_date = task.submission_date
    user_name = user.full_name
    user_topic = user.topic
    user_email = user.email

    session.close()

    # ============================================
    # ارسال به کانال
    # ============================================
    channel_id = Config.CHANNEL_ID

    if channel_id:
        try:
            channel_message = (
                f"📋 **تسک جدید**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔢 **شماره:** {task_code}\n"
                f"📚 **موضوع:** {user_topic}\n"
                f"📊 **باقی‌مانده:** {remaining}/{total}\n"
                f"📅 **تاریخ:** {format_date(task_date)}"
            )

            await context.bot.send_message(
                chat_id=channel_id,
                text=channel_message,
                parse_mode='Markdown'
            )

            await context.bot.send_photo(
                chat_id=channel_id,
                photo=task_screenshot,
                caption=f"📸 اسکرین‌شات - {task_code}"
            )

            await context.bot.send_voice(
                chat_id=channel_id,
                voice=task_voice,
                caption=f"🎤 پیام صوتی - {task_code}"
            )

            print(f"✅ تسک {task_code} به کانال ارسال شد")

            await update.message.reply_text(
                f"✅ تسک {task_code} ثبت شد.",
                reply_markup=get_main_keyboard()
            )

        except Exception as e:
            print(f"⚠️ خطا در ارسال به کانال: {e}")
            await update.message.reply_text(
                f"✅ تسک {task_code} ثبت شد.",
                reply_markup=get_main_keyboard()
            )
    else:
        await update.message.reply_text(
            f"✅ تسک {task_code} ثبت شد.",
            reply_markup=get_main_keyboard()
        )

    context.user_data.clear()

    if remaining == 0:
        await update.message.reply_text(
            f"🎉 **تبریک!** تمام {total} تسک را کامل کردید!",
            parse_mode='Markdown'
        )

    return ConversationHandler.END


# ============================================
# تغییر موضوع
# ============================================

async def show_change_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    else:
        query = None

    topics = Config.load_topics()
    active_topics = {k: v for k, v in topics.items() if v.get('is_active', True)}

    msg = (
        "🔄 **تغییر موضوع**\n\n"
        "⚠️ **توجه:**\n"
        "• تسک‌های قبلی شما **باقی می‌مانند**\n"
        "• تعداد تسک‌های باقی‌مانده بر اساس **موضوع جدید** محاسبه می‌شود\n\n"
        "📌 اگر موضوع مورد نظر را پیدا نکردید، روی دکمه ➕ موضوع جدید کلیک کنید."
    )

    if query:
        await query.edit_message_text(msg, reply_markup=get_topic_keyboard(active_topics), parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=get_topic_keyboard(active_topics), parse_mode='Markdown')


async def change_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_change_topic(update, context)


async def handle_change_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ لغو شد.", reply_markup=get_main_keyboard())
        return

    if query.data == "add_new_topic":
        await query.edit_message_text(
            "➕ **افزودن موضوع جدید**\n\n"
            "📝 **نام موضوع را وارد کنید:**",
            parse_mode='Markdown'
        )
        return WAITING_FOR_NEW_TOPIC_NAME

    topic_key = query.data.split('_')[1]
    topics = Config.load_topics()
    topic_info = topics.get(topic_key)

    if not topic_info or not topic_info.get('is_active', True):
        await query.edit_message_text("❌ موضوع نامعتبر!")
        return

    user_id = update.effective_user.id
    session = get_session()
    user = session.query(User).filter_by(telegram_id=user_id, is_active=True).first()

    if not user:
        await query.edit_message_text("❌ کاربر یافت نشد!")
        session.close()
        return

    done_tasks = user.total_tasks - user.remaining_tasks
    old_topic = user.topic
    new_tasks = topic_info['tasks_needed']
    new_remaining = max(0, new_tasks - done_tasks)

    user.topic = topic_info['name']
    user.topic_key = topic_key
    user.total_tasks = new_tasks
    user.remaining_tasks = new_remaining
    session.commit()
    session.close()

    await query.edit_message_text(
        f"✅ **موضوع تغییر کرد!**\n\n"
        f"📚 **قبلی:** {old_topic}\n"
        f"📚 **جدید:** {topic_info['name']}\n"
        f"📊 **انجام شده:** {done_tasks}\n"
        f"📊 **باقی‌مانده:** {new_remaining}\n\n"
        "از دکمه‌های زیر استفاده کنید:",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )


# ============================================
# وضعیت و گزارش
# ============================================

async def view_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
    else:
        user_id = update.effective_user.id

    session = get_session()
    user = session.query(User).filter_by(telegram_id=user_id, is_active=True).first()

    if not user:
        msg = "❌ ثبت‌نام نکرده‌اید."
        if update.callback_query:
            await query.edit_message_text(msg, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(msg, reply_markup=get_main_keyboard())
        session.close()
        return

    tasks = session.query(TaskSubmission).filter_by(user_id=user.id).all()
    total = len(tasks)
    approved = len([t for t in tasks if t.status == 'approved'])
    pending = len([t for t in tasks if t.status == 'pending'])

    recent = session.query(TaskSubmission).filter_by(user_id=user.id).order_by(
        TaskSubmission.submission_date.desc()
    ).limit(5).all()

    progress_bar = get_progress_bar(user)
    msg = (
        f"📊 **وضعیت شما**\n━━━━━━━━━━━━━━━━━━\n"
        f"👤 {user.full_name}\n"
        f"📧 {user.email}\n"
        f"📚 {user.topic}\n"
        f"📈 {progress_bar} {user.get_progress_percentage():.1f}%\n"
        f"📊 {user.remaining_tasks}/{user.total_tasks}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 آمار:\n"
        f"• کل: {total}\n"
        f"• ✅ تکمیل: {approved}\n"
        f"• ⏳ در انتظار: {pending}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📅 ثبت‌نام: {format_date(user.created_at)}"
    )

    if recent:
        msg += "\n\n📌 **۵ تسک آخر:**\n"
        for t in recent:
            emoji = '✅' if t.status == 'approved' else '⏳' if t.status == 'pending' else '❌'
            msg += f"  {emoji} {t.task_code} - {format_date(t.submission_date)}\n"

    session.close()

    if update.callback_query:
        await query.edit_message_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_status(update, context)


async def my_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
    else:
        user_id = update.effective_user.id

    session = get_session()
    user = session.query(User).filter_by(telegram_id=user_id, is_active=True).first()

    if not user:
        msg = "❌ ثبت‌نام نکرده‌اید."
        if update.callback_query:
            await query.edit_message_text(msg, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(msg, reply_markup=get_main_keyboard())
        session.close()
        return

    all_tasks = session.query(TaskSubmission).filter_by(user_id=user.id).order_by(
        TaskSubmission.submission_date.desc()
    ).all()

    total = len(all_tasks)
    approved = len([t for t in all_tasks if t.status == 'approved'])
    pending = len([t for t in all_tasks if t.status == 'pending'])

    progress_bar = get_progress_bar(user)

    report = (
        f"📄 **گزارش {user.full_name}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📧 {user.email}\n"
        f"📚 {user.topic}\n"
        f"📈 {progress_bar} {user.get_progress_percentage():.1f}%\n"
        f"📊 {user.remaining_tasks}/{user.total_tasks}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 خلاصه:\n"
        f"   • کل: {total}\n"
        f"   • ✅ تکمیل: {approved}\n"
        f"   • ⏳ در انتظار: {pending}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if all_tasks:
        report += "📌 **لیست تسک‌ها:**\n"
        for idx, t in enumerate(all_tasks, 1):
            emoji = '✅' if t.status == 'approved' else '⏳' if t.status == 'pending' else '❌'
            status_text = {'approved': 'تکمیل', 'pending': 'در انتظار'}.get(t.status, 'نامشخص')
            report += f"   {idx}. {emoji} **{t.task_code}**\n"
            report += f"      📅 {format_date(t.submission_date)}\n"
            report += f"      📊 {status_text}\n"
            report += f"      🎤 {t.voice_duration} ثانیه\n"
    else:
        report += "📭 **هیچ تسکی ثبت نشده.**"

    report += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📅 {format_date(datetime.now())}"
    session.close()

    if len(report) > 4096:
        parts = [report[i:i + 4000] for i in range(0, len(report), 4000)]
        for part in parts:
            if update.callback_query:
                await query.message.reply_text(part, parse_mode='Markdown')
            else:
                await update.message.reply_text(part, parse_mode='Markdown')
    else:
        if update.callback_query:
            await query.edit_message_text(report, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        else:
            await update.message.reply_text(report, reply_markup=get_main_keyboard(), parse_mode='Markdown')


async def view_my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
    else:
        user_id = update.effective_user.id

    session = get_session()
    user = session.query(User).filter_by(telegram_id=user_id, is_active=True).first()

    if not user:
        msg = "❌ ثبت‌نام نکرده‌اید."
        if update.callback_query:
            await query.edit_message_text(msg, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(msg, reply_markup=get_main_keyboard())
        session.close()
        return

    page = context.user_data.get('task_page', 0)
    per_page = 5

    tasks = session.query(TaskSubmission).filter_by(user_id=user.id).order_by(
        TaskSubmission.submission_date.desc()
    ).offset(page * per_page).limit(per_page).all()

    total_tasks = session.query(TaskSubmission).filter_by(user_id=user.id).count()
    total_pages = (total_tasks + per_page - 1) // per_page if total_tasks > 0 else 1

    if not tasks:
        session.close()
        msg = "📭 **هیچ تسکی ثبت نشده.**"
        if update.callback_query:
            await query.edit_message_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        return

    msg = f"📋 **تسک‌ها** (صفحه {page + 1}/{total_pages})\n━━━━━━━━━━━━━━━━━━\n"
    for idx, t in enumerate(tasks, start=page * per_page + 1):
        emoji = '✅' if t.status == 'approved' else '⏳' if t.status == 'pending' else '❌'
        status_text = {'approved': 'تکمیل ✅', 'pending': 'در انتظار ⏳'}.get(t.status, 'نامشخص')
        msg += f"{idx}. 🔢 **{t.task_code}** {emoji}\n"
        msg += f"   📅 {format_date(t.submission_date)}\n"
        msg += f"   📊 {status_text}\n"
        msg += f"   🎤 {t.voice_duration} ثانیه\n"
        msg += "   ──────────────────\n"

    session.close()

    keyboard = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data="prev_page"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data="next_page"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])

    if update.callback_query:
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_my_tasks(update, context)


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    else:
        query = None

    help_text = (
        "❓ **راهنما**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔹 **/start** - شروع و ثبت‌نام\n"
        "🔹 **/newtask** - ثبت تسک جدید\n"
        "🔹 **/status** - مشاهده وضعیت\n"
        "🔹 **/mytasks** - لیست تسک‌ها\n"
        "🔹 **/report** - گزارش کامل\n"
        "🔹 **/help** - راهنما\n"
        "🔹 **/cancel** - لغو عملیات\n\n"
        "💡 از دکمه‌های زیر استفاده کنید.\n\n"
        "📌 **نکات:**\n"
        "• شما می‌توانید **موضوع جدید** خود را اضافه کنید.\n"
        "• پس از ثبت هر تسک، به **کانال** ارسال می‌شود."
    )

    if query:
        await query.edit_message_text(help_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_help(update, context)


async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    page = context.user_data.get('task_page', 0)
    if query.data == "next_page":
        context.user_data['task_page'] = page + 1
    elif query.data == "prev_page":
        context.user_data['task_page'] = max(0, page - 1)

    await view_my_tasks(update, context)


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session()
    user = session.query(User).filter_by(telegram_id=user_id, is_active=True).first()

    if user:
        progress_bar = get_progress_bar(user)
        msg = f"🔙 **منوی اصلی**\n\n👤 {user.full_name}\n📚 {user.topic}\n📊 {user.remaining_tasks}/{user.total_tasks}\n📈 {progress_bar} {user.get_progress_percentage():.1f}%\n\nاز دکمه‌های زیر استفاده کنید:"
        session.close()
    else:
        msg = "🔙 **منوی اصلی**"

    await query.edit_message_text(msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')


# ============================================
# راه‌اندازی
# ============================================

def main():
    if not Config.TELEGRAM_TOKEN:
        print("❌ توکن ربات تنظیم نشده!")
        return

    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    application = Application.builder().token(Config.TELEGRAM_TOKEN).build()

    # تنظیم منوی شیشه‌ای
    try:
        application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        print("✅ منوی شیشه‌ای تنظیم شد!")
    except Exception as e:
        print(f"⚠️ خطا در تنظیم منوی شیشه‌ای: {e}")

    # ============================================
    # هندلر ثبت‌نام
    # ============================================
    register_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_FOR_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
            WAITING_FOR_TOPIC: [
                CallbackQueryHandler(handle_topic_selection, pattern='^(topic_\\d+|add_new_topic|cancel)$')],
            WAITING_FOR_NEW_TOPIC_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_topic_name)],
            WAITING_FOR_NEW_TOPIC_TASKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_topic_tasks)],
            WAITING_FOR_TASK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_count)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # ============================================
    # هندلر تغییر موضوع
    # ============================================
    change_topic_handler = ConversationHandler(
        entry_points=[
            CommandHandler('change_topic', change_topic),
            CallbackQueryHandler(change_topic, pattern='^change_topic$')
        ],
        states={
            WAITING_FOR_NEW_TOPIC_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_topic_name)],
            WAITING_FOR_NEW_TOPIC_TASKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_topic_tasks)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # ============================================
    # هندلر تسک
    # ============================================
    task_handler = ConversationHandler(
        entry_points=[
            CommandHandler('newtask', new_task),
            CallbackQueryHandler(new_task, pattern='^new_task$')
        ],
        states={
            WAITING_FOR_TASK_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_code)
            ],
            WAITING_FOR_SCREENSHOT: [
                MessageHandler(filters.PHOTO, handle_screenshot)
            ],
            WAITING_FOR_VOICE: [
                MessageHandler(filters.VOICE, handle_voice)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False,
    )

    # ============================================
    # اضافه کردن هندلرها
    # ============================================
    application.add_handler(register_handler)
    application.add_handler(change_topic_handler)
    application.add_handler(task_handler)

    # دکمه‌های Inline
    application.add_handler(CallbackQueryHandler(new_task, pattern='^new_task$'))
    application.add_handler(CallbackQueryHandler(view_status, pattern='^view_status$'))
    application.add_handler(CallbackQueryHandler(view_my_tasks, pattern='^my_tasks$'))
    application.add_handler(CallbackQueryHandler(my_report, pattern='^my_report$'))
    application.add_handler(CallbackQueryHandler(show_help, pattern='^help$'))
    application.add_handler(CallbackQueryHandler(show_change_topic, pattern='^change_topic$'))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
    application.add_handler(CallbackQueryHandler(handle_change_topic, pattern='^(topic_\\d+|add_new_topic|cancel)$'))
    application.add_handler(CallbackQueryHandler(handle_pagination, pattern='^(next_page|prev_page)$'))

    # دستورات
    application.add_handler(CommandHandler('status', status))
    application.add_handler(CommandHandler('mytasks', my_tasks))
    application.add_handler(CommandHandler('report', my_report))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('cancel', cancel))

    print("🤖 ربات در حال اجرا است...")
    print(f"📢 کانال: {Config.CHANNEL_ID}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()