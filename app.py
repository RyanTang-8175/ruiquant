"""AlphaEye v6 — A股反量化AI助手 · Industrial Mobile"""

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="AlphaEye", page_icon="📊",
    layout="wide", initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════
# v6 CSS — Industrial Mobile
# ═══════════════════════════════════════════
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg: #121821; --panel: #151D28; --card: #1B2532; --float: #233042;
  --border: #314052; --text: #F7F9FC; --muted: #B4BFCC;
  --weak: #7D8998;
  --red: #F04438; --green: #12B76A; --amber: #F79009;
  --ai: #4D8DFF; --risk: #F79009;
  --mono: 'SF Mono','JetBrains Mono','DIN Alternate',monospace;
  --sans: 'PingFang SC','Inter',-apple-system,sans-serif;
}
* { font-family: var(--sans); box-sizing: border-box; }
.stApp { background: radial-gradient(circle at 50% -20%, rgba(77,141,255,0.10), transparent 34%), var(--bg); color: var(--text); }
.price-num, .sr .pr, .sr .ch, .idx-cell .p, .idx-cell .c, .tv, .score-pill {
  font-family: var(--mono) !important;
  font-variant-numeric: tabular-nums;
}
.stApp > header { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
section[data-testid="stSidebar"] { display: none; }

.main .block-container {
  padding: 0 16px 80px 16px;
  max-width: 480px; margin: 0 auto;
}

.topbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 0 8px;
  border-bottom: 1px solid var(--border); margin-bottom: 12px;
  position: sticky; top: 0; background: var(--bg); z-index: 10;
}
.logo {
  font-family: var(--sans); font-size: 18px; font-weight: 700;
  color: var(--red); letter-spacing: -0.5px;
}
.logo span { color: var(--text); font-weight: 500; }

.ticker {
  overflow-x: auto; white-space: nowrap; padding: 6px 0;
  border-bottom: 1px solid var(--border); margin-bottom: 12px;
  font-family: var(--sans); font-size: 12px;
  -webkit-overflow-scrolling: touch;
}
.ticker::-webkit-scrollbar { display: none; }
.ti { display: inline-block; margin-right: 18px; font-family: var(--mono); }
.tn { color: var(--muted); font-family: var(--mono); }
.tv { font-family: var(--mono); font-weight: 600; }

.bottom-nav {
  position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 100%; max-width: 480px;
  display: flex; justify-content: space-around; align-items: center;
  background: var(--card); border-top: 1px solid var(--border);
  padding: 6px 0 max(6px, env(safe-area-inset-bottom));
  z-index: 100; height: 64px;
}
.nav-item {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center;
  min-width: 56px; min-height: 44px;
  color: var(--muted); font-size: 11px;
  font-family: var(--sans); cursor: pointer;
  transition: color 0.15s;
}
.nav-item.active { color: var(--amber); }
.nav-item.ai-center { color: var(--ai); }
.nav-item.ai-center.active {
  color: var(--ai);
  background: rgba(77,141,255,0.1); border-radius: 8px;
  padding: 2px 8px;
}
.nav-icon { font-size: 20px; margin-bottom: 2px; }

.card {
  background: rgba(27,37,50,0.96); border: 1px solid var(--border);
  border-radius: 12px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 10px 28px rgba(0,0,0,0.12);
}
.card.risk-low { border-left: 3px solid var(--green); }
.card.risk-mid { border-left: 3px solid var(--amber); }
.card.risk-high { border-left: 3px solid var(--red); }

.card-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-bottom: 1px solid var(--border);
}
.card-row:last-child { border-bottom: none; }

.idx-strip {
  display: flex; gap: 8px; margin-bottom: 12px;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
}
.idx-strip::-webkit-scrollbar { display: none; }
.idx-cell {
  flex: 1; min-width: 100px;
  background: var(--card); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 12px; text-align: center;
}
.idx-cell .n { color: var(--muted); font-size: 11px; font-family: var(--mono); }
.idx-cell .p { font-size: 18px; font-weight: 700; font-family: var(--mono); margin: 4px 0; }
.idx-cell .c { font-size: 13px; font-weight: 600; font-family: var(--mono); }

.sr {
  display: flex; align-items: center; padding: 10px 0;
  border-bottom: 1px solid var(--border); cursor: pointer;
}
.sr:active { background: var(--float); }
.sr .inf { flex: 1; margin-left: 8px; }
.sr .nm { color: var(--text); font-weight: 600; font-size: 15px; }
.sr .cd { color: var(--muted); font-size: 11px; font-family: var(--mono); }
.sr .pr { font-family: var(--mono); font-weight: 600; font-size: 15px; text-align: right; min-width: 70px; }
.sr .ch { font-family: var(--mono); font-weight: 600; font-size: 13px; text-align: right; min-width: 55px; }

