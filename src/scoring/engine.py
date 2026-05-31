"""
AlphaEye v6 评分引擎 —— 六维短线评分
保留 v5.2 ScoringEngine 向后兼容
"""

import logging
from datetime import datetime
from typing import Optional

from src.utils.database import SessionLocal
from src.data.models_v6 import ScoreRecordV6, AntiQuantRecord

from src.scoring.schemas import SixDimensionResult, DimensionScore
from src.scoring.heat import compute_heat
from src.scoring.support import compute_support
from src.scoring.theme import compute_theme
from src.scoring.continuation import compute_continuation
from src.scoring.anti_quant import compute_anti_quant
from src.scoring.strategy_match import compute_strategy_match

logger = logging.getLogger(__name__)

QUICK_WEIGHTS = {
    'momentum': 0.25, 'turnover': 0.20, 'volatility': 0.20,
    'volume_ratio': 0.20, 'trend': 0.15,
}


class ScoringEngine:
    """v5.2 兼容评分引擎"""

    def __init__(self):
        self.db = SessionLocal()
        self.weights = QUICK_WEIGHTS

    def close(self):
        try: self.db.close()
        except: pass

    def __enter__(self): return self
    def __exit__(self, *a): self.close(); return False

    def quick_score(self, q: dict) -> dict:
        p = q.get("price", 0); o = q.get("open", 0)
        h = q.get("high", 0); l = q.get("low", 0)
        chg = q.get("change_pct", 0); turn = q.get("turnover", 0)
        f = {}
        if chg > 5: f['momentum'] = 85
        elif chg > 2: f['momentum'] = 70
        elif chg > 0: f['momentum'] = 55
        elif chg > -2: f['momentum'] = 45
        elif chg > -5: f['momentum'] = 30
        else: f['momentum'] = 15
        if turn > 20: f['turnover'] = 25
        elif turn > 10: f['turnover'] = 40
        elif turn > 3: f['turnover'] = 65
        elif turn > 1: f['turnover'] = 80
        elif turn > .3: f['turnover'] = 60
        else: f['turnover'] = 40
        if h != l:
            body = abs(p - o) / (h - l)
            if body > .7: f['volatility'] = 80 if p > o else 30
            elif body > .4: f['volatility'] = 65
            elif body > .15: f['volatility'] = 50
            else: f['volatility'] = 40
        else: f['volatility'] = 50
        if turn > 5: f['volume_ratio'] = 70
        elif turn > 2: f['volume_ratio'] = 60
        elif turn > .8: f['volume_ratio'] = 50
        else: f['volume_ratio'] = 40
        if h != l:
            pos = (p - l) / (h - l)
            if pos > .8: f['trend'] = 80
            elif pos > .6: f['trend'] = 65
            elif pos > .4: f['trend'] = 50
            elif pos > .2: f['trend'] = 35
            else: f['trend'] = 20
        else: f['trend'] = 50
        tw = sum(self.weights.get(k, .1) for k in f)
        total = sum(f[k] * self.weights.get(k, .1) for k in f) / tw if tw > 0 else 50
        total = min(100, max(0, total))
        rating = "强关注" if total >= 80 else "观察" if total >= 65 else "中性" if total >= 50 else "不追"
        return {'code': q.get('code', ''), 'total_score': round(total, 1),
                'rating': rating, 'factors': f, 'quick': True,
                'calculated_at': datetime.now()}

    def score_stock(self, code: str) -> dict:
        from src.data.realtime import get_realtime_quote
        q = get_realtime_quote(code)
        if q and q.get("price", 0) > 0:
            r = self.quick_score(q); r['name'] = q.get('name', ''); return r
        return None

    def score_all_stocks(self, limit: int = 80) -> list:
        from src.data.realtime import get_top_stocks
        stocks = get_top_stocks(sort_field="amount", asc=False, limit=limit)
        results = []
        for s in (stocks or []):
            cd = s.get("code", "")
            if not cd: continue
            r = self.score_stock(cd)
            if r: r['name'] = s.get("name", cd); results.append(r)
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results

    def save_scores(self, results: list):
        if not results: return 0
        s = 0
        try:
            for r in results:
                f = r.get('factors', {})
                rec = ScoreRecordV6(
                    code=r['code'], name=r.get('name', ''),
                    score_date=r['calculated_at'],
                    total_score=r['total_score'],
                    heat_score=f.get('momentum'),
                    support_score=f.get('trend'),
                    theme_score=50, continuation_score=50,
                    strategy_match_score=50, anti_quant_penalty=0,
                    status_label=r.get('rating', ''),
                    risk_level='中',
                )
                self.db.add(rec); s += 1
            self.db.commit()
        except Exception as e:
            self.db.rollback(); logger.error(f"save: {e}")
        return s

    def get_watchlist(self, min_score: float = 0, limit: int = 30) -> list:
        try:
            results = self.score_all_stocks(limit=max(limit * 3, 80))
            if results:
                try: self.save_scores(results)
                except: pass
            return [r for r in results if r['total_score'] >= min_score][:limit]
        except Exception as e:
            logger.error(f"watchlist: {e}")
            return []


