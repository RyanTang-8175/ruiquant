"""
AI 对话页面
"""

import streamlit as st
from src.ai.chat import AIChat


def render_ai_chat_page():
    """渲染 AI 对话页面"""
    st.markdown('<div class="main-header">🤖 AI 对话</div>', unsafe_allow_html=True)

    # 初始化 AI 对话
    if 'ai_chat' not in st.session_state:
        st.session_state.ai_chat = AIChat()

    ai = st.session_state.ai_chat

    # 快捷按钮
    st.markdown("**快捷操作**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📊 今日市场", use_container_width=True):
            st.session_state['quick_question'] = "帮我分析一下今天的市场整体情况"

    with col2:
        if st.button("🔍 观察池", use_container_width=True):
            st.session_state['quick_question'] = "今天观察池有哪些值得关注的股票？"

    with col3:
        if st.button("📈 帮我选股", use_container_width=True):
            st.session_state['quick_question'] = "帮我分析一下最近有什么好的投资机会"

    with col4:
        if st.button("📝 今日复盘", use_container_width=True):
            st.session_state['quick_question'] = "帮我做一个今日市场复盘"

    st.markdown("---")

    # 对话历史
    for msg in ai.get_history():
        with st.chat_message("user"):
            st.write(msg["question"])
        with st.chat_message("assistant"):
            st.write(msg["answer"])

    # 输入框
    user_input = st.chat_input("问 AI 任何股票问题...")

    # 处理快捷问题
    if 'quick_question' in st.session_state:
        user_input = st.session_state.pop('quick_question')

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = ai.chat(user_input)
                st.write(response)

    # 清空对话按钮
    if ai.get_history():
        st.markdown("---")
        if st.button("🗑️ 清空对话"):
            ai.clear_history()
            st.rerun()
