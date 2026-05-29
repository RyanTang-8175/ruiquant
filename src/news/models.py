"""
新闻数据模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON
from src.utils.database import Base


class NewsItem(Base):
    __tablename__ = "news_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    source = Column(String(50))  # eastmoney, sina, cls
    url = Column(String(1000))
    published_at = Column(DateTime, index=True)
    related_codes = Column(JSON)  # ["600519", "000001"]
    sentiment_score = Column(Float)  # -1 to 1
    category = Column(String(50))  # policy, sector, company, macro
    is_important = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
