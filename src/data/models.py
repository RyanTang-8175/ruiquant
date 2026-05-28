"""
数据层模型
股票基础信息、日线数据、技术指标
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, UniqueConstraint
from src.utils.database import Base


class StockBasic(Base):
    """股票基础信息"""
    __tablename__ = "stock_basic"

    code = Column(String(10), primary_key=True)
    name = Column(String(50), nullable=False)
    sector = Column(String(50))
    list_date = Column(Date)
    is_st = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DailyQuote(Base):
    """日线行情"""
    __tablename__ = "daily_quote"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)  # 改为 Integer
    amount = Column(Float)
    change_pct = Column(Float)
    turnover_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('code', 'trade_date', name='uq_daily_quote_code_date'),
    )


class TechnicalIndicator(Base):
    """技术指标"""
    __tablename__ = "technical_indicator"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)

    # 均线
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)

    # MACD
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)

    # RSI
    rsi_6 = Column(Float)
    rsi_12 = Column(Float)

    # KDJ
    kdj_k = Column(Float)
    kdj_d = Column(Float)
    kdj_j = Column(Float)

    # 布林带
    boll_upper = Column(Float)
    boll_middle = Column(Float)
    boll_lower = Column(Float)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('code', 'trade_date', name='uq_indicator_code_date'),
    )
