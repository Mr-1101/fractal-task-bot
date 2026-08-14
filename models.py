from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import Config

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    full_name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)
    topic = Column(String(100), nullable=False)
    topic_key = Column(String(10))
    remaining_tasks = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_activity = Column(DateTime, default=datetime.now)

    def get_progress_percentage(self):
        if self.total_tasks == 0:
            return 0
        return ((self.total_tasks - self.remaining_tasks) / self.total_tasks) * 100


class TaskSubmission(Base):
    __tablename__ = 'task_submissions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    task_code = Column(String(50), nullable=False)
    screenshot_file_id = Column(String(255), nullable=False)
    voice_file_id = Column(String(255), nullable=False)
    voice_duration = Column(Integer, default=0)
    submission_date = Column(DateTime, default=datetime.now, index=True)
    status = Column(String(20), default='pending', index=True)


class UserProgress(Base):
    __tablename__ = 'user_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    total_submissions = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)
    last_submission_date = Column(DateTime)


# ایجاد دیتابیس
engine = create_engine(Config.DATABASE_URL, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def get_session():
    return Session()