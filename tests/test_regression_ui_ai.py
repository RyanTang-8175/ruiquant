from src.ai.chat import AIChat, SYSTEM_PROMPT
from src.data.stock_list import CONCEPTS
from src.pages.ai_chat import _build_group_context
from src.pages.radar import _resolve_stock_name
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
    assert "不要要求用户必须给单只股票代码" in ctx
    from src.data.stock_list import CONCEPTS as _CONCEPTS
    assert any(c in ctx for c in (_CONCEPTS.get("电力", []) + _CONCEPTS.get("半导体芯片", []))), "电力/半导体无候选"
    # 至少有一只半导体芯片概念股出现在候选里（不强制688981，实时评分可能变动）
    has_chip = any(code in ctx for code in CONCEPTS.get("半导体芯片", []))
    assert has_chip, "半导体芯片概念无候选"


def test_ai_prompt_no_longer_forces_brokerage_style_buy_sell():
    assert "必须明确选一个" not in SYSTEM_PROMPT
    assert "操作建议必须坚决明确" not in SYSTEM_PROMPT
    assert "强关注/观察/中性/不追" not in SYSTEM_PROMPT


def test_ai_scene_prompt_uses_old_hand_style_and_builtin_roles():
    prompt = AIChat.build_system_prompt(
        "sector_scan",
        "我有1w块，想买电力行业或半导体行业，该买什么股票",
    )

    assert "先给人话结论" in prompt
    assert "我会怎么做" in prompt
    assert "候选 / 风险 / 条件" in prompt
    assert "资金纪律" in prompt
    assert "短线研究员" in prompt
    assert "风险审查员" in prompt
    assert "不要先要求用户给单只股票代码" in prompt


def test_ai_fallback_handles_sector_questions_without_single_stock_demand():
    ai = AIChat()
    answer = ai._fallback_answer("我有1w块，想买电力行业或半导体行业，该买什么股票")

    assert "人话结论" in answer
    assert "我会怎么做" in answer
    assert "资金纪律" in answer
    assert "电力" in answer
    assert "半导体" in answer
    assert "贵州茅台" not in answer


def test_radar_stock_name_uses_code_canonical_name_over_quote_name():
    assert _resolve_stock_name("600900", "旧名称") == "长江电力"
    assert _resolve_stock_name("688981", "旧名称") == "中芯国际"
    assert _resolve_stock_name("000858", "金山办公") == "五粮液"
    assert _resolve_stock_name("600519", "海康威视") == "贵州茅台"
    assert _resolve_stock_name("002304", "中芯国际") == "洋河股份"
