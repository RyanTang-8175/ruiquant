"""我的"""

import streamlit as st
from src.config import get_setting, save_settings


def render_profile_page():
    st.markdown('<div class="sec-h">账户</div>', unsafe_allow_html=True)
    try:
        from src.trading.engine import TradingEngine
        with TradingEngine() as e: s = e.get_stats()
    except: s = {}
    c1, c2, c3 = st.columns(3)
    c1.metric("交易", s.get("total_trades", 0))
    wr = s.get("win_rate", 0)
    c2.metric("胜率", f"{wr:.0%}" if s.get("total_trades") else "-")
    pl = s.get("profit_loss_ratio", 0)
    c3.metric("盈亏比", f"{pl:.2f}" if s.get("total_trades") else "-")

    st.markdown('<div class="sec-h">偏好</div>', unsafe_allow_html=True)
    try:
        from src.memory.user_profile import get_profile
        p = get_profile()
        style = st.radio("风格", ["自动","激进","稳健","保守"],
                         index=["自动","激进","稳健","保守"].index(p.get("style","自动")),
                         horizontal=True, key="pf_st")
        if style != p.get("style"): p.set("style", style); st.rerun()
        cap = st.text_input("资金", value=p.get("capital",""), placeholder="如：1万", key="pf_cp")
        if cap != p.get("capital",""): p.set("capital", cap); st.rerun()
        top = p.top_stocks(5)
        if top:
            st.caption("常看: " + " | ".join(f"{n}({c})" for c, n, _ in top))
    except: pass

    st.markdown('<div class="sec-h">AI 配置</div>', unsafe_allow_html=True)
    cur_k = get_setting("api_key","DEEPSEEK_API_KEY","")
    cur_u = get_setting("base_url","DEEPSEEK_BASE_URL","https://api.deepseek.com")
    cur_m = get_setting("model","DEEPSEEK_MODEL","deepseek-chat")
    with st.form("cfg"):
        nk = st.text_input("API Key", value=cur_k, type="password", placeholder="sk-...")
        nu = st.text_input("Base URL", value=cur_u)
        nm = st.text_input("Model", value=cur_m)
        if st.form_submit_button("保存", use_container_width=True, type="primary"):
            save_settings({"api_key":nk,"base_url":nu,"model":nm,
                           "phone":get_setting("phone","","")})
            st.success("已保存"); st.rerun()

    if st.button("退出登录", use_container_width=True):
        save_settings({"phone":"","api_key":"","base_url":"","model":""})
        st.session_state["logged_in"] = False; st.rerun()
