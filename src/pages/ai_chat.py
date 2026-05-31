"""移动端 AI 助手页"""

from __future__ import annotations

import html
import re
from datetime import datetime

import streamlit as st

from src.ai.chat import AIChat


TASKS = [
    {
        "title": "风险审查",
        "desc": "追高、诱多、高位接盘",
        "icon": "!",
        "prompt": "请用 AlphaEye 风险审查员模式，审查当前股票的反量化风险、短线风险、参与条件和放弃条件。",
    },
    {
        "title": "持股预测",
        "desc": "隔夜 / 1-2天 / 2-3天",
        "icon": "T",
        "prompt": "请判断当前股票适合隔夜、1-2天还是2-3天短持，并给出继续持有条件和离场条件。",
    },
    {
        "title": "今日选股",
        "desc": "按六维评分找候选",
        "icon": "R",
        "prompt": "请基于六维评分和反量化风险，给出今天值得研究的短线候选股，并按行业和概念说明机会来源。",
    },
    {
        "title": "交易复盘",
        "desc": "策略、AI、执行偏差",
        "icon": "V",
        "prompt": "请复盘我最近的模拟交易，区分策略表现、AI判断和我的执行偏差。",
    },
]


def render_ai_chat_page():
    ai = _get_ai()
    history = ai.get_history()
    selected_code = st.session_state.get("selected_stock", "")

    st.markdown('<div class="ai-shell">', unsafe_allow_html=True)
    _render_hero(selected_code)
    _render_search()
    _render_statusbar(history, selected_code)
    _render_task_grid(selected_code)
    _render_memory(history)
    _handle_pending_quick_question(ai, selected_code)
    _render_dialog(ai, history)
    _render_input(ai)
    _render_footer_actions(ai, history)
    st.markdown('</div>', unsafe_allow_html=True)


def _get_ai() -> AIChat:
    if "aic" not in st.session_state:
        ai = AIChat()
        ai.load_from_disk()
        st.session_state["aic"] = ai
    return st.session_state["aic"]


