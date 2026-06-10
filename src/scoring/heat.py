"""
热度分 —— 有没有资金关注？

热度分高 ≠ 可以买。热度分只判断市场关注度，
买点质量由承接分、策略匹配和反量化风险决定。
"""


def compute_heat(quote: dict, daily_bars: list = None) -> dict:
    sub = {}
    chg = quote.get("change_pct", 0)

    # 涨幅状态 (25%) — 拉伸区间拉开差距
    if chg > 7:
        sub["涨幅"] = 95
    elif chg > 5:
        sub["涨幅"] = 85
    elif chg > 3:
        sub["涨幅"] = 75
    elif chg > 1:
        sub["涨幅"] = 60
    elif chg > 0:
        sub["涨幅"] = 50
    elif chg > -2:
        sub["涨幅"] = 35
    elif chg > -5:
        sub["涨幅"] = 20
    else:
        sub["涨幅"] = 5

    # 量比 (20%)
    vol_ratio = quote.get("volume_ratio", 1.0)
    if vol_ratio > 3:
        sub["量比"] = 75
    elif vol_ratio > 2:
        sub["量比"] = 80
    elif vol_ratio > 1.5:
        sub["量比"] = 70
    elif vol_ratio > 1.2:
        sub["量比"] = 60
    elif vol_ratio > 1.0:
        sub["量比"] = 50
    elif vol_ratio > 0.7:
        sub["量比"] = 40
    else:
        sub["量比"] = 25

    # 成交额 (20%)
    amount = quote.get("amount", 0)
    if amount > 50e8:
        sub["成交额"] = 85
    elif amount > 20e8:
        sub["成交额"] = 80
    elif amount > 10e8:
        sub["成交额"] = 70
    elif amount > 5e8:
        sub["成交额"] = 60
    elif amount > 1e8:
        sub["成交额"] = 50
    else:
        sub["成交额"] = 30

    # 换手率 (20%)
    turnover = quote.get("turnover", 0)
    if 5 <= turnover <= 10:
        sub["换手率"] = 75
    elif 3 <= turnover < 5:
        sub["换手率"] = 65
    elif 10 < turnover <= 15:
        sub["换手率"] = 55
    elif 1 <= turnover < 3:
        sub["换手率"] = 45
    elif turnover > 15:
        sub["换手率"] = 30
    else:
        sub["换手率"] = 20

    # 排行榜位置 (10%)
    sub["榜单"] = 60 if (chg > 0 and amount > 5e8) else 40

    # 日内振幅 (5%)
    high = quote.get("high", 0)
    low = quote.get("low", 0)
    pre_close = quote.get("pre_close", 1)
    if pre_close > 0 and high > low:
        amp = (high - low) / pre_close * 100
        if 3 <= amp <= 7:
            sub["振幅"] = 70
        elif 2 <= amp < 3:
            sub["振幅"] = 55
        elif amp > 7:
            sub["振幅"] = 40
        else:
            sub["振幅"] = 35
    else:
        sub["振幅"] = 50

    weights = {"涨幅": 0.25, "量比": 0.20, "成交额": 0.20,
               "换手率": 0.20, "榜单": 0.10, "振幅": 0.05}
    score = sum(sub[k] * weights[k] for k in sub)

    return {
        "score": round(score, 1),
        "sub_scores": sub,
        "explanation": f"热度分 {score:.0f} — 市场{'高度' if score > 70 else '适度' if score > 50 else '偏低'}关注"
    }