# ═══════════════════════════════════════════
# v6 六维评分引擎
# ═══════════════════════════════════════════

class V6ScoringEngine:
    """v6 六维短线评分引擎"""

    def __init__(self, data_provider=None):
        self.db = SessionLocal()
        self.provider = data_provider

    def close(self):
        try: self.db.close()
        except: pass

    def __enter__(self): return self
    def __exit__(self, *a): self.close(); return False

    def score_stock(self, code: str, quote: dict = None,
                    intraday_bars: list = None,
                    daily_bars: list = None,
                    sector_data: dict = None,
                    market_snapshot: dict = None) -> Optional[SixDimensionResult]:
        if quote is None and self.provider:
            quote = self.provider.get_realtime_quote(code)
        if quote is None:
            from src.data.realtime import get_realtime_quote
            quote = get_realtime_quote(code)
        if not quote or quote.get("price", 0) <= 0:
            return None

        if quote.get("volume_ratio", 0) <= 0:
            try:
                from src.data.realtime import get_realtime_quote
                full = get_realtime_quote(code)
                if full:
                    for k in ("volume_ratio", "pre_close", "open", "high", "low"):
                        if not quote.get(k) and full.get(k):
                            quote[k] = full[k]
            except Exception: pass

        if intraday_bars is None and self.provider:
            intraday_bars = self.provider.get_intraday_bars(code)
        if daily_bars is None and self.provider:
            daily_bars = self.provider.get_daily_bars(
                code, start="2026-01-01", end=datetime.now().strftime("%Y-%m-%d"))

        result = SixDimensionResult(code=code, name=quote.get("name", code))

        h = compute_heat(quote, daily_bars)
        result.heat = DimensionScore(score=h["score"], weight=0.20,
            sub_scores=h["sub_scores"], explanation=h["explanation"])
        s = compute_support(quote, intraday_bars)
        result.support = DimensionScore(score=s["score"], weight=0.25,
            sub_scores=s["sub_scores"], explanation=s["explanation"])
        t = compute_theme(quote, sector_data, market_snapshot)
        result.theme = DimensionScore(score=t["score"], weight=0.20,
            sub_scores=t["sub_scores"], explanation=t["explanation"])
        c = compute_continuation(quote, daily_bars)
        result.continuation = DimensionScore(score=c["score"], weight=0.15,
            sub_scores=c["sub_scores"], explanation=c["explanation"])
        sm = compute_strategy_match(quote, intraday_bars, daily_bars, sector_data)
        result.strategy_match = DimensionScore(score=sm["score"], weight=0.20,
            sub_scores=sm["sub_scores"], explanation=sm["explanation"])
        result.matched_strategies = sm.get("matched_strategies", [])

        aq = compute_anti_quant(quote, intraday_bars, daily_bars, sector_data)
        result.anti_quant.total_risk = aq["total_risk"]
        result.anti_quant.risk_level = aq["risk_level"]
        result.anti_quant.penalty = aq["penalty"]
        result.anti_quant.triggers = aq["triggers"]
        result.anti_quant.late_day_lure = aq.get("late_day_lure", {})
        result.anti_quant.high_position_trap = aq.get("high_position_trap", {})
        result.anti_quant.intraday_pulse = aq.get("intraday_pulse", {})
        result.anti_quant.volume_stall = aq.get("volume_stall", {})
        result.anti_quant.sector_divergence = aq.get("sector_divergence", {})

        result.compute_total()
        result.dimension_details = {"heat":h,"support":s,"theme":t,"continuation":c,"strategy_match":sm,"anti_quant":aq}
        self._save_score(result)
        self._save_anti_quant(result, aq)
        return result

    def _save_score(self, result: SixDimensionResult):
        try:
            rec = ScoreRecordV6(
                code=result.code, name=result.name, score_date=datetime.now(),
                heat_score=result.heat.score, support_score=result.support.score,
                theme_score=result.theme.score, continuation_score=result.continuation.score,
                strategy_match_score=result.strategy_match.score,
                anti_quant_penalty=result.anti_quant.penalty,
                total_score=result.total_score, status_label=result.status_label,
                risk_level=result.risk_level, dimension_details=result.dimension_details,
                matched_strategies=result.matched_strategies)
            self.db.add(rec); self.db.commit()
        except Exception as e: self.db.rollback(); logger.warning(f"save: {e}")

    def _save_anti_quant(self, result: SixDimensionResult, aq: dict):
        try:
            rec = AntiQuantRecord(
                code=result.code, name=result.name, scan_date=datetime.now(),
                total_risk=aq["total_risk"], risk_level=aq["risk_level"],
                late_day_lure=aq.get("late_day_lure",{}),
                high_position_trap=aq.get("high_position_trap",{}),
                intraday_pulse=aq.get("intraday_pulse",{}),
                volume_stall=aq.get("volume_stall",{}),
                sector_divergence=aq.get("sector_divergence",{}))
            self.db.add(rec); self.db.commit()
        except Exception as e: self.db.rollback(); logger.warning(f"anti: {e}")

    def score_batch(self, codes: list, **ctx) -> list:
        results = []
        for code in codes:
            r = self.score_stock(code, **ctx)
            if r: results.append(r.to_dict())
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results

    def get_watchlist_v6(self, min_score: float = 0, limit: int = 30) -> list:
        from src.data.realtime import get_top_stocks
        stocks = get_top_stocks(sort_field="amount", asc=False, limit=100)
        results = []
        for s in (stocks or []):
            code = s.get("code", "")
            if not code: continue
            r = self.score_stock(code, quote=s)
            if r: results.append(r.to_dict())
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return [r for r in results if r['total_score'] >= min_score][:limit]

    def build_ai_context(self, code: str, quote: dict = None) -> str:
        """给 AI 注入完整的评分细节、K线数据和反量化触发项"""
        result = self.score_stock(code, quote=quote)
        if not result: return f"无法获取 {code} 的评分数据"

        d = result.to_dict()
        anti = d['anti_quant']

        # K线
        kline_text = "不可用"
        try:
            from src.data.realtime import get_kline
            kls = get_kline(code, period="101", count=20)
            if kls and len(kls) >= 5:
                closes = [k["close"] for k in kls]
                ma5 = sum(closes[-5:]) / 5
                ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else ma5
                chg_5d = (closes[-1] / closes[-5] - 1) * 100 if closes[-5] else 0
                vol_5d_avg = sum(k.get("volume", 0) for k in kls[-5:]) / 5
                vol_today = kls[-1].get("volume", 0) if kls else 0
                vratio = vol_today / vol_5d_avg if vol_5d_avg > 0 else 1
                kline_text = f"MA5={ma5:.2f} MA10={ma10:.2f} 近5日涨幅={chg_5d:.1f}% 量/5日均量={vratio:.1f}倍"
        except Exception: pass

        lines = [
            f"[{d['name']}({code}) 六维评分]",
            f"机会分: {d['total_score']}/100 状态: {d['status_label']} 风险: {d['risk_level']}",
            f"热度 {d['heat']['score']:.0f} | 承接 {d['support']['score']:.0f} | 题材 {d['theme']['score']:.0f} | 延续 {d['continuation']['score']:.0f} | 策略匹配 {d['strategy_match']['score']:.0f}",
            f"",
            f"[热度明细] {result.heat.explanation}",
            f"[承接明细] {result.support.explanation}",
            f"[延续明细] {result.continuation.explanation}",
            f"[策略匹配] {result.strategy_match.explanation}",
            f"",
            f"[反量化] 风险={anti['risk']}/100 等级={anti['level']} 惩罚={anti['penalty']}分",
            f"[触发项] {' | '.join(anti['triggers'][:5]) if anti.get('triggers') else '无'}",
            f"",
            f"[K线] {kline_text}",
        ]

        if d.get('matched_strategies'):
            s_str = " ".join(f"{s['strategy']}({s.get('match','?')}%/{s['status']})" for s in d['matched_strategies'])
            lines.append(f"[策略] {s_str}")

        return "\n".join(lines)
