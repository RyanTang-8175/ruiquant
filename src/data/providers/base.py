"""
MarketDataProvider 抽象基类
所有数据源（公开/akshare/ifind）必须实现此接口。
策略层和 AI 层不直接依赖具体数据源。
"""

from abc import ABC, abstractmethod
from typing import Optional


class MarketDataProvider(ABC):
    """统一行情数据接口"""

    source_name: str = "base"

    @abstractmethod
    def get_realtime_quote(self, code: str) -> Optional[dict]:
        ...

    @abstractmethod
    def get_realtime_quotes(self, codes: list) -> list:
        ...

    @abstractmethod
    def get_intraday_bars(self, code: str, trade_date: str = None) -> list:
        ...

    @abstractmethod
    def get_daily_bars(self, code: str, start: str, end: str) -> list:
        ...

    @abstractmethod
    def get_float_market_cap(self, code: str) -> Optional[float]:
        ...

    @abstractmethod
    def get_sector_info(self, code: str) -> Optional[dict]:
        ...

    def get_market_snapshot(self) -> dict:
        return {"indices": [], "message": "not implemented"}

    def get_top_stocks(self, sort_field: str = "change_pct",
                       asc: bool = False, limit: int = 50) -> list:
        return []

    def get_news(self, code: str = None, limit: int = 20) -> list:
        return []

    def health_check(self) -> dict:
        return {"source": self.source_name, "status": "unknown"}
