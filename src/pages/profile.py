"""我的 - Industrial"""

import streamlit as st
from src.config import get_setting, save_settings

def render_profile_page():
    st.markdown("## PROFILE")
    st.markdown("### STATS")
    try:
        from src.trading.engine import TradingEngine
        with TradingEngine() as e: s = e.get_stats()
    except: s = {}
    c1,c2,c3 = st.columns(3)
    c1.metric("TRADES", f"{s.get('total_trades',0)}", border=True)
    wr = s.get('win_rate',0)
    c2.metric("WIN%", f"{wr:.0%}" if s.get('total_trades') else "N/A", border=True)
    pl = s.get('profit_loss_ratio',0)
    c3.metric("P/L R", f"{pl:.2f}" if s.get('total_trades') else "N/A", border=True)

    st.markdown("---"); st.markdown("### AI CONFIG")
    cur_k = get_setting("api_key","DEEPSEEK_API_KEY","")
    cur_u = get_setting("base_url","DEEPSEEK_BASE_URL","https://api.deepseek.com")
    cur_m = get_setting("model","DEEPSEEK_MODEL","deepseek-chat")
    with st.form("cfg"):
        nk = st.text_input("API KEY", value=cur_k, type="password")
        nu = st.text_input("BASE URL", value=cur_u)
        nm = st.text_input("MODEL", value=cur_m)
        c1,c2 = st.columns(2)
        with c1:
            if st.form_submit_button("SAVE", use_container_width=True, type="primary"):
                save_settings({"api_key":nk,"base_url":nu,"model":nm})
                st.session_state.pop("aic",None); st.success("SAVED"); st.rerun()
        with c2:
            if st.form_submit_button("TEST"):
                if not nk: st.error("NEED KEY")
                else:
                    try:
                        from openai import OpenAI
                        cl = OpenAI(api_key=nk,base_url=nu)
                        r = cl.chat.completions.create(model=nm,messages=[{"role":"user","content":"hi"}],max_tokens=10)
                        st.success("OK")
                    except Exception as e: st.error(str(e))
    st.markdown("---")
    with st.expander("ABOUT"):
        st.markdown("**AlphaEye** v5 - A股反量化AI助手")
        st.markdown("`Python + Streamlit + 东方财富API + DeepSeek`")
        st.markdown("[GitHub](https://github.com/RyanTang-8175/ruiquant)")
    if st.button("EXIT"): st.session_state["logged_in"] = False; st.rerun()
