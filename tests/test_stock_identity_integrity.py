from types import SimpleNamespace


def test_search_normalizes_fullwidth_stock_name(monkeypatch):
    from src.ui import search

    monkeypatch.setattr(
        search,
        "_load_all_stocks",
        lambda: [{"code": "000725", "name": "京东方Ａ", "price": 6.43, "change_pct": 4.55}],
    )

    assert search.fuzzy_search("京东方A", limit=1)[0]["code"] == "000725"


def test_search_tolerates_one_character_stock_name_typo(monkeypatch):
    from src.ui import search

    monkeypatch.setattr(
        search,
        "_load_all_stocks",
        lambda: [{"code": "000725", "name": "京东方Ａ", "price": 6.43, "change_pct": 4.55}],
    )

    assert search.fuzzy_search("京东发A", limit=1)[0]["code"] == "000725"


def test_search_never_returns_raw_invalid_query_as_stock_code(monkeypatch):
    from src.ui import search

    monkeypatch.setattr(search, "_load_all_stocks", lambda: [])

    assert search.resolve_search_code("不存在的股票") == ""


def test_realtime_rejects_invalid_stock_identifier_without_provider_call(monkeypatch):
    from src.data import realtime

    calls = []
    monkeypatch.setattr(realtime, "_provider_or_none", lambda: calls.append("provider"))

    assert realtime.get_realtime_quote("京东发A") is None
    assert calls == []


def test_ifind_rejects_invalid_stock_identifier_without_api_call(monkeypatch):
    from src.data.providers.ifind_provider import IFindProvider

    provider = IFindProvider()
    calls = []
    monkeypatch.setattr(provider, "_post", lambda *args, **kwargs: calls.append((args, kwargs)))

    assert provider.get_realtime_quote("京东发A") is None
    assert calls == []


def test_research_harness_rejects_invalid_stock_identifier_without_provider_call(tmp_path):
    from src.research.harness import ResearchHarness

    class Provider:
        source_name = "ifind"

        def get_realtime_quote(self, code):
            raise AssertionError("invalid code must not reach provider")

    result = ResearchHarness(
        provider=Provider(),
        cache_dir=tmp_path / "cache",
        knowledge_path=tmp_path / "knowledge.json",
    ).company_research("京东发A")

    assert result["error"] == "invalid_stock_code"
    assert result["code"] == ""


def test_ai_resolves_explicit_stock_name_instead_of_previous_stock():
    from src.ai.chat import AIChat

    ai = AIChat()
    ai._last_stock = "600900"

    code = ai._extract_stock_code("请分析京东方A的风险")
    rewritten = ai._resolve_pronouns("请分析京东方A的风险", code)

    assert code == "000725"
    assert "600900" not in rewritten
    assert "长江电力" not in rewritten


def test_ai_does_not_treat_every_short_message_as_previous_stock_followup():
    from src.ai.chat import AIChat

    ai = AIChat()
    ai._last_stock = "600900"

    assert ai._resolve_pronouns("你好", "") == "你好"


def test_local_fallback_for_explicit_stock_name_does_not_switch_to_sector_template():
    from src.ai.chat import AIChat

    answer = AIChat()._fallback_answer("请分析京东方A的风险")

    assert "000725" in answer
    assert "长江电力" not in answer


def test_ai_history_is_scoped_to_current_stock():
    from src.ai.chat import AIChat

    ai = AIChat()
    ai.history = [
        {"question": "分析 600900", "answer": "长江电力", "stock_code": "600900"},
        {"question": "分析 000725", "answer": "京东方A", "stock_code": "000725"},
        {"question": "今天大盘如何", "answer": "震荡", "stock_code": ""},
    ]

    scoped = ai._history_for_request("000725", "分析京东方A")

    assert [item["answer"] for item in scoped] == ["京东方A"]


def test_ai_tool_arguments_are_locked_to_single_request_stock():
    from src.ai.chat import AIChat

    ai = AIChat()

    args, error = ai._guard_tool_arguments(
        "get_stock_quote",
        {"code": "600900"},
        allowed_stock_codes=["000725"],
    )

    assert error == ""
    assert args["code"] == "000725"


def test_ai_blocks_stock_tool_without_explicit_stock_subject():
    from src.ai.chat import AIChat

    ai = AIChat()

    args, error = ai._guard_tool_arguments(
        "ifind_company_research",
        {"code": "600900"},
        allowed_stock_codes=[],
    )

    assert args == {}
    assert error == "当前问题没有明确股票，已阻止随机个股工具调用"


def test_tool_executor_rejects_invalid_code_before_handler(monkeypatch):
    from src.ai.tool_executor import ToolExecutor

    executor = ToolExecutor()
    monkeypatch.setattr(
        executor,
        "_get_stock_quote",
        lambda code: (_ for _ in ()).throw(AssertionError("handler must not run")),
    )

    result = executor.execute("get_stock_quote", {"code": "京东发A"})

    assert '"error": "invalid_stock_code"' in result


