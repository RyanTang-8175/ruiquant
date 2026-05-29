"""
用户模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from src.utils.database import Base


class User(Base):
    """用户账户"""
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    nickname = Column(String(50), default="")
    api_key = Column(String(200), default="")
    base_url = Column(String(200), default="https://api.deepseek.com")
    model = Column(String(50), default="deepseek-chat")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
