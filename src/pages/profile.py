"""
我的页面
"""

import streamlit as st
from src.config import DEEPSEEK_API_KEY, INITIAL_CAPITAL


def render_profile_page():
    """渲染我的页面"""
    st.markdown('<div class="main-header">👤 我的</div>', unsafe_allow_html=True)

    # AI 预测记录
    st.subheader("🤖 AI 预测记录")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总预测", "0 次")
    with col2:
        st.metric("命中率", "N/A")
    with col3:
        st.metric("平均收益", "N/A")
    st.caption("预测功能开发中...")

    st.markdown("---")

    # 交易统计
    st.subheader("📊 交易统计")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总交易", "0 笔")
    with col2:
        st.metric("胜率", "N/A")
    with col3:
        st.metric("盈亏比", "N/A")

    st.markdown("---")

    # 每日复盘
    st.subheader("📝 每日复盘")
    st.caption("复盘功能开发中...")

    st.markdown("---")

    # 设置
    st.subheader("⚙️ 设置")

    with st.expander("DeepSeek API 配置"):
        api_key = st.text_input("API Key", value=DEEPSEEK_API_KEY[:8] + "..." if DEEPSEEK_API_KEY else "", type="password")
        st.caption("在 .env 文件中配置 DEEPSEEK_API_KEY")

    with st.expander("模拟盘配置"):
        st.write(f"初始资金: ¥{INITIAL_CAPITAL:,.0f}")
        st.caption("在 .env 文件中配置 INITIAL_CAPITAL")

    with st.expander("关于"):
        st.write("**RuiQuant** - 个人 A 股 AI 研究助手")
        st.write("版本: v0.1.0")
        st.write("技术栈: Python + Streamlit + DeepSeek + AKShare")
        st.write("GitHub: https://github.com/RyanTang-8175/ruiquant")
        st.caption("仅供研究学习，不构成投资建议")
