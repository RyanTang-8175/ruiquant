"""AI 助手"""

import streamlit as st
from src.ai.chat import AIChat

def render_ai_chat_page():
    st.markdown("## AI 分析助手")

    if "aic" not in st.session_state: st.session_state["aic"] = AIChat()
    ai = st.session_state["aic"]

    c1, c2 = st.columns([3, 1])
    with c1:
        sc = st.text_input("", placeholder="输入股票代码如 600519", key="aicode", label_visibility="collapsed")
    with c2:
        if st.button("分析", key="alz", use_container_width=True, type="primary"):
            if sc.strip():
                st.session_state["qq"] = f"请对 {sc.strip()} 做全面分析"
                st.rerun()

    st.markdown("### 技能")
    sks = [
        ("📊 看大盘","分析今日大盘走势，包括指数、涨跌比、成交额和市场情绪"),
        ("📰 读新闻","解读今天的重要财经新闻，分析对A股的影响"),
        ("💼 看持仓","查看我的模拟盘持仓，逐只分析并给出操作建议"),
        ("🎯 选股","基于当前市场状态，推荐3只值得关注的股票"),
        ("📈 技术分析","对该股做详细技术分析，含K线形态、均线、MACD、RSI、支撑压力位"),
        ("⚠️ 风险评估","评估该股风险，含基本面、技术面、行业风险"),
    ]
    rows = [st.columns(3) for _ in range(2)]
    for i, (label, prompt) in enumerate(sks):
        with rows[i//3][i%3]:
            if st.button(label, use_container_width=True):
                st.session_state["qq"] = prompt
                st.rerun()

    st.markdown("---")

    if "qq" in st.session_state:
        q = st.session_state.pop("qq")
        try:
            with st.spinner("分析中..."): ai.chat(q)
        except Exception as e:
            st.error(f"AI失败: {e}")
        st.rerun()

    for msg in ai.get_history():
        with st.chat_message("user"): st.write(msg["question"])
        with st.chat_message("assistant"):
            st.write(msg["answer"])
            tools = msg.get("tools_used",[])
            if tools:
                nm = {"get_stock_quote":"行情","get_technical_analysis":"技术","get_scoring_result":"评分","get_market_snapshot":"大盘","get_news":"新闻","get_positions":"持仓"}
                st.caption(" 🔧 " + " · ".join(f"`{nm.get(t,t)}`" for t in tools))

    if u := st.chat_input("问 AI ..."):
        with st.chat_message("user"): st.write(u)
        with st.chat_message("assistant"):
            with st.spinner("思考中..."): st.write(ai.chat(u))
            tools = ai.get_last_tools_used()
            if tools:
                nm = {"get_stock_quote":"行情","get_technical_analysis":"技术","get_scoring_result":"评分","get_market_snapshot":"大盘","get_news":"新闻","get_positions":"持仓"}
                st.caption(" 🔧 " + " · ".join(f"`{nm.get(t,t)}`" for t in tools))

    if ai.get_history():
        if st.button("清空"): ai.clear_history(); st.rerun()
