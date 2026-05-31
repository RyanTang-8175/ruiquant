"""AI 助手"""

import streamlit as st
from src.ai.chat import AIChat


def render_ai_chat_page():
    st.markdown(
        '<div class="ai-hero">'
        '<div class="ai-hero-title">AI 风险审查员</div>'
        '<div class="ai-hero-sub">先看风险，再看机会。输入股票代码或问题，AI 会结合六维评分、反量化触发项和历史记忆给出条件化判断。</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── 全局搜索 ──
    from src.ui.search import render_search_bar
    code = render_search_bar(key="ai")
    if code:
        st.session_state["selected_stock"] = code
        st.session_state["current_page"] = "stock_detail"
        st.rerun()

    if "aic" not in st.session_state:
        ai = AIChat()
        ai.load_from_disk()
        st.session_state["aic"] = ai
    ai = st.session_state["aic"]

    # ── 快捷技能：移动端 2x2，避免按钮矩阵压迫 ──
    sks = [
        ("风险审查", "检查追高、诱多、高位接盘"),
        ("持股预测", "判断隔夜 / 1-2天 / 2-3天"),
        ("今日选股", "给出今日短线候选与理由"),
        ("复盘交易", "分析策略、AI和执行偏差"),
    ]
    for row in range(2):
        cols = st.columns(2)
        for i in range(2):
            idx = row * 2 + i
            if idx < len(sks):
                lbl, desc = sks[idx]
                with cols[i]:
                    st.markdown(
                        f'<div class="skill-card"><div class="skill-title">{lbl}</div>'
                        f'<div class="skill-desc">{desc}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(lbl, use_container_width=True, help=desc):
                        st.session_state["qq"] = desc
                        st.rerun()

    st.markdown('<div class="sec-h">对话</div>', unsafe_allow_html=True)

    if "qq" in st.session_state:
        q = st.session_state.pop("qq")
        try:
            with st.spinner("分析中..."):
                ai.chat(q)
        except Exception as e:
            st.error(f"错误: {e}")
        st.rerun()

    history = ai.get_history()
    if history:
        with st.expander(f"历史对话 · {len(history)} 条", expanded=True):
            for m in history[-8:]:
                with st.chat_message("user"):
                    st.write(m["question"])
                with st.chat_message("assistant"):
                    st.markdown(m["answer"])
                    if m.get("tools_used"):
                        nm = {
                            "get_stock_quote": "行情", "get_technical_analysis": "技术",
                            "get_scoring_result": "评分", "get_market_snapshot": "大盘",
                            "get_news": "新闻", "get_positions": "持仓",
                        }
                        st.caption(" · ".join(nm.get(t, t) for t in m["tools_used"]))
    else:
        st.markdown(
            '<div class="soft-card">'
            '<div style="font-weight:700;color:var(--text);font-size:15px;margin-bottom:4px">还没有对话</div>'
            '<div style="color:var(--muted);font-size:13px;line-height:1.55">可以直接输入股票代码，例如“帮我审查 600519 的短线风险”，或点击上面的快捷任务。</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    if u := st.chat_input("问股票、问大盘、问策略..."):
        with st.chat_message("user"):
            st.write(u)
        with st.chat_message("assistant"):
            with st.spinner("分析中..."):
                # 注入 v6 评分上下文
                stock_code = _extract_code(u)
                ctx_str = ""
                if stock_code:
                    try:
                        from src.scoring.engine import V6ScoringEngine
                        engine = V6ScoringEngine()
                        try:
                            ctx_str = "\n\n[系统已注入: " + engine.build_ai_context(stock_code) + "]"
                        finally:
                            engine.close()
                    except Exception:
                        pass
                ans = ai.chat(u + ctx_str)
                st.markdown(ans)
            if ai.get_last_tools_used():
                nm = {
                    "get_stock_quote": "行情", "get_technical_analysis": "技术",
                    "get_scoring_result": "评分", "get_market_snapshot": "大盘",
                    "get_news": "新闻", "get_positions": "持仓",
                }
                st.caption(" · ".join(nm.get(t, t) for t in ai.get_last_tools_used()))

    if history:
        if st.button("清空对话", use_container_width=True):
            ai.clear_history()
            st.rerun()


def _extract_code(text: str) -> str:
    import re
    m = re.search(r'\b(\d{6})\b', text)
    return m.group(1) if m else ""
