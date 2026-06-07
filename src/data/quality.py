"""
数据质量追踪 —— 行情/评分/AI 全链路标注
每个数据源返回都标记 source、quality_level、latency 和 is_delayed
"""

import logging
import time as _time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Phase 1.3: 统一数据质量标签体系
# ═══════════════════════════════════════════════════════════

QUALITY_BADGES = {
    "ifind":        {"label": "iFinD 实时",   "color": "#52C41A", "level": "优"},
    "ifind_wencai": {"label": "iFinD 选股",   "color": "#1890FF", "level": "良"},
    "ifind_pool":   {"label": "iFinD 股池",   "color": "#1890FF", "level": "良"},
    "tencent":      {"label": "腾讯(兜底)",    "color": "#FAAD14", "level": "一般"},
    "sina":         {"label": "新浪(兜底)",    "color": "#FAAD14", "level": "一般"},
    "eastmoney":    {"label": "东财(兜底)",    "color": "#FAAD14", "level": "一般"},
}

FALLBACK_WARNING = "⚠️ iFinD 暂时不可用，当前为公开源兜底数据，仅供参考"


def fmt_freshness(ts_epoch: float) -> str:
    """返回人类可读的新鲜度：'X秒前/X分钟前/X小时前'"""
    delta = int(_time.time() - ts_epoch)
    if delta < 60:
        return f"{delta}秒前"
    if delta < 3600:
        return f"{delta // 60}分钟前"
    return f"{delta // 3600}小时前"


def get_quality_badge(source: str) -> dict:
    """获取数据源对应的质量标签"""
    return QUALITY_BADGES.get(source, {"label": source, "color": "#999", "level": "未知"})


def render_quality_html(quote: dict) -> str:
    """生成数据质量标签的 HTML 片段（供 Streamlit 页面使用）"""
    src = quote.get("source", "unknown")
    badge = get_quality_badge(src)
    freshness = ""
    ts = quote.get("_ts")
    if ts:
        freshness = f" · {fmt_freshness(ts)}"
    delayed = " · 延迟" if quote.get("is_delayed") else ""
    fallback = " · ⚠️兜底" if quote.get("_fallback") else ""
    return (
        f'<span style="display:inline-block;padding:1px 8px;border-radius:3px;'
        f'font-size:10px;color:{badge["color"]};border:1px solid {badge["color"]};'
        f'margin-right:4px;">📡 {badge["label"]} · {badge["level"]}{freshness}{delayed}{fallback}</span>'
    )


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
        try:
            entry = DataQualityLog(
                source=source, endpoint=endpoint,
                check_time=datetime.now(), status=status,
                latency_ms=latency_ms,
                error_message=error_message,
            )
            db.add(entry)
            db.commit()
        finally:
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
        try:
            recent = (db.query(DataQualityLog)
                      .order_by(desc(DataQualityLog.check_time))
                      .limit(50).all())
        finally:
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
