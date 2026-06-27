from pathlib import Path
from datetime import datetime
from types import SimpleNamespace


def test_data_provider_registry_exposes_ifind_http_provider(monkeypatch):
    monkeypatch.setenv("ALPHAEYE_DATA_PROVIDER", "ifind")
    monkeypatch.delenv("IFIND_REFRESH_TOKEN", raising=False)
    # 防止本地 settings.json 残留 token 干扰测试
    import src.data.providers.registry as reg
    import src.data.providers.ifind_provider as ifd
    monkeypatch.setattr(reg, "get_setting", lambda key, env_key=None, default="": default)
    monkeypatch.setattr(ifd, "get_setting", lambda key, env_key=None, default="": default)

    status = reg.provider_status()
    assert status["provider"] == "ifind"
    assert status["ready"] is False
    assert "IFIND_REFRESH_TOKEN" in status["message"]


def test_ifind_provider_normalizes_realtime_quote(monkeypatch):
    monkeypatch.setenv("IFIND_REFRESH_TOKEN", "refresh-token")

    from src.data.providers.ifind_provider import IFindProvider

    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.content = b"{}"

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        calls.append((url, headers or {}, json or {}))
        if url.endswith("/get_access_token"):
            return FakeResponse({"data": {"access_token": "access-token"}})
        assert headers["access_token"] == "access-token"
        return FakeResponse({
            "tables": [
                {
                    "thscode": "600519.SH",
                    "time": ["2026-06-05 14:56:00"],
                    "table": {
                        "latest": [1668.8],
                        "open": [1650.0],
                        "high": [1680.0],
                        "low": [1640.0],
                        "preClose": [1660.0],
                        "volume": [123456],
                        "amount": [234567890.0],
                        "changeRatio": [0.53],
                        "turnoverRatio": [0.81],
                    },
                }
            ]
        })

    monkeypatch.setattr("src.data.providers.ifind_provider.requests.post", fake_post)
    quote = IFindProvider().get_realtime_quote("600519")

    assert quote["code"] == "600519"
    assert quote["source"] == "ifind"
    assert quote["price"] == 1668.8
    assert quote["prev_close"] == 1660.0
    assert quote["change_pct"] == 0.53
    assert quote["turnover"] == 0.81
    assert quote["_quality"]["source"] == "ifind"
    assert calls[0][0].endswith("/get_access_token")
    assert calls[1][0].endswith("/real_time_quotation")


def test_ifind_smart_stock_picking_uses_low_limit_and_normalizes_rows(monkeypatch):
    monkeypatch.setenv("IFIND_REFRESH_TOKEN", "refresh-token")

    from src.data.providers.ifind_provider import IFindProvider

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.content = b"{}"

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        if url.endswith("/get_access_token"):
            return FakeResponse({"data": {"access_token": "access-token"}})
        assert url.endswith("/smart_stock_picking")
        assert json["searchstring"] == "主力资金流入"
        return FakeResponse({
            "tables": [
                {
                    "table": {
                        "股票代码": ["600900.SH", "688981.SH"],
                        "股票简称": ["长江电力", "中芯国际"],
                        "涨跌幅": [1.2, -0.8],
                    }
                }
            ]
        })

    monkeypatch.setattr("src.data.providers.ifind_provider.requests.post", fake_post)
    rows = IFindProvider().smart_stock_picking("主力资金流入", limit=2)

    assert rows == [
        {"code": "600900", "name": "长江电力", "price": 0.0, "change_pct": 1.2, "volume": 0, "amount": 0, "turnover": 0, "pe_ratio": 0, "market_cap": 0, "source": "ifind_wencai"},
        {"code": "688981", "name": "中芯国际", "price": 0.0, "change_pct": -0.8, "volume": 0, "amount": 0, "turnover": 0, "pe_ratio": 0, "market_cap": 0, "source": "ifind_wencai"},
    ]


def test_ifind_provider_exposes_more_http_endpoints(monkeypatch):
    monkeypatch.setenv("IFIND_REFRESH_TOKEN", "refresh-token")

    from src.data.providers.ifind_provider import IFindProvider

    seen = []

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.content = b"{}"

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        seen.append((url.rsplit("/", 1)[-1], json or {}))
        if url.endswith("/get_access_token"):
            return FakeResponse({"data": {"access_token": "access-token"}})
        return FakeResponse({"tables": [{"table": {"x": [1]}}]})

    monkeypatch.setattr("src.data.providers.ifind_provider.requests.post", fake_post)
    provider = IFindProvider()

    provider.date_sequence("600900", "ths_close_price_stock", ["", "100", ""], "2026-06-01", "2026-06-05")
    provider.data_pool("p03425", {"date": "20260605", "blockname": "001005010"}, "p03291_f002")
    provider.edb_service("G009035746", "2026-05-01", "2026-06-01")

    endpoints = [name for name, _ in seen]
    assert "date_sequence" in endpoints
    assert "data_pool" in endpoints
    assert "edb_service" in endpoints
    assert provider.usage_stats()["calls"]["date_sequence"] == 1


def test_ifind_usage_stats_persist_daily_and_monthly_counts(monkeypatch, tmp_path):
    monkeypatch.setenv("IFIND_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setenv("ALPHAEYE_IFIND_USAGE_PATH", str(tmp_path / "ifind_usage.json"))

    from src.data.providers.ifind_provider import IFindProvider

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.content = b"{}"

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        if url.endswith("/get_access_token"):
            return FakeResponse({"data": {"access_token": "access-token"}})
        return FakeResponse({"tables": []})

    monkeypatch.setattr("src.data.providers.ifind_provider.requests.post", fake_post)
    provider = IFindProvider()
    provider.smart_stock_picking("主力资金流入", limit=1)
    usage = provider.usage_stats()

    assert usage["calls"]["smart_stock_picking"] == 1
    assert usage["today_calls"] >= 1
    assert usage["month_calls"] >= 1
    assert usage["usage_path"].endswith("ifind_usage.json")


def test_research_harness_caches_and_writes_knowledge(tmp_path):
    from src.research.harness import ResearchHarness

    class FakeProvider:
        source_name = "ifind"

        def __init__(self):
            self.calls = 0
            self.picks = 0

        def get_realtime_quote(self, code):
            self.calls += 1
            return {"code": code, "name": "长江电力", "price": 25.0, "change_pct": 1.2, "source": "ifind"}

        def get_daily_bars(self, code, start, end):
            return [{"date": "2026-06-05", "close": 25.0, "change_pct": 1.2}]

        def report_query(self, code, days=45, limit=20):
            return [{"title": "长江电力回购公告", "type": "announcement", "source": "iFinD公告"}]

        def smart_stock_picking(self, query, limit=20):
            self.picks += 1
            return [{"code": "600900", "name": "长江电力", "change_pct": 1.2}]

        def basic_data(self, codes, indicator, params=None):
            return {"tables": [{"table": {indicator: [123.4]}}]}

        def usage_stats(self):
            return {"calls": {"real_time_quotation": self.calls}}

    provider = FakeProvider()
    harness = ResearchHarness(provider=provider, cache_dir=tmp_path / "cache", knowledge_path=tmp_path / "knowledge.json")

    first = harness.company_research("600900", profile="deep")
    second = harness.company_research("600900", profile="deep")

    assert first["cached"] is False
    assert second["cached"] is True
    # 缓存命中时仍刷新实时行情(便宜的高频接口)，所以 get_realtime_quote 被调用两次
    assert provider.calls == 2
    # 但昂贵的智能选股(4000/月额度)绝不重复调用，仍走缓存
    assert provider.picks == 1
    assert second.get("live_refreshed") is True
    assert first["summary_cards"][0]["title"] == "行情"
    assert "公告" in first["evidence"]
    assert {item["name"] for item in first["scenario_report"]} == {"利好继续发酵", "冲高回落", "板块不联动"}
    assert (tmp_path / "knowledge.json").exists()

    refreshed = harness.company_research("600900", profile="deep", force=True)
    assert refreshed["cached"] is False
    # force=True 完整重跑：行情第3次、智能选股第2次
    assert provider.calls == 3
    assert provider.picks == 2


def test_tool_executor_exposes_ifind_research_harness(monkeypatch, tmp_path):
    monkeypatch.setenv("ALPHAEYE_RESEARCH_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("ALPHAEYE_RESEARCH_KNOWLEDGE", str(tmp_path / "knowledge.json"))

    class FakeHarness:
        def company_research(self, code, profile="quick"):
            return {"code": code, "profile": profile, "summary_cards": [{"title": "行情"}], "cached": False}

        def market_radar(self, queries=None):
            return {"queries": queries or [], "themes": [], "cached": False}

    monkeypatch.setattr("src.ai.tool_executor.ResearchHarness", lambda: FakeHarness())

    from src.ai.tool_executor import ToolExecutor

    company = ToolExecutor()._ifind_company_research("600900", "deep")
    market = ToolExecutor()._ifind_market_radar(["主力资金流入"])

    assert company["code"] == "600900"
    assert company["profile"] == "deep"
    assert market["queries"] == ["主力资金流入"]


def test_research_workflow_registry_loads_three_sops():
    from src.research.workflow import ResearchWorkflowRegistry

    registry = ResearchWorkflowRegistry()
    workflows = registry.list()
    ids = {item["id"] for item in workflows}

    assert ids >= {"company_diligence", "earnings_review", "thematic_market"}
    assert "supply_chain_chokepoint" in ids
    assert all(item["review_required"] is True for item in workflows)
    assert all(item["stages"] for item in workflows)
    assert registry.get("earnings_review")["quota_budget"]["smart_stock_picking"] <= 1


def test_research_workflow_runner_builds_sources_quality_and_quota(tmp_path):
    from src.research.workflow import ResearchWorkflowRunner

    class FakeProvider:
        source_name = "ifind"

        def usage_stats(self):
            return {
                "today_by_endpoint": {"real_time_quotation": 4, "report_query": 2},
                "month_by_endpoint": {"real_time_quotation": 40, "report_query": 20},
            }

    class FakeHarness:
        provider = FakeProvider()
        knowledge = SimpleNamespace(record_run=lambda payload: None)

        def company_research(self, code, profile="quick", force=False):
            return {
                "kind": "company_research",
                "code": code,
                "title": "长江电力研究底稿",
                "quality": "high",
                "source": "ifind",
                "evidence": {
                    "行情": {
                        "code": code,
                        "name": "长江电力",
                        "price": 25.0,
                        "change_pct": 1.2,
                        "turnover": 1.5,
                        "amount": 2_000_000_000,
                        "source": "ifind",
                        "quality_level": "professional",
                        "retrieved_at": "2026-06-06T15:20:00",
                    },
                    "K线": [
                        {"date": "2026-06-04", "close": 24.7, "change_pct": 0.2, "source": "ifind"},
                        {"date": "2026-06-05", "close": 25.0, "change_pct": 1.2, "source": "ifind"},
                    ],
                    "公告": [
                        {
                            "title": "长江电力2025年年度报告",
                            "published_at": "2026-04-30",
                            "source": "iFinD公告",
                            "url": "https://example.com/report.pdf",
                        }
                    ],
                    "基础数据": {"市盈率TTM": 18.5, "净利润": 123.4, "每股收益TTM": 1.2},
                    "智能选股": [{"code": code, "name": "长江电力", "source": "ifind_wencai"}],
                },
                "scenario_report": [{"name": "基准情景", "possibility": "50%", "evidence": "行情稳定"}],
            }

    runner = ResearchWorkflowRunner(
        harness=FakeHarness(),
        store_path=tmp_path / "workflow_runs.json",
    )
    run = runner.run("company_diligence", subject="长江电力深度研究", code="600900")

    assert run["status"] == "draft"
    assert run["review_required"] is True
    assert run["review"]["status"] == "pending"
    assert run["quality_gate"]["passed"] is True
    assert run["source_ledger"]
    assert {item["source_id"] for item in run["source_ledger"]} >= {"S1", "S2"}
    assert run["source_ledger"][0]["published_at"] == "2026-06-06T15:20:00"
    assert run["artifacts"]["research_note"].startswith("# 长江电力")
    assert "[S1]" in run["artifacts"]["research_note"]
    assert run["quota"]["budget"]["smart_stock_picking"] == 1
    assert run["quota"]["delta"]["today"] == {}
    assert runner.list_runs(limit=5)[0]["run_id"] == run["run_id"]


def test_earnings_workflow_blocks_without_financial_filing(tmp_path):
    import json

    from src.research.workflow import ResearchWorkflowRunner

    class FakeProvider:
        source_name = "ifind"

        def usage_stats(self):
            return {"today_by_endpoint": {}, "month_by_endpoint": {}}

    class FakeHarness:
        provider = FakeProvider()
        knowledge = SimpleNamespace(record_run=lambda payload: None)

        def company_research(self, code, profile="quick", force=False):
            return {
                "code": code,
                "quality": "medium",
                "source": "ifind",
                "evidence": {
                    "行情": {"code": code, "name": "测试公司", "price": 10.0, "source": "ifind"},
                    "K线": [{"date": "2026-06-05", "close": 10.0, "source": "ifind"}],
                    "公告": [{"title": "关于召开股东大会的公告", "source": "iFinD公告"}],
                    "基础数据": {"市盈率TTM": 20.0, "净利润": 3.2},
                    "智能选股": [],
                },
                "scenario_report": [],
            }

    runner = ResearchWorkflowRunner(
        harness=FakeHarness(),
        store_path=tmp_path / "workflow_runs.json",
    )
    run = runner.run("earnings_review", subject="测试公司最新财报", code="600001")
    artifact_text = json.dumps(run["artifacts"], ensure_ascii=False).lower()

    assert run["status"] == "blocked_missing_evidence"
    assert run["quality_gate"]["passed"] is False
    assert "财报事件公告" in run["quality_gate"]["missing"]
    assert "beat" not in artifact_text
    assert "miss" not in artifact_text
    assert "超预期" not in artifact_text
    assert "低于预期" not in artifact_text


def test_thematic_workflow_deduplicates_candidates_and_requires_three(tmp_path):
    from src.research.workflow import ResearchWorkflowRunner

    class FakeProvider:
        source_name = "ifind"

        def usage_stats(self):
            return {"today_by_endpoint": {"smart_stock_picking": 3}, "month_by_endpoint": {"smart_stock_picking": 30}}

    class FakeHarness:
        provider = FakeProvider()
        knowledge = SimpleNamespace(record_run=lambda payload: None)

        def market_radar(self, queries=None):
            return {
                "kind": "market_radar",
                "themes": [
                    {
                        "query": queries[0],
                        "rows": [
                            {"code": "600900", "name": "长江电力", "source": "ifind_wencai"},
                            {"code": "600900", "name": "长江电力", "source": "ifind_wencai"},
                        ],
                    },
                    {
                        "query": queries[1],
                        "rows": [
                            {"code": "600011", "name": "华能国际", "source": "ifind_wencai"},
                            {"code": "600886", "name": "国投电力", "source": "ifind_wencai"},
                        ],
                    },
                ],
                "quality": "ok",
            }

    runner = ResearchWorkflowRunner(
        harness=FakeHarness(),
        store_path=tmp_path / "workflow_runs.json",
    )
    run = runner.run("thematic_market", subject="电力央企改革")

    assert run["quality_gate"]["passed"] is True
    assert len(run["artifacts"]["candidate_shortlist"]) == 3
    assert run["artifacts"]["candidate_shortlist"][0]["code"] == "600900"
    assert len(run["source_ledger"]) >= 3


def test_workflow_review_requires_explicit_human_action(tmp_path):
    from src.research.workflow import WorkflowRunStore

    store = WorkflowRunStore(tmp_path / "workflow_runs.json")
    store.save({
        "run_id": "r1",
        "workflow_id": "company_diligence",
        "review": {"status": "pending", "notes": ""},
        "quality_gate": {"passed": True, "missing": []},
    })

    approved = store.review("r1", "approved", "数据已人工复核")

    assert approved["review"]["status"] == "approved"
    assert approved["review"]["notes"] == "数据已人工复核"
    assert approved["review"]["reviewed_at"]
    assert store.list(limit=1)[0]["run_id"] == "r1"


def test_workflow_store_rejects_missing_run_id(tmp_path):
    import pytest

    from src.research.workflow import WorkflowRunStore

    store = WorkflowRunStore(tmp_path / "workflow_runs.json")

    with pytest.raises(ValueError, match="run_id"):
        store.save({"workflow_id": "company_diligence"})


def test_workflow_store_preserves_concurrent_runs(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    from src.research.workflow import WorkflowRunStore

    store = WorkflowRunStore(tmp_path / "workflow_runs.json")

    def save(index):
        return store.save({
            "run_id": f"run-{index}",
            "workflow_id": "company_diligence",
            "quality_gate": {"passed": True},
        })

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(save, range(20)))

    run_ids = {item["run_id"] for item in store.list(limit=30)}
    assert run_ids == {f"run-{index}" for index in range(20)}


def test_workflow_review_cannot_approve_blocked_run(tmp_path):
    import pytest

    from src.research.workflow import WorkflowRunStore

    store = WorkflowRunStore(tmp_path / "workflow_runs.json")
    store.save({
        "run_id": "blocked",
        "workflow_id": "earnings_review",
        "review": {"status": "pending", "notes": ""},
        "quality_gate": {"passed": False, "missing": ["财报原文链接"]},
    })

    with pytest.raises(ValueError, match="质量门"):
        store.review("blocked", "approved", "忽略证据缺口")

    rejected = store.review("blocked", "rejected", "补齐原文后重跑")
    assert rejected["review"]["status"] == "rejected"


def test_earnings_workflow_requires_original_document_link(tmp_path):
    from src.research.workflow import ResearchWorkflowRunner

    class FakeProvider:
        source_name = "ifind"

        def usage_stats(self):
            return {"today_by_endpoint": {}, "month_by_endpoint": {}}

    class FakeHarness:
        provider = FakeProvider()
        knowledge = SimpleNamespace(record_run=lambda payload: None)

        def company_research(self, code, profile="quick", force=False):
            return {
                "code": code,
                "source": "ifind",
                "evidence": {
                    "行情": {
                        "code": code,
                        "name": "测试公司",
                        "price": 10.0,
                        "source": "ifind",
                        "quality_level": "professional",
                        "retrieved_at": "2026-06-06T15:20:00",
                    },
                    "公告": [{
                        "title": "测试公司2025年年度报告",
                        "published_at": "2026-04-30",
                        "source": "iFinD公告",
                        "url": "",
                    }],
                    "基础数据": {"市盈率TTM": 20.0, "净利润": 3.2},
                },
            }

    runner = ResearchWorkflowRunner(
        harness=FakeHarness(),
        store_path=tmp_path / "workflow_runs.json",
    )
    run = runner.run("earnings_review", subject="测试公司2025年报", code="600001")

    assert run["status"] == "blocked_missing_evidence"
    assert "财报原文链接" in run["quality_gate"]["missing"]


def test_workflow_quota_overrun_blocks_draft(tmp_path):
    from src.research.workflow import ResearchWorkflowRunner

    class FakeProvider:
        source_name = "ifind"

        def __init__(self):
            self.calls = 0

        def usage_stats(self):
            return {
                "today_by_endpoint": {"real_time_quotation": self.calls},
                "month_by_endpoint": {"real_time_quotation": self.calls},
            }

    provider = FakeProvider()

    class FakeHarness:
        knowledge = SimpleNamespace(record_run=lambda payload: None)

        def __init__(self):
            self.provider = provider

        def company_research(self, code, profile="quick", force=False):
            provider.calls = 2
            return {
                "code": code,
                "source": "ifind",
                "evidence": {
                    "行情": {
                        "code": code,
                        "name": "测试公司",
                        "price": 10.0,
                        "source": "ifind",
                        "quality_level": "professional",
                    },
                    "K线": [{"date": "2026-06-05", "close": 10.0, "source": "ifind"}],
                    "公告": [{"title": "测试公告", "source": "iFinD公告"}],
                    "基础数据": {"市盈率TTM": 20.0, "净利润": 3.2},
                },
            }

    runner = ResearchWorkflowRunner(
        harness=FakeHarness(),
        store_path=tmp_path / "workflow_runs.json",
    )
    run = runner.run("company_diligence", subject="测试公司", code="600001")

    assert run["status"] == "blocked_quota_overrun"
    assert run["quota"]["within_budget"] is False
    assert run["quota"]["violations"][0]["endpoint"] == "real_time_quotation"
    assert "额度预算" in run["quality_gate"]["missing"]


def test_company_workflow_invalid_code_is_blocked_without_data_call(tmp_path):
    from src.research.workflow import ResearchWorkflowRunner

    class FakeProvider:
        source_name = "ifind"

        def usage_stats(self):
            return {"today_by_endpoint": {}, "month_by_endpoint": {}}

    class FakeHarness:
        provider = FakeProvider()
        knowledge = SimpleNamespace(record_run=lambda payload: None)

        def __init__(self):
            self.calls = 0

        def company_research(self, code, profile="quick", force=False):
            self.calls += 1
            raise AssertionError("无效股票代码不应调用 iFinD")

    harness = FakeHarness()
    runner = ResearchWorkflowRunner(
        harness=harness,
        store_path=tmp_path / "workflow_runs.json",
    )
    run = runner.run("company_diligence", subject="无效标的", code="not-a-code")

    assert harness.calls == 0
    assert run["status"] == "blocked_missing_evidence"
    assert "有效股票代码" in run["quality_gate"]["missing"]
    assert run["code"] == ""


def test_ai_tools_expose_research_sops_without_review_tool():
    from src.ai.tools import TOOLS

    names = {tool["function"]["name"] for tool in TOOLS}

    assert "list_research_workflows" in names
    assert "run_research_workflow" in names
    assert "review_research_workflow" not in names


def test_tool_executor_runs_research_workflow(monkeypatch):
    class FakeRunner:
        def __init__(self):
            self.registry = SimpleNamespace(list=lambda: [{"id": "company_diligence"}])

        def run(self, workflow_id, subject, code=""):
            return {"workflow_id": workflow_id, "subject": subject, "code": code, "status": "draft"}

    monkeypatch.setattr("src.ai.tool_executor.ResearchWorkflowRunner", FakeRunner)

    from src.ai.tool_executor import ToolExecutor

    executor = ToolExecutor()
    listed = executor._list_research_workflows()
    run = executor._run_research_workflow("company_diligence", "长江电力", "600900")

    assert listed["workflows"] == [{"id": "company_diligence"}]
    assert run["status"] == "draft"
    assert run["code"] == "600900"


def test_research_page_exposes_sop_quality_sources_and_human_review():
    source = Path("src/pages/research.py").read_text(encoding="utf-8")

    assert "_workflow_panel" in source
    assert "runner.preview" in source
    assert "runner.run" in source
    assert "runner.review" in source
    assert "来源账本" in source
    assert "质量门" in source
    assert "人工复核" in source
    assert "[:5]" not in source


def test_research_page_exposes_standalone_thematic_sop():
    source = Path("src/pages/research.py").read_text(encoding="utf-8")

    assert '_workflow_panel("", {}, allowed_ids={"thematic_market"})' in source
    assert 'result.get("workflow_id") == selected' in source


def test_news_tool_accepts_declared_category_argument():
    import inspect

    from src.ai.tool_executor import ToolExecutor

    parameters = inspect.signature(ToolExecutor._get_news).parameters
    assert "category" in parameters


def test_research_summary_excludes_unavailable_basic_values():
    from src.research.harness import ResearchHarness

    cards = ResearchHarness._summary_cards({
        "行情": {"price": 10.0, "change_pct": 1.0},
        "公告": [],
        "基础数据": {
            "市盈率TTM": 20.0,
            "净利润": 0,
            "流通市值": "unavailable: endpoint failed",
            "_warning": "缓存值",
        },
        "智能选股": [],
    })
    basic_card = next(item for item in cards if item["title"] == "基础数据")

    assert basic_card["value"] == 1


def test_cached_company_research_recomputes_summary_cards(tmp_path):
    from datetime import datetime

    from src.research.harness import ResearchHarness

    class FakeProvider:
        source_name = "ifind"

        def get_realtime_quote(self, code):
            return {
                "code": code,
                "name": "测试公司",
                "price": 10.2,
                "change_pct": 2.0,
                "source": "ifind",
                "quality_level": "professional",
            }

    harness = ResearchHarness(
        provider=FakeProvider(),
        cache_dir=tmp_path / "cache",
        knowledge_path=tmp_path / "knowledge.json",
    )
    fingerprint = harness._fingerprint("company", "600001", "quick")
    harness._write_cache(fingerprint, {
        "code": "600001",
        "created_at": datetime.now().isoformat(),
        "summary_cards": [{"title": "基础数据", "value": 99, "note": "旧缓存"}],
        "evidence": {
            "行情": {"code": "600001", "price": 10.0, "source": "ifind"},
            "K线": [{"date": "2026-06-05", "close": 10.0}],
            "公告": [],
            "基础数据": {
                "市盈率TTM": 20.0,
                "流通市值": "unavailable: endpoint failed",
            },
            "智能选股": [],
        },
    })

    research = harness.company_research("600001", profile="quick")
    basic_card = next(
        item for item in research["summary_cards"] if item["title"] == "基础数据"
    )

    assert research["cached"] is True
    assert basic_card["value"] == 1


def test_research_page_uses_latest_four_kline_bars():
    source = Path("src/pages/research.py").read_text(encoding="utf-8")

    assert "recent = bars[-4:]" in source
    assert 'item.get("date") or f"最近{len(recent) - idx}日"' in source


def test_ifind_evidence_score_combines_opportunity_risk_and_confidence():
    from src.scoring.evidence import IFindEvidenceScorer

    research = {
        "code": "600900",
        "source": "ifind",
        "quality": "high",
        "evidence": {
            "行情": {"price": 25.0, "change_pct": 2.1, "turnover": 3.2, "amount": 4200000000, "source": "ifind"},
            "K线": [
                {"close": 23.5, "change_pct": 0.5},
                {"close": 24.2, "change_pct": 1.0},
                {"close": 25.0, "change_pct": 2.1},
            ],
            "公告": [
                {"title": "长江电力回购股份方案", "source": "iFinD公告"},
                {"title": "长江电力业绩预增公告", "source": "iFinD公告"},
            ],
            "基础数据": {"市盈率TTM": 18.5, "净利润": 123.4, "流通市值": 3000},
            "智能选股": [{"query": "主力资金流入", "code": "600900"}],
        },
    }

    score = IFindEvidenceScorer().score(research)

    assert score["code"] == "600900"
    assert score["opportunity_score"] >= 60
    assert score["risk_score"] < 70
    assert score["confidence"] in {"中", "高"}
    assert set(score["dimensions"]) == {"fund_heat", "support_quality", "catalyst", "fundamental_safety", "crowding_risk", "data_confidence"}
    assert score["action"] in {"可模拟验证", "可观察"}
    assert score["evidence_summary"]


def test_valuation_deviation_does_not_treat_broken_trend_as_undervaluation():
    from src.scoring.valuation_deviation import compute_valuation_deviation

    bars = [{"close": 100.0, "high": 101.0, "low": 99.0} for _ in range(60)]
    result = compute_valuation_deviation({"price": 75.0}, bars)

    assert result["score"] == 50
    assert result["direction"] == "估值未知"
    assert result["sub_scores"]["20日均线位置"] < 50
    assert "不判定低估" in result["explanation"]


def test_valuation_deviation_uses_fundamental_anchor_before_valuation_label():
    from src.scoring.valuation_deviation import compute_valuation_deviation

    bars = [{"close": 100.0, "high": 101.0, "low": 99.0} for _ in range(60)]
    result = compute_valuation_deviation({"price": 96.0, "pe_ratio": 12.0, "pb_ratio": 1.4}, bars)

    assert result["score"] >= 55
    assert result["direction"] in {"偏低估", "估值合理"}
    assert "PE分位" in result["sub_scores"]
    assert "PB分位" in result["sub_scores"]


def test_tool_executor_exposes_ifind_evidence_score(monkeypatch):
    class FakeHarness:
        def company_research(self, code, profile="quick"):
            return {
                "code": code,
                "source": "ifind",
                "quality": "medium",
                "evidence": {
                    "行情": {"price": 10.0, "change_pct": 0.5, "turnover": 1.0, "amount": 500000000},
                    "K线": [],
                    "公告": [],
                    "基础数据": {},
                    "智能选股": [],
                },
            }

    monkeypatch.setattr("src.ai.tool_executor.ResearchHarness", lambda: FakeHarness())

    from src.ai.tool_executor import ToolExecutor

    result = ToolExecutor()._ifind_evidence_score("600900")

    assert result["code"] == "600900"
    assert "opportunity_score" in result
    assert "risk_score" in result


def test_navigation_helper_keeps_transient_pages_out_of_main_nav():
    from src.ui.navigation import resolve_main_navigation

    state = resolve_main_navigation(
        current_page="stock_detail",
        selected_nav="market",
        last_nav_page="radar",
        tab_pages=["market", "radar", "research", "ai_chat", "lab", "profile"],
    )

    assert state["current_page"] == "stock_detail"
    assert state["show_main_nav"] is False
    assert state["selected_nav"] == "radar"


def test_system_prompt_mentions_ifind_research_tools_and_quota():
    from src.ai.chat import AIChat

    prompt = AIChat.build_system_prompt("deep_analysis", "请对 600900 做深度研究")

    assert "ifind_company_research" in prompt
    assert "ifind_market_radar" in prompt
    assert "ifind_evidence_score" in prompt
    assert "额度" in prompt
    assert "Research Harness" in prompt or "研究 Harness" in prompt


def test_research_evaluator_compares_legacy_and_ifind_scores():
    from src.research.evaluator import ResearchEvaluator

    rows = [
        {
            "strategy_name": "iFinD研究底稿 · quick",
            "hypothesis": "新评分 72 旧评分 58",
            "backfills": [{"day": 1, "hit_2pct": True, "hold_1d": 2.4}],
        },
        {
            "strategy_name": "旧六维评分",
            "hypothesis": "旧评分 75",
            "backfills": [{"day": 1, "hit_2pct": False, "hold_1d": -1.2}],
        },
    ]

    report = ResearchEvaluator().compare_score_systems(rows)

    assert report["ifind"]["total"] == 1
    assert report["ifind"]["hit_rate"] == 100.0
    assert report["legacy"]["total"] == 1
    assert report["legacy"]["hit_rate"] == 0.0
    assert report["winner"] == "ifind"


def test_strategy_governor_returns_four档_decision():
    from src.research.strategy import StrategyGovernor

    decision = StrategyGovernor().decide({
        "opportunity_score": 72,
        "risk_score": 48,
        "confidence": "高",
        "hit_rate": 66,
        "drawdown": 3,
        "environment_match": True,
    })

    assert decision["tier"] == "继续持有"
    assert "加仓" in decision["allowed_actions"]

    stop = StrategyGovernor().decide({
        "opportunity_score": 40,
        "risk_score": 82,
        "confidence": "低",
        "hit_rate": 20,
        "drawdown": 12,
        "environment_match": False,
    })

    assert stop["tier"] == "正式下线"
    assert stop["allow_real_trade"] is False


def test_strategy_explorer_sweeps_without_repeating_fingerprints(tmp_path):
    from src.research.strategy import StrategyExplorer

    explorer = StrategyExplorer(store_path=tmp_path / "explore.json")
    first = explorer.sweep_filter_values(
        base_config={"universe": "A股", "holding": "1-2天"},
        dimension="risk_limit",
        values=[55, 65, 65],
    )
    second = explorer.sweep_filter_values(
        base_config={"universe": "A股", "holding": "1-2天"},
        dimension="risk_limit",
        values=[55],
    )

    assert first["executed"] == 2
    assert first["skipped_duplicates"] == 1
    assert second["executed"] == 0
    assert second["skipped_duplicates"] == 1
    assert first["coverage"]["risk_limit"] == 2


def test_ai_tools_expose_research_loop_capabilities():
    from src.ai.tools import TOOLS

    names = {tool["function"]["name"] for tool in TOOLS}

    assert "get_research_score_comparison" in names
    assert "govern_strategy_tier" in names
    assert "sweep_strategy_values" in names


def test_radar_candidate_pool_keeps_recommended_stocks_with_ifind_scores():
    from src.pages.radar import _build_candidate_pool_rows

    legacy_result = SimpleNamespace(
        code="600900",
        name="长江电力",
        total_score=68,
        status_label="等待确认",
        anti_quant=SimpleNamespace(total_risk=28, risk_level="中", triggers=["承接尚可"]),
        heat=SimpleNamespace(score=70),
        support=SimpleNamespace(score=66),
        theme=SimpleNamespace(score=58),
        continuation=SimpleNamespace(score=62),
        strategy_match=SimpleNamespace(score=60),
    )
    rows = _build_candidate_pool_rows(
        scored_results=[
            (
                {
                    "code": "600900",
                    "name": "长江电力",
                    "price": 25.0,
                    "change_pct": 1.2,
                    "turnover": 3.1,
                    "amount": 3200000000,
                },
                legacy_result,
            )
        ],
        ifind_rows=[
            {
                "code": "600900",
                "name": "长江电力",
                "price": 25.0,
                "change_pct": 1.2,
                "turnover": 3.1,
                "amount": 3200000000,
                "source": "ifind_wencai",
            },
            {
                "code": "688981",
                "name": "中芯国际",
                "price": 102.5,
                "change_pct": 2.4,
                "turnover": 4.5,
                "amount": 5300000000,
                "source": "ifind_wencai",
            },
        ],
        market_scope="中国A股",
    )

    by_code = {row["code"]: row for row in rows}

    assert by_code["600900"]["market_scope"] == "中国A股"
    assert by_code["600900"]["legacy_score"] == 68
    assert by_code["600900"]["ifind_score"] > 0
    assert by_code["600900"]["score_source"] == "旧六维+iFinD证据"
    assert by_code["600900"]["action"] in {"研究候选", "可模拟验证", "可观察", "只观察"}
    assert by_code["688981"]["score_source"] == "iFinD证据"
    assert by_code["600900"]["rank_score"] >= by_code["688981"]["rank_score"]


def test_radar_candidate_pool_risk_gate_pushes_high_risk_below_safer_candidate():
    from src.pages.radar import _build_candidate_pool_rows

    risky_result = SimpleNamespace(
        code="600111",
        name="高风险样本",
        total_score=88,
        status_label="高热度",
        anti_quant=SimpleNamespace(total_risk=86, risk_level="极高", triggers=["尾盘诱多", "放量滞涨"]),
        heat=SimpleNamespace(score=92),
        support=SimpleNamespace(score=70),
        theme=SimpleNamespace(score=80),
        continuation=SimpleNamespace(score=76),
        strategy_match=SimpleNamespace(score=72),
    )
    safer_result = SimpleNamespace(
        code="600900",
        name="长江电力",
        total_score=68,
        status_label="等待确认",
        anti_quant=SimpleNamespace(total_risk=26, risk_level="低", triggers=[]),
        heat=SimpleNamespace(score=66),
        support=SimpleNamespace(score=66),
        theme=SimpleNamespace(score=58),
        continuation=SimpleNamespace(score=60),
        strategy_match=SimpleNamespace(score=62),
    )

    rows = _build_candidate_pool_rows(
        scored_results=[
            ({"code": "600111", "name": "高风险样本", "price": 10.0, "change_pct": 9.8}, risky_result),
            ({"code": "600900", "name": "长江电力", "price": 25.0, "change_pct": 1.2}, safer_result),
        ],
        ifind_rows=[],
    )

    assert [row["code"] for row in rows[:2]] == ["600900", "600111"]
    assert rows[1]["risk_gate"] == "回避"


def test_radar_market_scope_defaults_to_main_board_candidates():
    from src.pages.radar import _build_candidate_pool_rows

    bj_result = SimpleNamespace(
        code="830799",
        name="北交所样本",
        total_score=80,
        status_label="高热度",
        anti_quant=SimpleNamespace(total_risk=20, risk_level="低", triggers=[]),
        heat=SimpleNamespace(score=80),
        support=SimpleNamespace(score=80),
        theme=SimpleNamespace(score=80),
        continuation=SimpleNamespace(score=80),
        strategy_match=SimpleNamespace(score=80),
    )
    star_result = SimpleNamespace(
        code="688981",
        name="中芯国际",
        total_score=82,
        status_label="科创参考",
        anti_quant=SimpleNamespace(total_risk=22, risk_level="低", triggers=[]),
        heat=SimpleNamespace(score=82),
        support=SimpleNamespace(score=82),
        theme=SimpleNamespace(score=82),
        continuation=SimpleNamespace(score=82),
        strategy_match=SimpleNamespace(score=82),
    )
    sh_result = SimpleNamespace(
        code="600900",
        name="长江电力",
        total_score=60,
        status_label="等待确认",
        anti_quant=SimpleNamespace(total_risk=25, risk_level="低", triggers=[]),
        heat=SimpleNamespace(score=60),
        support=SimpleNamespace(score=60),
        theme=SimpleNamespace(score=60),
        continuation=SimpleNamespace(score=60),
        strategy_match=SimpleNamespace(score=60),
    )

    rows = _build_candidate_pool_rows(
        scored_results=[
            ({"code": "830799", "name": "北交所样本"}, bj_result),
            ({"code": "688981", "name": "中芯国际"}, star_result),
            ({"code": "600900", "name": "长江电力"}, sh_result),
        ],
        ifind_rows=[{"code": "430047", "name": "北交所iFinD样本"}, {"code": "300750", "name": "宁德时代"}],
        market_scope="主板优先",
    )

    assert {row["code"] for row in rows} == {"600900"}


def test_radar_market_scope_can_include_growth_and_star_but_exclude_beijing():
    from src.pages.radar import _build_candidate_pool_rows

    rows = _build_candidate_pool_rows(
        scored_results=[],
        ifind_rows=[
            {"code": "430047", "name": "北交所样本"},
            {"code": "300750", "name": "宁德时代"},
            {"code": "688981", "name": "中芯国际"},
            {"code": "600900", "name": "长江电力"},
        ],
        market_scope="沪深A股",
    )

    assert {row["code"] for row in rows} == {"300750", "688981", "600900"}


def test_radar_candidate_pool_can_attach_latest_news_evidence():
    from src.pages.radar import _attach_latest_news_evidence

    rows = [{"code": "600900", "name": "长江电力", "source_chain": ["公开行情"], "confidence": "中"}]

    def fake_fetcher(code, limit=3):
        assert code == "600900"
        return {
            "items": [
                {"title": "长江电力发布重大投资公告", "source": "公告", "published_at": "2026-06-27 09:30:00"},
            ]
        }

    enriched = _attach_latest_news_evidence(rows, news_fetcher=fake_fetcher)

    assert enriched[0]["latest_news_title"] == "长江电力发布重大投资公告"
    assert enriched[0]["latest_news_source"] == "公告"
    assert enriched[0]["news_freshness"] == "有最新证据"
    assert "最新新闻" in enriched[0]["source_chain"]


def test_ai_chat_marks_placeholder_key_as_not_ready(monkeypatch):
    from src.ai.chat import AIChat

    monkeypatch.setattr(
        "src.ai.chat.get_setting",
        lambda key, env_key=None, default="": {
            "api_key": "sk-test-placeholder",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
        }.get(key, default),
    )

    status = AIChat.provider_status()

    assert status["ready"] is False
    assert status["provider"] == "deepseek"
    assert "占位" in status["message"]


def test_ai_chat_uses_api_when_valid_key_is_configured(monkeypatch):
    from src.ai.chat import AIChat

    monkeypatch.setattr(
        "src.ai.chat.get_setting",
        lambda key, env_key=None, default="": {
            "api_key": "sk-valid-realistic-key",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
        }.get(key, default),
    )

    status = AIChat.provider_status()

    assert status["ready"] is True
    assert status["base_url"] == "https://api.deepseek.com"
    assert status["model"] == "deepseek-chat"


def test_ai_chat_provider_status_infers_qwen_openai_compatible_endpoint():
    from src.ai.chat import AIChat

    status = AIChat.provider_status(
        api_key="sk-live-qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus",
    )

    assert status["ready"] is True
    assert status["provider"] == "qwen"
    assert "OpenAI 兼容" in status["message"]


def test_profile_page_labels_main_model_as_openai_compatible():
    source = Path("src/pages/profile.py").read_text(encoding="utf-8")

    assert "主模型（OpenAI 兼容）" in source
    assert "DeepSeek 不可用时自动切换" in source


def test_market_radar_includes_research_views_and_sector_moves(monkeypatch):
    from src.news import radar

    def fake_smart(query, limit=10):
        if "机构" in query or "研报" in query:
            return [
                {
                    "title": "中芯国际(688981) 机构观点升温",
                    "content": "研报/机构关注升温",
                    "source": "iFinD机构观点",
                    "type": "research_view",
                    "related_codes": ["688981"],
                }
            ]
        if "行业" in query or "概念" in query:
            return [
                {
                    "title": "半导体行业异动",
                    "content": "行业涨幅与成交额升温",
                    "source": "iFinD行业异动",
                    "type": "sector_move",
                    "related_codes": ["688981"],
                }
            ]
        return []

    monkeypatch.setattr(radar, "fetch_ifind_smart_picks", fake_smart)
    monkeypatch.setattr(radar, "fetch_policy_updates", lambda limit=15: [])
    monkeypatch.setattr(radar, "fetch_irm_hot", lambda limit=20: [])
    monkeypatch.setattr("src.news.fetcher.fetch_all_news", lambda limit=30: [])

    result = radar.fetch_radar_market_overview(limit=12)

    assert result["sources"]["iFinD机构观点"] == 1
    assert result["sources"]["iFinD行业异动"] == 1
    assert any(item["type"] == "research_view" for item in result["items"])
    assert any(item["type"] == "sector_move" for item in result["items"])


def test_answer_evidence_guard_rewrites_stale_quote_and_unsupported_trade_claim():
    from src.ai.evidence_guard import AnswerEvidenceGuard

    answer = (
        "中国铝业（601600）—— 当前7.57元，周五跌-1.30%，"
        "换手0.94%，成交9.7亿。你持有1万股，周五收盘前还加仓了。\n"
        "如果低开破7.45，先观察。"
    )
    quote = {
        "code": "601600",
        "name": "中国铝业",
        "price": 10.68,
        "change_pct": -2.02,
        "turnover": 2.04,
        "amount": 2_900_000_000,
        "source": "ifind",
        "_fallback": False,
    }

    guarded, report = AnswerEvidenceGuard().validate_and_rewrite(
        answer=answer,
        user_message="我手上买了一万股的中国铝业，下周你有什么建议",
        stock_code="601600",
        quote=quote,
        verified_trades=[],
    )

    assert report["corrected"] is True
    assert "7.57元" not in guarded
    assert "周五跌-1.30%" not in guarded
    assert "换手0.94%" not in guarded
    assert "成交9.7亿" not in guarded
    assert "10.68元" in guarded
    assert "-2.02%" in guarded
    assert "换手率2.04%" in guarded
    assert "成交额29.0亿" in guarded
    assert "按你本轮口述" in guarded
    assert "周五收盘前还加仓了" not in guarded
    assert "没有可核验记录" in guarded
    assert "iFinD" in guarded


def test_answer_evidence_guard_preserves_conditional_support_levels():
    from src.ai.evidence_guard import AnswerEvidenceGuard

    guarded, _ = AnswerEvidenceGuard().validate_and_rewrite(
        answer="当前7.57元。如果下周低开跌破7.45元，研究假设失效。",
        user_message="分析601600",
        stock_code="601600",
        quote={
            "code": "601600",
            "name": "中国铝业",
            "price": 10.68,
            "change_pct": -2.02,
            "turnover": 2.04,
            "amount": 2_900_000_000,
            "source": "tencent",
            "_fallback": True,
        },
        verified_trades=[],
    )

    assert "当前10.68元" in guarded
    assert "跌破7.45元" in guarded
    assert "腾讯公开源兜底" in guarded


def test_answer_evidence_guard_preserves_future_scenarios_and_historical_metrics():
    from src.ai.evidence_guard import AnswerEvidenceGuard

    guarded, _ = AnswerEvidenceGuard().validate_and_rewrite(
        answer=(
            "当前7.57元。如果周一上涨3%，继续观察。"
            "2025年收盘价7.57元，成交额9.7亿，换手率0.94%。"
        ),
        user_message="分析601600",
        stock_code="601600",
        quote={
            "code": "601600",
            "name": "中国铝业",
            "price": 10.68,
            "change_pct": -2.02,
            "turnover": 2.04,
            "amount": 2_900_000_000,
            "source": "ifind",
        },
        verified_trades=[],
    )

    assert "当前10.68元" in guarded
    assert "如果周一上涨3%" in guarded
    assert "2025年收盘价7.57元" in guarded
    assert "成交额9.7亿" in guarded
    assert "换手率0.94%" in guarded


def test_ai_finalize_guards_answer_before_history_and_audit(monkeypatch):
    from src.ai.chat import AIChat

    ai = AIChat()
    ai.history = []
    ai._tools_used = ["get_stock_quote"]
    ai._last_stock = ""
    ai._conversation_context = {}
    ai._request_evidence = {
        "quotes": {
            "601600": {
                "code": "601600",
                "name": "中国铝业",
                "price": 10.68,
                "change_pct": -2.02,
                "turnover": 2.04,
                "amount": 2_900_000_000,
                "source": "ifind",
            }
        },
        "positions": {},
        "trades": [],
    }
    saved = {}

    monkeypatch.setattr(ai, "save_to_disk", lambda: None)
    monkeypatch.setattr(
        ai,
        "_save_ai_message",
        lambda **kwargs: saved.update({"answer": kwargs["answer"]}),
    )
    monkeypatch.setattr(ai, "_finish_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "src.data.realtime.get_realtime_quote",
        lambda _code: (_ for _ in ()).throw(AssertionError("不应重复调用行情接口")),
    )

    result = ai._finalize_response(
        user_message="我手上买了一万股的中国铝业",
        answer="当前7.57元。你持有1万股，周五收盘前还加仓了。",
        session_id=None,
        stock_code="601600",
        scene="deep_analysis",
        scratchpad=None,
        run_id=None,
    )

    assert "当前10.68元" in result
    assert "7.57元" not in result
    assert "周五收盘前还加仓了" not in result
    assert ai.history[-1]["answer"] == result
    assert saved["answer"] == result


def test_answer_evidence_guard_removes_current_price_when_quote_unavailable():
    from src.ai.evidence_guard import AnswerEvidenceGuard

    guarded, report = AnswerEvidenceGuard().validate_and_rewrite(
        answer="当前7.57元，建议继续观察。",
        user_message="分析601600",
        stock_code="601600",
        quote={},
        verified_trades=[],
    )

    assert report["corrected"] is True
    assert "7.57元" not in guarded
    assert "当前价格暂无可靠数据" in guarded


def test_validation_header_omits_metrics_that_source_did_not_return():
    from src.ai.evidence_guard import AnswerEvidenceGuard

    guarded, _ = AnswerEvidenceGuard().validate_and_rewrite(
        answer="当前7.57元。",
        user_message="分析601600",
        stock_code="601600",
        quote={
            "code": "601600",
            "name": "中国铝业",
            "price": 10.68,
            "source": "sina",
            "_fallback": True,
        },
        verified_trades=[],
    )

    header = guarded.split("\n", 1)[0]
    assert "10.68元" in header
    assert "涨跌幅" not in header
    assert "换手率" not in header
    assert "成交额" not in header


def test_answer_evidence_guard_requires_trade_time_to_match_claim():
    from datetime import datetime
    from src.ai.evidence_guard import AnswerEvidenceGuard

    guarded, _ = AnswerEvidenceGuard().validate_and_rewrite(
        answer="你周五收盘前还加仓了。",
        user_message="我持有中国铝业",
        stock_code="601600",
        quote={},
        verified_trades=[
            {
                "direction": "buy",
                "created_at": "2026-06-01T10:00:00",
            }
        ],
        validated_at=datetime(2026, 6, 6, 15, 0),
    )

    assert "周五收盘前还加仓了" not in guarded
    assert "没有可核验记录" in guarded


def test_trade_question_does_not_verify_that_trade_already_happened():
    from datetime import datetime
    from src.ai.evidence_guard import AnswerEvidenceGuard

    guarded, _ = AnswerEvidenceGuard().validate_and_rewrite(
        answer="你周五收盘前还加仓了。",
        user_message="我周一该不该加仓中国铝业？",
        stock_code="601600",
        quote={},
        verified_trades=[],
        validated_at=datetime(2026, 6, 6, 15, 0),
    )

    assert "周五收盘前还加仓了" not in guarded
    assert "没有可核验记录" in guarded


def test_user_reported_real_position_is_not_overwritten_by_paper_position():
    from src.ai.evidence_guard import AnswerEvidenceGuard

    guarded, _ = AnswerEvidenceGuard().validate_and_rewrite(
        answer="你持有1万股，先观察。",
        user_message="我真实账户持有一万股中国铝业",
        stock_code="601600",
        quote={},
        verified_position={"quantity": 5000, "cost_price": 9.8},
        verified_trades=[],
    )

    assert "按你本轮口述，你持有1万股" in guarded
    assert "模拟盘记录显示你持有5000股" not in guarded


def test_user_risk_state_enters_cooldown_after_recent_bad_feedback():
    from src.risk.user_state import evaluate_user_risk_state

    state = evaluate_user_risk_state(
        trade_stats={"total_trades": 5, "win_rate": 0.2, "total_pnl": -1200},
        recent_feedback=["no_stop_loss", "user_chasing", "strategy_error", "no_stop_loss"],
    )

    assert state["mode"] == "cooldown"
    assert state["allows_real_trade"] is False
    assert "只允许观察/模拟/复盘" in state["action_policy"]


def test_verification_record_preserves_trade_plan_metadata(tmp_path, monkeypatch):
    db_path = tmp_path / "lab.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    import importlib
    import src.config as config
    import src.utils.database as database
    import src.data.models_v6 as models_v6

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(models_v6)
    models_v6.Base.metadata.create_all(database.engine)

    from src.memory.analysis_memory import AnalysisMemory

    with AnalysisMemory() as memory:
        vid = memory.create_verification(
            "radar",
            "600900",
            "长江电力",
            datetime(2026, 6, 5, 10, 0),
            strategy_name="尾盘隔夜雷达",
            suggested_period="1-2天",
            hypothesis="电力防守方向有承接，若回踩不破均价线可模拟验证。",
            entry_conditions=["回踩不破分时均价线", "板块至少 3 只同步走强"],
            invalidation_conditions=["放量滞涨", "跌破昨日低点"],
            stop_loss_rule="亏损 2.5% 或跌破均价线 10 分钟不收回",
            risk_level="中",
            confidence_level="中",
            allow_real_trade=False,
        )
        record = memory.get_verification_results()[0]

    assert vid > 0
    assert record["hypothesis"].startswith("电力防守")
    assert record["allow_real_trade"] is False
    assert "回踩不破分时均价线" in record["entry_conditions"]


def test_scratchpad_records_tool_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHAEYE_SCRATCHPAD_DIR", str(tmp_path))

    from src.agent.scratchpad import Scratchpad

    sp = Scratchpad()
    run_id = sp.start_run("半导体还能不能看", scene="sector_scan")
    sp.log_tool_result(run_id, "get_market_snapshot", {"ok": True}, {"indices": []})
    path = sp.finish_run(run_id, answer_summary="只观察不追")

    text = Path(path).read_text(encoding="utf-8")
    assert "get_market_snapshot" in text
    assert "只观察不追" in text


def test_ai_chat_persists_db_memory_and_analysis(tmp_path, monkeypatch):
    db_path = tmp_path / "chat.db"
    scratch_dir = tmp_path / "scratch"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("ALPHAEYE_SCRATCHPAD_DIR", str(scratch_dir))

    import importlib
    import src.config as config
    import src.utils.database as database
    import src.data.models_v6 as models_v6

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(models_v6)
    models_v6.Base.metadata.create_all(database.engine)

    from src.ai.chat import AIChat

    ai = AIChat()
    ai.client = _FakeOpenAIClient(
        "### 人话结论\n先观察，不追。\n\n风险等级：中\n持有周期：1-2天"
    )
    ai.history = []

    answer = ai.chat("分析 600900 今天还能不能观察")

    db = database.SessionLocal()
    try:
        messages = db.query(models_v6.AIMessage).all()
        analyses = db.query(models_v6.AIAnalysisRecord).all()
    finally:
        db.close()

    assert "先观察" in answer
    assert len(messages) == 2
    assert messages[-1].structured_output["risk_level"] == "中"
    assert len(analyses) == 1
    assert analyses[0].stock_code == "600900"
    assert list(scratch_dir.glob("*.jsonl"))


def test_ai_chat_auto_creates_research_audit_for_observable_report(tmp_path, monkeypatch):
    db_path = tmp_path / "audit.db"
    scratch_dir = tmp_path / "scratch_audit"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("ALPHAEYE_SCRATCHPAD_DIR", str(scratch_dir))

    import importlib
    import src.config as config
    import src.utils.database as database
    import src.data.models_v6 as models_v6

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(models_v6)
    models_v6.Base.metadata.create_all(database.engine)

    from src.ai.chat import AIChat
    from src.memory.analysis_memory import AnalysisMemory

    ai = AIChat()
    ai.client = _FakeOpenAIClient(
        "## 结论摘要\n"
        "机会分 72（机会分=上涨条件是否充足），风险分 61（风险分=追高被套概率），置信度 中（置信度=数据是否足够）。\n"
        "结论：可观察，但不适合追高。\n\n"
        "## 交易计划表\n"
        "| 动作 | 触发条件 | 禁止条件 | 仓位/验证方式 | 复盘记录 |\n"
        "|---|---|---|---|---|\n"
        "| 加入观察 | 回踩不破均价线 | 高开急冲 | 仅模拟 | T+1/T+2/T+3 |\n\n"
        "## 反证与失效条件\n"
        "放量滞涨；跌破均价线；板块不联动。"
    )

    answer = ai.chat("分析 600900 今天能不能观察")

    with AnalysisMemory() as memory:
        records = memory.get_verification_results("600900")

    assert "机会分 72" in answer
    assert len(records) == 1
    assert records[0]["source_type"] == "ai_prediction"
    assert "可观察" in records[0]["hypothesis"]
    assert records[0]["allow_real_trade"] is False


def test_prompt_explains_three_scores_for_beginner():
    from src.ai.chat import AIChat

    prompt = AIChat.build_system_prompt("deep_analysis", "分析 600900")

    assert "机会分" in prompt
    assert "风险分" in prompt
    assert "置信度" in prompt
    assert "括号" in prompt
    assert "新手也能看懂" in prompt
    assert "持仓事实铁律" in prompt
    assert "用户口述" in prompt
    assert "get_positions" in prompt


def test_conversation_memory_indexes_threads_and_search(tmp_path, monkeypatch):
    db_path = tmp_path / "memory.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    import importlib
    import src.config as config
    import src.utils.database as database
    import src.data.models_v6 as models_v6

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(models_v6)
    models_v6.Base.metadata.create_all(database.engine)

    from src.memory.conversation_memory import ConversationMemory

    memory = ConversationMemory()
    try:
        sid = memory.create_session("deep_analysis", "长江电力复盘")
        memory.save_message(sid, "user", "分析 600900 止损纪律", stock_code="600900")
        memory.save_message(sid, "assistant", "长江电力先观察，止损条件是跌破均价线。", stock_code="600900")
        threads = memory.list_recent_threads()
        stock_rows = memory.get_stock_conversations("600900")
        search_rows = memory.search_messages("止损")
    finally:
        memory.close()

    assert threads[0]["stock_code"] == "600900"
    assert any("均价线" in row["content"] for row in stock_rows)
    assert len(search_rows) >= 2


def test_verification_backfill_stays_partial_until_required_days(tmp_path, monkeypatch):
    db_path = tmp_path / "backfill.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    import importlib
    import src.config as config
    import src.utils.database as database
    import src.data.models_v6 as models_v6

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(models_v6)
    models_v6.Base.metadata.create_all(database.engine)

    from src.memory.analysis_memory import AnalysisMemory

    with AnalysisMemory() as memory:
        vid = memory.create_verification(
            "manual", "600900", "长江电力", datetime(2026, 6, 5),
            suggested_period="2-3天",
        )
        memory.save_backfill(vid, {
            "trade_date": datetime(2026, 6, 6).date(),
            "day_offset": 1,
            "high_change_pct": 1.0,
        })
        first = memory.get_verification_results()[0]
        memory.save_backfill(vid, {
            "trade_date": datetime(2026, 6, 9).date(),
            "day_offset": 3,
            "high_change_pct": 2.5,
        })
        final = memory.get_verification_results()[0]

    assert first["backfill_status"] == "partial"
    assert final["backfill_status"] == "complete"


def test_ai_chat_api_failure_is_persisted(tmp_path, monkeypatch):
    db_path = tmp_path / "failure.db"
    scratch_dir = tmp_path / "scratch_failure"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("ALPHAEYE_SCRATCHPAD_DIR", str(scratch_dir))

    import importlib
    import src.config as config
    import src.utils.database as database
    import src.data.models_v6 as models_v6

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(models_v6)
    models_v6.Base.metadata.create_all(database.engine)

    from src.ai.chat import AIChat

    ai = AIChat()
    ai.client = _FailingOpenAIClient()
    answer = ai.chat("分析 600900")

    db = database.SessionLocal()
    try:
        messages = db.query(models_v6.AIMessage).all()
    finally:
        db.close()

    assert "模型服务暂时不可用" in answer
    assert "本地兜底研究" in answer
    assert "技术位参考" in answer
    assert len(messages) == 2
    assert messages[-1].role == "assistant"
    assert list(scratch_dir.glob("*.jsonl"))


def test_legacy_conversation_json_imports_to_db(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    legacy_path = tmp_path / "latest_conversation.json"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("ALPHAEYE_CONVERSATION_FILE", str(legacy_path))
    legacy_path.write_text(
        """
[
  {
    "question": "分析 600900",
    "answer": "### 人话结论\\n长江电力先观察。\\n\\n| 维度 | 结论 |\\n|---|---|\\n| 风险 | 中 |",
    "timestamp": "2026-06-01T10:00:00",
    "tools_used": ["get_stock_quote"]
  }
]
""",
        encoding="utf-8",
    )

    import importlib
    import src.config as config
    import src.utils.database as database
    import src.data.models_v6 as models_v6

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(models_v6)
    models_v6.Base.metadata.create_all(database.engine)

    from src.ai.chat import AIChat

    ai = AIChat()
    loaded = ai.load_from_disk()

    db = database.SessionLocal()
    try:
        messages = db.query(models_v6.AIMessage).order_by(models_v6.AIMessage.id).all()
    finally:
        db.close()

    assert loaded is True
    assert len(ai.get_history()) == 1
    assert len(messages) == 2
    assert messages[0].stock_code == "600900"
    assert messages[1].tools_used == ["get_stock_quote"]


def test_ai_prompt_requires_detailed_financial_memo():
    from src.ai.chat import AIChat

    prompt = AIChat.build_system_prompt("deep_analysis", "分析 600900")

    for section in ["结论摘要", "证据表", "反量化风险表", "交易计划表", "失效条件", "复盘入库"]:
        assert section in prompt
    assert "文表并用" in prompt
    assert "不要用两三句话糊弄" in prompt


class _FakeOpenAIClient:
    def __init__(self, answer: str):
        self.answer = answer
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        message = SimpleNamespace(content=self.answer, tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FailingOpenAIClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        raise RuntimeError("api down")


def test_specialized_ai_methods_use_local_fallback_when_model_down(monkeypatch):
    from src.data import realtime
    from src.ai.chat import AIChat

    monkeypatch.setattr(realtime, "get_market_overview", lambda: {
        "indices": [
            {"name": "上证指数", "price": 3050.12, "change_pct": 0.72},
            {"name": "创业板指", "price": 1888.32, "change_pct": -0.21},
        ]
    })
    monkeypatch.setattr(realtime, "get_top_stocks", lambda sort_field="changepercent", asc=False, limit=15: [
        {"code": "600900", "name": "长江电力", "price": 25.6, "change_pct": 2.1, "turnover": 1.8, "amount": 3200000000},
        {"code": "688981", "name": "中芯国际", "price": 58.2, "change_pct": 1.2, "turnover": 3.2, "amount": 4100000000},
    ][:limit])
    monkeypatch.setattr(realtime, "get_realtime_quote", lambda code: {
        "600900": {"code": "600900", "name": "长江电力", "price": 25.6, "change_pct": 2.1, "turnover": 1.8, "amount": 3200000000},
        "688981": {"code": "688981", "name": "中芯国际", "price": 58.2, "change_pct": 1.2, "turnover": 3.2, "amount": 4100000000},
    }.get(code, {"code": code, "name": code, "price": 0, "change_pct": 0, "turnover": 0, "amount": 0}))

    ai = AIChat()
    ai.client = _FailingOpenAIClient()

    morning = ai.morning_briefing()
    compare = ai.compare_stocks("600900", "688981")
    closing = ai.closing_summary()

    for answer in (morning, compare, closing):
        assert "模型服务暂时不可用" in answer
        assert "本地" in answer
        assert "AI 未配置" not in answer
        assert "暂不可用:" not in answer

    assert "盘前" in morning or "盘中" in morning
    assert "600900" in compare and "688981" in compare
    assert "上证指数" in closing


def test_account_diagnosis_uses_local_fallback_when_ai_not_configured():
    from src.ai.chat import AIChat

    ai = AIChat()
    ai.client = None
    answer = ai.account_diagnosis()

    assert "模型服务暂时不可用" in answer
    assert "本地账户诊断" in answer
    assert "AI 未配置" not in answer


def test_pytest_collects_only_portable_project_tests():
    from pathlib import Path

    config_path = Path(__file__).resolve().parents[1] / "pytest.ini"

    assert config_path.exists()
    config = config_path.read_text(encoding="utf-8")
    assert "testpaths = tests" in config


def test_aliyun_systemd_unit_runs_streamlit_from_server_workspace():
    from pathlib import Path

    unit_path = Path(__file__).resolve().parents[1] / "deploy" / "ruiquant.service"

    assert unit_path.exists()
    unit = unit_path.read_text(encoding="utf-8")
    assert "WorkingDirectory=/root/ruiquant" in unit
    assert "EnvironmentFile=-/root/ruiquant/.env" in unit
    assert "ExecStart=/root/ruiquant/venv/bin/streamlit run /root/ruiquant/app.py" in unit
    assert "--server.port=8501" in unit
    assert "Restart=always" in unit
