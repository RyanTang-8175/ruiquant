"""估值趋势偏离度因子: bp=1/pb 对行业趋势取残差
bp的短期偏离度 = 当期bp - 近期bp的滚动回归预测值
偏离越大=潜在回归空间越大
"""

def compute_valuation_deviation(quote: dict, daily_bars: list = None) -> dict:
    """计算估值偏离度(代理版: 用价格vs近20日均线的偏离替代bp回归)
    真实bp=1/pb需要iFinD基本面数据, 这里用价格对均线的偏离做代理
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

        # 偏离度打分: 低于均线越多=越低估=机会分越高
        if deviation_20 < -15:
            sub["20日均线偏离"] = 85  # 严重低估
        elif deviation_20 < -10:
            sub["20日均线偏离"] = 75
        elif deviation_20 < -5:
            sub["20日均线偏离"] = 65
        elif deviation_20 < 0:
            sub["20日均线偏离"] = 55
        elif deviation_20 < 5:
            sub["20日均线偏离"] = 45
        elif deviation_20 < 10:
            sub["20日均线偏离"] = 30
        else:
            sub["20日均线偏离"] = 15  # 严重高估

        if deviation_60 < -20:
            sub["60日均线偏离"] = 80
        elif deviation_60 < -10:
            sub["60日均线偏离"] = 65
        elif deviation_60 < 0:
            sub["60日均线偏离"] = 50
        elif deviation_60 < 10:
            sub["60日均线偏离"] = 35
        else:
            sub["60日均线偏离"] = 20
    else:
        sub["20日均线偏离"] = 50
        sub["60日均线偏离"] = 50

    # PE维度 (如果有)
    pe = quote.get("pe_ratio", 0) or 0
    if pe > 0:
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

    weights = {"20日均线偏离": 0.40, "60日均线偏离": 0.25, "PE分位": 0.20, "PB分位": 0.15}
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
