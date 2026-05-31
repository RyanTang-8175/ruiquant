"""
反量化风险评分 —— 是否容易被收割？

五个子模块各占 20%：
- 尾盘诱多 · 高位接盘 · 分时脉冲 · 放量滞涨 · 板块背离

惩罚规则：
- 低风险(0-20)：扣 0-5 分
- 中风险(21-40)：扣 6-15 分
- 高风险(41-70)：扣 16-30 分
- 极高风险(71-100)：扣 31-40 分，可直接降级为"不建议参与"
"""


def compute_anti_quant(quote: dict, intraday_bars: list = None,
                       daily_bars: list = None,
                       sector_data: dict = None) -> dict:
    if not intraday_bars:
        intraday_bars = []
    if not daily_bars:
        daily_bars = []
    if not sector_data:
        sector_data = {}

    late_lure = _check_late_day_lure(quote, intraday_bars, sector_data)
    high_trap = _check_high_position_trap(quote, daily_bars)
    pulse = _check_intraday_pulse(quote, intraday_bars)
    stall = _check_volume_stall(quote, daily_bars)
    divergence = _check_sector_divergence(quote, sector_data)

    modules = [late_lure, high_trap, pulse, stall, divergence]
    total_risk = sum(m["score"] * 0.2 for m in modules)

    if total_risk >= 71:
        level, penalty = "极高", 35
    elif total_risk >= 41:
        level, penalty = "高", 23
    elif total_risk >= 21:
        level, penalty = "中", 10
    else:
        level, penalty = "低", 3

    for m in modules:
        if m["score"] >= 71:
            penalty = max(penalty, 35)
            level = "极高"

    triggers = []
    for m in modules:
        for t in m.get("triggers", []):
            triggers.append(f"[{m['name']}] {t}")

    return {
        "total_risk": round(total_risk, 1),
        "risk_level": level,
        "penalty": penalty,
        "late_day_lure": {k: v for k, v in late_lure.items() if k != "name"},
        "high_position_trap": {k: v for k, v in high_trap.items() if k != "name"},
        "intraday_pulse": {k: v for k, v in pulse.items() if k != "name"},
        "volume_stall": {k: v for k, v in stall.items() if k != "name"},
        "sector_divergence": {k: v for k, v in divergence.items() if k != "name"},
        "triggers": triggers,
    }


# ── 1. 尾盘诱多 ──

def _check_late_day_lure(quote: dict, bars: list, sector: dict) -> dict:
    triggers = []
    score = 0

    chg = quote.get("change_pct", 0)
    late_bars = [b for b in bars if b.get("time", "") >= "14:30"]
    if late_bars and len(late_bars) >= 2:
        first_price = late_bars[0].get("price", 0)
        last_price = late_bars[-1].get("price", 0)
        if first_price > 0:
            late_chg = (last_price - first_price) / first_price * 100
            if late_chg > 2:
                score += 30
                triggers.append(f"尾盘急拉 {late_chg:.1f}%")
                if not _has_healthy_pullback(late_bars):
                    score += 20
                    triggers.append("无回踩确认")

    if late_bars and len(late_bars) >= 6:
        early_late = late_bars[:3]
        later_late = late_bars[-3:]
        early_vol = sum(b.get("volume", 0) for b in early_late) / max(len(early_late), 1)
        later_vol = sum(b.get("volume", 0) for b in later_late) / max(len(later_late), 1)
        if early_vol > 0 and later_vol > early_vol * 1.5:
            later_max = max(b.get("price", 0) for b in later_late)
            early_max = max(b.get("price", 0) for b in early_late)
            if later_max <= early_max:
                score += 25
                triggers.append("尾盘放量不续涨")

    high = quote.get("high", 0)
    low = quote.get("low", 0)
    price = quote.get("price", 0)
    if high > low:
        close_pos = (price - low) / (high - low) * 100
        if close_pos < 70:
            score += 10
            triggers.append(f"收盘位置偏低 {close_pos:.0f}%")

    if sector.get("change_pct", 0) < 0.2 and chg > 2:
        score += 20
        triggers.append("个股拉升板块未同步")

    return {"name": "尾盘诱多", "score": min(100, score), "triggers": triggers}


def _has_healthy_pullback(bars: list) -> bool:
    if len(bars) < 4:
        return False
    prices = [b.get("price", 0) for b in bars]
    peak_idx = prices.index(max(prices))
    if peak_idx >= len(prices) - 2:
        return False
    after_peak = prices[peak_idx + 1:]
    peak_price = prices[peak_idx]
    for p in after_peak:
        pullback = (peak_price - p) / peak_price * 100
        if 0.3 <= pullback <= 1.0 and p > prices[0]:
            return True
    return False


# ── 2. 高位接盘 ──

