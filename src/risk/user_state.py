"""
用户交易状态风控。

这不是投资建议模块，而是 AlphaEye 的刹车系统：当最近执行反馈和模拟盘
表现说明用户容易追高、不止损或连续亏损时，AI 只能给观察/模拟/复盘计划。
"""

from __future__ import annotations

from dataclasses import dataclass


BAD_FEEDBACK = {
    "no_stop_loss": "没有按止损纪律执行",
    "没止损": "没有按止损纪律执行",
    "user_chasing": "出现追高/冲动参与",
    "追高": "出现追高/冲动参与",
    "strategy_error": "策略或判断失效",
    "反向操作": "实际执行偏离计划",
    "提前卖出": "执行节奏偏离计划",
}


@dataclass
class RiskState:
    mode: str
    allows_real_trade: bool
    action_policy: str
    score: int
    reasons: list[str]

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "allows_real_trade": self.allows_real_trade,
            "action_policy": self.action_policy,
            "score": self.score,
            "reasons": self.reasons,
        }


def evaluate_user_risk_state(
    trade_stats: dict | None = None,
    recent_feedback: list[str] | None = None,
    verification_stats: dict | None = None,
) -> dict:
    """根据模拟盘、实验室反馈和验证命中率生成用户状态。"""
    trade_stats = trade_stats or {}
    recent_feedback = recent_feedback or []
    verification_stats = verification_stats or {}

    score = 0
    reasons: list[str] = []

    total_trades = int(trade_stats.get("total_trades") or 0)
    win_rate = trade_stats.get("win_rate")
    total_pnl = float(trade_stats.get("total_pnl") or 0)
    if total_trades >= 3 and win_rate is not None and float(win_rate) < 0.35:
        score += 35
        reasons.append(f"最近模拟胜率偏低({float(win_rate) * 100:.1f}%)")
    if total_pnl < 0:
        score += 20 if abs(total_pnl) < 1000 else 30
        reasons.append(f"模拟总盈亏为负({total_pnl:.0f})")

    bad_count = 0
    for fb in recent_feedback[-10:]:
        if fb in BAD_FEEDBACK:
            bad_count += 1
            reasons.append(BAD_FEEDBACK[fb])
    if bad_count >= 3:
        score += 45
    elif bad_count:
        score += 15 * bad_count

    hit_rate = verification_stats.get("hit_2pct_rate")
    if hit_rate is not None and float(hit_rate) < 35:
        score += 15
        reasons.append(f"实验室 +2% 命中率偏低({hit_rate}%)")

    if score >= 70:
        return RiskState(
            mode="cooldown",
            allows_real_trade=False,
            action_policy="只允许观察/模拟/复盘；AI 不给实盘买入建议，只输出触发条件、放弃条件和复盘问题。",
            score=min(score, 100),
            reasons=_dedupe(reasons) or ["近期风险过高，需要冷静期"],
        ).to_dict()
    if score >= 35:
        return RiskState(
            mode="caution",
            allows_real_trade=False,
            action_policy="只允许小样本模拟验证；所有候选必须写清入场条件、失效条件和止损规则。",
            score=min(score, 100),
            reasons=_dedupe(reasons) or ["风险状态需要谨慎"],
        ).to_dict()
    return RiskState(
        mode="normal",
        allows_real_trade=False,
        action_policy="默认仍以研究、观察和模拟为主；若未来接入实盘，也必须人工独立确认。",
        score=min(score, 100),
        reasons=_dedupe(reasons) or ["暂无明显执行风险"],
    ).to_dict()


def get_user_risk_state() -> dict:
    """从项目现有数据库尽量读取用户状态，失败时返回保守状态。"""
    trade_stats = {}
    recent_feedback: list[str] = []
    verification_stats = {}

    try:
        from src.trading.engine import TradingEngine

        with TradingEngine() as engine:
            trade_stats = engine.get_stats() or {}
    except Exception:
        trade_stats = {}

    try:
        from sqlalchemy import desc
        from src.utils.database import SessionLocal
        from src.data.models_v6 import UserFeedback
        from src.memory.analysis_memory import AnalysisMemory

        db = SessionLocal()
        try:
            rows = db.query(UserFeedback).order_by(desc(UserFeedback.created_at)).limit(10).all()
            recent_feedback = [r.feedback_type for r in rows]
        finally:
            db.close()
        with AnalysisMemory() as memory:
            verification_stats = memory.get_stats()
    except Exception:
        verification_stats = {}

    return evaluate_user_risk_state(trade_stats, recent_feedback, verification_stats)


def _dedupe(items: list[str]) -> list[str]:
    out = []
    seen = set()
    for item in items:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out
