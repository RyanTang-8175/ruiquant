"""
数据层模型
股票基础信息、日线数据、技术指标
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean
from src.utils.database import Base


class StockBasic(Base):
    """股票基础信息"""
    __tablename__ = "stock_basic"

    code = Column(String(10), primary_key=True)  # 股票代码
    name = Column(String(50), nullable=False)     # 股票名称
    sector = Column(String(50))                   # 行业
    list_date = Column(Date)                      # 上市日期
    is_st = Column(Boolean, default=False)        # 是否ST
    is_active = Column(Boolean, default=True)     # 是否活跃
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DailyQuote(Base):
    """日线行情"""
    __tablename__ = "daily_quote"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)  # 股票代码
    trade_date = Column(Date, nullable=False, index=True)  # 交易日期
    open = Column(Float)        # 开盘价
    high = Column(Float)        # 最高价
    low = Column(Float)         # 最低价
    close = Column(Float)       # 收盘价
    volume = Column(Float)      # 成交量
    amount = Column(Float)      # 成交额
    change_pct = Column(Float)  # 涨跌幅
    turnover_rate = Column(Float)  # 换手率
    created_at = Column(DateTime, default=datetime.now)


class TechnicalIndicator(Base):
    """技术指标"""
    __tablename__ = "technical_indicator"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)  # 股票代码
    trade_date = Column(Date, nullable=False, index=True)  # 交易日期

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
