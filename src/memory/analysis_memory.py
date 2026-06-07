"""
结构化 AI 分析记忆 —— 风险审查 · 持股预测 · 验证管理
"""

from __future__ import annotations

import json, logging
from datetime import datetime
from typing import Optional

from sqlalchemy import desc
from src.data.models_v6 import (
    AIAnalysisRecord, VerificationRecord, VerificationBackfill,
    UserFeedback,
)

logger = logging.getLogger(__name__)


class AnalysisMemory:
    """AI 分析结果持久化管理器"""

    def __init__(self):
        from src.utils.database import SessionLocal

        self.db = SessionLocal()

    def __enter__(self): return self
    def __exit__(self, *a): self.close(); return False

    def close(self):
        try: self.db.close()
        except Exception: pass

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
                            source_id: int = None,
                            hypothesis: str = None,
                            entry_conditions: list[str] = None,
                            invalidation_conditions: list[str] = None,
                            stop_loss_rule: str = None,
                            risk_level: str = None,
                            confidence_level: str = None,
                            allow_real_trade: bool = False,
                            max_loss_pct: float = None) -> int:
        plan = self._pack_plan_metadata(
            hypothesis=hypothesis,
            entry_conditions=entry_conditions,
            invalidation_conditions=invalidation_conditions,
            stop_loss_rule=stop_loss_rule,
            risk_level=risk_level,
            confidence_level=confidence_level,
            allow_real_trade=allow_real_trade,
            max_loss_pct=max_loss_pct,
        )
        v = VerificationRecord(
            source_type=source_type, source_id=source_id,
            stock_code=stock_code, stock_name=stock_name,
            strategy_name=strategy_name,
            suggested_period=suggested_period,
            signal_date=signal_date,
            user_note=json.dumps(plan, ensure_ascii=False) if plan else None,
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

    @staticmethod
    def _pack_plan_metadata(**kwargs) -> dict:
        cleaned = {}
        for key, value in kwargs.items():
            if value is None:
                continue
            if isinstance(value, list):
                cleaned[key] = [str(v).strip() for v in value if str(v).strip()]
            else:
                cleaned[key] = value
        if "allow_real_trade" not in cleaned:
            cleaned["allow_real_trade"] = False
        return cleaned

    @staticmethod
    def _plan_from_note(note: str | None) -> dict:
        defaults = {
            "hypothesis": "",
            "entry_conditions": [],
            "invalidation_conditions": [],
            "stop_loss_rule": "",
            "risk_level": "",
            "confidence_level": "",
            "allow_real_trade": False,
            "max_loss_pct": None,
        }
        if not note:
            return defaults
        try:
            data = json.loads(note)
            if isinstance(data, dict):
                defaults.update(data)
                defaults["entry_conditions"] = defaults.get("entry_conditions") or []
                defaults["invalidation_conditions"] = defaults.get("invalidation_conditions") or []
                defaults["allow_real_trade"] = bool(defaults.get("allow_real_trade", False))
        except Exception:
            defaults["hypothesis"] = note
        return defaults

    def get_pending_verifications(self) -> list:
        rows = (self.db.query(VerificationRecord)
                .filter(VerificationRecord.backfill_status != "complete")
                .order_by(desc(VerificationRecord.signal_date))
                .limit(50).all())
        out = []
        for r in rows:
            plan = self._plan_from_note(r.user_note)
            out.append({
                "id": r.id, "source_type": r.source_type,
                "stock_code": r.stock_code, "stock_name": r.stock_name,
                "strategy_name": r.strategy_name,
                "suggested_period": r.suggested_period,
                "signal_date": r.signal_date.isoformat(),
                "backfill_status": r.backfill_status,
                "user_action": r.user_action,
                **plan,
            })
        return out

    def save_backfill(self, verification_id: int, data: dict):
        day_offset = data.get("day_offset", 1)
        bf = (self.db.query(VerificationBackfill)
              .filter(VerificationBackfill.verification_id == verification_id)
              .filter(VerificationBackfill.day_offset == day_offset)
              .first())
        if not bf:
            bf = VerificationBackfill(verification_id=verification_id, day_offset=day_offset)
            self.db.add(bf)
        for key in [
            "trade_date", "open_change_pct", "high_change_pct", "low_change_pct",
            "close_change_pct", "hit_plus_2pct", "first_hit_2pct_time",
            "broke_avg_line", "open_low_2pct", "open_high_3pct",
            "hold_1d_return", "hold_2d_return", "hold_3d_return",
            "rule_based_return", "max_drawdown",
        ]:
            if key in data:
                setattr(bf, key, data.get(key))
        v = self.db.query(VerificationRecord).filter(
            VerificationRecord.id == verification_id).first()
        if v:
            max_offset = max(1, int(day_offset or 1))
            required = self._required_backfill_days(v.suggested_period)
            v.backfill_status = "complete" if max_offset >= required else "partial"
        self.db.commit()

    @staticmethod
    def _required_backfill_days(period: str | None) -> int:
        p = str(period or "")
        if "隔夜" in p:
            return 1
        if "1-2" in p:
            return 2
        if "2-3" in p:
            return 3
        if "5" in p:
            return 5
        return 3

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
            plan = self._plan_from_note(r.user_note)
            results.append({
                "id": r.id, "stock_code": r.stock_code,
                "stock_name": r.stock_name,
                "source_type": r.source_type,
                "source_id": r.source_id,
                "strategy": r.strategy_name,
                "strategy_name": r.strategy_name,
                "period": r.suggested_period,
                "suggested_period": r.suggested_period,
                "signal_date": r.signal_date.isoformat(),
                "backfill_status": r.backfill_status,
                "user_action": r.user_action,
                **plan,
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

        # 分母用 VerificationRecord（每个假设一条），而非 VerificationBackfill（每条有3行T+1/T+2/T+3）
        # 否则命中率被放大约3倍
        completed_ids = set(
            r.id for r in self.db.query(VerificationRecord)
            .filter(VerificationRecord.backfill_status == "complete").all()
        )
        total_completed = len(completed_ids) or 1
        # 每个已完成假设：任意一天的 high 达到+2% 即命中
        hit_ids = set(
            b.verification_id for b in self.db.query(VerificationBackfill).all()
            if b.hit_plus_2pct and b.verification_id in completed_ids
        )
        # avg_hold_1d_return：只取 day_offset=1 的行，防止多天混平均
        t1_rows = [
            b for b in self.db.query(VerificationBackfill).all()
            if b.day_offset == 1 and b.verification_id in completed_ids
        ]
        avg_1d = round(
            sum(b.hold_1d_return or 0 for b in t1_rows) / (len(t1_rows) or 1), 2
        )

        feedback_rows = self.db.query(UserFeedback).all()
        bad_feedback = sum(1 for f in feedback_rows if f.feedback_type in {
            "no_stop_loss", "没止损", "user_chasing", "追高", "strategy_error",
            "反向操作",
        })
        return {
            "total_verifications": total,
            "pending_backfills": pending,
            "completed_backfills": completed,
            "hit_2pct_rate": round(len(hit_ids) / total_completed * 100, 1),
            "avg_hold_1d_return": avg_1d,
            "feedback_count": len(feedback_rows),
            "bad_feedback_count": bad_feedback,
        }
