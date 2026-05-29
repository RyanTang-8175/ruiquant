"""
RuiQuant - 个人 A 股 AI 研究助手
专业金融风格 UI
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# 页面配置
st.set_page_config(
    page_title="RuiQuant - A 股 AI 研究助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 专业金融风格 CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        box-sizing: border-box;
    }

    /* 全局背景 */
    .stApp {
        background: #0a0e17;
    }

    /* 隐藏默认元素 */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* 主容器 */
    .main .block-container {
        padding: 1rem 2rem;
        max-width: 1400px;
    }

    /* 顶部导航栏 */
    .top-nav {
        background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
        padding: 1rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid #1e2738;
    }

    /* 指标卡片 */
    .metric-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #151b28 100%);
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid #1e2738;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        border-color: #FF4444;
        box-shadow: 0 4px 20px rgba(255, 68, 68, 0.1);
    }

    /* 股票卡片 */
    .stock-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #151b28 100%);
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid #1e2738;
        margin-bottom: 0.8rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .stock-card:hover {
        border-color: #FF4444;
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }

    /* 评分徽章 */
    .score-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        font-size: 1.4rem;
        font-weight: 700;
    }
    .score-high { background: #FF444420; color: #FF4444; border: 2px solid #FF4444; }
    .score-mid { background: #FFB80020; color: #FFB800; border: 2px solid #FFB800; }
    .score-low { background: #88888820; color: #888888; border: 2px solid #888888; }

    /* 评级标签 */
    .rating-tag {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .rating-strong { background: #FF4444; color: white; }
    .rating-watch { background: #4488FF; color: white; }
    .rating-neutral { background: #FFB800; color: #000; }
    .rating-avoid { background: #555; color: #aaa; }

    /* 价格显示 */
    .price-up { color: #FF4444; font-weight: 700; }
    .price-down { color: #00E676; font-weight: 700; }
    .price-flat { color: #888; }

    /* 按钮样式 */
    .stButton>button {
        background: linear-gradient(135deg, #FF4444 0%, #e63939 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #FF6666 0%, #FF4444 100%);
        box-shadow: 0 4px 15px rgba(255, 68, 68, 0.3);
    }

    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #1a1f2e 100%);
        border-right: 1px solid #1e2738;
    }

    /* 表格样式 */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }

    /* 指标文字 */
    .metric-label {
        color: #6b7280;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .metric-value {
        color: #E6EDF3;
        font-size: 1.6rem;
        font-weight: 700;
    }

    /* 分隔线 */
    hr {
        border-color: #1e2738;
        margin: 1.5rem 0;
    }

    /* 页面标题 */
    .main-header {
        font-size: 1.8rem;
        font-weight: 800;
        color: #E6EDF3;
        margin-bottom: 1rem;
    }

    /* 标题样式 */
    h1, h2, h3 {
        color: #E6EDF3;
        font-weight: 700;
    }
    h1 { font-size: 1.8rem; }
    h2 { font-size: 1.4rem; }
    h3 { font-size: 1.1rem; }

    /* 输入框 */
    .stTextInput>div>div>input {
        background: #1a1f2e;
        color: #E6EDF3;
        border: 1px solid #1e2738;
        border-radius: 8px;
    }

    /* 选择框 */
    .stSelectbox>div>div {
        background: #1a1f2e;
        color: #E6EDF3;
        border: 1px solid #1e2738;
        border-radius: 8px;
    }

    /* 滑块 */
    .stSlider>div>div>div {
        color: #FF4444;
    }

    /* 标签页 */
    .stTabs>div>div>div>div {
        background: #1a1f2e;
        border-radius: 8px 8px 0 0;
    }
</style>
""", unsafe_allow_html=True)

# 启动定时任务调度器
@st.cache_resource
def _start_scheduler():
    try:
        from src.scheduler import create_scheduler
        return create_scheduler()
    except Exception as e:
        return None

_start_scheduler()

# 顶部导航
st.markdown("""
<div class="top-nav">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <span style="font-size: 1.5rem; font-weight: 800; color: #FF4444;">R</span>
            <span style="font-size: 1.5rem; font-weight: 800; color: #E6EDF3;">uiQuant</span>
            <span style="color: #6b7280; margin-left: 0.5rem; font-size: 0.9rem;">A 股 AI 研究助手</span>
        </div>
        <div style="display: flex; gap: 1rem;">
            <span style="color: #6b7280; font-size: 0.8rem;">v0.1.0</span>
            <span style="color: #6b7280; font-size: 0.8rem;">仅供研究</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 页面状态
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'market'

# 底部导航栏（移动端友好）
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("📊 市场", use_container_width=True, key="nav_market"):
        st.session_state['current_page'] = 'market'
        st.rerun()

with col2:
    if st.button("🔍 选股", use_container_width=True, key="nav_watchlist"):
        st.session_state['current_page'] = 'watchlist'
        st.rerun()

with col3:
    if st.button("🤖 AI", use_container_width=True, key="nav_ai"):
        st.session_state['current_page'] = 'ai_chat'
        st.rerun()

with col4:
    if st.button("💰 交易", use_container_width=True, key="nav_trading"):
        st.session_state['current_page'] = 'trading'
        st.rerun()

with col5:
    if st.button("👤 我的", use_container_width=True, key="nav_profile"):
        st.session_state['current_page'] = 'profile'
        st.rerun()

st.markdown("---")

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

elif current == "ai_chat":
    from src.pages.ai_chat import render_ai_chat_page
    render_ai_chat_page()

elif current == "trading":
    from src.pages.trading import render_trading_page
    render_trading_page()

elif current == "profile":
    from src.pages.profile import render_profile_page
    render_profile_page()
