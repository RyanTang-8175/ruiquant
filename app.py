"""
RuiQuant v4.1 — 个人 A 股 AI 研究助手
"""

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="RuiQuant · A股AI研究助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========  专业金融风格 CSS ========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;700;900&display=swap');

:root {
    --bg: #0a0d14;
    --card: #131721;
    --border: #1f2534;
    --text: #e8ecf1;
    --muted: #6b7388;
    --red: #f53b47;
    --green: #00b468;
    --amber: #f0a030;
    --blue: #3399ff;
}
* { font-family: 'Inter', 'Noto Sans SC', sans-serif; }

.stApp { background: var(--bg); }
.stApp > header { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
section[data-testid="stSidebar"] { display: none; }
.main .block-container { padding: 0.6rem 1.2rem; max-width: 1400px; }

/* 顶部导航 */
.topbar {
    background: linear-gradient(180deg, #111620 0%, #0d1117 100%);
    border-bottom: 1px solid var(--border);
    padding: 0.5rem 1rem;
    display: flex; justify-content: space-between; align-items: center;
}

/* 底部 Tab */
.tab-bar {
    display: flex; gap: 0; background: #0f131a;
    border: 1px solid var(--border); border-radius: 10px;
    overflow: hidden; margin: 0.5rem 0;
}
.tab-item {
    flex: 1; text-align: center; padding: 0.5rem 0;
    font-size: 0.82rem; font-weight: 600; color: var(--muted);
    cursor: pointer; transition: all 0.15s; border-bottom: 2px solid transparent;
}
.tab-item:hover { color: var(--text); background: #181c28; }
.tab-item.active { color: #fff; background: linear-gradient(135deg, var(--red), #e0303a); }

/* 指数卡片 */
.index-bar { display: flex; gap: 0.5rem; margin: 0.5rem 0; overflow-x: auto; }
.idx-card {
    flex: 1; min-width: 140px; background: var(--card);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 0.8rem 1rem; text-align: center;
}
.idx-card .idx-name { color: var(--muted); font-size: 0.72rem; }
.idx-card .idx-price { font-size: 1.3rem; font-weight: 800; margin: 0.2rem 0; }
.idx-card .idx-chg { font-size: 0.85rem; font-weight: 600; }

/* 股票行 */
.stock-line {
    display: flex; align-items: center; padding: 0.5rem 0.7rem;
    background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; margin-bottom: 0.3rem;
}
.stock-line:hover { background: #181c28; border-color: #3a4455; }
.stock-line .rk { color: var(--muted); font-size: 0.78rem; width: 28px; text-align: center; font-weight: 600; }
.stock-line .inf { flex: 1; margin-left: 0.4rem; }
.stock-line .nm { color: var(--text); font-weight: 600; font-size: 0.92rem; }
.stock-line .cd { color: var(--muted); font-size: 0.7rem; margin-left: 0.3rem; }
.stock-line .pr { font-weight: 700; font-size: 0.95rem; min-width: 75px; text-align: right; }
.stock-line .ch { font-weight: 600; font-size: 0.85rem; min-width: 65px; text-align: right; }

/* 新闻 */
.news-line { padding: 0.5rem 0; border-bottom: 1px solid var(--border); }
.news-line .nt { color: var(--text); font-size: 0.88rem; }
.news-line .nm { color: var(--muted); font-size: 0.72rem; margin-top: 0.15rem; }
.news-badge {
    display: inline-block; padding: 1px 5px; border-radius: 3px;
    font-size: 0.68rem; font-weight: 600; margin-right: 0.3rem;
}

/* 按钮 */
.stButton > button {
    border-radius: 7px; font-weight: 600; font-size: 0.85rem;
    padding: 0.4rem 1rem; transition: all 0.15s; border: none;
}
.stButton > button[kind="primary"] { background: var(--red); color: #fff; }
.stButton > button[kind="primary"]:hover { background: #ff5555; }
.stButton > button[kind="secondary"] {
    background: var(--card); color: var(--muted); border: 1px solid var(--border);
}
.stButton > button[kind="secondary"]:hover { color: var(--text); }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; background: var(--card); border-radius: 8px;
    padding: 0.2rem; border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px; color: var(--muted); font-weight: 600; font-size: 0.82rem;
}
.stTabs [aria-selected="true"] { color: #fff; background: var(--red); }

/* Input */
.stTextInput input {
    background: var(--card) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text) !important; font-size: 0.9rem !important;
}
.stTextInput input:focus { border-color: var(--red) !important; }

/* Metric */
[data-testid="stMetric"] {
    background: var(--card); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.6rem !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: var(--card) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; margin: 0.3rem 0 !important;
}

hr { border-color: var(--border) !important; margin: 0.5rem 0 !important; }
h2 { color: var(--text); font-weight: 700; font-size: 1.15rem; margin: 0.8rem 0 0.4rem; }
h3 { color: var(--text); font-weight: 600; font-size: 1rem; margin: 0.6rem 0 0.3rem; }
small { color: var(--muted) !important; }
code { color: var(--amber); background: #1a2030; padding: 1px 4px; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ======== 登录 ========
st.session_state.setdefault("logged_in", False)
if not st.session_state["logged_in"]:
    from src.pages.login import render_login_page
    render_login_page()
    st.stop()

# ======== 顶栏 ========
from src.config import get_setting
st.markdown(f"""
<div class="topbar">
    <div style="display:flex;align-items:baseline;gap:0.5rem;">
        <span style="font-size:1.5rem;font-weight:900;color:var(--red);">R</span>
        <span style="font-size:1.5rem;font-weight:900;color:var(--text);">uiQuant</span>
        <span style="color:var(--muted);font-size:0.68rem;">A股AI研</span>
    </div>
    <span style="color:var(--muted);font-size:0.72rem;">{get_setting('phone','','')[:11]}</span>
</div>
""", unsafe_allow_html=True)

# ======== 状态 ========
st.session_state.setdefault("current_page", "market")
st.session_state.setdefault("selected_stock", "")

# ======== 导航 ========
tabs = [("market","行情","📈"), ("ai_chat","AI","🤖"), ("trading","交易","💰"), ("profile","我的","⚙️")]
cur = st.session_state["current_page"]

tab_html = '<div class="tab-bar">'
for pid, label, icon in tabs:
    cls = "active" if pid == cur else ""
    tab_html += f'<div class="tab-item {cls}">{icon} {label}</div>'
tab_html += '</div>'
st.markdown(tab_html, unsafe_allow_html=True)

cols = st.columns(len(tabs))
for i, (pid, label, icon) in enumerate(tabs):
    with cols[i]:
        if st.button(f"{icon} {label}", key=f"nav_{pid}", use_container_width=True,
                      type="primary" if pid == cur else "secondary"):
            st.session_state["current_page"] = pid
            st.rerun()

# ======== 路由 ========
page = st.session_state["current_page"]
if page == "market":
    from src.pages.market import render_market_page
    render_market_page()
elif page == "stock_detail":
    code = st.session_state.get("selected_stock", "")
    if code:
        from src.pages.stock_detail import render_stock_detail_page
        render_stock_detail_page(code)
    else:
        st.warning("请先选择股票")
elif page == "ai_chat":
    from src.pages.ai_chat import render_ai_chat_page
    render_ai_chat_page()
elif page == "trading":
    from src.pages.trading import render_trading_page
    render_trading_page()
elif page == "profile":
    from src.pages.profile import render_profile_page
    render_profile_page()
