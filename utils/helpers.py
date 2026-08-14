import re
from datetime import datetime

def validate_email(email):
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def get_progress_bar(user, length=20):
    if not user or user.total_tasks == 0:
        return "░░" * 10
    try:
        progress = user.get_progress_percentage() / 100
        filled = int(progress * length)
        empty = length - filled
        return "█" * filled + "░" * empty
    except:
        return "░░" * 10

def format_date(date):
    if not date:
        return "-"
    return date.strftime('%Y-%m-%d %H:%M')