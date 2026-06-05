"""iFinD 证据评分。

把研究底稿里的行情、K线、公告、基本面与智能选股信号，
重新组合成 AlphaEye 的证据化评分。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log10


@dataclass
class _DimensionView:
    score: float
    detail: str


class IFindEvidenceScorer:
    """将 iFinD 研究底稿转成机会/风险/置信度评分。"""

    def score(self, research: dict) -> dict:
        research = research or {}
        evidence = research.get("evidence") or {}
        quote = evidence.get("行情") or {}
        bars = evidence.get("K线") or []
        announcements = evidence.get("公告") or []
        basics = evidence.get("基础数据") or {}
        smart_picks = evidence.get("智能选股") or []

        fund_heat = self._score_fund_heat(quote)
        support_quality = self._score_support_quality(bars, quote)
        catalyst = self._score_catalyst(announcements, smart_picks)
        fundamental_safety = self._score_fundamental_safety(basics)
        crowding_risk = self._score_crowding_risk(quote, bars, smart_picks)
        data_confidence = self._score_data_confidence(research, evidence)

        opportunity_score = self._bounded(
            fund_heat.score * 0.28
            + support_quality.score * 0.24
            + catalyst.score * 0.23
            + fundamental_safety.score * 0.15
            + data_confidence.score * 0.10
            - crowding_risk.score * 0.18
        )
        risk_score = self._bounded(
            crowding_risk.score * 0.55
            + (100 - data_confidence.score) * 0.18
            + (100 - fundamental_safety.score) * 0.15
            + max(0, 60 - support_quality.score) * 0.05
        )

        confidence = self._confidence(data_confidence.score, opportunity_score, risk_score)
        action = self._action(opportunity_score, risk_score, confidence)

        return {
            "code": research.get("code", ""),
            "source": research.get("source", ""),
            "profile": research.get("profile", "quick"),
            "quality": research.get("quality", "unknown"),
            "opportunity_score": round(opportunity_score, 1),
            "risk_score": round(risk_score, 1),
            "confidence": confidence,
            "action": action,
            "dimensions": {
                "fund_heat": self._pack(fund_heat),
                "support_quality": self._pack(support_quality),
                "catalyst": self._pack(catalyst),
                "fundamental_safety": self._pack(fundamental_safety),
                "crowding_risk": self._pack(crowding_risk),
                "data_confidence": self._pack(data_confidence),
            },
            "evidence_summary": self._evidence_summary(research, quote, announcements, basics, smart_picks),
        }

    @staticmethod
    def _pack(view: _DimensionView) -> dict:
        return {"score": round(view.score, 1), "detail": view.detail}

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(100.0, float(value)))

    def _score_fund_heat(self, quote: dict) -> _DimensionView:
        chg = float(quote.get("change_pct") or 0.0)
        turnover = float(quote.get("turnover") or 0.0)
        amount = float(quote.get("amount") or 0.0)
        score = 52 + chg * 4.5 + min(turnover, 12) * 2.2 + min(log10(amount + 1), 12) * 1.2
        return _DimensionView(
            score=self._bounded(score),
            detail=f"涨跌幅 {chg:+.2f}%，换手 {turnover:.2f}%，成交额 {amount / 1e8:.1f} 亿。",
        )

    def _score_support_quality(self, bars: list, quote: dict) -> _DimensionView:
        closes = [float(item.get("close") or 0.0) for item in bars if isinstance(item, dict)]
        if len(closes) < 2:
            base = 50 + float(quote.get("change_pct") or 0.0) * 2
            return _DimensionView(score=self._bounded(base), detail="K线样本不足，按实时涨跌粗略评估。")

        first = closes[0]
        last = closes[-1]
        slope = 0.0 if first == 0 else (last - first) / abs(first) * 100
        up_days = 0
        for idx in range(1, len(bars)):
            prev = float(bars[idx - 1].get("close") or 0.0)
            cur = float(bars[idx].get("close") or 0.0)
            if cur >= prev:
                up_days += 1
        score = 50 + slope * 0.8 + (up_days / max(len(closes) - 1, 1)) * 18
        return _DimensionView(
            score=self._bounded(score),
            detail=f"近 {len(closes)} 根K线收盘从 {first:.2f} 到 {last:.2f}，上涨日 {up_days} 天。",
        )

    def _score_catalyst(self, announcements: list, smart_picks: list) -> _DimensionView:
        titles = [str(item.get("title") or item.get("name") or "") for item in announcements if isinstance(item, dict)]
        joined = " ".join(titles)
        keyword_hits = sum(
            1
            for keyword in ("回购", "增持", "业绩预增", "中标", "订单", "重组", "分红")
            if keyword in joined
        )
        pick_bonus = min(len(smart_picks), 5) * 8
        score = 40 + min(len(announcements), 5) * 10 + keyword_hits * 6 + pick_bonus
        return _DimensionView(
            score=self._bounded(score),
            detail=f"公告 {len(announcements)} 条，关键词命中 {keyword_hits} 个，智能选股命中 {len(smart_picks)} 条。",
        )

    def _score_fundamental_safety(self, basics: dict) -> _DimensionView:
        pe = self._safe_float(basics.get("市盈率TTM"))
        net_profit = self._safe_float(basics.get("净利润"))
        market_cap = self._safe_float(basics.get("流通市值"))
        eps = self._safe_float(basics.get("每股收益TTM"))

        score = 55.0
        if pe and pe > 0:
            if pe < 15:
                score += 18
            elif pe < 25:
                score += 12
            elif pe < 40:
                score += 6
            else:
                score -= 5
        if net_profit > 0:
            score += 12
        if market_cap > 0:
            score += 5 if market_cap < 8000 else 2
        if eps > 0:
            score += 8

        detail = []
        detail.append(f"PE TTM {pe:.2f}" if pe else "PE缺失")
        detail.append(f"净利润 {net_profit:.2f}" if net_profit else "净利润缺失")
        detail.append(f"流通市值 {market_cap:.2f}" if market_cap else "市值缺失")
        return _DimensionView(score=self._bounded(score), detail="，".join(detail) + "。")

    def _score_crowding_risk(self, quote: dict, bars: list, smart_picks: list) -> _DimensionView:
        chg = float(quote.get("change_pct") or 0.0)
        turnover = float(quote.get("turnover") or 0.0)
        amount = float(quote.get("amount") or 0.0)
        last_close = float((bars[-1] or {}).get("close") or quote.get("price") or 0.0) if bars else float(quote.get("price") or 0.0)
        first_close = float((bars[0] or {}).get("close") or last_close) if bars else last_close
        momentum_gap = 0.0 if first_close == 0 else (last_close - first_close) / abs(first_close) * 100

        score = 28 + min(turnover, 12) * 2.8 + max(chg, 0) * 2.0 + min(log10(amount + 1), 12) * 1.0 + max(momentum_gap, 0) * 0.3
        if len(smart_picks) >= 3:
            score += 5
        return _DimensionView(
            score=self._bounded(score),
            detail=f"换手 {turnover:.2f}%，涨跌幅 {chg:+.2f}%，资金热度与题材热度叠加后风险上升。",
        )

    def _score_data_confidence(self, research: dict, evidence: dict) -> _DimensionView:
        quality = str(research.get("quality") or "unknown").lower()
        source = str(research.get("source") or "").lower()
        filled = sum(1 for value in evidence.values() if value not in (None, [], {}, ""))

        score = 45 + filled * 8
        if source == "ifind":
            score += 14
        if quality == "high":
            score += 14
        elif quality == "medium":
            score += 8
        elif quality == "low":
            score -= 6

        return _DimensionView(
            score=self._bounded(score),
            detail=f"来源 {source or 'unknown'}，证据块 {filled}/5，质量标签 {quality}。",
        )

    @staticmethod
    def _confidence(data_confidence: float, opportunity: float, risk: float) -> str:
        if data_confidence >= 82 and opportunity >= 68 and risk <= 58:
            return "高"
        if data_confidence >= 65 and opportunity >= 55:
            return "中"
        return "低"

    @staticmethod
    def _action(opportunity: float, risk: float, confidence: str) -> str:
        if opportunity >= 68 and risk <= 58 and confidence in {"中", "高"}:
            return "可模拟验证"
        if opportunity >= 55 and risk <= 68:
            return "可观察"
        return "只观察"

    @staticmethod
    def _safe_float(value) -> float:
        try:
            if value in (None, "", []):
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _evidence_summary(research: dict, quote: dict, announcements: list, basics: dict, smart_picks: list) -> list[str]:
        code = research.get("code", "")
        name = (quote or {}).get("name") or code
        price = float((quote or {}).get("price") or 0.0)
        chg = float((quote or {}).get("change_pct") or 0.0)
        summary = [
            f"{name}({code}) 当前价格 {price:.2f}，涨跌幅 {chg:+.2f}%。",
            f"公告命中 {len(announcements)} 条，iFinD 智能选股命中 {len(smart_picks)} 条。",
            f"基础数据可用项 {sum(1 for v in basics.values() if v not in (None, '', 0))} 个。",
        ]
        if announcements:
            first = announcements[0]
            title = first.get("title") or first.get("name") or ""
            if title:
                summary.append(f"首条公告：{title}。")
        return summary
