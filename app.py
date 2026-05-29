"""
RuiQuant v4.0 - A 股 AI 研究助手
参考同花顺/东方财富设计风格
"""

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="RuiQuant - A 股 AI 研究助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== 专业金融风格 CSS ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif; }
.stApp { background: #0B0E14; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
.main .block-container { padding: 0.8rem 1.5rem; max-width: 1600px; }

/* 顶部导航 */
.top-bar {
    background: linear-gradient(180deg, #151923 0%, #0f1318 100%);
    padding: 0.6rem 1.2rem;
    border-radius: 0 0 12px 12px;
    border-bottom: 1px solid #1e2738;
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 0.8rem;
}

/* 导航按钮 */
.nav-tabs {
    display: flex; gap: 0.3rem;
    background: #0f1318;
    border-radius: 10px;
    padding: 0.3rem;
    border: 1px solid #1e2738;
}
.nav-tab {
    padding: 0.5rem 1.2rem;
    border-radius: 8px;
    font-size: 0.9rem;
    font-weight: 600;
    color: #6b7280;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
    background: transparent;
}
.nav-tab:hover { color: #E6EDF3; background: #1a1f2e; }
.nav-tab.active { color: #fff; background: linear-gradient(135deg, #FF4444, #e63939); }

/* 数据卡片 */
.data-card {
    background: linear-gradient(135deg, #151923 0%, #111620 100%);
    border: 1px solid #1e2738;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    transition: all 0.2s;
}
.data-card:hover { border-color: #2d3748; }
.data-card .label { color: #6b7280; font-size: 0.75rem; font-weight: 500; }
.data-card .value { color: #E6EDF3; font-size: 1.4rem; font-weight: 800; }
.data-card .value.up { color: #FF4444; }
.data-card .value.down { color: #00E676; }
.data-card .value.neutral { color: #888; }
.data-card .sub { font-size: 0.8rem; font-weight: 600; }

/* 指数条 */
.index-strip {
    display: flex; gap: 0.5rem;
    background: #111620;
    border-radius: 10px;
    padding: 0.6rem 1rem;
    border: 1px solid #1e2738;
    margin-bottom: 0.8rem;
}
.index-item {
    flex: 1; text-align: center;
    padding: 0.3rem;
    border-radius: 8px;
}
.index-item .name { color: #888; font-size: 0.75rem; }
.index-item .price { font-size: 1.1rem; font-weight: 800; }
.index-item .pct { font-size: 0.85rem; font-weight: 600; }

/* 股票列表行 */
.stock-row {
    display: flex; align-items: center;
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid #1a1f2e;
    transition: background 0.15s;
    cursor: pointer;
}
.stock-row:hover { background: #151923; }
.stock-row .rank { color: #4a5568; font-size: 0.8rem; width: 30px; text-align: center; }
.stock-row .info { flex: 1; margin-left: 0.5rem; }
.stock-row .name { color: #E6EDF3; font-weight: 600; font-size: 0.95rem; }
.stock-row .code { color: #4a5568; font-size: 0.75rem; }
.stock-row .price { text-align: right; font-weight: 700; font-size: 1rem; min-width: 80px; }
.stock-row .change { text-align: right; font-weight: 600; font-size: 0.9rem; min-width: 70px; }
.stock-row .vol { text-align: right; color: #6b7280; font-size: 0.8rem; min-width: 80px; }

/* 新闻行 */
.news-item {
    padding: 0.6rem 0;
    border-bottom: 1px solid #1a1f2e;
}
.news-item .title { color: #E6EDF3; font-size: 0.9rem; font-weight: 500; }
.news-item .meta { color: #4a5568; font-size: 0.75rem; margin-top: 0.2rem; }
.news-tag {
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 0.7rem; font-weight: 600;
    margin-right: 0.3rem;
}
.news-tag.hot { background: #FF444430; color: #FF4444; }
.news-tag.policy { background: #4488FF30; color: #4488FF; }
.news-tag.sector { background: #FFB80030; color: #FFB800; }

/* 搜索框 */
.search-box input {
    background: #151923 !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
    color: #E6EDF3 !important;
    font-size: 0.9rem !important;
}
.search-box input:focus { border-color: #FF4444 !important; }

/* 按钮 */
.stButton>button {
    border-radius: 8px; font-weight: 600;
    transition: all 0.2s;
}

/* 标签页 */
.stTabs [data-baseweb="tab-list"] { gap: 0; background: #111620; border-radius: 8px; padding: 0.2rem; }
.stTabs [data-baseweb="tab"] { border-radius: 6px; color: #6b7280; font-weight: 600; font-size: 0.85rem; }
.stTabs [aria-selected="true"] { color: #E6EDF3; background: #1a1f2e; }

/* 表格 */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* 分隔线 */
hr { border-color: #1a1f2e !important; margin: 0.6rem 0 !important; }

/* 标题 */
h1, h2, h3 { color: #E6EDF3; font-weight: 700; }
h2 { font-size: 1.2rem; }
h3 { font-size: 1rem; }

/* 隐藏 label */
[data-testid="stWidgetLabel"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ========== 登录检查 ==========
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    from src.pages.login import render_login_page
    render_login_page()
    st.stop()

# ========== 顶部导航 ==========
from src.config import get_setting
phone = get_setting("phone", "", "用户")

st.markdown(f"""
<div class="top-bar">
    <div style="display:flex;align-items:center;gap:0.8rem;">
        <span style="font-size:1.6rem;font-weight:900;color:#FF4444;">R</span>
        <span style="font-size:1.6rem;font-weight:900;color:#E6EDF3;">uiQuant</span>
        <span style="color:#4a5568;font-size:0.75rem;margin-left:0.3rem;">v4.0</span>
    </div>
    <div style="display:flex;align-items:center;gap:1rem;">
        <span style="color:#6b7280;font-size:0.8rem;">{phone}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 导航标签
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "market"
if "selected_stock" not in st.session_state:
    st.session_state["selected_stock"] = ""

nav_items = [
    ("market", "行情", "📈"),
    ("watchlist", "选股", "🔍"),
    ("ai_chat", "AI 助手", "🤖"),
    ("trading", "交易", "💰"),
    ("profile", "我的", "👤"),
]

nav_html = '<div class="nav-tabs">'
for page_id, label, icon in nav_items:
    is_active = st.session_state["current_page"] == page_id
    cls = "active" if is_active else ""
    nav_html += f'<div class="nav-tab {cls}">{icon} {label}</div>'
nav_html += '</div>'

st.markdown(nav_html, unsafe_allow_html=True)

# Streamlit 按钮（实际交互）
cols = st.columns(len(nav_items))
for i, (page_id, label, icon) in enumerate(nav_items):
    with cols[i]:
        if st.button(f"{icon} {label}", key=f"nav_{page_id}", use_container_width=True):
            st.session_state["current_page"] = page_id
            st.rerun()

# ========== 路由 ==========
current = st.session_state["current_page"]

if current == "market":
    from src.pages.market import render_market_page
    render_market_page()
elif current == "watchlist":
    from src.pages.watchlist import render_watchlist_page
    render_watchlist_page()
elif current == "stock_detail":
    code = st.session_state.get("selected_stock", "")
    if code:
        from src.pages.stock_detail import render_stock_detail_page
        render_stock_detail_page(code)
    else:
        st.warning("未选择股票")
elif current == "ai_chat":
    from src.pages.ai_chat import render_ai_chat_page
    render_ai_chat_page()
elif current == "trading":
    from src.pages.trading import render_trading_page
    render_trading_page()
elif current == "profile":
    from src.pages.profile import render_profile_page
    render_profile_page()
