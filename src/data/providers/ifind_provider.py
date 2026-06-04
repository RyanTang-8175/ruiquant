"""
iFinD Provider 预留层。

当前用于在 iFinD 免费试用 API 到位前稳定架构。它不会伪造专业数据；
未配置时明确返回不可用。拿到 API 后，只需要在本文件实现同花顺接口映射，
上层 AI、雷达、实验室和页面无需重写。
"""

from typing import Optional

from src.config import get_setting
from src.data.providers.base import MarketDataProvider


class IFindProvider(MarketDataProvider):
    """同花顺 iFinD 专业数据源适配器占位实现。"""

    source_name = "ifind"

    def __init__(self):
        self.username = get_setting("ifind_username", "IFIND_USERNAME", "")
        self.password = get_setting("ifind_password", "IFIND_PASSWORD", "")
        self.token = get_setting("ifind_token", "IFIND_TOKEN", "")

    @property
    def configured(self) -> bool:
        return bool(self.token or (self.username and self.password))

    def _not_ready(self):
        return None

    def get_realtime_quote(self, code: str) -> Optional[dict]:
        return self._not_ready()

    def get_realtime_quotes(self, codes: list) -> list:
        return []

    def get_intraday_bars(self, code: str, trade_date: str = None) -> list:
        return []

    def get_daily_bars(self, code: str, start: str, end: str) -> list:
        return []

    def get_float_market_cap(self, code: str) -> Optional[float]:
        return None

    def get_sector_info(self, code: str) -> Optional[dict]:
        return None

    def get_market_snapshot(self) -> dict:
        return {"indices": [], "source": self.source_name, "status": "not_configured"}

    def get_top_stocks(self, sort_field: str = "change_pct",
                       asc: bool = False, limit: int = 50) -> list:
        return []

    def get_news(self, code: str = None, limit: int = 20) -> list:
        return []

    def health_check(self) -> dict:
        if not self.configured:
            return {
                "source": self.source_name,
                "status": "not_configured",
                "ready": False,
                "message": "IFIND_USERNAME/IFIND_PASSWORD 或 IFIND_TOKEN 未配置，等待 iFinD 试用 API。",
            }
        return {
            "source": self.source_name,
            "status": "configured_pending_implementation",
            "ready": False,
            "message": "iFinD 凭据已配置，但接口映射尚未实现。",
        }
