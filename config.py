import os
import json
from dotenv import load_dotenv

load_dotenv()


class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CHANNEL_ID = os.getenv('CHANNEL_ID')  # -1003916305856
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/task_bot.db')

    admin_ids_str = os.getenv('ADMIN_IDS', '')
    ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip().isdigit()]

    MAX_TASKS_PER_USER = int(os.getenv('MAX_TASKS_PER_USER', 500))
    TASK_PAGE_SIZE = int(os.getenv('TASK_PAGE_SIZE', 5))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    TOPICS_FILE = 'data/topics.json'

    @classmethod
    def load_topics(cls):
        if os.path.exists(cls.TOPICS_FILE):
            try:
                with open(cls.TOPICS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return cls.get_default_topics()
        return cls.get_default_topics()

    @classmethod
    def save_topics(cls, topics):
        os.makedirs(os.path.dirname(cls.TOPICS_FILE), exist_ok=True)
        with open(cls.TOPICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(topics, f, ensure_ascii=False, indent=2)

    @classmethod
    def get_default_topics(cls):
        return {
            '1': {'name': 'رسم اینساید', 'tasks_needed': 1000, 'emoji': '📖', 'is_active': True},
            '2': {'name': 'رسم اینساید تا لایه 3', 'tasks_needed': 1000, 'emoji': '📖', 'is_active': True},
            '3': {'name': 'رسم ترند لاین', 'tasks_needed': 1000, 'emoji': '📖', 'is_active': True},
            '4': {'name': 'پیدا کردن داجی', 'tasks_needed': 1000, 'emoji': '📖', 'is_active': True},
            '5': {'name': 'پیدا کردن ATR', 'tasks_needed': 1000, 'emoji': '📖', 'is_active': True},
            '6': {'name': 'تمرین کامل فرکتال', 'tasks_needed': 1000, 'emoji': '💡', 'is_active': True},
            '7': {'name': 'پوزیشن ها', 'tasks_needed': 1000, 'emoji': '$$', 'is_active': True},
        }


Config.TOPICS = Config.load_topics()

if not Config.TELEGRAM_TOKEN:
    print("❌ توکن ربات تنظیم نشده!")