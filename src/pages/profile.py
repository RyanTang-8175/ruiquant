"""我的"""

import streamlit as st
from src.config import get_setting, save_settings

def render_profile_page():
    st.markdown("## 我的")

    st.subheader("交易统计")
    try:
        from src.trading.engine import TradingEngine
        with TradingEngine() as e: s = e.get_stats()
    except: s = {}
    c1,c2,c3 = st.columns(3)
    c1.metric("总交易", f"{s.get('total_trades',0)}笔", border=True)
    wr = s.get('win_rate',0)
    c2.metric("胜率", f"{wr:.0%}" if s.get('total_trades') else "N/A", border=True)
    pl = s.get('profit_loss_ratio',0)
    c3.metric("盈亏比", f"{pl:.2f}" if s.get('total_trades') else "N/A", border=True)

    st.markdown("---")
    st.subheader("AI 配置")
    st.caption("支持 DeepSeek / OpenAI / 智谱等兼容接口")

    cur_k = get_setting("api_key","DEEPSEEK_API_KEY","")
    cur_u = get_setting("base_url","DEEPSEEK_BASE_URL","https://api.deepseek.com")
    cur_m = get_setting("model","DEEPSEEK_MODEL","deepseek-chat")

    with st.form("cfg"):
        nk = st.text_input("API Key", value=cur_k, type="password")
        nu = st.text_input("API 地址", value=cur_u)
        nm = st.text_input("模型", value=cur_m)
        c1,c2 = st.columns(2)
        with c1:
            if st.form_submit_button("保存", use_container_width=True, type="primary"):
                save_settings({"api_key":nk,"base_url":nu,"model":nm})
                st.session_state.pop("aic",None)
                st.success("已保存"); st.rerun()
        with c2:
            if st.form_submit_button("测试"):
                if not nk: st.error("填 Key")
                else:
                    try:
                        from openai import OpenAI
                        cl = OpenAI(api_key=nk,base_url=nu)
                        r = cl.chat.completions.create(model=nm,messages=[{"role":"user","content":"hi"}],max_tokens=10)
                        st.success("连接成功")
                    except Exception as e: st.error(str(e))

    st.markdown("---")
    with st.expander("关于"):
        st.write("**RuiQuant** v4.1 · A股AI研究助手")
        st.write("Python + Streamlit + DeepSeek + 东方财富API")
        st.write("[GitHub](https://github.com/RyanTang-8175/ruiquant)")

    if st.button("退出"): st.session_state["logged_in"]=False; st.rerun()
