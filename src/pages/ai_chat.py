"""AI 助手"""

import streamlit as st
from src.ai.chat import AIChat

def render_ai_chat_page():
    if "aic" not in st.session_state: st.session_state["aic"] = AIChat()
    ai = st.session_state["aic"]

    c1, c2 = st.columns([4, 1])
    with c1:
        sc = st.text_input("", placeholder="输入代码...", key="ac", label_visibility="collapsed")
    with c2:
        if st.button("GO", key="az", use_container_width=True, type="primary"):
            if sc.strip(): st.session_state["qq"] = f"分析 {sc.strip()}"; st.rerun()

    sks = [("大盘","分析今日大盘走势"),("新闻","解读今天重要财经新闻"),("持仓","分析我的模拟盘持仓"),("选股","推荐3只关注股票"),("技术","详细技术分析该股"),("风险","评估该股风险")]
    for row in range(2):
        cols = st.columns(3)
        for i in range(3):
            idx = row*3+i
            if idx < len(sks):
                lbl, desc = sks[idx]
                with cols[i]:
                    if st.button(lbl, use_container_width=True, help=desc):
                        st.session_state["qq"] = desc; st.rerun()

    st.markdown("---")

    if "qq" in st.session_state:
        q = st.session_state.pop("qq")
        try:
            with st.spinner("..."): ai.chat(q)
        except Exception as e: st.error(f"ERR: {e}")
        st.rerun()

    for m in ai.get_history():
        with st.chat_message("user"): st.write(m["question"])
        with st.chat_message("assistant"):
            st.markdown(m["answer"])  # markdown renders cleaner
            if m.get("tools_used"):
                nm = {"get_stock_quote":"Q","get_technical_analysis":"TECH","get_scoring_result":"SCORE","get_market_snapshot":"MKT","get_news":"NEWS","get_positions":"POS"}
                st.caption(" ".join(nm.get(t,t) for t in m["tools_used"]))

    if u := st.chat_input("..."):
        with st.chat_message("user"): st.write(u)
        with st.chat_message("assistant"):
            with st.spinner("..."): st.markdown(ai.chat(u))
            if ai.get_last_tools_used():
                nm = {"get_stock_quote":"Q","get_technical_analysis":"TECH","get_scoring_result":"SCORE","get_market_snapshot":"MKT","get_news":"NEWS","get_positions":"POS"}
                st.caption(" ".join(nm.get(t,t) for t in ai.get_last_tools_used()))

    if ai.get_history():
        if st.button("清空"): ai.clear_history(); st.rerun()
