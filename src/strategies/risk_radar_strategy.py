"""
风险雷达 —— 先找不能碰的股票
"""

from src.strategies.base import BaseStrategy


class RiskRadar(BaseStrategy):
    name = "risk_radar"
    description = "优先识别不能碰的股票，九类风险信号"

    def check_hard_filters(self, quote: dict, **context) -> tuple:
        return True, []

    def compute_match(self, quote: dict, **context) -> dict:
        risks = []
        chg = quote.get("change_pct", 0)
        turnover = quote.get("turnover", 0)
        vol_ratio = quote.get("volume_ratio", 1.0)
        high = quote.get("high", 0)
        low = quote.get("low", 0)
        price = quote.get("price", 0)
        open_p = quote.get("open", price)

        if chg > 5:
            risks.append({"type": "追高风险", "level": "中" if chg < 7 else "高",
                         "detail": f"涨幅{chg:.1f}%"})
        if turnover > 10:
            risks.append({"type": "高换手", "level": "高" if turnover > 15 else "中",
                         "detail": f"换手率{turnover:.1f}%"})
        if high > max(open_p, price) and high > low:
            shadow = (high - max(open_p, price)) / (high - low) * 100
            if shadow > 35:
                risks.append({"type": "长上影", "level": "高" if shadow > 50 else "中",
                             "detail": f"上影线{shadow:.0f}%"})
        if vol_ratio > 1.5 and chg < 3:
            risks.append({"type": "放量滞涨", "level": "中",
                         "detail": f"量比{vol_ratio:.1f}x"})

        bars = context.get("daily_bars", [])
        if bars and len(bars) >= 20 and price > 0:
            high_20 = max(b.get("high", 0) for b in bars[-20:])
            space = (high_20 - price) / price * 100
            if 0 < space < 3:
                risks.append({"type": "前高压力", "level": "中",
                             "detail": f"距前高仅{space:.1f}%"})
        if bars and len(bars) >= 5:
            chg_5d = (bars[-1].get("close", 0) / bars[-5].get("close", 1) - 1) * 100
            if chg_5d > 15:
                level = "高" if chg_5d > 25 else "中"
                risks.append({"type": "高位接盘", "level": level,
                             "detail": f"近5日{chg_5d:.1f}%"})

        match = min(100, len(risks) * 25)
        high_count = sum(1 for r in risks if r["level"] == "高")
        status = "高风险" if high_count >= 2 else "中风险" if risks else "低风险"
        return {"match": match, "status": status, "risks": risks}

    def assess_suitability(self, market_snapshot: dict) -> str:
        return "高"
