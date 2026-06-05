"""
CachedDataProvider —— 带本地缓存的代理层
先查缓存，未命中时调用底层 Provider 并写入缓存。
"""

import json, logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.data.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


class CachedDataProvider(MarketDataProvider):
    """缓存代理 —— 包装任意 Provider，增加 JSON 文件缓存"""

    source_name = "cached"

    def __init__(self, provider: MarketDataProvider, cache_dir: str = None):
        self._provider = provider
        self.source_name = f"cached_{provider.source_name}"

        if cache_dir:
            self._cache_dir = Path(cache_dir)
        else:
            self._cache_dir = Path(__file__).parent.parent.parent.parent / "data" / "cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        self._ttl = {
            "quote": 60,
            "intraday": 120,
            "daily": 3600,
            "cap": 86400,
        }

    @property
    def provider(self):
        return self._provider

    def _cache_key(self, prefix: str, *args) -> str:
        return f"{prefix}_{'_'.join(str(a) for a in args)}.json"

    def _read_cache(self, key: str, ttl: int) -> Optional[dict]:
        f = self._cache_dir / key
        if not f.exists():
            return None
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            ts = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
            if (datetime.now() - ts).total_seconds() > ttl:
                return None
            return data.get("_payload")
        except Exception:
            return None

    def _write_cache(self, key: str, payload):
        try:
            data = {"_cached_at": datetime.now().isoformat(),
                    "_payload": payload}
            (self._cache_dir / key).write_text(
                json.dumps(data, ensure_ascii=False, default=str),
                encoding="utf-8")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    def get_realtime_quote(self, code: str) -> Optional[dict]:
        key = self._cache_key("q", code)
        cached = self._read_cache(key, self._ttl["quote"])
        if cached:
            return cached
        result = self._provider.get_realtime_quote(code)
        if result:
            self._write_cache(key, result)
        return result

    def get_realtime_quotes(self, codes: list) -> list:
        results = []
        for code in codes:
            q = self.get_realtime_quote(code)
            if q:
                results.append(q)
        return results

    def get_intraday_bars(self, code: str, trade_date: str = None) -> list:
        td = trade_date or datetime.now().strftime("%Y-%m-%d")
        key = self._cache_key("ib", code, td)
        cached = self._read_cache(key, self._ttl["intraday"])
        if cached:
            return cached
        result = self._provider.get_intraday_bars(code, trade_date)
        if result:
            self._write_cache(key, result)
        return result

    def get_daily_bars(self, code: str, start: str, end: str) -> list:
        key = self._cache_key("db", code, start, end)
        # 含今日数据：5分钟缓存；纯历史区间：1小时缓存
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        ttl = 5 * 60 if end >= today else self._ttl["daily"]
        cached = self._read_cache(key, ttl)
        if cached:
            return cached
        result = self._provider.get_daily_bars(code, start, end)
        if result:
            self._write_cache(key, result)
        return result

    def get_float_market_cap(self, code: str) -> Optional[float]:
        key = self._cache_key("cap", code)
        cached = self._read_cache(key, self._ttl["cap"])
        if cached is not None:
            return cached
        result = self._provider.get_float_market_cap(code)
        if result is not None:
            self._write_cache(key, result)
        return result

    def get_sector_info(self, code: str) -> Optional[dict]:
        return self._provider.get_sector_info(code)

    def get_market_snapshot(self) -> dict:
        key = self._cache_key("ms")
        cached = self._read_cache(key, 30)
        if cached:
            return cached
        result = self._provider.get_market_snapshot()
        if result:
            self._write_cache(key, result)
        return result

    def get_top_stocks(self, sort_field: str = "change_pct",
                       asc: bool = False, limit: int = 50) -> list:
        key = self._cache_key("top", sort_field, str(asc), str(limit))
        cached = self._read_cache(key, 60)
        if cached:
            return cached
        result = self._provider.get_top_stocks(sort_field, asc, limit)
        if result:
            self._write_cache(key, result)
        return result

    def get_news(self, code: str = None, limit: int = 20) -> list:
        key = self._cache_key("news", code or "_", str(limit))
        cached = self._read_cache(key, 120)
        if cached:
            return cached
        result = self._provider.get_news(code, limit)
        if result:
            self._write_cache(key, result)
        return result

    def health_check(self) -> dict:
        return {
            "source": self.source_name,
            "backend": self._provider.health_check(),
        }
