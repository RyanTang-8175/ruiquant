from src.ai.chat import AIChat, SYSTEM_PROMPT
from src.ai.tool_executor import ToolExecutor
from src.data.stock_list import CONCEPTS
from src.pages.ai_chat import _build_group_context
from src.pages.radar import _resolve_stock_name
from src.scoring.engine import ScoringEngine, V6ScoringEngine


def test_realtime_quote_normalizes_code_and_name(monkeypatch):
    from src.data import realtime

    realtime._QCACHE.clear()

    class Resp:
        text = 'v_sh600900="1~错名~999999~25.00~24.50~24.60~1000~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~2.04~25.50~24.20~0~0~12~1.2~10~0~0~0~5.3~0~0~0~0~0~1.4";'

    monkeypatch.setattr(realtime.requests, "get", lambda *a, **k: Resp())

    q = realtime.get_realtime_quote("600900")

    assert q["code"] == "600900"
    assert q["name"] == "长江电力"


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
    assert "直接给候选表" in prompt
    assert "不要把任务甩给用户去雷达页自己找" in prompt


def test_watchlist_uses_light_readable_card_styles():
    from pathlib import Path

    text = Path("src/pages/watchlist.py").read_text(encoding="utf-8")

    assert "background:#131510" not in text
    assert "color:#E8E8E5" not in text
    assert "VIEW {name}" not in text
    assert "研究审计" in text or "加入审计" in text


def test_ai_fallback_handles_sector_questions_without_single_stock_demand():
    ai = AIChat()
    answer = ai._fallback_answer("我有1w块，想买电力行业或半导体行业，该买什么股票")

    assert "人话结论" in answer
    assert "周一操作建议" in answer
    assert "周一操作两步走" in answer
    assert "资金纪律" in answer
    assert "时间表" in answer
    assert "雷达页分别切到" not in answer
    assert "自己筛" not in answer
    assert "贵州茅台" not in answer
    import re
    assert re.search(r'60\d{4}', answer), "无电力/主板候选"
    assert re.search(r'68\d{4}', answer), "无半导体候选"


def test_sector_candidate_tool_returns_named_candidates():
    data = ToolExecutor()._get_sector_candidates("我有1w块，想买电力行业或半导体行业，该买什么股票", limit=3)

    assert data["groups"]
    text = str(data)
    import re
    assert re.search(r'60\d{4}', text), "无电力候选"
    assert re.search(r'68\d{4}', text), "无半导体候选" or "立讯精密" in text

    for group in data["groups"]:
        for item in group["candidates"]:
            if item["score"] is None:
                assert item["action"] == "等待实时确认"


def test_radar_stock_name_uses_code_canonical_name_over_quote_name():
    assert _resolve_stock_name("600900", "旧名称") == "长江电力"
    assert _resolve_stock_name("688981", "旧名称") == "中芯国际"
    assert _resolve_stock_name("000858", "金山办公") == "五粮液"
    assert _resolve_stock_name("600519", "海康威视") == "贵州茅台"
    assert _resolve_stock_name("002304", "中芯国际") == "洋河股份"
