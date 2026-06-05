"""
数据质量追踪 —— 行情/评分/AI 全链路标注
每个数据源返回都标记 source、quality_level、latency 和 is_delayed
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def assess_quote_quality(quote: dict, source: str) -> dict:
    """评估单条行情数据质量，返回质量标记字典，同时写入 quote['_quality']"""
    if not quote:
        return {"quality_level": "unavailable", "source": source,
                "is_delayed": True, "missing_fields": ["all"],
                "warnings": ["无行情数据"]}

    warnings = []
    required = ["price", "open", "high", "low", "change_pct"]
    missing = [k for k in required if quote.get(k) is None]
    zero_fields = [k for k in required if quote.get(k, 0) == 0
                   and k not in ("change_pct",)]

    is_delayed = True  # 腾讯/新浪均为非Level2延迟行情
    quality = "ok"

    if missing:
        quality = "degraded"
        warnings.append(f"缺失: {', '.join(missing)}")
    if zero_fields:
        quality = "degraded"
        warnings.append(f"零值: {', '.join(zero_fields)}")
    if quote.get("high", 0) < quote.get("low", 0):
        quality = "invalid"
        warnings.append("high < low")
    if quote.get("price", 0) <= 0:
        quality = "unavailable"
        warnings.append("price <= 0")

    result = {
        "quality_level": quality,
        "source": source,
        "is_delayed": is_delayed,
        "missing_fields": missing,
        "warnings": warnings,
        "assessed_at": datetime.now().isoformat(),
    }
    quote["_quality"] = result
    return result


def log_data_quality(source: str, endpoint: str, status: str,
                     latency_ms: float = None, error_message: str = None):
    """写入数据质量日志到数据库（非阻塞,失败不影响主流程）"""
    try:
        from src.utils.database import SessionLocal
        from src.data.models_v6 import DataQualityLog

        db = SessionLocal()
        entry = DataQualityLog(
            source=source, endpoint=endpoint,
            check_time=datetime.now(), status=status,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        db.add(entry)
        db.commit()
        db.close()
    except Exception as e:
        logger.debug(f"QualityLog skipped: {e}")


def get_quality_summary() -> dict:
    """获取最近数据源健康摘要"""
    try:
        from src.utils.database import SessionLocal
        from src.data.models_v6 import DataQualityLog
        from sqlalchemy import desc

        db = SessionLocal()
        recent = (db.query(DataQualityLog)
                  .order_by(desc(DataQualityLog.check_time))
                  .limit(50).all())
        db.close()

        if not recent:
            return {"status": "no_data", "sources": {}}

        sources = {}
        for r in recent:
            if r.source not in sources:
                sources[r.source] = {"ok": 0, "degraded": 0, "error": 0,
                                     "last_check": None}
            sources[r.source][r.status] = sources[r.source].get(r.status, 0) + 1
            sources[r.source]["last_check"] = (
                r.check_time.isoformat() if r.check_time else None)

        total = len(recent)
        ok_count = sum(1 for r in recent if r.status == "ok")
        return {
            "status": "healthy" if ok_count / max(total, 1) > 0.8 else "degraded",
            "total_checks": total,
            "ok_rate": round(ok_count / max(total, 1) * 100, 1),
            "sources": sources,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}
