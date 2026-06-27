"""估值趋势偏离度因子。

短线场景里，价格低于均线不等于低估。这里保守处理为:
- PE/PB 是估值锚，决定主要方向。
- 均线偏离只表达拥挤/趋势位置，不能单独把下跌趋势奖励成机会。
"""


def _trend_location_score(deviation: float, long_horizon: bool = False) -> int:
    """价格相对均线的位置分。

    分数接近 50 表示位置健康；过高是拥挤，过低是趋势破坏风险。
    """
    if long_horizon:
        if deviation < -20:
            return 30
        if deviation < -10:
            return 42
        if deviation < 10:
            return 55
        if deviation < 20:
            return 42
        return 28

    if deviation < -15:
        return 25
    if deviation < -8:
        return 38
    if deviation < -3:
        return 48
    if deviation < 5:
        return 58
    if deviation < 10:
        return 45
    return 25

def compute_valuation_deviation(quote: dict, daily_bars: list = None) -> dict:
    """计算估值偏离度。

    没有基本面时返回中性。只有价格均线数据时，输出趋势位置提示，
    不把跌破均线解释为低估，避免对下跌趋势给出虚假的机会加分。
    """
    sub = {}
    price = quote.get("price", 0) or 0
    if price <= 0:
        return {"score": 50, "sub_scores": {}, "direction": "中性", "explanation": "无有效价格"}

    # 均线偏离 (代理: 代替bp对趋势的偏离)
    if daily_bars and len(daily_bars) >= 20:
        closes = [b.get("close", 0) for b in daily_bars]
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
        deviation_20 = (price - ma20) / ma20 * 100 if ma20 > 0 else 0
        deviation_60 = (price - ma60) / ma60 * 100 if ma60 > 0 else 0

        sub["20日均线位置"] = _trend_location_score(deviation_20)
        sub["60日均线位置"] = _trend_location_score(deviation_60, long_horizon=True)
    else:
        sub["20日均线位置"] = 50
        sub["60日均线位置"] = 50

    # PE维度 (如果有)
    pe = quote.get("pe_ratio", 0) or 0
    has_fundamental = False
    if pe > 0:
        has_fundamental = True
        if pe < 10:
            sub["PE分位"] = 80  # 低PE=便宜
        elif pe < 20:
            sub["PE分位"] = 65
        elif pe < 40:
            sub["PE分位"] = 50
        elif pe < 80:
            sub["PE分位"] = 35
        else:
            sub["PE分位"] = 20
    else:
        sub["PE分位"] = 50

    # PB维度 (如果有, 来自quote)
    pb = quote.get("pb_ratio", 0) or 0
    if pb > 0:
        has_fundamental = True
        if pb < 1:
            sub["PB分位"] = 80  # 破净=极度低估
        elif pb < 2:
            sub["PB分位"] = 65
        elif pb < 4:
            sub["PB分位"] = 50
        elif pb < 8:
            sub["PB分位"] = 35
        else:
            sub["PB分位"] = 20
    else:
        sub["PB分位"] = 50

    if not has_fundamental:
        return {
            "score": 50,
            "sub_scores": sub,
            "direction": "估值未知",
            "explanation": "缺少 PE/PB 估值锚，仅展示均线位置，不判定低估或高估",
        }

    weights = {"20日均线位置": 0.20, "60日均线位置": 0.15, "PE分位": 0.40, "PB分位": 0.25}
    score = sum(sub[k] * weights.get(k, 0.1) for k in sub)

    if score >= 70:
        direction = "显著低估"
    elif score >= 60:
        direction = "偏低估"
    elif score >= 45:
        direction = "估值合理"
    elif score >= 35:
        direction = "偏高估"
    else:
        direction = "显著高估"

    return {
        "score": round(score, 1), "sub_scores": sub, "direction": direction,
        "explanation": f"估值偏离 {score:.0f} — {direction}"
    }
