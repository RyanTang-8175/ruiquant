"""AI 助手 - Industrial"""

import streamlit as st
from src.ai.chat import AIChat

def render_ai_chat_page():
    st.markdown("## AI")
    if "aic" not in st.session_state: st.session_state["aic"] = AIChat()
    ai = st.session_state["aic"]

    c1, c2 = st.columns([3, 1])
    with c1: sc = st.text_input("", placeholder="输入代码 如 600519", key="ac", label_visibility="collapsed")
    with c2:
        if st.button("GO", key="az", use_container_width=True, type="primary"):
            if sc.strip(): st.session_state["qq"] = f"分析 {sc.strip()}"; st.rerun()

    st.markdown("### SKILLS")
    sks = [("MARKET","分析今日大盘走势"),("NEWS","解读今日重要新闻"),("POS","分析我的模拟持仓"),("PICK","推荐3只关注股票"),("TECH","技术分析该股"),("RISK","风险评估该股")]
    rows = [st.columns(3) for _ in range(2)]
    for i, (lbl, pmt) in enumerate(sks):
        with rows[i//3][i%3]:
            if st.button(lbl, use_container_width=True): st.session_state["qq"] = pmt; st.rerun()
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
            st.write(m["answer"])
            if m.get("tools_used"):
                nm = {"get_stock_quote":"Q","get_technical_analysis":"TECH","get_scoring_result":"SCORE","get_market_snapshot":"MKT","get_news":"NEWS","get_positions":"POS"}
                st.caption("TOOLS " + " ".join(nm.get(t,t) for t in m["tools_used"]))

    if u := st.chat_input("..."):
        with st.chat_message("user"): st.write(u)
        with st.chat_message("assistant"):
            with st.spinner("..."): st.write(ai.chat(u))
            if ai.get_last_tools_used():
                nm = {"get_stock_quote":"Q","get_technical_analysis":"TECH","get_scoring_result":"SCORE","get_market_snapshot":"MKT","get_news":"NEWS","get_positions":"POS"}
                st.caption("TOOLS " + " ".join(nm.get(t,t) for t in ai.get_last_tools_used()))

    if ai.get_history():
        if st.button("CLEAR"): ai.clear_history(); st.rerun()
