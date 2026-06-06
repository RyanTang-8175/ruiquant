"""研究 Harness。

LLM 只负责提出研究意图；Harness 负责安全执行、查重缓存、结果裁剪和入库。
这让 iFinD 不再只是按钮，而是 AlphaEye 的研究生产线。
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from src.research.knowledge import ResearchKnowledge


class ResearchHarness:
    def __init__(self, provider=None, cache_dir: str | Path | None = None,
                 knowledge_path: str | Path | None = None):
        if provider is None:
            from src.data.providers.registry import get_provider

            provider = get_provider()
        self.provider = provider
        raw_cache = cache_dir or os.getenv("ALPHAEYE_RESEARCH_CACHE_DIR")
        self.cache_dir = Path(raw_cache) if raw_cache else Path(__file__).resolve().parents[2] / "data" / "research_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge = ResearchKnowledge(knowledge_path)

    def company_research(self, code: str, profile: str = "quick", force: bool = False) -> dict:
        code = str(code or "").strip()[:6]
        profile = profile or "quick"
        fp = self._fingerprint("company", code, profile)
        cached = None if force else self._read_cache(fp, ttl=6 * 3600)
        if cached:
            cached["cached"] = True
            # 关键：缓存命中时强制刷新行情字段为实时，慢变数据(公告/基本面/K线)仍走缓存省额度
            # 否则 AI 会拿到几小时前的旧价格，回答数据全错
            self._refresh_live_quote(cached, code)
            evidence = cached.get("evidence") or {}
            cached["summary_cards"] = self._summary_cards(evidence)
            cached["quality"] = self._quality(evidence)
            cached["updated_at"] = datetime.now().isoformat()
            self._write_cache(fp, cached)
            return cached

        quote = self._safe(lambda: self.provider.get_realtime_quote(code), {})
        bars = self._safe(lambda: self.provider.get_daily_bars(
            code,
            (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
        ), [])
        announcements = self._safe(lambda: self.provider.report_query(code, days=90, limit=12), [])
        basics = self._company_basics(code)
        picks = self._safe(lambda: self.provider.smart_stock_picking(f"{code} 资金流向 股性评分", limit=8), [])

        evidence = {
            "行情": self._compact_quote(quote),
            "K线": bars[-20:] if isinstance(bars, list) else [],
            "公告": announcements[:12] if isinstance(announcements, list) else [],
            "基础数据": basics,
            "智能选股": picks[:8] if isinstance(picks, list) else [],
        }
        result = {
            "kind": "company_research",
            "code": code,
            "profile": profile,
            "title": f"{quote.get('name') or code}({code}) iFinD研究底稿",
            "fingerprint": fp,
            "cached": False,
            "source": getattr(self.provider, "source_name", "unknown"),
            "summary_cards": self._summary_cards(evidence),
            "evidence": evidence,
            "scenario_report": self._scenario_report(evidence),
            "quality": self._quality(evidence),
            "usage": self._usage(),
            "created_at": datetime.now().isoformat(),
        }
        self._write_cache(fp, result)
        self.knowledge.record_run(result)
        return result

    def _refresh_live_quote(self, cached: dict, code: str) -> None:
        """缓存命中时，把研究底稿里的行情和K线强制刷新为实时。

        之前只刷行情字段，但缓存里的K线数据仍是几天前的旧价格，
        AI看到30根旧K线 vs 一行实时行情，会信K线而忽略实时价。
        现在：行情刷新 + K线最后一根更新 + 价格偏差超2%时标记数据冲突。
        """
        try:
            live = self._safe(lambda: self.provider.get_realtime_quote(code), {})
            if not live or not live.get("price"):
                return
            live_price = live.get("price", 0)
            compact = self._compact_quote(live)

            evidence = cached.get("evidence")
            if isinstance(evidence, dict):
                old_quote = evidence.get("行情") or {}
                old_price = float(old_quote.get("price") or 0)

                evidence["行情"] = compact

                # 刷新K线最后一根：旧K线严重过期时标记不可靠
                klines = evidence.get("K线") or []
                if klines and old_price > 0 and abs(live_price - old_price) / old_price > 0.02:
                    evidence["_kline_stale"] = True
                    evidence["_kline_warning"] = (
                        f"缓存K线基于旧价{old_price:.2f}，与实时{live_price:.2f}偏差"
                        f"超2%。K线不可靠，请以实时行情为准。"
                    )
                    if klines:
                        klines[-1]["close"] = live_price
                        klines[-1]["_adjusted_from_cache"] = True

                # PE等基于旧价，标记可能不准确
                basics = evidence.get("基础数据") or {}
                if isinstance(basics, dict) and old_price > 0 and abs(live_price - old_price) / old_price > 0.02:
                    basics["_stale_from_cache"] = True
                    basics["_warning"] = f"基于旧价{old_price:.2f}计算，现价{live_price:.2f}已有显著变化"

            for card in cached.get("summary_cards") or []:
                if isinstance(card, dict) and card.get("title") == "行情":
                    card["value"] = f"{live_price:.2f}"
                    card["note"] = f"{live.get('change_pct', 0) or 0:+.2f}%"

            if isinstance(evidence, dict):
                cached["scenario_report"] = self._scenario_report(evidence)

            cached["live_refreshed"] = True
            cached["live_quote"] = compact
            cached["live_price"] = live_price
        except Exception:
            pass

    def market_radar(self, queries: list[str] | None = None) -> dict:
        queries = queries or ["主力资金流入 涨幅居前", "政策利好 行业", "换手率活跃 成交额居前"]
        fp = self._fingerprint("market", *queries)
        cached = self._read_cache(fp, ttl=10 * 60)
        if cached:
            cached["cached"] = True
            return cached
        themes = []
        for query in queries[:6]:
            rows = self._safe(lambda q=query: self.provider.smart_stock_picking(q, limit=10), [])
            themes.append({"query": query, "rows": rows[:10] if isinstance(rows, list) else []})
        result = {
            "kind": "market_radar",
            "queries": queries[:6],
            "themes": themes,
            "cached": False,
            "fingerprint": fp,
            "quality": "ok" if any(t["rows"] for t in themes) else "empty",
            "usage": self._usage(),
            "created_at": datetime.now().isoformat(),
        }
        self._write_cache(fp, result)
        self.knowledge.record_run({
            **result,
            "title": "全市场 iFinD 智能雷达",
            "evidence": {t["query"]: t["rows"] for t in themes},
        })
        return result

    def knowledge_context(self, limit: int = 8) -> dict:
        return self.knowledge.recent_context(limit=limit)

    def _company_basics(self, code: str) -> dict:
        indicators = {
            "总股本": "ths_total_shares_stock",
            "流通市值": "ths_float_mv_stock",
            "市盈率TTM": "ths_pe_ttm_stock",
            "每股收益TTM": "ths_eps_ttm_stock",
            "净利润": "ths_np_atoopc_pit_stock",
        }
        out = {}
        today = datetime.now().strftime("%Y%m%d")
        for label, indicator in indicators.items():
            try:
                data = self.provider.basic_data(code, indicator, [today])
                out[label] = self._extract_first_table_value(data, indicator)
            except Exception as exc:
                out[label] = f"unavailable: {str(exc)[:40]}"
        return out

    @staticmethod
    def _extract_first_table_value(data: dict, indicator: str):
        for table in (data or {}).get("tables", []) or []:
            raw = table.get("table", table)
            if isinstance(raw, dict):
                value = raw.get(indicator)
                if isinstance(value, list):
                    return value[0] if value else None
                return value
        return None

    @staticmethod
    def _compact_quote(quote: dict) -> dict:
        if not isinstance(quote, dict):
            return {}
        keys = [
            "code",
            "name",
            "price",
            "change_pct",
            "turnover",
            "amount",
            "source",
            "quality_level",
            "is_delayed",
            "_fallback",
        ]
        compact = {k: quote.get(k) for k in keys if k in quote}
        compact["retrieved_at"] = (
            quote.get("retrieved_at")
            or quote.get("quote_time")
            or datetime.now().isoformat()
        )
        return compact

    @staticmethod
    def _summary_cards(evidence: dict) -> list:
        quote = evidence.get("行情") or {}
        announcements = evidence.get("公告") or []
        basics = evidence.get("基础数据") or {}
        smart = evidence.get("智能选股") or []
        usable_basics = [
            value
            for key, value in basics.items()
            if not str(key).startswith("_")
            and value not in (None, "", 0, "--")
            and not str(value).startswith("unavailable")
        ]
        return [
            {"title": "行情", "value": f"{quote.get('price', 0) or 0:.2f}", "note": f"{quote.get('change_pct', 0) or 0:+.2f}%"},
            {"title": "公告", "value": len(announcements), "note": "近90天"},
            {"title": "基础数据", "value": len(usable_basics), "note": "可用指标"},
            {"title": "智能选股", "value": len(smart), "note": "问财命中"},
        ]

    @staticmethod
    def _scenario_report(evidence: dict) -> list[dict]:
        quote = evidence.get("行情") or {}
        announcements = evidence.get("公告") or []
        smart = evidence.get("智能选股") or []
        bars = evidence.get("K线") or []
        chg = float(quote.get("change_pct") or 0.0)
        turnover = float(quote.get("turnover") or 0.0)
        last_bar = bars[-1] if bars else {}
        last_change = float(last_bar.get("change_pct") or chg)
        catalyst_count = len(announcements) + len(smart)

        bullish = min(80, 35 + catalyst_count * 8 + max(chg, 0) * 3)
        pullback = min(85, 40 + max(chg, 0) * 5 + max(turnover - 4, 0) * 4)
        invalid = min(80, 35 + (10 if catalyst_count == 0 else 0) + max(-last_change, 0) * 5)

        return [
            {
                "name": "利好继续发酵",
                "possibility": f"{bullish:.0f}%",
                "evidence": f"公告 {len(announcements)} 条，智能选股命中 {len(smart)} 条，当前涨跌幅 {chg:+.2f}%。",
                "trigger": "公告/政策/资金信号继续被行情确认，板块内出现同步走强。",
                "failure": "消息有热度但成交不跟，或同板块核心股不联动。",
                "watch_window": "T+1 到 T+3",
            },
            {
                "name": "冲高回落",
                "possibility": f"{pullback:.0f}%",
                "evidence": f"涨跌幅 {chg:+.2f}%，换手 {turnover:.2f}%，短线拥挤度可能抬升。",
                "trigger": "高开急冲后跌回分时均价线，放量但价格推不动。",
                "failure": "回踩不破且成交额温和放大，说明承接没有失效。",
                "watch_window": "盘中 30-90 分钟",
            },
            {
                "name": "板块不联动",
                "possibility": f"{invalid:.0f}%",
                "evidence": f"最近K线涨跌 {last_change:+.2f}%，外部证据块数量 {catalyst_count}。",
                "trigger": "个股单独拉升，行业/概念没有扩散，新闻或公告无法复核。",
                "failure": "同方向出现 2-3 只核心股同步走强，并且尾盘不回落。",
                "watch_window": "T+1",
            },
        ]

    @staticmethod
    def _quality(evidence: dict) -> str:
        score = 0
        if evidence.get("行情"):
            score += 1
        if evidence.get("K线"):
            score += 1
        if evidence.get("公告"):
            score += 1
        if evidence.get("智能选股"):
            score += 1
        return "high" if score >= 3 else "medium" if score >= 2 else "low"

    def _usage(self) -> dict:
        if hasattr(self.provider, "usage_stats"):
            try:
                return self.provider.usage_stats()
            except Exception:
                return {}
        return {}

    @staticmethod
    def _safe(fn, default):
        try:
            value = fn()
            return default if value is None else value
        except Exception:
            return default

    @staticmethod
    def _fingerprint(*parts) -> str:
        raw = json.dumps(parts, ensure_ascii=False, sort_keys=True)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _cache_path(self, fingerprint: str) -> Path:
        return self.cache_dir / f"{fingerprint}.json"

    def _read_cache(self, fingerprint: str, ttl: int):
        path = self._cache_path(fingerprint)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            created = datetime.fromisoformat(payload.get("created_at", "2000-01-01"))
            if (datetime.now() - created).total_seconds() > ttl:
                return None
            return payload
        except Exception:
            return None

    def _write_cache(self, fingerprint: str, payload: dict) -> None:
        self._cache_path(fingerprint).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
