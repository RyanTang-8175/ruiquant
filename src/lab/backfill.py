"""短线实验室验证回填。"""

from __future__ import annotations

from datetime import datetime


def backfill_pending_verifications(limit: int = 30) -> dict:
    """回填待验证记录的后续 K 线表现。"""
    from src.memory.analysis_memory import AnalysisMemory

    completed = 0
    skipped = 0
    errors = []
    with AnalysisMemory() as memory:
        pending = memory.get_pending_verifications()[:limit]
        for record in pending:
            try:
                if _backfill_one(memory, record):
                    completed += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors.append(f"{record.get('stock_code')}: {str(exc)[:80]}")
    return {
        "checked": len(pending),
        "completed": completed,
        "skipped": skipped,
        "errors": errors,
    }


def _backfill_one(memory, record: dict) -> bool:
    from src.data.providers.registry import get_provider

    code = record.get("stock_code")
    signal_date = _parse_dt(record.get("signal_date"))
    if not code or not signal_date:
        return False

    provider = get_provider()
    bars = provider.get_daily_bars(code, start="", end="")
    if not bars:
        return False

    rows = sorted([b for b in bars if b.get("date")], key=lambda b: str(b.get("date")))
    signal_key = signal_date.strftime("%Y-%m-%d")
    future = [b for b in rows if str(b.get("date"))[:10] > signal_key]
    if not future:
        return False

    base_close = _last_close_before(rows, signal_key)
    if not base_close:
        return False

    first_hit = None
    lows = []
    closes = []
    for idx, bar in enumerate(future[:3], start=1):
        high_change = _pct(bar.get("high"), base_close)
        low_change = _pct(bar.get("low"), base_close)
        close_change = _pct(bar.get("close"), base_close)
        lows.append(low_change)
        closes.append(close_change)
        if first_hit is None and high_change is not None and high_change >= 2:
            first_hit = idx
        memory.save_backfill(record["id"], {
            "trade_date": _date_only(bar.get("date")),
            "day_offset": idx,
            "open_change_pct": _pct(bar.get("open"), base_close),
            "high_change_pct": high_change,
            "low_change_pct": low_change,
            "close_change_pct": close_change,
            "hit_plus_2pct": bool(high_change is not None and high_change >= 2),
            "first_hit_2pct_time": f"T+{first_hit}" if first_hit == idx else None,
            "hold_1d_return": closes[0] if len(closes) >= 1 else None,
            "hold_2d_return": closes[1] if len(closes) >= 2 else None,
            "hold_3d_return": closes[2] if len(closes) >= 3 else None,
            "max_drawdown": min([x for x in lows if x is not None], default=None),
        })
    return True


def _last_close_before(rows: list[dict], signal_key: str) -> float | None:
    prior = [b for b in rows if str(b.get("date"))[:10] <= signal_key]
    if not prior:
        return None
    close = prior[-1].get("close")
    return float(close) if close else None


def _pct(value, base) -> float | None:
    if value is None or not base:
        return None
    try:
        return round((float(value) - float(base)) / float(base) * 100, 2)
    except Exception:
        return None


def _parse_dt(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _date_only(value):
    text = str(value)[:10]
    return datetime.fromisoformat(text).date()
