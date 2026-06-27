"""市场Regime识别: ADX+波动率→趋势/震荡/高波/低波
借鉴Regime择时策略: 不同市场状态用不同因子权重
"""

def compute_regime(daily_bars: list = None, quote: dict = None) -> dict:
    """判断当前市场状态: trending_up/trending_down/ranging/high_vol/low_vol"""
    if not daily_bars or len(daily_bars) < 14:
        return {"regime": "unknown", "label": "数据不足", "confidence": 0}

    closes = [b.get("close", 0) for b in daily_bars]
    highs = [b.get("high", 0) for b in daily_bars]
    lows = [b.get("low", 0) for b in daily_bars]

    # ADX (14周期简化版)
    n = 14
    tr_list, plus_dm, minus_dm = [], [], []
    for i in range(1, min(len(closes), n + 5)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        up = up_move if up_move > 0 else 0
        down = down_move if down_move > 0 else 0
        plus_dm.append(up if up > down else 0)
        minus_dm.append(down if down > up else 0)

    atr = sum(tr_list[-n:]) / max(len(tr_list[-n:]), 1) if tr_list else 0
    pdi = (sum(plus_dm[-n:]) / max(len(plus_dm[-n:]), 1)) / atr * 100 if atr > 0 else 0
    mdi = (sum(minus_dm[-n:]) / max(len(minus_dm[-n:]), 1)) / atr * 100 if atr > 0 else 0
    dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0
    adx = dx  # simplified, no smoothing

    # 波动率 (近14日收益率标准差年化)
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes)) if closes[i-1] > 0]
    if len(returns) >= 5:
        mean_r = sum(returns) / len(returns)
        vol = (sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)) ** 0.5 * (252 ** 0.5) * 100 if len(returns) > 1 else 0
    else:
        vol = 0

    price_trend = closes[-1] - closes[-min(5, len(closes))]
    trend_pct = price_trend / closes[-min(5, len(closes))] * 100 if closes[-min(5, len(closes))] > 0 else 0

    if vol > 50 or adx > 40:
        regime = "trending_up" if trend_pct > 0 else "trending_down"
        label = "趋势上涨" if trend_pct > 0 else "趋势下跌"
        confidence = min(90, int(max(vol / 2, adx)))
    elif vol > 25 or adx > 25:
        regime = "high_vol" if vol > 30 else "ranging"
        label = "高波动" if vol > 30 else "震荡"
        confidence = min(75, int(max(vol / 2, adx)))
    elif vol < 10:
        regime = "low_vol"
        label = "低波动"
        confidence = max(30, int(50 - vol))
    else:
        regime = "ranging"
        label = "震荡"
        confidence = 60

    return {
        "regime": regime, "label": label, "confidence": confidence,
        "adx": round(adx, 1), "volatility_annual": round(vol, 1),
        "trend_5d_pct": round(trend_pct, 1),
        "advice": _regime_advice(regime)
    }

def _regime_advice(regime: str) -> str:
    return {
        "trending_up": "趋势向上——动量因子和趋势因子权重可提高，风控因子可放宽",
        "trending_down": "趋势向下——风控因子优先，动量因子降权，不宜追高",
        "high_vol": "高波动——量价因子噪音大，基本面因子更可靠",
        "low_vol": "低波动——可提高仓位但需警惕变盘",
        "ranging": "震荡市——横截面因子优于时序因子，反转因子可关注",
    }.get(regime, "")
