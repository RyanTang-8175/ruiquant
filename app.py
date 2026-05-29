"""
RuiQuant - 个人 A 股 AI 研究助手
Streamlit 主入口
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# 页面配置
st.set_page_config(
    page_title="RuiQuant - A 股 AI 研究助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# PWA 支持
st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="RuiQuant">
<link rel="apple-touch-icon" href="/static/icon.svg">
<meta name="theme-color" content="#0D1117">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
""", unsafe_allow_html=True)

# 自定义样式
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #FFFFFF;
        padding: 0.5rem 0;
        border-bottom: 2px solid #FF4444;
        margin-bottom: 1rem;
    }

    .stButton>button {
        background: linear-gradient(135deg, #FF4444 0%, #CC0000 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }

    .stButton>button:hover {
        background: linear-gradient(135deg, #FF6666 0%, #EE2222 100%);
    }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0D1117 0%, #161B22 100%);
    }

    div[data-testid="stSidebar"] .stRadio label {
        color: #E6EDF3;
    }

    /* 隐藏 Streamlit 默认菜单 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 侧边栏
st.sidebar.markdown("""
<div style="text-align: center; padding: 1rem 0;">
    <h1 style="color: #FF4444; margin: 0;">RuiQuant</h1>
    <p style="color: #888; font-size: 0.8rem;">A 股 AI 研究助手</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

# 页面路由
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'market'

# 导航选项
page = st.sidebar.radio(
    "导航",
    ["📊 市场概览", "🔍 选股", "🤖 AI 对话", "💰 模拟盘", "👤 我的"],
    label_visibility="collapsed",
    index=["market", "watchlist", "ai_chat", "trading", "profile"].index(st.session_state['current_page']) if st.session_state['current_page'] in ["market", "watchlist", "ai_chat", "trading", "profile"] else 0
)

# 更新当前页面
page_map = {
    "📊 市场概览": "market",
    "🔍 选股": "watchlist",
    "🤖 AI 对话": "ai_chat",
    "💰 模拟盘": "trading",
    "👤 我的": "profile"
}
st.session_state['current_page'] = page_map.get(page, "market")

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; color: #666; font-size: 0.7rem;">
    v0.1.0 | 仅供研究学习
</div>
""", unsafe_allow_html=True)

# 页面路由
current = st.session_state['current_page']

if current == "market":
    from src.pages.market import render_market_page
    render_market_page()

elif current == "watchlist":
    from src.pages.watchlist import render_watchlist_page
    render_watchlist_page()

elif current == "stock_detail":
    from src.pages.stock_detail import render_stock_detail_page
    code = st.session_state.get('selected_stock', '')
    if code:
        render_stock_detail_page(code)
    else:
        st.error("未选择股票")
        if st.button("返回观察池"):
            st.session_state['current_page'] = 'watchlist'
            st.rerun()

elif current == "ai_chat":
    from src.pages.ai_chat import render_ai_chat_page
    render_ai_chat_page()

elif current == "trading":
    from src.pages.trading import render_trading_page
    render_trading_page()

elif current == "profile":
    from src.pages.profile import render_profile_page
    render_profile_page()
