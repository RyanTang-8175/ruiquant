"""
持股延续分 —— 能不能从隔夜升级为 1-2 天或 2-3 天短持？
"""


def compute_continuation(quote: dict, daily_bars: list = None) -> dict:
    sub = {}
    if not daily_bars:
        daily_bars = []

    ma5 = _get_ma(daily_bars, 5)
    ma10 = _get_ma(daily_bars, 10)
    price = quote.get("price", 0)

    if ma5 and ma10 and price:
        if price > ma5 > ma10:
            sub["均线"] = 85
        elif price > ma5:
            sub["均线"] = 65
        elif price > ma10:
            sub["均线"] = 50
        else:
            sub["均线"] = 30
    else:
        sub["均线"] = 50

    chg_5d = _calc_5d_change(daily_bars)
    if chg_5d is None:
        sub["近5日涨幅"] = 50
    elif chg_5d <= 10:
        sub["近5日涨幅"] = 80
    elif chg_5d <= 15:
        sub["近5日涨幅"] = 55
    elif chg_5d <= 25:
        sub["近5日涨幅"] = 30
    else:
        sub["近5日涨幅"] = 10

    chg = quote.get("change_pct", 0)
    vol_ratio = quote.get("volume_ratio", 1.0)
    if chg > 0 and vol_ratio >= 1.2:
        sub["量价"] = 75
    elif chg > 0 and vol_ratio >= 1.0:
        sub["量价"] = 60
    elif chg < 0 and vol_ratio < 1.0:
        sub["量价"] = 55
    elif chg < 0 and vol_ratio >= 1.5:
        sub["量价"] = 25
    else:
        sub["量价"] = 50

    high_20 = _get_high_20(daily_bars)
    if high_20 and price:
        space = (high_20 - price) / price * 100
        if space > 5:
            sub["压力空间"] = 80
        elif space > 3:
            sub["压力空间"] = 60
        elif space > 1:
            sub["压力空间"] = 40
        else:
            sub["压力空间"] = 20
    else:
        sub["压力空间"] = 50

    sub["板块延续"] = 55

    if chg > 5:
        sub["低开风险"] = 35
    elif chg > 3:
        sub["低开风险"] = 45
    elif chg > 0:
        sub["低开风险"] = 60
    else:
        sub["低开风险"] = 70

    weights = {"均线": 0.20, "近5日涨幅": 0.20, "量价": 0.20,
               "压力空间": 0.15, "板块延续": 0.15, "低开风险": 0.10}
    score = sum(sub[k] * weights[k] for k in sub)

    return {
        "score": round(score, 1),
        "sub_scores": sub,
        "explanation": f"延续分 {score:.0f} — {'可延长' if score > 65 else '维持' if score > 45 else '不建议延长'}"
    }


def _get_ma(bars: list, period: int) -> float:
    if not bars or len(bars) < period:
        return None
    closes = [b.get("close", b.get("price", 0)) for b in bars[-period:]]
    return sum(closes) / period


def _calc_5d_change(bars: list) -> float:
    if not bars or len(bars) < 5:
        return None
    first = bars[-5].get("close", bars[-5].get("price", 0))
    last = bars[-1].get("close", bars[-1].get("price", 0))
    if first and first > 0:
        return (last - first) / first * 100
    return None


def _get_high_20(bars: list) -> float:
    if not bars:
        return None
    highs = [b.get("high", b.get("price", 0)) for b in bars[-20:]]
    return max(highs) if highs else None
