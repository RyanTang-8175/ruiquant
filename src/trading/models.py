"""
模拟盘模型
账户、持仓、交易记录
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from src.utils.database import Base


class PaperAccount(Base):
    """模拟盘账户"""
    __tablename__ = "paper_account"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)  # 账户名称
    initial_capital = Column(Float, nullable=False)  # 初始资金
    cash = Column(Float, nullable=False)  # 现金余额
    status = Column(String(20), default="active")  # active/paused/daily_limit/consecutive_loss
    consecutive_losses = Column(Integer, default=0)  # 连续亏损次数
    daily_pnl = Column(Float, default=0)  # 当日盈亏
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    positions = relationship("Position", back_populates="account")
    trades = relationship("Trade", back_populates="account")


class Position(Base):
    """持仓"""
    __tablename__ = "position"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("paper_account.id"), nullable=False)
    code = Column(String(10), nullable=False)  # 股票代码
    name = Column(String(50))  # 股票名称
    quantity = Column(Integer, nullable=False)  # 持仓数量
    cost_price = Column(Float, nullable=False)  # 成本价
    buy_date = Column(Date, nullable=False)  # 买入日期（T+1 检查用）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    account = relationship("PaperAccount", back_populates="positions")


class Trade(Base):
    """交易记录"""
    __tablename__ = "trade"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("paper_account.id"), nullable=False)
    code = Column(String(10), nullable=False)  # 股票代码
    name = Column(String(50))  # 股票名称
    direction = Column(String(10), nullable=False)  # "buy" / "sell"
    price = Column(Float, nullable=False)  # 交易价格
    quantity = Column(Integer, nullable=False)  # 交易数量
    amount = Column(Float, nullable=False)  # 交易金额
    commission = Column(Float)  # 佣金
    stamp_tax = Column(Float)   # 印花税
    transfer_fee = Column(Float)  # 过户费
    total_cost = Column(Float)  # 总费用
    pnl = Column(Float)  # 盈亏（卖出时计算）
    cash_before = Column(Float)  # 交易前现金
    cash_after = Column(Float)   # 交易后现金
    note = Column(String(200))   # 备注
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    account = relationship("PaperAccount", back_populates="trades")
