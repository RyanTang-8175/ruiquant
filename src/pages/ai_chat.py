"""
AI 对话页面 — 专业金融分析助手
"""

import streamlit as st
from src.ai.chat import AIChat


def render_ai_chat_page():
    """渲染 AI 对话页面"""
    st.markdown('<div class="main-header">🤖 AI 分析助手</div>', unsafe_allow_html=True)

    # 初始化 AI
    if 'ai_chat' not in st.session_state:
        st.session_state['ai_chat'] = AIChat()

    ai = st.session_state['ai_chat']

    # 股票代码快速输入
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        stock_code = st.text_input("股票代码", placeholder="输入代码后点击快捷分析，如 600519", key="ai_stock_code")
    with col_btn:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        if st.button("📊 分析此股", key="analyze_stock_btn", use_container_width=True):
            if stock_code.strip():
                st.session_state['quick_question'] = f"请对 {stock_code.strip()} 做全面的技术面和消息面分析"
                st.rerun()
            else:
                st.warning("请输入股票代码")

    st.markdown("---")

    # 快捷操作按钮 - 第一行
    st.caption("快捷分析")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📊 今日市场", use_container_width=True):
            st.session_state['quick_question'] = "帮我分析一下今天的市场整体情况"
            st.rerun()
    with col2:
        if st.button("🔍 观察池", use_container_width=True):
            st.session_state['quick_question'] = "今天观察池有哪些值得关注的股票？"
            st.rerun()
    with col3:
        if st.button("📈 帮我选股", use_container_width=True):
            st.session_state['quick_question'] = "基于当前市场状态，推荐几只值得关注的股票"
            st.rerun()
    with col4:
        if st.button("📝 今日复盘", use_container_width=True):
            st.session_state['quick_question'] = "帮我做一个今日市场复盘"
            st.rerun()

    # 快捷操作按钮 - 第二行
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        if st.button("📰 新闻解读", use_container_width=True):
            st.session_state['quick_question'] = "解读今天的重大财经新闻对A股的影响"
            st.rerun()
    with col6:
        if st.button("💹 板块分析", use_container_width=True):
            st.session_state['quick_question'] = "分析当前热门板块和板块轮动趋势"
            st.rerun()
    with col7:
        if st.button("🎯 技术分析", use_container_width=True):
            if stock_code.strip():
                st.session_state['quick_question'] = f"对 {stock_code.strip()} 做详细的技术分析，包括均线、MACD、RSI"
                st.rerun()
            else:
                st.warning("请先输入股票代码")
    with col8:
        if st.button("💼 我的持仓", use_container_width=True):
            st.session_state['quick_question'] = "分析一下我的模拟盘持仓情况"
            st.rerun()

    st.markdown("---")

    # 处理快捷问题
    if 'quick_question' in st.session_state:
        question = st.session_state.pop('quick_question')
        try:
            with st.spinner("AI 分析中..."):
                ai.chat(question)
        except Exception as e:
            st.error(f"AI 响应失败: {e}")
        st.rerun()

    # 显示对话历史
    for msg in ai.get_history():
        with st.chat_message("user"):
            st.write(msg["question"])
        with st.chat_message("assistant"):
            st.write(msg["answer"])
            tools_used = msg.get("tools_used", [])
            if tools_used:
                tool_names = {
                    "get_stock_quote": "行情",
                    "get_technical_analysis": "技术指标",
                    "get_scoring_result": "量化评分",
                    "get_market_snapshot": "市场概况",
                    "get_watchlist": "观察池",
                    "get_news": "新闻",
                    "get_financial_data": "基本面",
                    "get_positions": "持仓",
                    "get_kline_data": "K线",
                }
                tags = [f"`{tool_names.get(t, t)}`" for t in tools_used]
                st.caption(f"🔧 使用了: {', '.join(tags)}")

    # 输入框
    if user_input := st.chat_input("问 AI 任何股票问题..."):
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = ai.chat(user_input)
            st.write(response)
            tools_used = ai.get_last_tools_used()
            if tools_used:
                tool_names = {
                    "get_stock_quote": "行情",
                    "get_technical_analysis": "技术指标",
                    "get_scoring_result": "量化评分",
                    "get_market_snapshot": "市场概况",
                    "get_watchlist": "观察池",
                    "get_news": "新闻",
                    "get_financial_data": "基本面",
                    "get_positions": "持仓",
                    "get_kline_data": "K线",
                }
                tags = [f"`{tool_names.get(t, t)}`" for t in tools_used]
                st.caption(f"🔧 使用了: {', '.join(tags)}")

    # 清空按钮
    if ai.get_history():
        st.markdown("---")
        if st.button("🗑️ 清空对话"):
            ai.clear_history()
            st.rerun()
