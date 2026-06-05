"""
iFinD HTTP 数据源适配器。

官方 HTTP 示例流程：
1. 用 refresh_token 请求 /get_access_token
2. 后续接口使用 access_token 请求头

本适配器只在明确配置 IFIND_REFRESH_TOKEN 时启用，并对高消耗接口做短 TTL 缓存。
失败时抛出可读错误，由上层统一回退公开源，避免页面刷新反复消耗额度。
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

from src.config import get_setting
from src.data.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


class IFindProvider(MarketDataProvider):
    """同花顺 iFinD 专业数据源 HTTP 适配器。"""

    source_name = "ifind"
    _base_urls = [
        "https://quantapi.51ifind.com/api/v1",
        "https://quantapi.10jqka.com.cn/api/v1",
    ]
    base_url = _base_urls[0]

    def __init__(self):
        self.refresh_token = get_setting("ifind_refresh_token", "IFIND_REFRESH_TOKEN", "")
        self.access_token = get_setting("ifind_access_token", "IFIND_ACCESS_TOKEN", "")
        self.timeout = float(get_setting("ifind_timeout", "IFIND_TIMEOUT", "8") or 8)
        self._verify_ssl = os.getenv("IFIND_VERIFY_SSL", "1") != "0"
        self._last_error: str = ""
        self._access_token_expire_at = 0.0
        self._cache: dict[tuple, tuple[float, object]] = {}
        self._calls: dict[str, int] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        raw_usage = os.getenv("ALPHAEYE_IFIND_USAGE_PATH")
        self._usage_path = Path(raw_usage) if raw_usage else Path(__file__).resolve().parents[3] / "data" / "ifind_usage.json"
        self._usage_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def configured(self) -> bool:
        return bool(self.refresh_token or self.access_token)

    def _ttl_get(self, key: tuple, ttl: int):
        cached = self._cache.get(key)
        if not cached:
            self._cache_misses += 1
            return None
        ts, payload = cached
        if time.time() - ts > ttl:
            self._cache_misses += 1
            return None
        self._cache_hits += 1
        return payload

    def _ttl_set(self, key: tuple, payload):
        self._cache[key] = (time.time(), payload)
        return payload

    def _get_access_token(self) -> str:
        if self.access_token and time.time() < self._access_token_expire_at:
            return self.access_token
        if self.access_token and not self.refresh_token:
            return self.access_token
        if not self.refresh_token:
            raise RuntimeError("未配置 IFIND_REFRESH_TOKEN")

        last_err = ""
        for base in self._base_urls:
            try:
                kwargs: dict = {"headers": {"Content-Type": "application/json", "refresh_token": self.refresh_token}, "timeout": self.timeout}
                if not self._verify_ssl:
                    kwargs["verify"] = False
                response = requests.post(f"{base}/get_access_token", **kwargs)
                payload = response.json()
                token = (payload.get("data") or {}).get("access_token") or payload.get("access_token")
                if token:
                    self.base_url = base
                    self.access_token = token
                    self._access_token_expire_at = time.time() + 50 * 60
                    logger.info("iFinD access_token 获取成功 via %s", base)
                    return token
                last_err = f"{base}: {str(payload)[:120]}"
            except Exception as exc:
                last_err = f"{base}: {exc}"
                logger.debug("iFinD token attempt failed: %s", last_err)
        self._last_error = last_err
        raise RuntimeError(f"iFinD access_token 获取失败: {last_err}")

    def _post(self, endpoint: str, payload: dict) -> dict:
        if not self.configured:
            raise RuntimeError("未配置 IFIND_REFRESH_TOKEN")
        token = self._get_access_token()
        last_err = ""
        for base in self._base_urls:
            try:
                kwargs = {"json": payload, "headers": {"Content-Type": "application/json", "access_token": token}, "timeout": self.timeout}
                if not self._verify_ssl:
                    kwargs["verify"] = False
                response = requests.post(f"{base}/{endpoint}", **kwargs)
                data = response.json()
                self._record_call(endpoint)
                code = data.get("errorcode", data.get("code", 0))
                if code not in (0, "0", None):
                    msg = data.get("errmsg") or data.get("message") or str(data)[:160]
                    raise RuntimeError(f"iFinD {endpoint} 返回错误 {code}: {msg}")
                self._last_error = ""
                return data
            except Exception as exc:
                last_err = str(exc)[:200]
                logger.debug("iFinD %s attempt via %s failed: %s", endpoint, base, last_err)
                continue
        self._last_error = last_err
        raise RuntimeError(f"iFinD {endpoint} 失败: {last_err}")

    def _record_call(self, endpoint: str) -> None:
        self._calls[endpoint] = self._calls.get(endpoint, 0) + 1
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        try:
            usage = self._load_usage()
            usage.setdefault("daily", {}).setdefault(today, {})
            usage.setdefault("monthly", {}).setdefault(month, {})
            usage["daily"][today][endpoint] = int(usage["daily"][today].get(endpoint, 0)) + 1
            usage["monthly"][month][endpoint] = int(usage["monthly"][month].get(endpoint, 0)) + 1
            usage["last_call_at"] = datetime.now().isoformat()
            self._save_usage(usage)
        except Exception as exc:
            logger.debug("iFinD usage ledger write failed: %s", exc)

    def _load_usage(self) -> dict:
        if not self._usage_path.exists():
            return {"daily": {}, "monthly": {}, "last_call_at": None}
        try:
            return json.loads(self._usage_path.read_text(encoding="utf-8"))
        except Exception:
            return {"daily": {}, "monthly": {}, "last_call_at": None}

    def _save_usage(self, usage: dict) -> None:
        self._usage_path.write_text(json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _ths_code(code: str) -> str:
        code = str(code or "").strip().upper()
        if "." in code:
            return code
        if code.startswith(("6", "9")):
            return f"{code}.SH"
        if code.startswith(("8", "4")):
            return f"{code}.BJ"
        return f"{code}.SZ"

    @staticmethod
    def _plain_code(ths_code: str) -> str:
        return str(ths_code or "").split(".")[0]

    @staticmethod
    def _first(value, default=None):
        if isinstance(value, list):
            return value[0] if value else default
        return default if value is None else value

    @classmethod
    def _table_value(cls, table: dict, *names, default=None):
        raw = table.get("table", table)
        for name in names:
            if isinstance(raw, dict) and name in raw:
                return cls._first(raw.get(name), default)
            if name in table:
                return cls._first(table.get(name), default)
        return default

    @staticmethod
    def _num(value, default=0.0) -> float:
        try:
            if value in ("", None, "--", "None"):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _normalize_quote_table(self, table: dict, fallback_code: str) -> dict:
        ths_code = table.get("thscode") or table.get("code") or self._ths_code(fallback_code)
        code = self._plain_code(ths_code)
        price = self._num(self._table_value(table, "latest", "new", "close"))
        prev_close = self._num(self._table_value(table, "preClose", "pre_close", "prev_close"))
        change_pct = self._table_value(table, "changeRatio", "change_pct", "涨跌幅")
        if change_pct is None and price and prev_close:
            change_pct = price / prev_close * 100 - 100
        quote = {
            "code": code,
            "name": str(self._table_value(table, "secName", "stockname", "股票简称", default=code) or code),
            "price": price,
            "prev_close": prev_close,
            "open": self._num(self._table_value(table, "open")),
            "high": self._num(self._table_value(table, "high")),
            "low": self._num(self._table_value(table, "low")),
            "volume": int(self._num(self._table_value(table, "volume"), 0)),
            "amount": self._num(self._table_value(table, "amount", "amt"), 0),
            "change_pct": self._num(change_pct, 0),
            "turnover": self._num(self._table_value(table, "turnoverRatio", "turnover"), 0),
            "volume_ratio": self._num(self._table_value(table, "volumeRatio", "volume_ratio"), 1.0),
            "source": "ifind",
            "quality_level": "professional",
            "is_delayed": False,
            "_quality": {
                "source": "ifind",
                "quality_level": "professional",
                "is_delayed": False,
                "issues": [],
            },
        }
        if not quote["name"] or quote["name"] == code:
            try:
                from src.data.stock_list import resolve_stock_name

                quote["name"] = resolve_stock_name(code, code)
            except Exception:
                pass
        return quote

    def get_realtime_quote(self, code: str) -> Optional[dict]:
        rows = self.get_realtime_quotes([code])
        return rows[0] if rows else None

    def get_realtime_quotes(self, codes: list) -> list:
        clean_codes = [str(code or "").strip()[:6] for code in codes if str(code or "").strip()]
        if not clean_codes:
            return []
        key = ("rq", tuple(clean_codes))
        cached = self._ttl_get(key, 20)
        if cached is not None:
            return cached
        payload = {
            "codes": ",".join(self._ths_code(code) for code in clean_codes),
            "indicators": "latest,open,high,low,preClose,volume,amount,changeRatio,turnoverRatio,volumeRatio,secName",
        }
        data = self._post("real_time_quotation", payload)
        tables = data.get("tables") or data.get("data") or []
        if isinstance(tables, dict):
            tables = [tables]
        rows = [self._normalize_quote_table(table, clean_codes[i if i < len(clean_codes) else 0])
                for i, table in enumerate(tables)]
        return self._ttl_set(key, [row for row in rows if row.get("price", 0) > 0])

    def get_intraday_bars(self, code: str, trade_date: str = None) -> list:
        day = trade_date or datetime.now().strftime("%Y-%m-%d")
        key = ("hf", code, day)
        cached = self._ttl_get(key, 90)
        if cached is not None:
            return cached
        payload = {
            "codes": self._ths_code(code),
            "indicators": "open,high,low,close,volume,amount,changeRatio",
            "starttime": f"{day} 09:15:00",
            "endtime": f"{day} 15:30:00",
        }
        data = self._post("high_frequency", payload)
        return self._ttl_set(key, self._normalize_bar_tables(data))

    def get_daily_bars(self, code: str, start: str, end: str) -> list:
        key = ("daily", code, start, end)
        cached = self._ttl_get(key, 6 * 3600)
        if cached is not None:
            return cached
        payload = {
            "codes": self._ths_code(code),
            "indicators": "open,high,low,close,volume,amount,changeRatio",
            "startdate": start,
            "enddate": end,
            "functionpara": {"Fill": "Previous"},
        }
        data = self._post("cmd_history_quotation", payload)
        return self._ttl_set(key, self._normalize_bar_tables(data))

    def _normalize_bar_tables(self, data: dict) -> list:
        bars = []
        for table in data.get("tables", []) or []:
            raw = table.get("table", table)
            if not isinstance(raw, dict):
                continue
            times = raw.get("time") or table.get("time") or raw.get("日期") or []
            closes = raw.get("close") or raw.get("latest") or []
            total = max(len(times or []), len(closes or []))
            for i in range(total):
                pick = lambda name, default=0: self._first(raw.get(name, []), default) if i == 0 else (
                    raw.get(name, [default] * total)[i] if isinstance(raw.get(name), list) and i < len(raw.get(name)) else default
                )
                bars.append({
                    "date": str(pick("time", ""))[:19],
                    "open": self._num(pick("open")),
                    "high": self._num(pick("high")),
                    "low": self._num(pick("low")),
                    "close": self._num(pick("close", pick("latest"))),
                    "volume": int(self._num(pick("volume"))),
                    "amount": self._num(pick("amount")),
                    "change_pct": self._num(pick("changeRatio")),
                    "source": "ifind",
                })
        return [bar for bar in bars if bar["date"] or bar["close"] > 0]

    def get_float_market_cap(self, code: str) -> Optional[float]:
        today = datetime.now().strftime("%Y%m%d")
        data = self.basic_data(code, "ths_float_mv_stock", [today])
        for table in data.get("tables", []) or []:
            value = self._table_value(table, "ths_float_mv_stock")
            num = self._num(value, 0)
            if num:
                return num
        return None

    def get_sector_info(self, code: str) -> Optional[dict]:
        data = self.basic_data(code, "ths_industry_sw_stock", ["2021"])
        for table in data.get("tables", []) or []:
            industry = self._table_value(table, "ths_industry_sw_stock")
            if industry:
                return {"industry": industry, "source": "ifind"}
        return None

    def get_market_snapshot(self) -> dict:
        # iFinD 指数代码：上证 000001.SH / 深证 399001.SZ / 创业板 399006.SZ
        # 不能用 get_realtime_quotes，因为它把 000001 映射成 000001.SZ（平安银行）
        codes_map = {"000001.SH": "上证指数", "399001.SZ": "深证成指", "399006.SZ": "创业板指"}
        ths_codes = list(codes_map.keys())
        key = ("idx", tuple(ths_codes))
        cached = self._ttl_get(key, 30)
        if cached is not None:
            return cached
        payload = {
            "codes": ",".join(ths_codes),
            "indicators": "latest,open,high,low,preClose,volume,amount,changeRatio,secName",
        }
        data = self._post("real_time_quotation", payload)
        tables = data.get("tables") or data.get("data") or []
        if isinstance(tables, dict):
            tables = [tables]
        indices = []
        for table in tables:
            ths_code = table.get("thscode") or table.get("code") or ""
            name = codes_map.get(ths_code, ths_code)
            price = self._num(self._table_value(table, "latest", "close"))
            if price <= 0:
                continue
            indices.append({
                "name": name,
                "price": price,
                "change_pct": self._num(self._table_value(table, "changeRatio", "change_pct")),
            })
        result = {"source": "ifind", "indices": indices}
        return self._ttl_set(key, result)

    def get_top_stocks(self, sort_field: str = "change_pct", asc: bool = False, limit: int = 50) -> list:
        query_map = {
            "changepercent": "A股涨幅榜" if not asc else "A股跌幅榜",
            "change_pct": "A股涨幅榜" if not asc else "A股跌幅榜",
            "amount": "A股成交额排名",
            "turnoverratio": "A股换手率排名",
        }
        rows = self.smart_stock_picking(query_map.get(sort_field, "A股涨幅榜"), limit=limit)
        # 用批量行情补齐 price/volume/amount（wencai 返回的数据可能不完整）
        if rows:
            codes = [r.get("code") for r in rows if r.get("code")]
            if codes:
                try:
                    # 分批获取行情，避免单次请求过多
                    quotes = self.get_realtime_quotes(codes[:50])
                    qmap = {q.get("code"): q for q in quotes}
                    for row in rows:
                        q = qmap.get(row.get("code"))
                        if q:
                            # 直接覆盖而非 if not，确保使用最新实时数据
                            row["price"] = q.get("price", row.get("price", 0))
                            row["volume"] = q.get("volume", row.get("volume", 0))
                            row["amount"] = q.get("amount", row.get("amount", 0))
                            row["turnover"] = q.get("turnover", row.get("turnover", 0))
                            row["open"] = q.get("open", row.get("open", 0))
                            row["high"] = q.get("high", row.get("high", 0))
                            row["low"] = q.get("low", row.get("low", 0))
                            row["change_pct"] = q.get("change_pct", row.get("change_pct", 0))
                except Exception as e:
                    logger.warning(f"榜单数据补齐失败: {e}")
        return rows

    def smart_stock_picking(self, query: str, limit: int = 20) -> list:
        limit = max(1, min(int(limit or 20), 50))
        key = ("wc", query, limit)
        cached = self._ttl_get(key, 10 * 60)
        if cached is not None:
            return cached
        data = self._post("smart_stock_picking", {"searchstring": query, "searchtype": "stock"})
        rows = self._normalize_wencai_tables(data)[:limit]
        return self._ttl_set(key, rows)

    def _normalize_wencai_tables(self, data: dict) -> list:
        rows = []
        for table in data.get("tables", []) or []:
            raw = table.get("table", table)
            if isinstance(raw, list):
                for item in raw:
                    rows.append(self._normalize_wencai_row(item))
            elif isinstance(raw, dict):
                code_values = raw.get("股票代码") or raw.get("thscode") or raw.get("code") or []
                total = len(code_values) if isinstance(code_values, list) else 1
                for i in range(total):
                    item = {}
                    for k, v in raw.items():
                        item[k] = v[i] if isinstance(v, list) and i < len(v) else v
                    rows.append(self._normalize_wencai_row(item))
        return [row for row in rows if row.get("code")]

    def _normalize_wencai_row(self, item: dict) -> dict:
        ths_code = item.get("股票代码") or item.get("thscode") or item.get("code") or ""
        code = self._plain_code(ths_code)
        name = (item.get("股票简称") or item.get("secName") or item.get("name") or code)
        try:
            from src.data.stock_list import resolve_stock_name
            name = resolve_stock_name(code, str(name))
        except Exception:
            pass

        # 智能选股返回的数据字段可能不全，先提取有的字段
        price = self._num(item.get("最新价") or item.get("latest") or item.get("close") or item.get("现价"))
        change_pct = self._num(item.get("涨跌幅") or item.get("changeRatio") or item.get("change_pct"))
        volume = int(self._num(item.get("成交量") or item.get("volume"), 0))
        amount = self._num(item.get("成交额") or item.get("amount") or item.get("amt"), 0)
        turnover = self._num(item.get("换手率") or item.get("turnoverRatio") or item.get("turnover"), 0)

        return {
            "code": code,
            "name": name,
            "price": price,
            "change_pct": change_pct,
            "volume": volume,
            "amount": amount,
            "turnover": turnover,
            "open": self._num(item.get("今开") or item.get("open"), 0),
            "high": self._num(item.get("最高") or item.get("high"), 0),
            "low": self._num(item.get("最低") or item.get("low"), 0),
            "pe_ratio": self._num(item.get("市盈率") or item.get("pe") or item.get("peRatio"), 0),
            "market_cap": self._num(item.get("总市值") or item.get("totalMarketCap") or item.get("marketCap"), 0),
            "source": "ifind_wencai",
        }

    def report_query(self, code: str, days: int = 30, limit: int = 20) -> list:
        end = datetime.now().date()
        start = end - timedelta(days=max(1, int(days or 30)))
        key = ("report", code, days, limit)
        cached = self._ttl_get(key, 6 * 3600)
        if cached is not None:
            return cached
        data = self._post("report_query", {
            "codes": self._ths_code(code),
            "functionpara": {"reportType": "901"},
            "beginrDate": start.isoformat(),
            "endrDate": end.isoformat(),
            "outputpara": "reportDate:Y,thscode:Y,secName:Y,ctime:Y,reportTitle:Y,pdfURL:Y,seq:Y",
        })
        rows = []
        for table in data.get("tables", []) or []:
            raw = table.get("table", table)
            if not isinstance(raw, dict):
                continue
            titles = raw.get("reportTitle") or raw.get("公告标题") or []
            total = len(titles) if isinstance(titles, list) else 1
            for i in range(total):
                pick = lambda name: raw.get(name, [""] * total)[i] if isinstance(raw.get(name), list) and i < len(raw.get(name)) else raw.get(name, "")
                title = pick("reportTitle") or pick("公告标题")
                if title:
                    rows.append({
                        "title": title,
                        "source": "iFinD公告",
                        "type": "announcement",
                        "published_at": pick("reportDate") or pick("ctime"),
                        "url": pick("pdfURL"),
                    })
        return self._ttl_set(key, rows[:limit])

    def basic_data(self, codes: str, indicator: str, params: list | None = None) -> dict:
        return self._post("basic_data_service", {
            "codes": ",".join(self._ths_code(code.strip()) for code in str(codes).split(",") if code.strip()),
            "indipara": [{"indicator": indicator, "indiparams": params or [""]}],
        })

    def date_sequence(self, codes: str, indicator: str, params: list | None,
                      start: str, end: str, fill: str = "Blank") -> dict:
        """日期序列接口：用于财务/估值/日频指标跨日期查询。"""
        return self._post("date_sequence", {
            "codes": ",".join(self._ths_code(code.strip()) for code in str(codes).split(",") if code.strip()),
            "startdate": start,
            "enddate": end,
            "functionpara": {"Fill": fill},
            "indipara": [{"indicator": indicator, "indiparams": params or [""]}],
        })

    def data_pool(self, reportname: str, functionpara: dict, outputpara: str) -> dict:
        """专题报表接口：用于板块成分、专题列表、全 A 池等低频数据。"""
        return self._post("data_pool", {
            "reportname": reportname,
            "functionpara": functionpara or {},
            "outputpara": outputpara,
        })

    def edb_service(self, indicators: str, start: str, end: str) -> dict:
        """经济数据库接口：用于宏观指标和政策背景。"""
        return self._post("edb_service", {
            "indicators": indicators,
            "startdate": start,
            "enddate": end,
        })

    def get_trade_dates(self, marketcode: str = "212001", startdate: str = None,
                        offset: int = -10) -> dict:
        """交易日接口：用于审计回放和低频任务调度。"""
        startdate = startdate or datetime.now().strftime("%Y-%m-%d")
        return self._post("get_trade_dates", {
            "marketcode": marketcode,
            "functionpara": {
                "dateType": "0",
                "period": "D",
                "offset": str(offset),
                "dateFormat": "0",
                "output": "sequencedate",
            },
            "startdate": startdate,
        })

    def usage_stats(self) -> dict:
        usage = self._load_usage()
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        today_by_endpoint = usage.get("daily", {}).get(today, {})
        month_by_endpoint = usage.get("monthly", {}).get(month, {})
        cache_total = self._cache_hits + self._cache_misses
        return {
            "source": self.source_name,
            "calls": dict(self._calls),
            "today_calls": sum(int(v) for v in today_by_endpoint.values()),
            "month_calls": sum(int(v) for v in month_by_endpoint.values()),
            "today_by_endpoint": today_by_endpoint,
            "month_by_endpoint": month_by_endpoint,
            "cache_entries": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": round(self._cache_hits / cache_total, 3) if cache_total else 0,
            "configured": self.configured,
            "last_call_at": usage.get("last_call_at"),
            "usage_path": str(self._usage_path),
        }

    def get_news(self, code: str = None, limit: int = 20) -> list:
        return self.report_query(code, days=45, limit=limit) if code else []

    def health_check(self) -> dict:
        if not self.configured:
            return {
                "source": self.source_name,
                "status": "not_configured",
                "ready": False,
                "message": "未配置 IFIND_REFRESH_TOKEN；当前会自动使用公开源兜底。",
            }
        try:
            token = self._get_access_token()
            return {
                "source": self.source_name,
                "status": "ok" if token else "error",
                "ready": bool(token),
                "message": "iFinD HTTP 接口已配置，行情/历史/智能选股会优先使用 iFinD。",
            }
        except Exception as exc:
            return {
                "source": self.source_name,
                "status": "error",
                "ready": False,
                "message": f"iFinD 检查失败: {str(exc)[:120]}",
            }