.stButton > button {
  font-family: var(--sans); font-size: 13px; font-weight: 600;
  border: 1px solid var(--border); background: var(--card);
  color: var(--text); padding: 8px 16px;
  min-height: 44px; transition: all 0.1s; border-radius: 8px;
}
.stButton > button:hover { border-color: var(--muted); background: var(--float); }
.stButton > button[kind="primary"] {
  background: var(--ai); color: #fff; border-color: var(--ai); font-weight: 700;
}

.stTextInput input {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  color: var(--text) !important; font-family: var(--sans) !important;
  font-size: 14px !important; padding: 10px 12px !important;
  border-radius: 8px !important; min-height: 44px;
}
.stTextInput input:focus { border-color: var(--ai) !important; }

[data-testid="stMetric"] {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  padding: 10px !important; border-radius: 8px !important;
}
[data-testid="stMetric"] label {
  font-family: var(--mono) !important; font-size: 10px !important;
  text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted) !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-family: var(--mono) !important; font-size: 18px !important; font-weight: 700 !important;
}

.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-family: var(--sans); font-size: 11px; font-weight: 700;
}
.badge-low { background: rgba(18,183,106,0.15); color: var(--green); }
.badge-mid { background: rgba(247,144,9,0.15); color: var(--amber); }
.badge-high { background: rgba(240,68,56,0.15); color: var(--red); }
.badge-ai { background: rgba(77,141,255,0.15); color: var(--ai); }

.sec-h {
  font-family: var(--sans); font-size: 13px; font-weight: 700;
  color: var(--muted); margin: 16px 0 8px;
  border-bottom: 1px solid var(--border); padding-bottom: 6px;
}

[data-testid="stChatMessage"] {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: 10px !important; padding: 10px !important; margin: 4px 0 !important;
  color: var(--text) !important; font-size: 14px !important; line-height: 1.55 !important;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
  color: var(--text) !important;
}
[data-testid="stExpander"] {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}

hr { border-color: var(--border) !important; margin: 12px 0 !important; }
h2 {
  color: var(--text); font-weight: 700; font-size: 18px;
  margin: 12px 0 6px; font-family: var(--sans);
  border-bottom: 1px solid var(--border); padding-bottom: 6px;
}
h3 {
  color: var(--text); font-weight: 600; font-size: 14px;
  font-family: var(--sans);
}
small { color: var(--muted) !important; font-family: var(--sans) !important; }
code { color: var(--amber); background: var(--float); font-family: var(--mono); padding: 1px 4px; border-radius: 3px; }

.page-kicker { color: var(--muted); font-size: 12px; margin: -2px 0 12px; }
.soft-card {
  background: linear-gradient(180deg, rgba(35,48,66,0.94), rgba(27,37,50,0.94));
  border: 1px solid var(--border); border-radius: 14px; padding: 14px; margin-bottom: 12px;
}
.ai-hero {
  background: linear-gradient(135deg, rgba(77,141,255,0.20), rgba(27,37,50,0.98));
  border: 1px solid rgba(77,141,255,0.30); border-radius: 16px;
  padding: 16px; margin-bottom: 12px;
}
.ai-hero-title { color: var(--text); font-size: 19px; font-weight: 750; margin-bottom: 4px; }
.ai-hero-sub { color: var(--muted); font-size: 13px; line-height: 1.55; }
.skill-card {
  min-height: 70px; background: rgba(27,37,50,0.96); border: 1px solid var(--border);
  border-radius: 12px; padding: 10px; margin-bottom: 8px;
}
.skill-title { color: var(--text); font-size: 14px; font-weight: 700; margin-bottom: 4px; }
.skill-desc { color: var(--muted); font-size: 12px; line-height: 1.4; }
.recommend-card {
  background: rgba(27,37,50,0.98); border: 1px solid var(--border);
  border-radius: 14px; padding: 12px; margin-bottom: 10px;
}
.score-row { display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }
.score-pill {
  color: var(--muted); border: 1px solid var(--border); border-radius: 999px;
  padding: 3px 8px; font-size: 11px; background: rgba(18,24,33,0.50);
  font-family: var(--mono);
}

