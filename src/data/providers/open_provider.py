"""
OpenDataProvider

现有公开数据源的统一包装层。它把当前项目里已经可用的新浪/腾讯/东财
函数包装成 MarketDataProvider 接口，确保页面、AI 和策略层不再直接依赖
具体公开接口。后续接入 iFinD 时，只需要切换 Provider。
"""

from typing import Optional

from src.data.providers.base import MarketDataProvider


class OpenDataProvider(MarketDataProvider):
    """公开免费数据源包装：腾讯/新浪/东财/新闻源。"""

    source_name = "open"

    def get_realtime_quote(self, code: str) -> Optional[dict]:
        from src.data.realtime import _open_realtime_quote

        quote = _open_realtime_quote(code)
        if quote:
            quote.setdefault("source", "open")
            quote.setdefault("quality_level", "open_unverified")
        return quote

    def get_realtime_quotes(self, codes: list) -> list:
        return [q for q in (self.get_realtime_quote(code) for code in codes) if q]

    def get_intraday_bars(self, code: str, trade_date: str = None) -> list:
        # 当前公开源暂未稳定提供完整分时均价线，保留接口给策略层统一调用。
        return []

    def get_daily_bars(self, code: str, start: str, end: str) -> list:
        from src.data.realtime import _open_kline

        bars = _open_kline(code, period="101", count=240)
        for bar in bars:
            bar.setdefault("source", "open")
        return bars

    def get_float_market_cap(self, code: str) -> Optional[float]:
        return None

    def get_sector_info(self, code: str) -> Optional[dict]:
        return None

    def get_market_snapshot(self) -> dict:
        from src.data.realtime import _open_market_overview

        snapshot = _open_market_overview()
        snapshot.setdefault("source", "open")
        return snapshot

    def get_top_stocks(self, sort_field: str = "change_pct",
                       asc: bool = False, limit: int = 50) -> list:
        from src.data.realtime import _open_top_stocks

        rows = _open_top_stocks(sort_field=sort_field, asc=asc, limit=limit)
        for row in rows:
            row.setdefault("source", "open")
        return rows

    def get_news(self, code: str = None, limit: int = 20) -> list:
        from src.news.fetcher import fetch_all_news, fetch_stock_news

        return fetch_stock_news(code, limit) if code else fetch_all_news(limit)

    def health_check(self) -> dict:
        quote = self.get_realtime_quote("000001")
        return {
            "source": self.source_name,
            "status": "ok" if quote else "degraded",
            "message": "公开数据源可用，但仅作研究和验证，不作为实盘唯一依据。",
        }
