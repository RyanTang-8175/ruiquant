"""
实时行情数据模块
使用东方财富 HTTP API 获取实时数据，无需第三方库
"""

import logging
import requests
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://quote.eastmoney.com/',
}


def _get_market(code: str) -> int:
    """判断股票市场: 0=深圳, 1=上海"""
    if code.startswith('6'):
        return 1
    return 0


def get_realtime_quote(code: str) -> Optional[Dict]:
    """获取单只股票实时行情"""
    try:
        market = _get_market(code)
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": f"{market}.{code}",
            "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f116,f117,f162,f168,f170,f171",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        data = resp.json().get("data")
        if not data:
            return None

        # 价格除以100（东方财富返回的价格是乘以100的整数）
        def p(v): return (v or 0) / 100 if isinstance(v, (int, float)) else 0

        return {
            "code": str(data.get("f57", code)),
            "name": data.get("f58", ""),
            "price": p(data.get("f43")),
            "high": p(data.get("f44")),
            "low": p(data.get("f45")),
            "open": p(data.get("f46")),
            "volume": data.get("f47", 0),          # 手
            "amount": data.get("f48", 0),           # 元
            "prev_close": p(data.get("f60")),
            "change_pct": p(data.get("f170")),
            "turnover": p(data.get("f168")),
            "pe_ratio": p(data.get("f162")),
        }
    except Exception as e:
        logger.warning(f"获取实时行情失败 {code}: {e}")
        return None


def get_realtime_quotes_batch(codes: List[str]) -> List[Dict]:
    """批量获取实时行情（使用全市场接口）"""
    try:
        url = "http://push2.eastmoney.com/api/qt/ulist.np/get"
        # 构造 secids: 1.600519,0.000001,...
        secids = ",".join(f"{_get_market(c)}.{c}" for c in codes)
        params = {
            "secids": secids,
            "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f15,f16,f17,f18",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json().get("data", {})
        items = data.get("diff", [])

        results = []
        for item in items:
            results.append({
                "code": str(item.get("f12", "")),
                "name": item.get("f14", ""),
                "price": (item.get("f2", 0) or 0) / 100,
                "change_pct": (item.get("f3", 0) or 0) / 100,
                "change_amt": (item.get("f4", 0) or 0) / 100,
                "volume": item.get("f5", 0),
                "amount": item.get("f6", 0),
                "high": (item.get("f15", 0) or 0) / 100,
                "low": (item.get("f16", 0) or 0) / 100,
                "open": (item.get("f17", 0) or 0) / 100,
                "prev_close": (item.get("f18", 0) or 0) / 100,
                "turnover": (item.get("f8", 0) or 0) / 100,
                "pe_ratio": (item.get("f9", 0) or 0) / 100,
            })
        return results
    except Exception as e:
        logger.warning(f"批量获取行情失败: {e}")
        return []


def get_market_overview() -> Dict:
    """获取全市场概览（涨跌家数、涨停跌停等）"""
    try:
        url = "http://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "secids": "1.000001,0.399001,0.399006",  # 上证、深证、创业板
            "fields": "f2,f3,f4,f12,f14",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        data = resp.json().get("data", {})
        items = data.get("diff", [])

        indices = []
        for item in items:
            indices.append({
                "code": str(item.get("f12", "")),
                "name": item.get("f14", ""),
                "price": (item.get("f2", 0) or 0) / 100,
                "change_pct": (item.get("f3", 0) or 0) / 100,
            })

        return {"indices": indices}
    except Exception as e:
        logger.warning(f"获取市场概览失败: {e}")
        return {"indices": []}


def get_top_stocks(sort_field: str = "f3", asc: bool = False, limit: int = 15) -> List[Dict]:
    """获取涨幅榜/跌幅榜/成交额榜
    sort_field: f3=涨跌幅, f6=成交额, f8=换手率
    asc: True=升序(跌幅榜), False=降序(涨幅榜)
    """
    try:
        url = "http://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "pn": "1",
            "pz": str(limit),
            "po": "0" if asc else "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": sort_field,
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # A股
            "fields": "f2,f3,f4,f5,f6,f7,f8,f12,f14,f15,f16,f17,f18",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json().get("data", {})
        items = data.get("diff", [])

        results = []
        for item in items:
            results.append({
                "code": str(item.get("f12", "")),
                "name": item.get("f14", ""),
                "price": (item.get("f2", 0) or 0) / 100,
                "change_pct": (item.get("f3", 0) or 0) / 100,
                "volume": item.get("f5", 0),
                "amount": item.get("f6", 0),
                "turnover": (item.get("f8", 0) or 0) / 100,
                "high": (item.get("f15", 0) or 0) / 100,
                "low": (item.get("f16", 0) or 0) / 100,
                "open": (item.get("f17", 0) or 0) / 100,
                "prev_close": (item.get("f18", 0) or 0) / 100,
            })
        return results
    except Exception as e:
        logger.warning(f"获取排行榜失败: {e}")
        return []


def get_kline(code: str, period: str = "101", count: int = 100) -> List[Dict]:
    """获取K线数据
    period: "1"=1分, "5"=5分, "15"=15分, "30"=30分, "60"=60分, "101"=日线, "102"=周线, "103"=月线
    """
    try:
        market = _get_market(code)
        url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": f"{market}.{code}",
            "fields1": "f1,f2,f3,f4,f5,f6,f7,f8",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": period,
            "fqt": "1",
            "beg": "0",
            "end": "20500101",
            "lmt": str(count),
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        klines_raw = resp.json().get("data", {}).get("klines", [])

        results = []
        for k in klines_raw:
            parts = k.split(",")
            if len(parts) >= 11:
                results.append({
                    "date": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "volume": int(float(parts[5])),
                    "amount": float(parts[6]),
                    "amplitude": float(parts[7]),
                    "change_pct": float(parts[8]),
                    "change_amt": float(parts[9]),
                    "turnover": float(parts[10]),
                })
        return results
    except Exception as e:
        logger.warning(f"获取K线失败 {code}: {e}")
        return []
