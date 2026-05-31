"""
策略匹配分 —— 符合哪个短线方法？

第一阶段实现：尾盘隔夜 / 短持延续 / 风险雷达
"""


def compute_strategy_match(quote: dict, intraday_bars: list = None,
                           daily_bars: list = None,
                           sector_data: dict = None) -> dict:
    sub = {}
    matched = []

    overnight = _match_overnight(quote, intraday_bars, daily_bars)
    sub["尾盘隔夜"] = round(overnight["match"], 1)
    if overnight["match"] >= 50:
        matched.append({"strategy": "尾盘隔夜雷达", "match": overnight["match"],
                        "status": overnight["status"]})

    continuation = _match_continuation_radar(quote, daily_bars)
    sub["短持延续"] = round(continuation["match"], 1)
    if continuation["match"] >= 50:
        matched.append({"strategy": "短持延续雷达", "match": continuation["match"],
                        "status": continuation["status"]})

    risk = _match_risk_radar(quote, daily_bars)
    sub["风险雷达"] = round(risk["match"], 1)
    if risk["match"] >= 50:
        matched.append({"strategy": "风险雷达", "match": risk["match"],
                        "status": risk["status"]})

    scores = [overnight["match"], continuation["match"]]
    strategy_score = max(scores) if scores else 50

    return {
        "score": round(strategy_score, 1),
        "sub_scores": sub,
        "matched_strategies": matched,
        "explanation": f"策略匹配 {strategy_score:.0f} — 匹配 {len(matched)} 个策略"
    }


def _match_overnight(quote: dict, intraday_bars: list, daily_bars: list) -> dict:
    cond_met, cond_fail = [], []

    chg = quote.get("change_pct", 0)
    if 2.5 <= chg <= 5.5:
        cond_met.append(f"涨幅{chg:.1f}%")
    elif chg < 2.5:
        cond_fail.append(f"涨幅不足 {chg:.1f}%")
    elif chg > 6:
        cond_fail.append(f"涨幅过大{chg:.1f}%追高风险")
    else:
        cond_fail.append(f"涨幅{chg:.1f}%偏热")

    vol_ratio = quote.get("volume_ratio", 0)
    if vol_ratio >= 1.2:
        cond_met.append(f"量比{vol_ratio:.1f}")
    else:
        cond_fail.append(f"量比不足 {vol_ratio:.1f}")

    turnover = quote.get("turnover", 0)
    if 5 <= turnover <= 10:
        cond_met.append(f"换手{turnover:.1f}%")
    elif turnover < 5:
        cond_fail.append(f"换手偏低{turnover:.1f}%")
    else:
        cond_fail.append(f"换手偏高{turnover:.1f}%")

    if daily_bars and len(daily_bars) >= 20:
        ma5 = sum(b.get("close", 0) for b in daily_bars[-5:]) / 5
        ma10 = sum(b.get("close", 0) for b in daily_bars[-10:]) / 10
        ma20 = sum(b.get("close", 0) for b in daily_bars[-20:]) / 20
        price = quote.get("price", 0)
        if price > ma5 > ma10 > ma20:
            cond_met.append("MA多头排列")
        elif price <= ma5:
            cond_fail.append("价格低于MA5")
        else:
            cond_fail.append("均线未多头排列")

    if intraday_bars:
        above = sum(1 for b in intraday_bars
                    if b.get("price", 0) >= b.get("avg_price", 0))
        above_ratio = above / len(intraday_bars) * 100
        if above_ratio >= 70:
            cond_met.append(f"分时均线上方{above_ratio:.0f}%")
        else:
            cond_fail.append(f"分时均线上方仅{above_ratio:.0f}%")
    else:
        cond_fail.append("无分时数据")

    met = len(cond_met)
    total = met + len(cond_fail)
    match = met / max(total, 1) * 100

    if match >= 80:
        status = "可执行"
    elif match >= 60:
        status = "等待确认"
    elif match >= 40:
        status = "初筛候选"
    else:
        status = "排除"

    return {"match": match, "status": status,
            "cond_met": cond_met, "cond_fail": cond_fail}


def _match_continuation_radar(quote: dict, daily_bars: list) -> dict:
    cond_met, cond_fail = [], []

    if daily_bars and len(daily_bars) >= 20:
        ma5 = sum(b.get("close", 0) for b in daily_bars[-5:]) / 5
        ma10 = sum(b.get("close", 0) for b in daily_bars[-10:]) / 10
        price = quote.get("price", 0)
        if price > ma5 and ma5 > ma10:
            cond_met.append("趋势未破")
        else:
            cond_fail.append("趋势偏弱")

        chg_5d = (daily_bars[-1].get("close", 0) / daily_bars[-5].get("close", 1) - 1) * 100
        if chg_5d <= 15:
            cond_met.append(f"近5日涨幅{chg_5d:.1f}%可控")
        else:
            cond_fail.append(f"近5日涨幅{chg_5d:.1f}%偏高")
    else:
        cond_fail.append("K线数据不足")

    vol_ratio = quote.get("volume_ratio", 1.0)
    if 1.0 <= vol_ratio <= 2.5:
        cond_met.append("量价健康")
    elif vol_ratio > 2.5:
        cond_fail.append("量能过大")
    else:
        cond_fail.append("量能不足")

    met = len(cond_met)
    total = met + len(cond_fail)
    match = met / max(total, 1) * 100

    if match >= 70:
        status = "2-3天"
    elif match >= 50:
        status = "1-2天"
    else:
        status = "不建议继续"

    return {"match": match, "status": status,
            "cond_met": cond_met, "cond_fail": cond_fail}


def _match_risk_radar(quote: dict, daily_bars: list) -> dict:
    risk_flags = []

    chg = quote.get("change_pct", 0)
    turnover = quote.get("turnover", 0)
    vol_ratio = quote.get("volume_ratio", 1.0)

    if chg > 5:
        risk_flags.append("涨幅偏高")
    if turnover > 10:
        risk_flags.append("换手过高")
    if vol_ratio > 2.5:
        risk_flags.append("量比异常")

    high = quote.get("high", 0)
    low = quote.get("low", 0)
    price = quote.get("price", 0)
    open_p = quote.get("open", price)
    if high > max(open_p, price) and high > low:
        shadow = (high - max(open_p, price)) / (high - low) * 100
        if shadow > 35:
            risk_flags.append("长上影")

    if daily_bars and len(daily_bars) >= 5:
        chg_5d = (daily_bars[-1].get("close", 0) / daily_bars[-5].get("close", 1) - 1) * 100
        if chg_5d > 15:
            risk_flags.append("高位风险")

    match = min(100, len(risk_flags) * 25)
    status = "高风险" if match >= 60 else "中风险" if match >= 30 else "低风险"

    return {"match": match, "status": status, "risk_flags": risk_flags}
