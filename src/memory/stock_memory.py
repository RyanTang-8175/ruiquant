"""
股票记忆管理 —— 股票档案、快照、历史、风险画像
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import desc
from src.data.models_v6 import (
    Stock, StockSnapshot, StockMemoryEntry,
    ScoreRecordV6, AntiQuantRecord, StrategySignal,
)

logger = logging.getLogger(__name__)


class StockMemory:
    """股票记忆管理器"""

    def __init__(self):
        from src.utils.database import SessionLocal

        self.db = SessionLocal()

    def close(self):
        try: self.db.close()
        except Exception: pass

    def get_profile(self, code: str) -> Optional[dict]:
        row = self.db.query(Stock).filter(Stock.code == code).first()
        if not row:
            return None
        return {
            "code": row.code, "name": row.name,
            "sector": row.sector, "concepts": row.concepts or [],
            "float_market_cap": row.float_market_cap,
            "total_market_cap": row.total_market_cap,
            "is_st": row.is_st, "is_suspended": row.is_suspended,
            "delist_risk": row.delist_risk,
            "vol_character": row.vol_character,
            "turnover_range": row.turnover_range,
            "easy_pullback": row.easy_pullback,
            "anti_quant_history_risk": row.anti_quant_history_risk,
            "is_watchlist": row.is_watchlist,
            "is_holding": row.is_holding,
        }

    def upsert_profile(self, code: str, **fields) -> Stock:
        row = self.db.query(Stock).filter(Stock.code == code).first()
        if not row:
            row = Stock(code=code, name=fields.get("name", code))
            self.db.add(row)
        for k, v in fields.items():
            if hasattr(row, k):
                setattr(row, k, v)
        row.updated_at = datetime.now()
        self.db.commit()
        return row

    def set_watchlist(self, code: str, active: bool = True):
        row = self.db.query(Stock).filter(Stock.code == code).first()
        if row:
            row.is_watchlist = active
            row.updated_at = datetime.now()
            self.db.commit()

    def get_watchlist_stocks(self) -> list:
        rows = self.db.query(Stock).filter(Stock.is_watchlist == True).all()
        return [r.code for r in rows]

    def save_snapshot(self, code: str, data: dict) -> StockSnapshot:
        snap = StockSnapshot(
            code=code, snapshot_time=datetime.now(),
            price=data.get("price"), open=data.get("open"),
            high=data.get("high"), low=data.get("low"),
            pre_close=data.get("pre_close"),
            change_pct=data.get("change_pct"),
            volume=data.get("volume"), amount=data.get("amount"),
            turnover=data.get("turnover"),
            volume_ratio=data.get("volume_ratio"),
            source=data.get("source", "unknown"),
            is_delayed=data.get("is_delayed", False),
            quality_level=data.get("quality_level", "ok"),
        )
        self.db.add(snap)
        self.db.commit()
        return snap

    def get_latest_snapshot(self, code: str) -> Optional[dict]:
        row = (self.db.query(StockSnapshot)
               .filter(StockSnapshot.code == code)
               .order_by(desc(StockSnapshot.snapshot_time)).first())
        if not row:
            return None
        return {c.name: getattr(row, c.name) for c in row.__table__.columns}

    def add_memory(self, code: str, entry_type: str, title: str,
                   summary: str = "", snapshot: dict = None):
        entry = StockMemoryEntry(
            stock_code=code, entry_type=entry_type,
            title=title, summary=summary,
            data_snapshot=snapshot,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def get_memories(self, code: str, entry_type: str = None,
                     limit: int = 50) -> list:
        q = (self.db.query(StockMemoryEntry)
             .filter(StockMemoryEntry.stock_code == code))
        if entry_type:
            q = q.filter(StockMemoryEntry.entry_type == entry_type)
        rows = q.order_by(desc(StockMemoryEntry.created_at)).limit(limit).all()
        return [
            {"type": r.entry_type, "title": r.title,
             "summary": r.summary, "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def get_recent_memory_summary(self, code: str) -> str:
        entries = self.get_memories(code, limit=10)
        if not entries:
            return f"暂无 {code} 的历史记忆"
        lines = [f"## {code} 近期记忆"]
        for e in entries:
            lines.append(f"- [{e['type']}] {e['title']}: {e['summary']}")
        return "\n".join(lines)

    def get_score_history(self, code: str, limit: int = 20) -> list:
        rows = (self.db.query(ScoreRecordV6)
                .filter(ScoreRecordV6.code == code)
                .order_by(desc(ScoreRecordV6.score_date))
                .limit(limit).all())
        return [
            {"date": r.score_date.isoformat(), "total": r.total_score,
             "heat": r.heat_score, "support": r.support_score,
             "theme": r.theme_score, "continuation": r.continuation_score,
             "strategy_match": r.strategy_match_score,
             "anti_quant_penalty": r.anti_quant_penalty,
             "status": r.status_label, "risk": r.risk_level}
            for r in rows
        ]

    def get_risk_profile(self, code: str) -> dict:
        rows = (self.db.query(AntiQuantRecord)
                .filter(AntiQuantRecord.code == code)
                .order_by(desc(AntiQuantRecord.scan_date))
                .limit(30).all())
        if not rows:
            return {"avg_risk": 0, "risk_level": "未知", "recent_risks": []}
        avg = sum(r.total_risk for r in rows) / len(rows)
        recent = [
            {"date": r.scan_date.isoformat(), "risk": r.total_risk,
             "level": r.risk_level}
            for r in rows[:5]
        ]
        level = "低" if avg < 20 else "中" if avg < 40 else "高" if avg < 70 else "极高"
        return {"avg_risk": round(avg, 1), "risk_level": level, "recent_risks": recent}

    def build_ai_context(self, code: str, current_snapshot: dict = None) -> dict:
        return {
            "profile": self.get_profile(code),
            "snapshot": current_snapshot or self.get_latest_snapshot(code),
            "recent_scores": self.get_score_history(code, limit=5),
            "risk_profile": self.get_risk_profile(code),
            "recent_memories": self.get_memories(code, limit=10),
            "strategy_history": self._get_strategy_history(code),
        }

    def _get_strategy_history(self, code: str) -> list:
        rows = (self.db.query(StrategySignal)
                .filter(StrategySignal.code == code)
                .order_by(desc(StrategySignal.signal_date))
                .limit(10).all())
        return [
            {"strategy": r.strategy_name, "match": r.match_score,
             "status": r.signal_status, "date": r.signal_date.isoformat()}
            for r in rows
        ]
