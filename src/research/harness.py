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

    def company_research(self, code: str, profile: str = "quick") -> dict:
        code = str(code or "").strip()[:6]
        profile = profile or "quick"
        fp = self._fingerprint("company", code, profile)
        cached = self._read_cache(fp, ttl=6 * 3600)
        if cached:
            cached["cached"] = True
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
            "quality": self._quality(evidence),
            "usage": self._usage(),
            "created_at": datetime.now().isoformat(),
        }
        self._write_cache(fp, result)
        self.knowledge.record_run(result)
        return result

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
        keys = ["code", "name", "price", "change_pct", "turnover", "amount", "source", "quality_level"]
        return {k: quote.get(k) for k in keys if k in quote}

    @staticmethod
    def _summary_cards(evidence: dict) -> list:
        quote = evidence.get("行情") or {}
        announcements = evidence.get("公告") or []
        basics = evidence.get("基础数据") or {}
        smart = evidence.get("智能选股") or []
        return [
            {"title": "行情", "value": f"{quote.get('price', 0) or 0:.2f}", "note": f"{quote.get('change_pct', 0) or 0:+.2f}%"},
            {"title": "公告", "value": len(announcements), "note": "近90天"},
            {"title": "基础数据", "value": sum(1 for v in basics.values() if v not in (None, "", 0)), "note": "可用指标"},
            {"title": "智能选股", "value": len(smart), "note": "问财命中"},
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
