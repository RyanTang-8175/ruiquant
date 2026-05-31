"""
AlphaEye v6 新增数据库模型
—— 股票记忆 · AI会话 · 策略信号 · 反量化 · 验证系统

所有新表与现有表共存，不破坏 v5.2 数据。
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean,
    Text, JSON, ForeignKey, UniqueConstraint, Index,
)
from src.utils.database import Base


# ═══════════════════════════════════════════
# 股票档案
# ═══════════════════════════════════════════

class Stock(Base):
    """股票基础档案（扩展 stock_basic）"""
    __tablename__ = "stocks"

    code = Column(String(10), primary_key=True)
    name = Column(String(50), nullable=False)
    sector = Column(String(50))
    concepts = Column(JSON)
    float_market_cap = Column(Float)
    total_market_cap = Column(Float)
    is_st = Column(Boolean, default=False)
    is_suspended = Column(Boolean, default=False)
    delist_risk = Column(Boolean, default=False)

    vol_character = Column(String(50))
    turnover_range = Column(String(30))
    volume_ratio_range = Column(String(30))
    easy_pullback = Column(Boolean)
    anti_quant_history_risk = Column(Float)

    is_watchlist = Column(Boolean, default=False)
    is_holding = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_at = Column(DateTime, default=datetime.now)


class StockSnapshot(Base):
    """股票实时快照"""
    __tablename__ = "stock_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    snapshot_time = Column(DateTime, nullable=False, index=True)

    price = Column(Float)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    pre_close = Column(Float)
    change_pct = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    turnover = Column(Float)
    volume_ratio = Column(Float)

    source = Column(String(30))
    is_delayed = Column(Boolean, default=False)
    quality_level = Column(String(10), default="ok")

    created_at = Column(DateTime, default=datetime.now)


class IntradayBar(Base):
    """分钟级分时数据"""
    __tablename__ = "intraday_bars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)
    time = Column(String(10), nullable=False)
    price = Column(Float)
    volume = Column(Float)
    avg_price = Column(Float)

    source = Column(String(30))
    quality_level = Column(String(10), default="ok")

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('code', 'trade_date', 'time', name='uq_intraday_bar'),
        Index('ix_intraday_code_date', 'code', 'trade_date'),
    )


class DailyBar(Base):
    """日线数据"""
    __tablename__ = "daily_bars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)

    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    change_pct = Column(Float)
    turnover_rate = Column(Float)

    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    high_20d = Column(Float)
    amplitude = Column(Float)
    upper_shadow_pct = Column(Float)
    close_position = Column(Float)

    source = Column(String(30))
    quality_level = Column(String(10), default="ok")

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('code', 'trade_date', name='uq_daily_bar'),
    )


# ═══════════════════════════════════════════
# 六维评分 & 反量化
# ═══════════════════════════════════════════

class ScoreRecordV6(Base):
    """v6 六维评分记录"""
    __tablename__ = "score_records_v6"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50))
    score_date = Column(DateTime, nullable=False, index=True)

    heat_score = Column(Float)
    support_score = Column(Float)
    theme_score = Column(Float)
    continuation_score = Column(Float)
    strategy_match_score = Column(Float)
    anti_quant_penalty = Column(Float)
    total_score = Column(Float)

    status_label = Column(String(20))
    risk_level = Column(String(10))

    dimension_details = Column(JSON)
    matched_strategies = Column(JSON)

    created_at = Column(DateTime, default=datetime.now)


class AntiQuantRecord(Base):
    """反量化风险记录"""
    __tablename__ = "anti_quant_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50))
    scan_date = Column(DateTime, nullable=False, index=True)

    total_risk = Column(Float)
    risk_level = Column(String(10))

    late_day_lure = Column(JSON)
    high_position_trap = Column(JSON)
    intraday_pulse = Column(JSON)
    volume_stall = Column(JSON)
    sector_divergence = Column(JSON)

    summary = Column(Text)
    source_snapshot_id = Column(Integer, ForeignKey("stock_snapshots.id"))

    created_at = Column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════
# 策略信号
# ═══════════════════════════════════════════

class StrategySignal(Base):
    """策略触发信号"""
    __tablename__ = "strategy_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50))
    signal_date = Column(DateTime, nullable=False, index=True)

    strategy_name = Column(String(50), nullable=False)
    match_score = Column(Float)
    suitability = Column(String(10))

    signal_status = Column(String(20))

    conditions_met = Column(JSON)
    conditions_failed = Column(JSON)
    risk_flags = Column(JSON)
    next_day_plan = Column(Text)

    is_verified = Column(Boolean, default=False)
    top_n_rank = Column(Integer)

    created_at = Column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════
# AI 会话 & 分析
# ═══════════════════════════════════════════

class AISession(Base):
    """AI 会话"""
    __tablename__ = "ai_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_type = Column(String(30), nullable=False)
    title = Column(String(200))

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AIMessage(Base):
    """AI 消息"""
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("ai_sessions.id"), nullable=False, index=True)
    stock_code = Column(String(10), index=True)

    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    structured_output = Column(JSON)
    tools_used = Column(JSON)

    used_snapshot_ids = Column(JSON)
    used_score_record_id = Column(Integer)
    used_signal_id = Column(Integer)

    created_at = Column(DateTime, default=datetime.now)


class AIAnalysisRecord(Base):
    """结构化 AI 分析结果"""
    __tablename__ = "ai_analysis_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("ai_messages.id"))

    analysis_type = Column(String(30))
    timeframe = Column(String(20))

    risk_level = Column(String(10))
    anti_quant_level = Column(String(10))
    suggested_holding_period = Column(String(20))
    status_label = Column(String(30))

    opportunity_summary = Column(Text)
    risk_points = Column(JSON)
    participation_conditions = Column(JSON)
    exit_conditions = Column(JSON)
    watch_points = Column(JSON)

    is_verified = Column(Boolean, default=False)
    source_score_record_id = Column(Integer)
    source_signal_id = Column(Integer)

    created_at = Column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════
# 股票记忆条目
# ═══════════════════════════════════════════

class StockMemoryEntry(Base):
    """股票记忆条目"""
    __tablename__ = "stock_memory_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)

    entry_type = Column(String(30), nullable=False)
    title = Column(String(200))
    summary = Column(Text)
    data_snapshot = Column(JSON)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('ix_memory_stock_time', 'stock_code', 'created_at'),
    )


# ═══════════════════════════════════════════
# 短线实验室
# ═══════════════════════════════════════════

class VerificationRecord(Base):
    """验证记录"""
    __tablename__ = "verification_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(20), nullable=False)
    source_id = Column(Integer)
    stock_code = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(50))

    strategy_name = Column(String(50))
    suggested_period = Column(String(20))
    signal_date = Column(DateTime, nullable=False)

    user_action = Column(String(30))
    user_note = Column(Text)

    backfill_status = Column(String(20), default="pending")

    created_at = Column(DateTime, default=datetime.now)


class VerificationBackfill(Base):
    """回填结果"""
    __tablename__ = "verification_backfills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    verification_id = Column(Integer, ForeignKey("verification_records.id"), nullable=False, index=True)

    trade_date = Column(Date, nullable=False)
    day_offset = Column(Integer)

    open_change_pct = Column(Float)
    high_change_pct = Column(Float)
    low_change_pct = Column(Float)
    close_change_pct = Column(Float)

    hit_plus_2pct = Column(Boolean)
    first_hit_2pct_time = Column(String(10))
    broke_avg_line = Column(Boolean)
    open_low_2pct = Column(Boolean)
    open_high_3pct = Column(Boolean)

    hold_1d_return = Column(Float)
    hold_2d_return = Column(Float)
    hold_3d_return = Column(Float)
    rule_based_return = Column(Float)
    max_drawdown = Column(Float)

    created_at = Column(DateTime, default=datetime.now)


class UserFeedback(Base):
    """用户反馈"""
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    verification_id = Column(Integer, ForeignKey("verification_records.id"), index=True)
    feedback_type = Column(String(30), nullable=False)

    created_at = Column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════
# 配置 & 健康
# ═══════════════════════════════════════════

class UserPreference(Base):
    """用户偏好"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text)

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DataQualityLog(Base):
    """数据源健康日志"""
    __tablename__ = "data_quality_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(30), nullable=False)
    endpoint = Column(String(200))
    check_time = Column(DateTime, nullable=False, index=True)

    status = Column(String(20))
    latency_ms = Column(Float)
    error_message = Column(Text)
    fields_missing = Column(JSON)

    created_at = Column(DateTime, default=datetime.now)
