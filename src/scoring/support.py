"""
承接分 —— 上涨之后有没有人接？
"""


def compute_support(quote: dict, intraday_bars: list = None) -> dict:
    sub = {}

    above_avg_ratio = _compute_above_avg_ratio(intraday_bars)
    if above_avg_ratio >= 70:
        sub["均价线上方"] = 80
    elif above_avg_ratio >= 50:
        sub["均价线上方"] = 55
    elif above_avg_ratio >= 30:
        sub["均价线上方"] = 35
    else:
        sub["均价线上方"] = 20

    late_above = _check_late_above_avg(intraday_bars)
    sub["回踩确认"] = 80 if late_above else 40

    late_stable = _check_late_stable(intraday_bars, quote)
    sub["尾盘企稳"] = late_stable

    high = quote.get("high", 0)
    low = quote.get("low", 0)
    price = quote.get("price", 0)
    if high > low:
        pos = (price - low) / (high - low) * 100
        if pos >= 85:
            sub["收盘位置"] = 85
        elif pos >= 70:
            sub["收盘位置"] = 65
        elif pos >= 50:
            sub["收盘位置"] = 50
        elif pos >= 30:
            sub["收盘位置"] = 35
        else:
            sub["收盘位置"] = 20
    else:
        sub["收盘位置"] = 50

    open_p = quote.get("open", price)
    if high > max(open_p, price):
        upper_shadow = high - max(open_p, price)
        total_range = high - low if high > low else 0.01
        shadow_pct = upper_shadow / total_range * 100
        if shadow_pct <= 20:
            sub["上影线"] = 80
        elif shadow_pct <= 35:
            sub["上影线"] = 55
        else:
            sub["上影线"] = 25
    else:
        sub["上影线"] = 70

    if high > price and high > 0:
        pullback = (high - price) / high * 100
        if pullback <= 0.5:
            sub["冲高回落"] = 80
        elif pullback <= 1.5:
            sub["冲高回落"] = 60
        elif pullback <= 3:
            sub["冲高回落"] = 40
        else:
            sub["冲高回落"] = 20
    else:
        sub["冲高回落"] = 75

    weights = {"均价线上方": 0.25, "回踩确认": 0.20, "尾盘企稳": 0.20,
               "收盘位置": 0.15, "上影线": 0.10, "冲高回落": 0.10}
    score = sum(sub[k] * weights[k] for k in sub)

    return {
        "score": round(score, 1),
        "sub_scores": sub,
        "explanation": f"承接分 {score:.0f} — 承接{'良好' if score > 65 else '一般' if score > 45 else '不足'}"
    }


def _compute_above_avg_ratio(bars: list) -> float:
    if not bars:
        return 55
    above = sum(1 for b in bars if b.get("price", 0) >= b.get("avg_price", 0))
    return above / len(bars) * 100 if bars else 55


def _check_late_above_avg(bars: list) -> bool:
    if not bars:
        return True
    late_bars = [b for b in bars if b.get("time", "") >= "14:30"]
    if not late_bars:
        late_bars = bars[-max(1, len(bars) // 6):]
    above = sum(1 for b in late_bars if b.get("price", 0) >= b.get("avg_price", 0))
    return above >= len(late_bars) * 0.6


def _check_late_stable(bars: list, quote: dict) -> float:
    if not bars:
        return 55
    late_bars = [b for b in bars if b.get("time", "") >= "14:30"]
    if not late_bars:
        return 55
    prices = [b.get("price", 0) for b in late_bars]
    if len(prices) < 2:
        return 55
    changes = [abs(prices[i] - prices[i - 1]) / prices[i - 1] * 100
               for i in range(1, len(prices)) if prices[i - 1] > 0]
    avg_change = sum(changes) / len(changes) if changes else 0
    if avg_change <= 0.15:
        return 80
    elif avg_change <= 0.3:
        return 65
    elif avg_change <= 0.5:
        return 45
    else:
        return 25
