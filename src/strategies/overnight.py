"""
尾盘隔夜雷达 —— 一夜持股法
"""

from src.strategies.base import BaseStrategy


class OvernightRadar(BaseStrategy):
    name = "overnight"
    description = "尾盘筛选隔夜候选，目标次日冲高2%，优先规避尾盘诱多和量化收割"

    def check_hard_filters(self, quote: dict, **context) -> tuple:
        failed = []

        chg = quote.get("change_pct", 0)
        if chg < 2.5:
            failed.append(f"涨幅{chg:.1f}%低于2.5%")
        elif chg > 6:
            failed.append(f"涨幅{chg:.1f}%偏高")

        vol_ratio = quote.get("volume_ratio", 0)
        if vol_ratio < 1.2:
            failed.append(f"量比{vol_ratio:.1f}不满足≥1.2")

        turnover = quote.get("turnover", 0)
        if turnover < 5:
            failed.append(f"换手率{turnover:.1f}%不足")
        elif turnover > 10:
            failed.append(f"换手率{turnover:.1f}%过大")

        cap = context.get("float_market_cap", None)
        if cap is not None:
            if cap < 50:
                failed.append(f"流通市值{cap:.0f}亿偏低")
            elif cap > 200:
                failed.append(f"流通市值{cap:.0f}亿偏高")
        else:
            failed.append("缺少流通市值数据")

        bars = context.get("daily_bars", [])
        if bars and len(bars) >= 20:
            ma5 = sum(b.get("close", 0) for b in bars[-5:]) / 5
            ma10 = sum(b.get("close", 0) for b in bars[-10:]) / 10
            ma20 = sum(b.get("close", 0) for b in bars[-20:]) / 20
            price = quote.get("price", 0)
            if not (price > ma5 > ma10 > ma20):
                failed.append("K线形态不满足多头排列")
        else:
            failed.append("日线数据不足")

        high = quote.get("high", 0)
        low = quote.get("low", 0)
        price = quote.get("price", 0)
        if high > low:
            close_pos = (price - low) / (high - low) * 100
            if close_pos < 70:
                failed.append(f"收盘位置{close_pos:.0f}%偏弱")

        open_p = quote.get("open", price)
        if high > max(open_p, price) and high > low:
            shadow = (high - max(open_p, price)) / (high - low) * 100
            if shadow > 35:
                failed.append(f"上影线{shadow:.0f}%抛压")

        if bars and len(bars) >= 5:
            chg_5d = (bars[-1].get("close", 0) / bars[-5].get("close", 1) - 1) * 100
            if chg_5d > 25:
                failed.append(f"近5日涨幅{chg_5d:.1f}%过高")

        intraday = context.get("intraday_bars", [])
        if intraday:
            above = sum(1 for b in intraday
                       if b.get("price", 0) >= b.get("avg_price", 0))
            above_ratio = above / len(intraday) * 100
            if above_ratio < 70:
                failed.append(f"分时均线上方仅{above_ratio:.0f}%")

        return len(failed) == 0, failed

    def compute_match(self, quote: dict, **context) -> dict:
        _, failed = self.check_hard_filters(quote, **context)
        total = 8
        match = (total - len(failed)) / total * 100
        if match >= 90:
            status = "可执行"
        elif match >= 75:
            status = "等待确认"
        elif match >= 50:
            status = "初筛候选"
        else:
            status = "排除"
        return {"match": match, "status": status, "failed": failed}

    def assess_suitability(self, market_snapshot: dict) -> str:
        if not market_snapshot:
            return "中"
        indices = market_snapshot.get("indices", [])
        main = next((i for i in indices if "上证" in i.get("name", "")), None)
        if main:
            chg = main.get("change_pct", 0)
            if chg < -1.5:
                return "不适用"
            elif chg < -0.5:
                return "低"
            elif chg > 0.5:
                return "高"
        return "中"
