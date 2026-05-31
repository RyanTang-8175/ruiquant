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

    # ── 初始化 ──
    if "aic" not in st.session_state:
        ai = AIChat()
        ai.load_from_disk()
        st.session_state["aic"] = ai
        st.session_state["ai_title"] = ""
    ai = st.session_state["aic"]

    # ── 对话标题 ──
    ct_key = "ai_title"
    if ct_key not in st.session_state:
        st.session_state[ct_key] = ""
    title = st.text_input(
        "对话名称", value=st.session_state[ct_key],
        placeholder="可选：给当前对话起个名字",
        key="ai_title_input", label_visibility="collapsed",
    )
    if title != st.session_state[ct_key]:
        st.session_state[ct_key] = title

    st.markdown("---")

    # ── 快捷操作 2x2 ──
    actions = [
        ("审查风险", "请审查这只股票的反量化风险和短线风险"),
        ("持股预测", "判断这只股票适合隔夜、1-2天还是2-3天持有"),
        ("今日选股", "根据六维评分，今天哪些股票值得关注"),
        ("复盘交易", "请复盘我最近的模拟交易表现"),
    ]
    for row in range(2):
        cols = st.columns(2)
        for i in range(2):
            idx = row * 2 + i
            if idx < len(actions):
                lbl, desc = actions[idx]
                with cols[i]:
                    if st.button(lbl, key=f"qa_{idx}", use_container_width=True,
                                 help=desc):
                        st.session_state["qq"] = desc
                        st.rerun()

    st.markdown("---")

    # ── 快捷提问 ──
    if "qq" in st.session_state:
        q = st.session_state.pop("qq")
        try:
            with st.spinner("分析中..."):
                ai.chat(q)
                # 自动生成标题
                if not st.session_state.get(ct_key):
                    short = q[:20] + ("..." if len(q) > 20 else "")
                    st.session_state[ct_key] = short
        except Exception as e:
            st.error(f"错误: {e}")
        st.rerun()

    # ── 对话历史 ──
    history = ai.get_history()
    if history:
        for i, m in enumerate(history[-12:]):
            role = "user"
            content = m.get("question", str(m))
            answer = m.get("answer", "")

            # 用户消息
            st.markdown(
                f'<div style="background:rgba(77,141,255,0.06);border-radius:10px;'
                f'padding:8px 12px;margin:2px 0 8px 8px;font-size:14px;'
                f'color:var(--text);line-height:1.5">{content}</div>',
                unsafe_allow_html=True,
            )

            # AI 回复
            st.markdown(
                f'<div style="background:var(--card);border:1px solid var(--border);'
                f'border-radius:10px;padding:10px 14px;margin:2px 0 8px 0;'
                f'font-size:14px;color:var(--text);line-height:1.6;word-break:break-word">'
                f'{_fmt(answer)}</div>',
                unsafe_allow_html=True,
            )

            # 工具使用
            tools = m.get("tools_used", [])
            if tools:
                nm = {"get_stock_quote": "行情", "get_technical_analysis": "技术",
                      "get_scoring_result": "评分", "get_market_snapshot": "大盘",
                      "get_news": "新闻", "get_positions": "持仓",
                      "get_kline_data": "K线", "get_watchlist": "选股",
                      "get_financial_data": "财务"}
                st.caption(" · ".join(nm.get(t, t) for t in tools))
    else:
        st.info("输入股票代码或点击快捷操作开始对话")

    # ── 输入区 ──
    u = st.chat_input("输入股票代码或问题，如「分析 600519 风险」")
    if u:
        with st.spinner("分析中..."):
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
            ai.chat(u + ctx_str)
            if not st.session_state.get(ct_key):
                st.session_state[ct_key] = u[:20] + ("..." if len(u) > 20 else "")
            st.rerun()

    # ── 底部操作 ──
    if history:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("清空对话", use_container_width=True):
                ai.clear_history()
                st.session_state[ct_key] = ""
                st.rerun()
        with c2:
            if st.button("保存对话", use_container_width=True, type="primary"):
                ai.save_to_disk()
                st.success("已保存")


def _extract_code(text: str) -> str:
    import re
    m = re.search(r'\b(\d{6})\b', text)
    return m.group(1) if m else ""


def _fmt(text: str) -> str:
    """预处理 AI 回复中的 markdown 表格，确保移动端可滚动"""
    import re
    # 给表格加 wrapper
    if "|---" in text:
        lines = text.split("\n")
        out = []
        in_table = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and "|" in stripped[1:]:
                if not in_table:
                    out.append('<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;margin:8px 0">')
                    in_table = True
                out.append(line)
            else:
                if in_table:
                    out.append('</div>')
                    in_table = False
                out.append(line)
        if in_table:
            out.append('</div>')
        text = "\n".join(out)
    return text