def test_context_stock_name_overrides_stale_selected_stock():
    from src.pages.ai_chat import _resolve_context_stock

    assert _resolve_context_stock("分析京东方A的承接", "600900") == "000725"


def test_general_market_question_does_not_inherit_stale_selected_stock():
    from src.pages.ai_chat import _resolve_context_stock

    assert _resolve_context_stock("今天大盘如何", "600900") == ""


def test_ai_page_hides_other_stock_history_from_current_subject():
    from src.pages.ai_chat import _history_for_view

    history = [
        {"question": "分析 600900", "answer": "长江电力", "stock_code": "600900"},
        {"question": "分析京东方A", "answer": "京东方A", "stock_code": "000725"},
        {"question": "今天大盘如何", "answer": "震荡", "stock_code": ""},
    ]

    visible = _history_for_view(history, "000725")

    assert [item["answer"] for item in visible] == ["京东方A"]


def test_ai_tool_whitelist_ignores_codes_inside_injected_system_context():
    from src.ai.chat import AIChat
    from src.data.stock_list import extract_stock_references

    message = "请分析京东方A\n[系统: 股票长期记忆]\n以前分析过长江电力(600900)"
    query = AIChat._user_query_segment(message)

    assert query == "请分析京东方A"
    assert extract_stock_references(query) == ["000725"]


def test_answer_guard_corrects_wrong_name_bound_to_requested_code():
    from src.ai.evidence_guard import AnswerEvidenceGuard

    guarded, report = AnswerEvidenceGuard().validate_and_rewrite(
        answer="长江电力(000725)当前价6.43元。",
        user_message="分析京东方A",
        stock_code="000725",
        quote={
            "code": "000725",
            "name": "京东方A",
            "price": 6.43,
            "change_pct": 0.5,
            "turnover": 1.2,
            "amount": 1_000_000_000,
            "source": "ifind",
        },
    )

    assert "京东方A(000725)" in guarded
    assert "长江电力(000725)" not in guarded
    assert any("股票名称" in issue for issue in report["issues"])


class _ToolCallClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=self)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            function = SimpleNamespace(
                name="get_stock_quote",
                arguments='{"code":"600900"}',
            )
            tool_call = SimpleNamespace(id="call-1", function=function)
            message = SimpleNamespace(content="", tool_calls=[tool_call])
        else:
            message = SimpleNamespace(
                content="京东方A(000725)只做观察。",
                tool_calls=None,
            )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_ai_overrides_model_tool_code_and_does_not_call_previous_stock(monkeypatch):
    from src.ai.chat import AIChat

    ai = AIChat()
    ai.client = _ToolCallClient()
    ai.history = [
        {"question": "分析600900", "answer": "长江电力", "stock_code": "600900"},
    ]
    executed = []

    def execute(name, args):
        executed.append((name, dict(args)))
        return '{"code":"000725","name":"京东方A","price":6.43,"change_pct":0.5}'

    monkeypatch.setattr(ai.tool_executor, "execute", execute)
    monkeypatch.setattr(ai, "_live_quote_guard", lambda code: "")
    monkeypatch.setattr(ai, "_apply_answer_evidence_guard", lambda **kwargs: (kwargs["answer"], {}))
    monkeypatch.setattr(ai, "_save_user_message", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai, "_save_ai_message", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai, "_start_audit", lambda *args, **kwargs: (None, None))
    monkeypatch.setattr(ai, "_finish_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai, "save_to_disk", lambda: None)

    answer = ai.chat("请分析京东方A\n[系统: 股票长期记忆]\n以前分析过长江电力(600900)")

    assert "京东方A" in answer
    assert executed == [("get_stock_quote", {"code": "000725"})]


class _RepeatedToolCallClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=self)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls <= 2:
            function = SimpleNamespace(
                name="get_stock_quote",
                arguments='{"code":"000725"}',
            )
            message = SimpleNamespace(
                content="",
                tool_calls=[SimpleNamespace(id=f"call-{self.calls}", function=function)],
            )
        else:
            message = SimpleNamespace(content="京东方A(000725)只做观察。", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_ai_reuses_duplicate_tool_result_within_one_request(monkeypatch):
    from src.ai.chat import AIChat

    ai = AIChat()
    ai.client = _RepeatedToolCallClient()
    executed = []
    monkeypatch.setattr(
        ai.tool_executor,
        "execute",
        lambda name, args: executed.append((name, dict(args))) or '{"code":"000725","price":6.43}',
    )
    monkeypatch.setattr(ai, "_live_quote_guard", lambda code: "")
    monkeypatch.setattr(ai, "_apply_answer_evidence_guard", lambda **kwargs: (kwargs["answer"], {}))
    monkeypatch.setattr(ai, "_save_user_message", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai, "_save_ai_message", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai, "_start_audit", lambda *args, **kwargs: (None, None))
    monkeypatch.setattr(ai, "_finish_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai, "save_to_disk", lambda: None)

    ai.chat("请分析京东方A")

    assert executed == [("get_stock_quote", {"code": "000725"})]
