"""
登录页面 - 手机号+密码 + API Key 配置
"""

import streamlit as st
from src.config import save_settings, get_setting


def render_login_page():
    """渲染登录页"""
    st.markdown("""
    <div style="text-align:center;padding:2rem 0;">
        <span style="font-size:3rem;font-weight:800;color:#FF4444;">R</span>
        <span style="font-size:3rem;font-weight:800;color:#E6EDF3;">uiQuant</span>
        <div style="color:#6b7280;margin-top:0.5rem;">A 股 AI 研究助手</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 登录")

        with st.form("login_form"):
            phone = st.text_input("手机号", placeholder="请输入手机号")
            password = st.text_input("密码", type="password", placeholder="请输入密码")

            st.markdown("---")
            st.markdown("#### AI 模型配置")
            st.caption("首次登录请填写 API Key，之后可在「我的」页面修改")

            api_key = st.text_input("API Key", type="password", placeholder="DeepSeek / OpenAI API Key")
            base_url = st.text_input("API 地址", value=get_setting("base_url", "DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
            model = st.text_input("模型名称", value=get_setting("model", "DEEPSEEK_MODEL", "deepseek-chat"))

            submitted = st.form_submit_button("登录", use_container_width=True, type="primary")

            if submitted:
                if not phone or not password:
                    st.error("请输入手机号和密码")
                elif not api_key:
                    st.error("请填写 API Key")
                else:
                    # 保存配置
                    save_settings({
                        "phone": phone,
                        "api_key": api_key,
                        "base_url": base_url,
                        "model": model,
                    })
                    # 标记已登录
                    st.session_state["logged_in"] = True
                    st.session_state["phone"] = phone
                    st.rerun()

        st.markdown("---")
        st.caption("首次使用：输入手机号+任意密码即可注册")
        st.caption("已有账号：输入手机号+密码登录")
