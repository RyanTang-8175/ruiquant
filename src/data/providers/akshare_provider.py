"""
AKShare 数据源适配器
将 AKShare 的数据格式映射为统一的 MarketDataProvider 接口。
"""

import logging
from datetime import datetime
from typing import Optional

from src.data.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


class AKShareProvider(MarketDataProvider):
    """AKShare 行情数据源"""

    source_name = "akshare"

    def __init__(self):
        self._ak = None

    @property
    def ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                logger.warning("akshare 未安装")
                self._ak = False
        return self._ak if self._ak is not False else None

    def get_realtime_quote(self, code: str) -> Optional[dict]:
        if not self.ak:
            return None
        try:
            df = self.ak.stock_zh_a_spot_em()
            row = df[df["代码"] == code]
            if row.empty:
                return None
            r = row.iloc[0]
            return {
                "code": code,
                "name": r.get("名称", ""),
                "price": float(r.get("最新价", 0)),
                "open": float(r.get("今开", 0)),
                "high": float(r.get("最高", 0)),
                "low": float(r.get("最低", 0)),
                "pre_close": float(r.get("昨收", 0)),
                "change_pct": float(r.get("涨跌幅", 0)),
                "volume": float(r.get("成交量", 0)),
                "amount": float(r.get("成交额", 0)),
                "turnover": float(r.get("换手率", 0)),
                "source": self.source_name,
                "quality_level": "ok",
            }
        except Exception as e:
            logger.error(f"AKShare quote {code}: {e}")
            return None

    def get_realtime_quotes(self, codes: list) -> list:
        results = []
        for code in codes:
            q = self.get_realtime_quote(code)
            if q:
                results.append(q)
        return results

    def get_intraday_bars(self, code: str, trade_date: str = None) -> list:
        if not self.ak:
            return []
        try:
            symbol = self._normalize_code(code)
            df = self.ak.stock_zh_a_hist_min_em(
                symbol=symbol, period="1", adjust=""
            )
            if df is None or df.empty:
                return []
            bars = []
            for _, r in df.iterrows():
                bars.append({
                    "time": str(r.get("时间", "")),
                    "price": float(r.get("收盘", 0)),
                    "volume": float(r.get("成交量", 0)),
                    "avg_price": float(r.get("均价", 0)) if "均价" in r else None,
                })
            return bars
        except Exception as e:
            logger.error(f"AKShare intraday {code}: {e}")
            return []

    def get_daily_bars(self, code: str, start: str, end: str) -> list:
        if not self.ak:
            return []
        try:
            symbol = self._normalize_code(code)
            df = self.ak.stock_zh_a_hist(
                symbol=symbol, period="daily",
                start_date=start.replace("-", ""),
                end_date=end.replace("-", ""),
                adjust="qfq",
            )
            if df is None or df.empty:
                return []
            bars = []
            for _, r in df.iterrows():
                bars.append({
                    "trade_date": str(r.get("日期", "")),
                    "open": float(r.get("开盘", 0)),
                    "high": float(r.get("最高", 0)),
                    "low": float(r.get("最低", 0)),
                    "close": float(r.get("收盘", 0)),
                    "volume": float(r.get("成交量", 0)),
                    "amount": float(r.get("成交额", 0)),
                    "change_pct": float(r.get("涨跌幅", 0)),
                    "turnover_rate": float(r.get("换手率", 0)),
                    "source": self.source_name,
                })
            return bars
        except Exception as e:
            logger.error(f"AKShare daily {code}: {e}")
            return []

    def get_float_market_cap(self, code: str) -> Optional[float]:
        if not self.ak:
            return None
        try:
            df = self.ak.stock_zh_a_spot_em()
            row = df[df["代码"] == code]
            if row.empty:
                return None
            cap = row.iloc[0].get("流通市值", None)
            if cap is None:
                return None
            return float(cap) / 1e8
        except Exception as e:
            logger.error(f"AKShare cap {code}: {e}")
            return None

    def get_sector_info(self, code: str) -> Optional[dict]:
        return None

    def _normalize_code(self, code: str) -> str:
        code = code.replace("sh", "").replace("sz", "").replace("bj", "")
        if code.startswith("6"):
            return f"sh{code}"
        elif code.startswith(("0", "3")):
            return f"sz{code}"
        elif code.startswith(("8", "9", "4")):
            return f"bj{code}"
        return code

    def health_check(self) -> dict:
        if not self.ak:
            return {"source": self.source_name, "status": "error",
                    "error": "akshare not installed"}
        try:
            t0 = datetime.now()
            q = self.get_realtime_quote("000001")
            latency = (datetime.now() - t0).total_seconds() * 1000
            return {
                "source": self.source_name, "status": "ok" if q else "empty",
                "latency_ms": round(latency, 1),
            }
        except Exception as e:
            return {"source": self.source_name, "status": "error",
                    "error": str(e)[:200]}
