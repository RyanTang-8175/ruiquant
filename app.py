"""
RuiQuant - 个人 A 股 AI 研究助手
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

# CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .stApp { background: #0A0E17; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    .main .block-container { padding: 1rem 2rem; max-width: 1400px; }
    .stButton>button {
        background: linear-gradient(135deg, #FF4444 0%, #e63939 100%);
        color: white; border: none; border-radius: 8px;
        padding: 0.5rem 1.2rem; font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #FF6666 0%, #FF4444 100%);
        box-shadow: 0 4px 15px rgba(255, 68, 68, 0.3);
    }
    hr { border-color: #1e2738; margin: 1rem 0; }
    h1, h2, h3 { color: #E6EDF3; font-weight: 700; }
    h2 { font-size: 1.3rem; }
    h3 { font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# 登录检查
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    from src.pages.login import render_login_page
    render_login_page()
    st.stop()

# 已登录 - 显示主界面
from src.config import get_setting

# 顶部导航
phone = get_setting("phone", "", "用户")
st.markdown(f"""
<div style="background:linear-gradient(135deg,#1a1f2e,#0d1117);padding:0.8rem 1.5rem;border-radius:12px;border:1px solid #1e2738;display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
    <div>
        <span style="font-size:1.4rem;font-weight:800;color:#FF4444;">R</span>
        <span style="font-size:1.4rem;font-weight:800;color:#E6EDF3;">uiQuant</span>
        <span style="color:#6b7280;margin-left:0.5rem;font-size:0.85rem;">A 股 AI 研究助手</span>
    </div>
    <div style="display:flex;gap:1rem;align-items:center;">
        <span style="color:#6b7280;font-size:0.8rem;">{phone}</span>
        <span style="color:#6b7280;font-size:0.75rem;">v3.0</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 启动定时任务
@st.cache_resource
def _start_scheduler():
    try:
        from src.scheduler import create_scheduler
        return create_scheduler()
    except Exception:
        return None

_start_scheduler()

# 路由
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "market"
if "selected_stock" not in st.session_state:
    st.session_state["selected_stock"] = ""

# 导航栏
nav_items = [
    ("market", "行情"),
    ("watchlist", "选股"),
    ("ai_chat", "AI"),
    ("trading", "交易"),
    ("profile", "我的"),
]

cols = st.columns(len(nav_items))
for i, (page_id, label) in enumerate(nav_items):
    with cols[i]:
        is_active = st.session_state["current_page"] == page_id
        btn_type = "primary" if is_active else "secondary"
        if st.button(label, key=f"nav_{page_id}", use_container_width=True, type=btn_type):
            st.session_state["current_page"] = page_id
            st.rerun()

st.markdown("---")

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
