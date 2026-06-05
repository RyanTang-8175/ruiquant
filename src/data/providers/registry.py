"""
数据源注册中心。

AlphaEye 的页面、策略和 AI 工具都应通过这里拿数据源。这样 iFinD API
到位后只需要完成 ifind_provider 的接口映射，不需要重写业务层。
"""

from __future__ import annotations

import os
from functools import lru_cache

from src.config import get_setting
from src.data.providers.base import MarketDataProvider
from src.data.providers.ifind_provider import IFindProvider
from src.data.providers.open_provider import OpenDataProvider


def _provider_name(name: str | None = None) -> str:
    raw = name or get_setting(
        "data_provider",
        "ALPHAEYE_DATA_PROVIDER",
        os.getenv("ALPHAEYE_DATA_PROVIDER", "open"),
    )
    return str(raw or "open").strip().lower()


@lru_cache(maxsize=8)
def get_provider(name: str | None = None) -> MarketDataProvider:
    """返回统一行情数据源。默认使用项目现有公开源。"""
    selected = _provider_name(name)
    if selected in {"ifind", "ths", "同花顺"}:
        return IFindProvider()
    if selected in {"open", "public", "free", "akshare"}:
        return OpenDataProvider()
    return OpenDataProvider()


def provider_status(name: str | None = None) -> dict:
    """数据源健康状态，供我的页面/健康检查/AI 上下文展示。"""
    provider = get_provider(name)
    try:
        status = provider.health_check() or {}
    except Exception as exc:
        status = {
            "source": provider.source_name,
            "status": "error",
            "ready": False,
            "message": f"数据源检查失败: {str(exc)[:120]}",
        }
    ready = bool(status.get("ready", status.get("status") == "ok"))
    return {
        "provider": provider.source_name,
        "ready": ready,
        "status": status.get("status", "unknown"),
        "message": status.get("message", ""),
        "raw": status,
    }


def clear_provider_cache():
    get_provider.cache_clear()