def _check_high_position_trap(quote: dict, bars: list) -> dict:
    triggers = []
    score = 0

    if bars and len(bars) >= 5:
        chg_5d = (bars[-1].get("close", 0) / bars[-5].get("close", 1) - 1) * 100
        if chg_5d > 25:
            score += 40
            triggers.append(f"近5日涨幅 {chg_5d:.1f}% 极高")
        elif chg_5d > 15:
            score += 25
            triggers.append(f"近5日涨幅 {chg_5d:.1f}% 高位")

    turnover = quote.get("turnover", 0)
    if turnover > 10:
        score += 15
        triggers.append(f"换手率 {turnover:.1f}% 偏高")

    chg = quote.get("change_pct", 0)
    vol_ratio = quote.get("volume_ratio", 1.0)
    if vol_ratio > 1.5 and chg < 3:
        score += 20
        triggers.append("放量滞涨")

    high = quote.get("high", 0)
    low = quote.get("low", 0)
    price = quote.get("price", 0)
    open_p = quote.get("open", price)
    if high > max(open_p, price) and high > low:
        shadow = (high - max(open_p, price)) / (high - low) * 100
        if shadow > 35:
            score += 20
            triggers.append(f"长上影 {shadow:.0f}%")

    if bars and len(bars) >= 20:
        high_20 = max(b.get("high", 0) for b in bars[-20:])
        if high_20 > 0 and price > 0:
            space = (high_20 - price) / price * 100
            if space < 3:
                score += 15
                triggers.append("上方3%内前高压力")

    return {"name": "高位接盘", "score": min(100, score), "triggers": triggers}


# ── 3. 分时脉冲 ──

def _check_intraday_pulse(quote: dict, bars: list) -> dict:
    triggers = []
    score = 0

    if not bars or len(bars) < 10:
        return {"name": "分时脉冲", "score": score, "triggers": triggers}

    pulses = 0
    for i in range(5, len(bars)):
        window = bars[i - 5:i + 1]
        prices = [b.get("price", 0) for b in window]
        if prices[0] > 0:
            chg_5min = (prices[-1] - prices[0]) / prices[0] * 100
            if chg_5min >= 1:
                pulses += 1
                if i + 10 < len(bars):
                    future_price = bars[i + 10].get("price", prices[-1])
                    retrace = (prices[-1] - future_price) / prices[-1] * 100
                    if retrace > 0.5 * abs(chg_5min):
                        score += 15
                        triggers.append(f"脉冲后回吐 {retrace:.1f}%")

    if pulses >= 3:
        score += 20
        triggers.append(f"多次脉冲 {pulses}次")

    crosses = _count_avg_crosses(bars)
    if crosses >= 4:
        score += 20
        triggers.append(f"均价线反复穿越 {crosses}次")

    return {"name": "分时脉冲", "score": min(100, score), "triggers": triggers}


def _count_avg_crosses(bars: list) -> int:
    crosses = 0
    prev_above = None
    for b in bars:
        above = b.get("price", 0) > b.get("avg_price", 0)
        if prev_above is not None and above != prev_above:
            crosses += 1
        prev_above = above
    return crosses


# ── 4. 放量滞涨 ──

def _check_volume_stall(quote: dict, bars: list) -> dict:
    triggers = []
    score = 0

    chg = quote.get("change_pct", 0)
    vol_ratio = quote.get("volume_ratio", 1.0)

    if vol_ratio > 1.5 and chg < 3:
        score += 35
        triggers.append(f"量比{vol_ratio:.1f}x 涨幅仅{chg:.1f}%")

    high = quote.get("high", 0)
    low = quote.get("low", 0)
    price = quote.get("price", 0)
    if high > low:
        close_pos = (price - low) / (high - low) * 100
        if vol_ratio > 1.3 and close_pos < 70:
            score += 20
            triggers.append("放量+收盘偏弱")

    open_p = quote.get("open", price)
    if vol_ratio > 1.3 and high > max(open_p, price) and high > low:
        shadow = (high - max(open_p, price)) / (high - low) * 100
        if shadow > 35:
            score += 20
            triggers.append("放量+长上影")

    return {"name": "放量滞涨", "score": min(100, score), "triggers": triggers}


# ── 5. 板块背离 ──

def _check_sector_divergence(quote: dict, sector: dict) -> dict:
    triggers = []
    score = 0

    chg = quote.get("change_pct", 0)
    sector_chg = sector.get("change_pct", None)

    if sector_chg is not None:
        if chg >= 3 and sector_chg < 0.5:
            score += 35
            triggers.append(f"个股+{chg:.1f}% 板块仅{sector_chg:.1f}%")

    if sector.get("leader_status", "") == "weak":
        score += 20
        triggers.append("龙头走弱")

    if sector.get("ebb_risk", 0) > 0.5:
        score += 25
        triggers.append("板块退潮风险高")

    return {"name": "板块背离", "score": min(100, score), "triggers": triggers}
