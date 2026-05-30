"""登录页"""

import streamlit as st
from src.config import save_settings, get_setting


def render_login_page():
    _, c, _ = st.columns([1, 1.2, 1])

    with c:
        st.markdown("""
        <div style="text-align:center;padding:3rem 0 1rem;">
            <span style="font-size:3.5rem;font-weight:900;color:#f53b47;">R</span>
            <span style="font-size:3.5rem;font-weight:900;color:#e8ecf1;">uiQuant</span>
            <p style="color:#6b7388;font-size:0.9rem;">A 股 AI 研究助手</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("f"):
            phone = st.text_input("手机号", placeholder="输入手机号")
            pwd = st.text_input("密码", type="password", placeholder="输入密码")
            st.markdown("---")
            st.caption("AI 模型配置")
            key = st.text_input("API Key", type="password", placeholder="sk-...")
            url = st.text_input("API 地址", value=get_setting("base_url","DEEPSEEK_BASE_URL","https://api.deepseek.com"))
            model = st.text_input("模型", value=get_setting("model","DEEPSEEK_MODEL","deepseek-chat"))

            if st.form_submit_button("登录", use_container_width=True, type="primary"):
                if not phone or not pwd:
                    st.error("请输入手机号和密码")
                elif not key:
                    st.error("请填写 API Key")
                else:
                    save_settings({"phone":phone,"api_key":key,"base_url":url,"model":model})
                    st.session_state["logged_in"] = True
                    st.rerun()

        st.caption("首次使用自动注册 · 已有账号直接登录")
