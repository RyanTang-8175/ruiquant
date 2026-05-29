"""
评分引擎模型
评分记录
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from src.utils.database import Base


class ScoreRecord(Base):
    """评分记录"""
    __tablename__ = "score_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)  # 股票代码
    name = Column(String(50))                               # 股票名称
    score_date = Column(DateTime, nullable=False, index=True)  # 评分日期

    # 总分
    total_score = Column(Float, nullable=False)  # 总分 0-100
    rating = Column(String(20))                  # 评级：强关注/观察/中性/不追

    # 量化因子分数
    trend_score = Column(Float)           # 均线趋势
    reversal_score = Column(Float)        # 短期反转
    volume_ratio_score = Column(Float)    # 量比
    turnover_score = Column(Float)        # 换手率
    volatility_score = Column(Float)      # 波动率
    volume_price_corr_score = Column(Float)  # 量价相关性
    divergence_score = Column(Float)      # 量价背离
    kline_score = Column(Float)           # K线形态
    rsi_score = Column(Float)             # RSI
    macd_score = Column(Float)            # MACD
    sector_score = Column(Float)          # 板块热度
    northbound_score = Column(Float)      # 北向资金
    capital_flow_score = Column(Float)    # 主力资金
    dragon_tiger_score = Column(Float)    # 龙虎榜
    limit_streak_score = Column(Float)    # 连板天数
    market_temp_score = Column(Float)     # 市场温度
    ep_score = Column(Float)              # EP(盈利收益率)
    roe_score = Column(Float)             # ROE
    analyst_score = Column(Float)         # 分析师修正

    # AI 因子分数
    ai_news_score = Column(Float)         # 新闻情绪
    ai_policy_score = Column(Float)       # 政策影响
    ai_anomaly_score = Column(Float)      # 异常事件

    # 因子权重（JSON）
    factor_weights = Column(JSON)         # 各因子权重

    # 所有因子分数快照（JSON）
    factors_json = Column(JSON)           # 完整因子分数字典

    created_at = Column(DateTime, default=datetime.now)
