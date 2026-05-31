"""AI 助手"""

import streamlit as st
from src.ai.chat import AIChat


def render_ai_chat_page():
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

    # ── 快捷技能 ──
    sks = [
        ("大盘", "分析今日大盘走势"),
        ("新闻", "解读今天重要财经新闻"),
        ("持仓", "分析我的模拟盘持仓"),
        ("选股", "推荐3只关注股票"),
        ("技术", "详细技术分析该股"),
        ("风险", "评估该股风险"),
    ]
    for row in range(2):
        cols = st.columns(3)
        for i in range(3):
            idx = row * 3 + i
            if idx < len(sks):
                lbl, desc = sks[idx]
                with cols[i]:
                    if st.button(lbl, use_container_width=True, help=desc):
                        st.session_state["qq"] = desc
                        st.rerun()

    st.markdown("---")

    if "qq" in st.session_state:
        q = st.session_state.pop("qq")
        try:
            with st.spinner("分析中..."):
                ai.chat(q)
        except Exception as e:
            st.error(f"错误: {e}")
        st.rerun()

    for m in ai.get_history():
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
                st.markdown(ai.chat(u + ctx_str))
            if ai.get_last_tools_used():
                nm = {
                    "get_stock_quote": "行情", "get_technical_analysis": "技术",
                    "get_scoring_result": "评分", "get_market_snapshot": "大盘",
                    "get_news": "新闻", "get_positions": "持仓",
                }
                st.caption(" · ".join(nm.get(t, t) for t in ai.get_last_tools_used()))

    if ai.get_history():
        if st.button("清空对话"):
            ai.clear_history()
            st.rerun()


def _extract_code(text: str) -> str:
    import re
    m = re.search(r'\b(\d{6})\b', text)
    return m.group(1) if m else ""
