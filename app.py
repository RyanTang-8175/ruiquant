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

# 自定义样式（专业金融深色风格）
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

    .metric-card {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid #2D3748;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }

    .stock-up { color: #FF4444; font-weight: 600; }
    .stock-down { color: #00E676; font-weight: 600; }
    .stock-flat { color: #888888; }

    .score-high { color: #FF4444; font-size: 1.5rem; font-weight: 700; }
    .score-mid { color: #FFB800; font-size: 1.5rem; font-weight: 700; }
    .score-low { color: #888888; font-size: 1.5rem; font-weight: 700; }

    .rating-strong { background: #FF444422; color: #FF4444; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
    .rating-watch { background: #4488FF22; color: #4488FF; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
    .rating-neutral { background: #88888822; color: #888888; padding: 4px 12px; border-radius: 20px; font-weight: 600; }
    .rating-avoid { background: #33333322; color: #666666; padding: 4px 12px; border-radius: 20px; font-weight: 600; }

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
</style>
""", unsafe_allow_html=True)

# 侧边栏导航
st.sidebar.markdown("""
<div style="text-align: center; padding: 1rem 0;">
    <h1 style="color: #FF4444; margin: 0;">RuiQuant</h1>
    <p style="color: #888; font-size: 0.8rem;">A 股 AI 研究助手</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "导航",
    ["📊 市场概览", "🔍 选股", "🤖 AI 对话", "💰 模拟盘", "👤 我的"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; color: #666; font-size: 0.7rem;">
    v0.1.0 | 仅供研究学习
</div>
""", unsafe_allow_html=True)

# ============ 页面路由 ============

if page == "📊 市场概览":
    from src.pages.market import render_market_page
    render_market_page()

elif page == "🔍 选股":
    from src.pages.watchlist import render_watchlist_page
    render_watchlist_page()

elif page == "🤖 AI 对话":
    from src.pages.ai_chat import render_ai_chat_page
    render_ai_chat_page()

elif page == "💰 模拟盘":
    from src.pages.trading import render_trading_page
    render_trading_page()

elif page == "👤 我的":
    from src.pages.profile import render_profile_page
    render_profile_page()
