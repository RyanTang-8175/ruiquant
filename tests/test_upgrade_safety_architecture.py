from pathlib import Path
from datetime import datetime
from types import SimpleNamespace


def test_data_provider_registry_exposes_ifind_stub(monkeypatch):
    monkeypatch.setenv("ALPHAEYE_DATA_PROVIDER", "ifind")

    from src.data.providers.registry import get_provider, provider_status

    provider = get_provider()
    status = provider_status()

    assert provider.source_name == "ifind"
    assert status["provider"] == "ifind"
    assert status["ready"] is False
    assert "IFIND" in status["message"]


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


class _FakeOpenAIClient:
    def __init__(self, answer: str):
        self.answer = answer
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        message = SimpleNamespace(content=self.answer, tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])
