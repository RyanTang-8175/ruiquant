"""
数据库工具
SQLAlchemy 配置和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import DATABASE_URL

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 需要
    echo=False
)

# 创建会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
