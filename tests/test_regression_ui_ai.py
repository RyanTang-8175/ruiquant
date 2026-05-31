from src.ai.chat import AIChat, SYSTEM_PROMPT
from src.pages.ai_chat import _build_group_context
from src.scoring.engine import ScoringEngine, V6ScoringEngine


def test_scoring_engines_support_context_manager():
    with ScoringEngine() as engine:
        assert engine is not None

    with V6ScoringEngine() as engine:
        assert engine is not None


def test_ai_chat_can_delete_single_history_item(tmp_path, monkeypatch):
    monkeypatch.setattr(AIChat, "_history_file", staticmethod(lambda: tmp_path / "history.json"))
    ai = AIChat()
    ai.history = [
        {"question": "one", "answer": "a"},
        {"question": "two", "answer": "b"},
    ]

    assert ai.delete_history_item(0) is True

    assert [item["question"] for item in ai.history] == ["two"]


def test_group_context_includes_static_candidates_for_sector_question():
    ctx = _build_group_context("我有1w块，想买电力行业或半导体行业，该买什么股票")

    assert "电力" in ctx
    assert "半导体芯片" in ctx
    assert "600900" in ctx
    assert "688981" in ctx
    assert "不要要求用户必须给单只股票代码" in ctx


def test_ai_prompt_no_longer_forces_brokerage_style_buy_sell():
    assert "必须明确选一个" not in SYSTEM_PROMPT
    assert "操作建议必须坚决明确" not in SYSTEM_PROMPT
    assert "强关注/观察/中性/不追" not in SYSTEM_PROMPT


def test_ai_fallback_handles_sector_questions_without_single_stock_demand():
    ai = AIChat()
    answer = ai._fallback_answer("我有1w块，想买电力行业或半导体行业，该买什么股票")

    assert "行业/概念选股" in answer
    assert "电力" in answer
    assert "半导体" in answer
    assert "贵州茅台" not in answer
