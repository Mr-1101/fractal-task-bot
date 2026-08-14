# handlers/admin_panel.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import Config
from models import get_session, User, TaskSubmission

# وضعیت‌های مدیریت
(ADMIN_MENU, ADD_TOPIC_NAME, ADD_TOPIC_TASKS, ADD_TOPIC_EMOJI,
 EDIT_TOPIC_SELECT, EDIT_TOPIC_NAME, EDIT_TOPIC_TASKS, EDIT_TOPIC_EMOJI,
 DELETE_TOPIC_CONFIRM, VIEW_STATS) = range(10)


def is_admin(user_id):
    """بررسی ادمین بودن کاربر"""
    return user_id in Config.ADMIN_IDS


def get_admin_keyboard():
    """کیبورد مدیریت ادمین"""
    keyboard = [
        [InlineKeyboardButton("📋 لیست موضوعات", callback_data="admin_list_topics")],
        [InlineKeyboardButton("➕ اضافه کردن موضوع جدید", callback_data="admin_add_topic")],
        [InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_stats")],
        [InlineKeyboardButton("📈 گزارش کلی", callback_data="admin_report")],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_topic_management_keyboard(topic_id, topic_data):
    """کیبورد مدیریت یک موضوع خاص"""
    keyboard = [
        [InlineKeyboardButton(f"✏️ ویرایش {topic_data['name']}", callback_data=f"admin_edit_topic_{topic_id}")],
        [InlineKeyboardButton(f"🗑️ حذف {topic_data['name']}", callback_data=f"admin_delete_topic_{topic_id}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="admin_list_topics")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ورود به پنل مدیریت"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ شما دسترسی ادمین ندارید!")
        return

    await update.message.reply_text(
        "👑 **پنل مدیریت**\n\n"
        "از دکمه‌های زیر برای مدیریت استفاده کنید:",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )


async def admin_list_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست موضوعات برای مدیریت"""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.edit_message_text("⛔ شما دسترسی ادمین ندارید!")
        return

    topics = Config.load_topics()

    if not topics:
        await query.edit_message_text(
            "📭 هیچ موضوعی تعریف نشده است.\n"
            "از دکمه ➕ اضافه کردن موضوع جدید استفاده کنید.",
            reply_markup=get_admin_keyboard()
        )
        return

    message = "📋 **لیست موضوعات**\n━━━━━━━━━━━━━━━━━━\n"
    for key, topic in topics.items():
        status = "✅ فعال" if topic.get('is_active', True) else "❌ غیرفعال"
        message += (
            f"🔹 **{topic['emoji']} {topic['name']}**\n"
            f"   🆔 {key}\n"
            f"   📊 تعداد تسک‌ها: {topic['tasks_needed']}\n"
            f"   📝 {topic.get('description', '')}\n"
            f"   📌 وضعیت: {status}\n"
            f"   ──────────────────\n"
        )

    # دکمه‌های مدیریت هر موضوع
    keyboard = []
    for key, topic in topics.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{topic['emoji']} مدیریت {topic['name']}",
                callback_data=f"admin_manage_topic_{key}"
            )
        ])

    keyboard.append([InlineKeyboardButton("➕ اضافه کردن موضوع جدید", callback_data="admin_add_topic")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin")])

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def admin_manage_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت یک موضوع خاص"""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.edit_message_text("⛔ شما دسترسی ادمین ندارید!")
        return

    topic_id = query.data.split('_')[3]
    topics = Config.load_topics()
    topic = topics.get(topic_id)

    if not topic:
        await query.edit_message_text("❌ موضوع یافت نشد!")
        return

    message = (
        f"📋 **مدیریت موضوع**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔹 **نام:** {topic['name']}\n"
        f"🆔 **آیدی:** {topic_id}\n"
        f"📊 **تعداد تسک‌ها:** {topic['tasks_needed']}\n"
        f"📝 **توضیحات:** {topic.get('description', '')}\n"
        f"📌 **وضعیت:** {'✅ فعال' if topic.get('is_active', True) else '❌ غیرفعال'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"عملیات مورد نظر را انتخاب کنید:"
    )

    await query.edit_message_text(
        message,
        reply_markup=get_topic_management_keyboard(topic_id, topic),
        parse_mode='Markdown'
    )


async def admin_add_topic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند اضافه کردن موضوع جدید"""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.edit_message_text("⛔ شما دسترسی ادمین ندارید!")
        return

    await query.edit_message_text(
        "➕ **اضافه کردن موضوع جدید**\n\n"
        "لطفاً **نام** موضوع را وارد کنید:\n"
        "(برای لغو /cancel)",
        parse_mode='Markdown'
    )
    return ADD_TOPIC_NAME


async def admin_add_topic_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام موضوع جدید"""
    name = update.message.text

    if name == "/cancel":
        await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END

    context.user_data['new_topic_name'] = name

    await update.message.reply_text(
        f"✅ نام **{name}** ثبت شد.\n\n"
        "📊 **تعداد تسک‌ها** را وارد کنید:\n"
        "(مثلاً: 500)",
        parse_mode='Markdown'
    )
    return ADD_TOPIC_TASKS


async def admin_add_topic_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت تعداد تسک‌های موضوع جدید"""
    tasks = update.message.text

    if tasks == "/cancel":
        await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END

    try:
        tasks_needed = int(tasks)
        if tasks_needed <= 0:
            raise ValueError
    except:
        await update.message.reply_text(
            "❌ تعداد نامعتبر! لطفاً یک عدد مثبت وارد کنید:"
        )
        return ADD_TOPIC_TASKS

    context.user_data['new_topic_tasks'] = tasks_needed

    await update.message.reply_text(
        f"✅ تعداد تسک‌ها: **{tasks_needed}**\n\n"
        "🎨 **ایموجی** موضوع را وارد کنید:\n"
        "(مثلاً: 🐍 یا 📚)",
        parse_mode='Markdown'
    )
    return ADD_TOPIC_EMOJI


async def admin_add_topic_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت ایموجی موضوع جدید و ذخیره آن"""
    emoji = update.message.text

    if emoji == "/cancel":
        await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END

    # ذخیره موضوع جدید
    topics = Config.load_topics()

    # پیدا کردن جدیدترین آیدی
    max_id = 0
    for key in topics.keys():
        try:
            if int(key) > max_id:
                max_id = int(key)
        except:
            pass

    new_id = str(max_id + 1)

    topics[new_id] = {
        'name': context.user_data['new_topic_name'],
        'tasks_needed': context.user_data['new_topic_tasks'],
        'emoji': emoji,
        'description': context.user_data.get('new_topic_description', ''),
        'is_active': True
    }

    Config.save_topics(topics)
    Config.TOPICS = topics  # به‌روزرسانی کش

    # به‌روزرسانی مدل‌های کاربران (اختیاری)
    # session = get_session()
    # users = session.query(User).all()
    # برای کاربرانی که موضوع قبلی داشتند، می‌توانیم تغییر دهیم
    # session.close()

    await update.message.reply_text(
        f"✅ **موضوع جدید با موفقیت اضافه شد!** 🎉\n\n"
        f"🔹 **نام:** {topics[new_id]['name']}\n"
        f"🆔 **آیدی:** {new_id}\n"
        f"📊 **تعداد تسک‌ها:** {topics[new_id]['tasks_needed']}\n"
        f"🎨 **ایموجی:** {topics[new_id]['emoji']}\n\n"
        "از دکمه‌های زیر استفاده کنید:",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


async def admin_edit_topic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ویرایش موضوع"""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.edit_message_text("⛔ شما دسترسی ادمین ندارید!")
        return

    topic_id = query.data.split('_')[3]
    context.user_data['editing_topic_id'] = topic_id
    topics = Config.load_topics()
    topic = topics.get(topic_id)

    if not topic:
        await query.edit_message_text("❌ موضوع یافت نشد!")
        return

    keyboard = [
        [InlineKeyboardButton("✏️ ویرایش نام", callback_data=f"admin_edit_name_{topic_id}")],
        [InlineKeyboardButton("✏️ ویرایش تعداد تسک‌ها", callback_data=f"admin_edit_tasks_{topic_id}")],
        [InlineKeyboardButton("✏️ ویرایش ایموجی", callback_data=f"admin_edit_emoji_{topic_id}")],
        [InlineKeyboardButton("✏️ ویرایش توضیحات", callback_data=f"admin_edit_desc_{topic_id}")],
        [InlineKeyboardButton("🔄 تغییر وضعیت", callback_data=f"admin_toggle_status_{topic_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin_manage_topic_{topic_id}")]
    ]

    await query.edit_message_text(
        f"✏️ **ویرایش موضوع**\n\n"
        f"🔹 {topic['emoji']} {topic['name']}\n"
        f"📊 تعداد: {topic['tasks_needed']}\n"
        f"📝 توضیحات: {topic.get('description', '')}\n"
        f"📌 وضعیت: {'✅ فعال' if topic.get('is_active', True) else '❌ غیرفعال'}\n\n"
        "قسمت مورد نظر برای ویرایش را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def admin_edit_topic_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ویرایش یک فیلد خاص از موضوع"""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.edit_message_text("⛔ شما دسترسی ادمین ندارید!")
        return

    action, field, topic_id = query.data.split('_')
    context.user_data['editing_topic_id'] = topic_id
    context.user_data['editing_field'] = field

    field_names = {
        'name': 'نام',
        'tasks': 'تعداد تسک‌ها',
        'emoji': 'ایموجی',
        'desc': 'توضیحات'
    }

    await query.edit_message_text(
        f"✏️ **ویرایش {field_names.get(field, field)}**\n\n"
        f"مقدار جدید را وارد کنید:\n"
        f"(برای لغو /cancel)",
        parse_mode='Markdown'
    )
    return EDIT_TOPIC_NAME if field == 'name' else EDIT_TOPIC_TASKS if field == 'tasks' else EDIT_TOPIC_EMOJI


async def admin_save_topic_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره تغییرات ویرایش موضوع"""
    value = update.message.text

    if value == "/cancel":
        await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END

    topic_id = context.user_data['editing_topic_id']
    field = context.user_data['editing_field']
    topics = Config.load_topics()

    if topic_id not in topics:
        await update.message.reply_text("❌ موضوع یافت نشد!")
        return ConversationHandler.END

    # اعتبارسنجی
    if field == 'tasks':
        try:
            value = int(value)
            if value <= 0:
                raise ValueError
        except:
            await update.message.reply_text("❌ تعداد نامعتبر! لطفاً یک عدد مثبت وارد کنید:")
            return
    elif field == 'emoji':
        # اعتبارسنجی ایموجی (ساده)
        if len(value) > 2:
            await update.message.reply_text("❌ لطفاً یک ایموجی معتبر وارد کنید (مثلاً: 🐍):")
            return

    # ذخیره تغییرات
    field_names = {
        'name': 'name',
        'tasks': 'tasks_needed',
        'emoji': 'emoji',
        'desc': 'description'
    }

    topics[topic_id][field_names[field]] = value
    Config.save_topics(topics)
    Config.TOPICS = topics

    await update.message.reply_text(
        f"✅ **تغییرات با موفقیت ذخیره شد!**\n\n"
        f"🔹 {topics[topic_id]['emoji']} {topics[topic_id]['name']}\n"
        f"📊 تعداد: {topics[topic_id]['tasks_needed']}\n"
        f"📝 توضیحات: {topics[topic_id].get('description', '')}",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


async def admin_toggle_topic_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر وضعیت فعال/غیرفعال موضوع"""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.edit_message_text("⛔ شما دسترسی ادمین ندارید!")
        return

    topic_id = query.data.split('_')[3]
    topics = Config.load_topics()

    if topic_id not in topics:
        await query.edit_message_text("❌ موضوع یافت نشد!")
        return

    # تغییر وضعیت
    current_status = topics[topic_id].get('is_active', True)
    topics[topic_id]['is_active'] = not current_status
    Config.save_topics(topics)
    Config.TOPICS = topics

    status_text = "فعال ✅" if topics[topic_id]['is_active'] else "غیرفعال ❌"

    await query.edit_message_text(
        f"✅ **وضعیت موضوع تغییر کرد!**\n\n"
        f"🔹 {topics[topic_id]['emoji']} {topics[topic_id]['name']}\n"
        f"📌 وضعیت جدید: {status_text}",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کلی"""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.edit_message_text("⛔ شما دسترسی ادمین ندارید!")
        return

    session = get_session()

    # آمار کاربران
    total_users = session.query(User).filter_by(is_active=True).count()
    total_tasks = session.query(TaskSubmission).count()
    approved_tasks = session.query(TaskSubmission).filter_by(status='approved').count()
    pending_tasks = session.query(TaskSubmission).filter_by(status='pending').count()
    rejected_tasks = session.query(TaskSubmission).filter_by(status='rejected').count()

    # کاربران بر اساس موضوع
    topics_stats = {}
    users = session.query(User).filter_by(is_active=True).all()
    for user in users:
        topic = user.topic
        if topic not in topics_stats:
            topics_stats[topic] = 0
        topics_stats[topic] += 1

    session.close()

    message = (
        f"📊 **آمار کلی**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 **کل کاربران:** {total_users}\n"
        f"📝 **کل تسک‌ها:** {total_tasks}\n"
        f"✅ **تکمیل شده:** {approved_tasks}\n"
        f"⏳ **در انتظار:** {pending_tasks}\n"
        f"❌ **رد شده:** {rejected_tasks}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📚 **توزیع موضوعات:**\n"
    )

    for topic, count in topics_stats.items():
        message += f"   • {topic}: {count} نفر\n"

    await query.edit_message_text(
        message,
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )