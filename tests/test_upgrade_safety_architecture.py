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

    def fake_post(url, headers=None, json=None, timeout=None):
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

    def fake_post(url, headers=None, json=None, timeout=None):
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

    def fake_post(url, headers=None, json=None, timeout=None):
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

    def fake_post(url, headers=None, json=None, timeout=None):
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
    assert "结论摘要" in answer
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