/* ── chip 筛选器 ── */
.chip-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.chip-item {
  padding: 6px 14px; border-radius: 999px; border: 1px solid var(--border);
  font-size: 12px; cursor: pointer; white-space: nowrap;
  background: var(--card); color: var(--muted);
  transition: all 0.15s; user-select: none;
}
.chip-item:hover { border-color: var(--muted); color: var(--text); }
.chip-item.active { background: var(--ai); color: #fff; border-color: var(--ai); }

/* ── 交易按钮 ── */
.btn-buy button {
  background: var(--red) !important; border-color: var(--red) !important;
  color: #fff !important; font-weight: 700 !important;
}
.btn-sell button {
  background: var(--green) !important; border-color: var(--green) !important;
  color: #fff !important; font-weight: 700 !important;
}

/* ── 行情页 tab 分割线 ── */
.tab-divider { border-bottom: 1px solid var(--border); margin-bottom: 10px; }

/* ── AI 对话可读性 ── */
[data-testid="stChatMessage"] {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: 12px !important; padding: 12px !important; margin: 6px 0 !important;
  color: var(--text) !important; font-size: 14px !important; line-height: 1.6 !important;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
  color: var(--text) !important;
}
.chat-msg-user {
  background: rgba(77,141,255,0.08); border-radius: 12px; padding: 10px 14px;
  margin: 4px 0 10px; font-size: 14px; color: var(--text); line-height: 1.55;
}
.chat-msg-assistant {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 12px 14px; margin: 4px 0 10px; font-size: 14px; color: var(--text); line-height: 1.6;
}
.chat-tools { color: var(--weak); font-size: 11px; margin-top: 6px; font-family: var(--mono); }

@media (max-width: 400px) {
  .main .block-container { padding: 0 12px 80px 12px; }
}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# Login
# ═══════════════════════════════════════════
from src.config import get_setting
st.session_state.setdefault("logged_in", bool(get_setting("phone", "", "")))
if not st.session_state["logged_in"]:
    from src.pages.login import render_login_page
    render_login_page()
    st.stop()

# ═══════════════════════════════════════════
# Topbar
# ═══════════════════════════════════════════
st.markdown(
    f'<div class="topbar">'
    f'<div class="logo">A<span>lphaEye</span></div>'
    f'<div style="font-family:var(--mono);font-size:11px;color:var(--muted)">'
    f'{get_setting("phone","","")[:11]}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════
# Ticker
# ═══════════════════════════════════════════
from src.data.realtime import get_market_overview
ov = get_market_overview()
indices = ov.get("indices", [])
if indices:
    t = '<div class="ticker">'
    for idx in indices:
        p = idx.get("change_pct", 0)
        c = "#F04438" if p > 0 else "#12B76A" if p < 0 else "#667180"
        s = "+" if p > 0 else ""
        t += (
            f'<span class="ti">'
            f'<span class="tn">{idx.get("name","")}</span> '
            f'<span class="tv" style="color:{c}">{idx.get("price",0):.2f} '
            f'{s}{p:.2f}%</span></span>'
        )
    t += '</div>'
    st.markdown(t, unsafe_allow_html=True)

# ═══════════════════════════════════════════
# State + Tabs
# ═══════════════════════════════════════════
st.session_state.setdefault("current_page", "market")
st.session_state.setdefault("selected_stock", "")

TABS = [
    ("market", "行情", "📈"),
    ("radar", "雷达", "🛡"),
    ("ai_chat", "AI", "◇"),
    ("lab", "实验室", "🧪"),
    ("profile", "我的", "⚙"),
]
cur = st.session_state["current_page"]

cols = st.columns(len(TABS))
for i, (pid, label, icon) in enumerate(TABS):
    with cols[i]:
        is_cur = pid == cur
        if st.button(
            f"{icon} {label}", key=f"n_{pid}",
            use_container_width=True,
            type="primary" if is_cur else "secondary",
        ):
            st.session_state["current_page"] = pid
            st.rerun()

# ═══════════════════════════════════════════
# Page routing
# ═══════════════════════════════════════════
p = st.session_state["current_page"]

if p == "market":
    from src.pages.market import render_market_page
    render_market_page()

elif p == "radar":
    from src.pages.radar import render_radar_page
    render_radar_page()

elif p == "stock_detail":
    c = st.session_state.get("selected_stock", "")
    if c:
        from src.pages.stock_detail import render_stock_detail_page
        render_stock_detail_page(c)
    else:
        st.warning("请先选择股票")

elif p == "ai_chat":
    from src.pages.ai_chat import render_ai_chat_page
    render_ai_chat_page()

elif p == "trading":
    from src.pages.trading import render_trading_page
    render_trading_page()

elif p == "lab":
    from src.pages.lab import render_lab_page
    render_lab_page()

elif p == "profile":
    from src.pages.profile import render_profile_page
    render_profile_page()
