"""
结构化 AI 分析记忆 —— 风险审查 · 持股预测 · 验证管理
"""

import json, logging
from datetime import datetime
from typing import Optional

from sqlalchemy import desc
from src.utils.database import SessionLocal
from src.data.models_v6 import (
    AIAnalysisRecord, VerificationRecord, VerificationBackfill,
    UserFeedback,
)

logger = logging.getLogger(__name__)


class AnalysisMemory:
    """AI 分析结果持久化管理器"""

    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        try: self.db.close()
        except: pass

    def save_analysis(self, stock_code: str, analysis_type: str,
                      data: dict, message_id: int = None) -> int:
        record = AIAnalysisRecord(
            stock_code=stock_code, message_id=message_id,
            analysis_type=analysis_type,
            timeframe=data.get("timeframe"),
            risk_level=data.get("risk_level"),
            anti_quant_level=data.get("anti_quant_level"),
            suggested_holding_period=data.get("suggested_holding_period"),
            status_label=data.get("status_label"),
            opportunity_summary=data.get("opportunity_summary"),
            risk_points=data.get("risk_points"),
            participation_conditions=data.get("participation_conditions"),
            exit_conditions=data.get("exit_conditions"),
            watch_points=data.get("watch_points"),
            source_score_record_id=data.get("source_score_record_id"),
            source_signal_id=data.get("source_signal_id"),
        )
        self.db.add(record)
        self.db.commit()
        return record.id

    def get_analyses(self, stock_code: str, analysis_type: str = None,
                     limit: int = 20) -> list:
        q = (self.db.query(AIAnalysisRecord)
             .filter(AIAnalysisRecord.stock_code == stock_code))
        if analysis_type:
            q = q.filter(AIAnalysisRecord.analysis_type == analysis_type)
        rows = q.order_by(desc(AIAnalysisRecord.created_at)).limit(limit).all()
        return [
            {"id": r.id, "type": r.analysis_type,
             "risk_level": r.risk_level,
             "anti_quant_level": r.anti_quant_level,
             "holding_period": r.suggested_holding_period,
             "status": r.status_label,
             "risk_points": r.risk_points,
             "participation_conditions": r.participation_conditions,
             "exit_conditions": r.exit_conditions,
             "is_verified": r.is_verified,
             "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def create_verification(self, source_type: str,
                            stock_code: str, stock_name: str,
                            signal_date: datetime,
                            strategy_name: str = None,
                            suggested_period: str = None,
                            source_id: int = None) -> int:
        v = VerificationRecord(
            source_type=source_type, source_id=source_id,
            stock_code=stock_code, stock_name=stock_name,
            strategy_name=strategy_name,
            suggested_period=suggested_period,
            signal_date=signal_date,
        )
        self.db.add(v)
        self.db.commit()
        if source_id and source_type == "ai_prediction":
            ar = self.db.query(AIAnalysisRecord).filter(
                AIAnalysisRecord.id == source_id).first()
            if ar:
                ar.is_verified = True
                self.db.commit()
        return v.id

    def get_pending_verifications(self) -> list:
        rows = (self.db.query(VerificationRecord)
                .filter(VerificationRecord.backfill_status != "complete")
                .order_by(desc(VerificationRecord.signal_date))
                .limit(50).all())
        return [
            {"id": r.id, "source_type": r.source_type,
             "stock_code": r.stock_code, "stock_name": r.stock_name,
             "strategy_name": r.strategy_name,
             "suggested_period": r.suggested_period,
             "signal_date": r.signal_date.isoformat(),
             "backfill_status": r.backfill_status,
             "user_action": r.user_action}
            for r in rows
        ]

    def save_backfill(self, verification_id: int, data: dict):
        bf = VerificationBackfill(
            verification_id=verification_id,
            trade_date=data.get("trade_date"),
            day_offset=data.get("day_offset", 1),
            open_change_pct=data.get("open_change_pct"),
            high_change_pct=data.get("high_change_pct"),
            low_change_pct=data.get("low_change_pct"),
            close_change_pct=data.get("close_change_pct"),
            hit_plus_2pct=data.get("hit_plus_2pct", False),
            first_hit_2pct_time=data.get("first_hit_2pct_time"),
            broke_avg_line=data.get("broke_avg_line", False),
            open_low_2pct=data.get("open_low_2pct", False),
            open_high_3pct=data.get("open_high_3pct", False),
            hold_1d_return=data.get("hold_1d_return"),
            hold_2d_return=data.get("hold_2d_return"),
            hold_3d_return=data.get("hold_3d_return"),
            rule_based_return=data.get("rule_based_return"),
            max_drawdown=data.get("max_drawdown"),
        )
        self.db.add(bf)
        v = self.db.query(VerificationRecord).filter(
            VerificationRecord.id == verification_id).first()
        if v:
            v.backfill_status = "complete"
        self.db.commit()

    def get_verification_results(self, stock_code: str = None) -> list:
        q = self.db.query(VerificationRecord)
        if stock_code:
            q = q.filter(VerificationRecord.stock_code == stock_code)
        rows = q.order_by(desc(VerificationRecord.signal_date)).limit(30).all()
        results = []
        for r in rows:
            backfills = (self.db.query(VerificationBackfill)
                         .filter(VerificationBackfill.verification_id == r.id)
                         .order_by(VerificationBackfill.day_offset).all())
            results.append({
                "id": r.id, "stock_code": r.stock_code,
                "stock_name": r.stock_name,
                "source_type": r.source_type,
                "strategy": r.strategy_name,
                "period": r.suggested_period,
                "signal_date": r.signal_date.isoformat(),
                "backfill_status": r.backfill_status,
                "user_action": r.user_action,
                "backfills": [
                    {"day": b.day_offset, "high": b.high_change_pct,
                     "hit_2pct": b.hit_plus_2pct,
                     "hold_1d": b.hold_1d_return,
                     "max_dd": b.max_drawdown}
                    for b in backfills
                ],
            })
        return results

    def save_feedback(self, verification_id: int, feedback_type: str):
        fb = UserFeedback(
            verification_id=verification_id,
            feedback_type=feedback_type,
        )
        v = self.db.query(VerificationRecord).filter(
            VerificationRecord.id == verification_id).first()
        if v:
            v.user_action = feedback_type
        self.db.add(fb)
        self.db.commit()

    def get_stats(self) -> dict:
        total = self.db.query(VerificationRecord).count()
        completed = (self.db.query(VerificationRecord)
                     .filter(VerificationRecord.backfill_status == "complete")
                     .count())
        pending = total - completed
        backfills = self.db.query(VerificationBackfill).all()
        hit_2pct = sum(1 for b in backfills if b.hit_plus_2pct)
        total_bf = len(backfills) or 1
        return {
            "total_verifications": total,
            "pending_backfills": pending,
            "completed_backfills": completed,
            "hit_2pct_rate": round(hit_2pct / total_bf * 100, 1),
            "avg_hold_1d_return": round(
                sum(b.hold_1d_return or 0 for b in backfills) / total_bf, 2
            ),
        }
