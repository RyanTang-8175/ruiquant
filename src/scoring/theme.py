"""
题材分 —— 是不是市场主线？
"""


def compute_theme(quote: dict, sector_data: dict = None,
                  market_snapshot: dict = None) -> dict:
    sub = {}
    if not sector_data:
        sector_data = {}

    sector_chg = sector_data.get("change_pct", 0)
    if sector_chg > 3:
        sub["板块涨幅"] = 85
    elif sector_chg > 2:
        sub["板块涨幅"] = 75
    elif sector_chg > 1:
        sub["板块涨幅"] = 65
    elif sector_chg > 0:
        sub["板块涨幅"] = 55
    elif sector_chg > -1:
        sub["板块涨幅"] = 40
    else:
        sub["板块涨幅"] = 25

    limit_up_count = sector_data.get("limit_up_count", 0)
    if limit_up_count >= 5:
        sub["涨停数"] = 85
    elif limit_up_count >= 3:
        sub["涨停数"] = 75
    elif limit_up_count >= 2:
        sub["涨停数"] = 65
    elif limit_up_count >= 1:
        sub["涨停数"] = 50
    else:
        sub["涨停数"] = 35

    strong_ratio = sector_data.get("strong_ratio", 0)
    if strong_ratio > 0.5:
        sub["强势股"] = 80
    elif strong_ratio > 0.3:
        sub["强势股"] = 65
    elif strong_ratio > 0.1:
        sub["强势股"] = 50
    else:
        sub["强势股"] = 35

    leader_status = sector_data.get("leader_status", "unknown")
    if leader_status == "strong":
        sub["龙头"] = 85
    elif leader_status == "stable":
        sub["龙头"] = 65
    elif leader_status == "weak":
        sub["龙头"] = 30
    else:
        sub["龙头"] = 45

    linkage = sector_data.get("linkage", 0.5)
    sub["联动"] = round(linkage * 100, 1)

    news_score = sector_data.get("news_score", 50)
    sub["催化"] = news_score

    ebb_risk = sector_data.get("ebb_risk", 0)
    sub["退潮风险"] = -ebb_risk * 100 if ebb_risk > 0 else 0

    weights = {"板块涨幅": 0.15, "涨停数": 0.20, "强势股": 0.15,
               "龙头": 0.20, "联动": 0.15, "催化": 0.10, "退潮风险": 0.20}
    score = sum(sub.get(k, 50 if k != "退潮风险" else 0) * weights[k]
                for k in weights)

    chg = quote.get("change_pct", 0)
    if chg >= 3 and sector_chg < 0.5:
        score *= 0.6
        sub["孤立上涨"] = True
    else:
        sub["孤立上涨"] = False

    return {
        "score": round(max(0, min(100, score)), 1),
        "sub_scores": sub,
        "explanation": f"题材分 {score:.0f} — {'主线' if score > 65 else '活跃' if score > 50 else '偏弱'}"
    }
