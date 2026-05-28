"""
AI 预测模型
预测记录与回填结果
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from src.utils.database import Base


class Prediction(Base):
    """预测记录"""
    __tablename__ = "prediction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)  # 股票代码
    name = Column(String(50))                               # 股票名称
    prediction_date = Column(DateTime, nullable=False, index=True)  # 预测时间
    prediction_type = Column(String(20))  # "auto" / "manual"

    # 预测时的价格
    price_at_prediction = Column(Float)

    # T+1 预测
    t1_direction = Column(String(10))     # "up" / "down" / "neutral"
    t1_magnitude = Column(String(20))     # "2-3%"
    t1_confidence = Column(Float)         # 0-1

    # T+3 预测
    t3_direction = Column(String(10))
    t3_magnitude = Column(String(20))
    t3_confidence = Column(Float)

    # T+5 预测
    t5_direction = Column(String(10))
    t5_magnitude = Column(String(20))
    t5_confidence = Column(Float)

    # 预测依据
    quant_score = Column(Float)           # 量化评分
    ai_sentiment = Column(Float)          # AI 情绪分
    main_reason = Column(String(500))     # 主要理由
    risk_factors = Column(JSON)           # 风险因素

    # 回填结果
    actual_price_t1 = Column(Float)
    actual_price_t3 = Column(Float)
    actual_price_t5 = Column(Float)
    actual_return_t1 = Column(Float)
    actual_return_t3 = Column(Float)
    actual_return_t5 = Column(Float)
    hit_t1 = Column(Boolean)
    hit_t3 = Column(Boolean)
    hit_t5 = Column(Boolean)

    status = Column(String(20), default="pending")  # pending/completed/expired
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
