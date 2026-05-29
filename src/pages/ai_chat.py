"""
AI 助手 - 专业股票分析技能
"""

import streamlit as st
from src.ai.chat import AIChat


def render_ai_chat_page():
    st.markdown("## AI 分析助手")

    # 初始化
    if "ai_chat" not in st.session_state:
        st.session_state["ai_chat"] = AIChat()
    ai = st.session_state["ai_chat"]

    # 股票输入
    c1, c2 = st.columns([3, 1])
    with c1:
        stock_code = st.text_input("", placeholder="输入股票代码，如 600519", key="ai_code", label_visibility="collapsed")
    with c2:
        if st.button("分析该股", key="analyze", use_container_width=True, type="primary"):
            if stock_code.strip():
                st.session_state["quick_q"] = f"请对 {stock_code.strip()} 做全面分析"
                st.rerun()

    # 技能按钮
    st.markdown("### 分析技能")
    sk1, sk2, sk3, sk4 = st.columns(4)
    with sk1:
        if st.button("📊 今日大盘", use_container_width=True):
            st.session_state["quick_q"] = "分析今日大盘走势，包括三大指数、涨跌家数、成交额、市场情绪"
            st.rerun()
    with sk2:
        if st.button("📰 新闻解读", use_container_width=True):
            st.session_state["quick_q"] = "解读今天的重要财经新闻，分析对A股的影响"
            st.rerun()
    with sk3:
        if st.button("🔥 热门板块", use_container_width=True):
            st.session_state["quick_q"] = "分析当前热门板块和板块轮动趋势"
            st.rerun()
    with sk4:
        if st.button("💼 我的持仓", use_container_width=True):
            st.session_state["quick_q"] = "查看我的模拟盘持仓，逐只分析并给出操作建议"
            st.rerun()

    sk5, sk6, sk7, sk8 = st.columns(4)
    with sk5:
        if st.button("🎯 智能选股", use_container_width=True):
            st.session_state["quick_q"] = "基于当前市场状态，推荐3只值得关注的股票，说明理由"
            st.rerun()
    with sk6:
        if st.button("📈 技术分析", use_container_width=True):
            if stock_code.strip():
                st.session_state["quick_q"] = f"对 {stock_code.strip()} 做详细技术分析，包括K线形态、均线、MACD、RSI、支撑压力位"
            else:
                st.warning("请先输入代码")
            st.rerun()
    with sk7:
        if st.button("⚠️ 风险评估", use_container_width=True):
            if stock_code.strip():
                st.session_state["quick_q"] = f"评估 {stock_code.strip()} 的风险，包括基本面风险、技术面风险、行业风险"
            else:
                st.warning("请先输入代码")
            st.rerun()
    with sk8:
        if st.button("📝 复盘报告", use_container_width=True):
            st.session_state["quick_q"] = "生成今日市场复盘报告，包括大盘走势、板块轮动、情绪面、明日展望"
            st.rerun()

    st.markdown("---")

    # 处理快捷问题
    if "quick_q" in st.session_state:
        q = st.session_state.pop("quick_q")
        try:
            with st.spinner("分析中..."):
                ai.chat(q)
        except Exception as e:
            st.error(f"AI 失败: {e}")
        st.rerun()

    # 对话历史
    for msg in ai.get_history():
        with st.chat_message("user"):
            st.write(msg["question"])
        with st.chat_message("assistant"):
            st.write(msg["answer"])
            tools = msg.get("tools_used", [])
            if tools:
                names = {
                    "get_stock_quote":"行情","get_technical_analysis":"技术指标",
                    "get_scoring_result":"评分","get_market_snapshot":"市场概况",
                    "get_watchlist":"观察池","get_news":"新闻","get_financial_data":"基本面",
                    "get_positions":"持仓","get_kline_data":"K线",
                }
                tags = [f"`{names.get(t,t)}`" for t in tools]
                st.caption(f"工具: {', '.join(tags)}")

    # 输入
    if user_input := st.chat_input("问 AI 任何股票问题..."):
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                resp = ai.chat(user_input)
            st.write(resp)
            tools = ai.get_last_tools_used()
            if tools:
                names = {
                    "get_stock_quote":"行情","get_technical_analysis":"技术指标",
                    "get_scoring_result":"评分","get_market_snapshot":"市场概况",
                    "get_watchlist":"观察池","get_news":"新闻","get_financial_data":"基本面",
                    "get_positions":"持仓","get_kline_data":"K线",
                }
                tags = [f"`{names.get(t,t)}`" for t in tools]
                st.caption(f"工具: {', '.join(tags)}")

    # 清空
    if ai.get_history():
        if st.button("清空对话"):
            ai.clear_history()
            st.rerun()
