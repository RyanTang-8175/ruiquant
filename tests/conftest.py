"""测试环境隔离。

正式服务器会通过 .env/settings.json 配置 iFinD。测试必须忽略这些生产配置，
除非单个用例显式提供假 Token 和假 HTTP 响应，避免消耗真实月度额度。
"""

from __future__ import annotations

import requests
import pytest


@pytest.fixture(autouse=True)
def isolate_external_services(monkeypatch, tmp_path):
    monkeypatch.setenv("ALPHAEYE_DATA_PROVIDER", "open")
    monkeypatch.setenv("IFIND_VERIFY_SSL", "1")
    monkeypatch.delenv("IFIND_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("IFIND_ACCESS_TOKEN", raising=False)

    import src.config as config

    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")

    from src.data import realtime
    from src.data.providers.registry import clear_provider_cache

    clear_provider_cache()
    realtime._QCACHE.clear()
    monkeypatch.setattr(realtime, "_provider_or_none", lambda: None)

    def block_unmocked_http(self, method, url, *args, **kwargs):
        raise AssertionError(
            f"测试禁止访问外部网络，请为请求显式提供 mock: {method} {url}"
        )

    monkeypatch.setattr(
        requests.sessions.Session,
        "request",
        block_unmocked_http,
    )

    yield

    clear_provider_cache()
    realtime._QCACHE.clear()
