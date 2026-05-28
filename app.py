"""
RuiQuant - 个人 A 股 AI 研究助手
Streamlit 主入口
"""

import streamlit as st
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="RuiQuant - A 股 AI 研究助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #FF4444;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        background-color: #1E1E1E;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #333;
    }
    .stock-up { color: #FF4444; }
    .stock-down { color: #00AA00; }
</style>
""", unsafe_allow_html=True)

# 侧边栏导航
st.sidebar.title("RuiQuant")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "导航",
    ["📊 市场概览", "🔍 选股", "🤖 AI 对话", "💰 模拟盘", "👤 我的"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("v0.1.0")

# 页面路由
if page == "📊 市场概览":
    st.markdown('<div class="main-header">市场概览</div>', unsafe_allow_html=True)
    st.info("🚧 开发中...")

elif page == "🔍 选股":
    st.markdown('<div class="main-header">选股</div>', unsafe_allow_html=True)
    st.info("🚧 开发中...")

elif page == "🤖 AI 对话":
    st.markdown('<div class="main-header">AI 对话</div>', unsafe_allow_html=True)
    st.info("🚧 开发中...")

elif page == "💰 模拟盘":
    st.markdown('<div class="main-header">模拟盘</div>', unsafe_allow_html=True)
    st.info("🚧 开发中...")

elif page == "👤 我的":
    st.markdown('<div class="main-header">我的</div>', unsafe_allow_html=True)
    st.info("🚧 开发中...")
