"""资金流因子: 量价背离检测 + 主力资金方向推断
借鉴: 大小单残差资金流强度 = 原始资金流 - Ret20回归剥离价格效应
用成交额/量比/换手率构造代理因子
"""

def compute_fund_flow(quote: dict, daily_bars: list = None) -> dict:
    sub: dict = {}
    vol_ratio = quote.get("volume_ratio", 1.0) or 1.0
    chg = quote.get("change_pct", 0) or 0
    amount = quote.get("amount", 0) or 0
    turnover = quote.get("turnover", 0) or 0

    # 1. 量价协同 (50%): 放量大涨=正向; 放量大跌=负向
    if vol_ratio > 1.5 and chg > 3: sub["量价协同"] = 85
    elif vol_ratio > 1.3 and chg > 1: sub["量价协同"] = 70
    elif vol_ratio > 1.5 and chg < -3: sub["量价协同"] = 15
    elif vol_ratio > 1.3 and chg < -1: sub["量价协同"] = 30
    elif 0.8 <= vol_ratio <= 1.2 and abs(chg) < 1: sub["量价协同"] = 50
    elif vol_ratio < 0.7: sub["量价协同"] = 40
    else: sub["量价协同"] = 50

    # 2. 量价背离 (30%): 放量但价格推不动=出货
    if vol_ratio > 1.2 and abs(chg) < 0.5: sub["量价背离"] = 20
    elif vol_ratio < 0.8 and abs(chg) > 3: sub["量价背离"] = 75
    elif vol_ratio > 1.5 and abs(chg) > 5: sub["量价背离"] = 60
    else: sub["量价背离"] = 50

    # 3. 成交额强度 (10%)
    if amount > 50e8 and chg > 2: sub["成交额强度"] = 80
    elif amount > 20e8 and chg > 1: sub["成交额强度"] = 70
    elif amount > 50e8 and chg < -2: sub["成交额强度"] = 20
    elif amount > 20e8 and chg < -1: sub["成交额强度"] = 35
    elif amount > 1e8: sub["成交额强度"] = 55
    else: sub["成交额强度"] = 40

    # 4. 换手率 (10%)
    if 5 <= turnover <= 10: sub["换手活跃"] = 65
    elif 10 < turnover <= 15: sub["换手活跃"] = 45
    elif turnover > 15: sub["换手活跃"] = 30
    elif 1 <= turnover < 5: sub["换手活跃"] = 55
    else: sub["换手活跃"] = 35

    # 5. K线量价趋势 (5%)
    if daily_bars and len(daily_bars) >= 5:
        recent_vol = [b.get("volume", 0) for b in daily_bars[-5:]]
        recent_close = [b.get("close", 0) for b in daily_bars[-5:]]
        avg_vol = sum(recent_vol) / max(len(recent_vol), 1)
        if avg_vol > 0 and recent_vol[-1] > avg_vol * 1.3:
            sub["量价趋势"] = 75 if recent_close[-1] > recent_close[-2] else 30
        elif avg_vol > 0 and recent_vol[-1] < avg_vol * 0.7:
            sub["量价趋势"] = 45
        else: sub["量价趋势"] = 55
    else: sub["量价趋势"] = 50

    weights = {"量价协同": 0.50, "量价背离": 0.30, "成交额强度": 0.10, "换手活跃": 0.05, "量价趋势": 0.05}
    score = sum(sub[k] * weights.get(k, 0.1) for k in sub)
    direction = "主力积极" if score >= 70 else "资金偏多" if score >= 55 else "资金中性" if score >= 45 else "资金偏空" if score >= 30 else "主力出货"
    return {"score": round(score, 1), "sub_scores": sub, "direction": direction,
            "explanation": f"资金流 {score:.0f} — {direction}（量比={vol_ratio:.1f} 涨跌={chg:+.1f}%）"}
