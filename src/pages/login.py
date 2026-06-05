"""AlphaEye 登录"""

import streamlit as st
from src.config import save_settings, get_setting

def render_login_page():
    _,c,_=st.columns([1,1.2,1])
    with c:
        st.markdown('<div style="text-align:center;padding:3rem 0 1rem;"><div style="font-family:JetBrains Mono,monospace;font-size:3rem;font-weight:800;color:#246BFE;letter-spacing:-1px;">A<span style="color:#17212F;font-weight:750;">lphaEye</span></div><p style="color:#5D6B7C;font-size:.85rem;font-family:JetBrains Mono,monospace;text-transform:uppercase;letter-spacing:1px;">A 股反量化 AI 助手</p></div>',unsafe_allow_html=True)
        with st.form("f"):
            ph=st.text_input("手机号",placeholder="手机号")
            pw=st.text_input("密码",type="password",placeholder="密码")
            st.markdown("---")
            st.caption("AI 模型")
            ky=st.text_input("API Key",type="password",placeholder="sk-...")
            ur=st.text_input("API 地址",value=get_setting("base_url","DEEPSEEK_BASE_URL","https://api.deepseek.com"))
            md=st.text_input("模型",value=get_setting("model","DEEPSEEK_MODEL","deepseek-chat"))
            if st.form_submit_button("ENTER",use_container_width=True,type="primary"):
                if not ph or not pw:st.error("请输入手机号和密码")
                elif not ky:st.error("请填写 API Key")
                else:
                    save_settings({"phone":ph,"api_key":ky,"base_url":ur,"model":md})
                    st.session_state["logged_in"]=True
                    st.rerun()
        st.caption("首次使用自动注册 - 已有账号直接登录")