def _render_hero(selected_code: str):
    stock_line = "未绑定股票"
    if selected_code:
        stock_line = f"当前股票 {selected_code}"
    st.markdown(
        '<div class="ai-hero">'
        '<div class="ai-hero-title">AlphaEye AI</div>'
        f'<div class="ai-hero-sub">默认先审风险，再看机会。{stock_line}，所有分析都会尽量结合六维评分、反量化触发项和历史记忆。</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_search():
    from src.ui.search import render_search_bar

    code = render_search_bar(key="ai")
    if code:
        st.session_state["selected_stock"] = code
        st.session_state["current_page"] = "stock_detail"
        st.rerun()


def _render_statusbar(history: list, selected_code: str):
    env = _market_label()
    stock = selected_code or "未选择"
    st.markdown(
        '<div class="ai-statusbar">'
        f'<div class="ai-stat"><div class="ai-stat-label">市场环境</div><div class="ai-stat-value">{env}</div></div>'
        f'<div class="ai-stat"><div class="ai-stat-label">当前股票</div><div class="ai-stat-value">{stock}</div></div>'
        f'<div class="ai-stat"><div class="ai-stat-label">记忆数量</div><div class="ai-stat-value">{len(history)} 条</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _market_label() -> str:
    try:
        from src.data.realtime import get_market_overview

        indices = get_market_overview().get("indices", [])
        if not indices:
            return "待刷新"
        main = next((i for i in indices if "上证" in i.get("name", "")), indices[0])
        chg = main.get("change_pct", 0)
        if chg > 0.5:
            return "偏暖"
        if chg > -0.5:
            return "震荡"
        if chg > -1.5:
            return "谨慎"
        return "不适合"
    except Exception:
        return "待刷新"


def _render_task_grid(selected_code: str):
    st.markdown('<div class="ai-section-title">快捷任务</div>', unsafe_allow_html=True)
    for row in range(2):
        cols = st.columns(2)
        for col_index, col in enumerate(cols):
            task = TASKS[row * 2 + col_index]
            with col:
                st.markdown(
                    '<div class="ai-task">'
                    f'<div class="ai-task-icon">{task["icon"]}</div>'
                    f'<div class="ai-task-title">{task["title"]}</div>'
                    f'<div class="ai-task-desc">{task["desc"]}</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                label = f"启动：{task['title']}"
                if st.button(label, key=f"ai_task_{task['title']}", use_container_width=True):
                    prompt = task["prompt"]
                    if selected_code and task["title"] != "今日选股":
                        prompt = f"{prompt}\n股票代码：{selected_code}"
                    st.session_state["qq"] = prompt
                    st.rerun()


def _render_memory(history: list):
    st.markdown('<div class="ai-section-title">对话记忆</div>', unsafe_allow_html=True)
    if not history:
        st.markdown(
            '<div class="ai-memory-card">'
            '<div class="ai-memory-q">还没有对话</div>'
            '<div style="color:var(--muted);font-size:12px;line-height:1.55;margin-top:5px">输入股票代码或点击快捷任务开始。AI 会保存对话，方便下次继续。</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    rows = []
    for item in history[-4:][::-1]:
        question = html.escape(str(item.get("question", ""))[:36])
        ts = _short_time(item.get("timestamp", ""))
        rows.append(
            '<div class="ai-memory-row">'
            f'<div class="ai-memory-q">{question}</div>'
            f'<div class="ai-memory-t">{ts}</div>'
            '</div>'
        )
    st.markdown('<div class="ai-memory-card">' + "".join(rows) + '</div>', unsafe_allow_html=True)


def _handle_pending_quick_question(ai: AIChat, selected_code: str):
    if "qq" not in st.session_state:
        return
    q = st.session_state.pop("qq")
    if selected_code and "股票代码" not in q and "今天值得研究" not in q:
        q = f"{q}\n股票代码：{selected_code}"
    with st.spinner("AI 正在读取行情、评分和历史记忆..."):
        ai.chat(_with_context(q))
    st.rerun()


def _render_dialog(ai: AIChat, history: list):
    st.markdown('<div class="ai-section-title">当前对话</div>', unsafe_allow_html=True)
    if not history:
        return

    start_index = max(0, len(history) - 6)
    for offset, item in enumerate(history[-6:]):
        history_index = start_index + offset
        question = html.escape(str(item.get("question", "")))
        answer = _answer_to_html(str(item.get("answer", "")))
        st.markdown(f'<div class="chat-msg-user">{question}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-msg-assistant">{answer}</div>', unsafe_allow_html=True)
        tools = item.get("tools_used", [])
        if tools:
            st.markdown(
                f'<div class="chat-tools">工具：{html.escape(_tool_names(tools))}</div>',
                unsafe_allow_html=True,
            )
        if st.button("删除这条", key=f"delete_ai_msg_{history_index}", use_container_width=True):
            ai.delete_history_item(history_index)
            st.rerun()


def _render_input(ai: AIChat):
    user_text = st.chat_input("问股票、问行业、问风险，例如：审查 600519")
    if not user_text:
        return
    with st.spinner("AI 正在分析..."):
        ai.chat(_with_context(user_text))
    st.rerun()


def _render_footer_actions(ai: AIChat, history: list):
    if not history:
        return
    c1, c2 = st.columns(2)
    with c1:
        if st.button("保存记忆", use_container_width=True, type="primary"):
            ai.save_to_disk()
            st.success("已保存")
    with c2:
        if st.button("清空对话", use_container_width=True):
            ai.clear_history()
            st.rerun()


def _with_context(text: str) -> str:
    stock_code = _extract_code(text) or st.session_state.get("selected_stock", "")
    if not stock_code:
        group_context = _build_group_context(text)
        return f"{text}\n\n[系统已注入行业/概念候选上下文]\n{group_context}" if group_context else text
    try:
        from src.scoring.engine import V6ScoringEngine

        engine = V6ScoringEngine()
        try:
            context = engine.build_ai_context(stock_code)
        finally:
            engine.close()
        return f"{text}\n\n[系统已注入股票上下文]\n{context}"
    except Exception:
        return text


def _build_group_context(text: str) -> str:
    """为“我有1万块，想买电力或半导体”这类问题注入本地股票池和评分结果。"""
    from src.data.stock_list import CONCEPTS, SW_INDUSTRY

    groups = []
    normalized = text.replace("，", " ").replace("、", " ").replace("/", " ")
    for name, codes in SW_INDUSTRY.items():
        if name in normalized:
            groups.append(("行业", name, codes))
    for name, codes in CONCEPTS.items():
        if name in normalized:
            groups.append(("概念", name, codes))

    # 用户常用表达映射。
    aliases = {
        "半导体": ("概念", "半导体芯片", CONCEPTS.get("半导体芯片", [])),
        "芯片": ("概念", "半导体芯片", CONCEPTS.get("半导体芯片", [])),
        "电力行业": ("行业", "公用事业", SW_INDUSTRY.get("公用事业", [])),
        "电力": ("概念", "电力", CONCEPTS.get("电力", [])),
    }
    for alias, group in aliases.items():
        if alias in normalized and group[2]:
            groups.append(group)

    dedup = []
    seen_names = set()
    for group in groups:
        key = (group[0], group[1])
        if key not in seen_names:
            seen_names.add(key)
            dedup.append(group)
    groups = dedup[:4]
    if not groups:
        return ""

    try:
        from src.data.realtime import get_realtime_quote
        from src.scoring.engine import V6ScoringEngine

        engine = V6ScoringEngine()
        lines = [
            "用户问题是行业/概念选股，不要要求用户必须给单只股票代码。",
            "请基于以下本地股票池候选，给出短线研究候选、风险提示和仓位纪律。",
            "用户资金约 1 万元时，应强调分批、轻仓、验证，不要建议满仓。",
        ]
        try:
            for kind, name, codes in groups:
                scored = []
                for code in codes[:10]:
                    q = get_realtime_quote(code)
                    if not q:
                        continue
                    r = engine.score_stock(code, quote=q)
                    if not r:
                        continue
                    scored.append((r.total_score, q, r))
                scored.sort(key=lambda x: x[0], reverse=True)
                lines.append(f"\n{kind}：{name}")
                for _, q, r in scored[:5]:
                    triggers = "、".join(r.anti_quant.triggers[:2]) if r.anti_quant.triggers else "无明显触发"
                    lines.append(
                        f"- {q.get('name', r.code)}({r.code})：机会分{r.total_score:.0f}，"
                        f"涨幅{q.get('change_pct', 0):+.2f}%，状态{r.status_label}，"
                        f"反量化{r.anti_quant.risk_level}，风险触发：{triggers}"
                    )
                if not scored:
                    lines.append("- 实时行情暂不可用，静态候选池：" + "、".join(codes[:10]))
        finally:
            engine.close()
        return "\n".join(lines)
    except Exception:
        # 本地数据失败时也给模型明确任务，避免输出“请分析贵州茅台”这种兜底。
        names = "、".join(f"{kind}:{name}" for kind, name, _ in groups)
        return (
            f"用户在问行业/概念选股：{names}。即使实时评分暂不可用，也应解释筛选框架，"
            "给出需要去雷达页按行业/概念查看的候选方向和风险条件，不要要求用户换成单只股票。"
        )


def _extract_code(text: str) -> str:
    match = re.search(r"\b(\d{6})\b", text)
    return match.group(1) if match else ""


def _answer_to_html(text: str) -> str:
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", safe)
    safe = safe.replace("\n\n", "</p><p>")
    safe = safe.replace("\n", "<br>")
    return f"<p>{safe}</p>"


def _short_time(raw: str) -> str:
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw).strftime("%m-%d %H:%M")
    except Exception:
        return raw[:10]


def _tool_names(tools: list) -> str:
    names = {
        "get_stock_quote": "行情",
        "get_technical_analysis": "技术",
        "get_scoring_result": "评分",
        "get_market_snapshot": "大盘",
        "get_news": "新闻",
        "get_positions": "持仓",
        "get_kline_data": "K线",
        "get_watchlist": "选股",
        "get_financial_data": "财务",
    }
    return " · ".join(names.get(t, t) for t in tools)
