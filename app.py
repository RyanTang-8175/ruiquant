"""AlphaEye v6 — A股反量化AI助手 · Mobile First"""

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="AlphaEye", page_icon="📊",
    layout="wide", initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════
# v6 CSS — Mobile First Financial UI
# ═══════════════════════════════════════════
st.markdown("""<style>
:root {
  --bg: #F4F7FA; --panel: #EEF3F8; --card: #FFFFFF; --float: #E7EEF6;
  --border: #D8E1EA; --text: #17212F; --muted: #5D6B7C;
  --weak: #8B98A7;
  --red: #E53935; --green: #0A9B66; --amber: #D88312;
  --ai: #246BFE; --risk: #D88312;
  --mono: 'SF Mono','DIN Alternate','Menlo',monospace;
  --sans: 'PingFang SC','HarmonyOS Sans','Noto Sans SC',-apple-system,BlinkMacSystemFont,sans-serif;
}
* { font-family: var(--sans); box-sizing: border-box; }
.stApp {
  background:
    linear-gradient(180deg, rgba(36,107,254,0.08), rgba(244,247,250,0) 220px),
    var(--bg);
  color: var(--text);
}
.price-num, .sr .pr, .sr .ch, .idx-cell .p, .idx-cell .c, .tv, .score-pill {
  font-family: var(--mono) !important;
  font-variant-numeric: tabular-nums;
}
.stApp > header { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
section[data-testid="stSidebar"] { display: none; }

.main .block-container {
  padding: 0 14px 86px 14px;
  max-width: 480px; margin: 0 auto;
}

.topbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 0 8px;
  margin-bottom: 10px;
  position: sticky; top: 0;
  background: rgba(244,247,250,0.94);
  backdrop-filter: blur(16px);
  z-index: 10;
}
.logo {
  font-family: var(--sans); font-size: 18px; font-weight: 800;
  color: var(--ai); letter-spacing: -0.4px;
}
.logo span { color: var(--text); font-weight: 650; }

.ticker {
  overflow-x: auto; white-space: nowrap; padding: 6px 0;
  margin-bottom: 10px;
  font-family: var(--sans); font-size: 12px;
  -webkit-overflow-scrolling: touch;
}
.ticker::-webkit-scrollbar { display: none; }
.ti {
  display: inline-block; margin-right: 8px; font-family: var(--sans);
  background: rgba(255,255,255,0.76); border: 1px solid var(--border);
  border-radius: 999px; padding: 5px 9px;
}
.tn { color: var(--muted); font-family: var(--sans); }
.tv { font-family: var(--mono); font-weight: 600; }

.bottom-nav {
  position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 100%; max-width: 480px;
  display: flex; justify-content: space-around; align-items: center;
  background: rgba(255,255,255,0.94); border-top: 1px solid var(--border);
  box-shadow: 0 -10px 28px rgba(23,33,47,0.10);
  backdrop-filter: blur(18px);
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
.nav-item.active { color: var(--ai); }
.nav-item.ai-center { color: var(--ai); }
.nav-item.ai-center.active {
  color: var(--ai);
  background: rgba(36,107,254,0.10); border-radius: 12px;
  padding: 2px 8px;
}
.nav-icon { font-size: 20px; margin-bottom: 2px; }

.card {
  background: rgba(255,255,255,0.96); border: 1px solid var(--border);
  border-radius: 16px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 10px 28px rgba(23,33,47,0.08);
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
  background: rgba(255,255,255,0.92); border: 1px solid var(--border);
  border-radius: 14px; padding: 10px 12px; text-align: center;
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
  border: 1px solid #D8E1EA; background: #fff !important;
  color: #17212F !important; padding: 8px 16px;
  min-height: 44px; transition: all 0.12s; border-radius: 12px;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}
.stButton > button:hover { border-color: var(--ai); background: #F0F4FF !important; }
.stButton > button:active { background: #E4EBF7 !important; transform: scale(0.98); }
.stButton > button[kind="primary"] {
  background: var(--ai) !important; color: #fff !important;
  border-color: var(--ai) !important; font-weight: 700 !important;
}
.stButton > button[kind="secondary"] {
  background: #fff !important; color: #17212F !important;
  border-color: #D8E1EA !important;
}

.stTextInput input {
  background: rgba(255,255,255,0.98) !important; border: 1px solid var(--border) !important;
  color: var(--text) !important; font-family: var(--sans) !important;
  font-size: 14px !important; padding: 10px 12px !important;
  border-radius: 12px !important; min-height: 44px;
}
.stTextInput input:focus { border-color: var(--ai) !important; }

[data-testid="stMetric"] {
  background: rgba(255,255,255,0.96) !important; border: 1px solid var(--border) !important;
  padding: 10px !important; border-radius: 14px !important;
}
[data-testid="stMetric"] label {
  font-family: var(--mono) !important; font-size: 10px !important;
  text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted) !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-family: var(--mono) !important; font-size: 18px !important; font-weight: 700 !important;
  color: var(--text) !important;
}

.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-family: var(--sans); font-size: 11px; font-weight: 700;
}
.badge-low { background: rgba(18,183,106,0.15); color: var(--green); }
.badge-mid { background: rgba(216,131,18,0.14); color: var(--amber); }
.badge-high { background: rgba(229,57,53,0.12); color: var(--red); }
.badge-ai { background: rgba(36,107,254,0.12); color: var(--ai); }

.sec-h {
  font-family: var(--sans); font-size: 13px; font-weight: 700;
  color: var(--muted); margin: 16px 0 8px;
  border-bottom: 1px solid var(--border); padding-bottom: 6px;
}

[data-testid="stChatMessage"] {
  background: #fff !important; border: 1px solid #D8E1EA !important;
  border-radius: 14px !important; padding: 12px !important; margin: 6px 0 !important;
  color: var(--text) !important; font-size: 14px !important; line-height: 1.6 !important;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
  color: var(--text) !important;
}
[data-testid="stExpander"] {
  background: #fff !important; border: 1px solid #D8E1EA !important;
  border-radius: 14px !important; margin: 6px 0 !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] details summary {
  padding: 10px 14px !important; font-size: 14px !important;
  font-weight: 650 !important; color: #17212F !important;
  cursor: pointer !important; min-height: 44px !important;
  display: flex !important; align-items: center !important;
}
[data-testid="stExpander"] details summary:hover {
  background: rgba(36,107,254,0.03) !important;
}
[data-testid="stExpander"] details[open] summary {
  border-bottom: 1px solid #E7EEF6 !important;
  color: #246BFE !important;
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
  background: rgba(255,255,255,0.96);
  border: 1px solid var(--border); border-radius: 18px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 10px 24px rgba(23,33,47,0.07);
}
.ai-hero {
  background: linear-gradient(135deg, #1F66F2 0%, #163E8C 100%);
  border: none; border-radius: 22px;
  padding: 18px; margin-bottom: 14px;
  box-shadow: 0 16px 38px rgba(36,107,254,0.24);
}
.ai-hero-title { color: #fff; font-size: 20px; font-weight: 800; margin-bottom: 5px; }
.ai-hero-sub { color: rgba(255,255,255,0.78); font-size: 13px; line-height: 1.55; }
.skill-card {
  min-height: 74px; background: rgba(255,255,255,0.98); border: 1px solid var(--border);
  border-radius: 16px; padding: 11px; margin-bottom: 8px;
  box-shadow: 0 8px 22px rgba(23,33,47,0.06);
}
.skill-title { color: var(--text); font-size: 14px; font-weight: 700; margin-bottom: 4px; }
.skill-desc { color: var(--muted); font-size: 12px; line-height: 1.4; }
.recommend-card {
  background: rgba(255,255,255,0.98); border: 1px solid var(--border);
  border-radius: 16px; padding: 12px; margin-bottom: 10px;
  box-shadow: 0 10px 26px rgba(23,33,47,0.07);
}
.score-row { display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }
.score-pill {
  color: var(--muted); border: 1px solid var(--border); border-radius: 999px;
  padding: 3px 8px; font-size: 11px; background: rgba(244,247,250,0.84);
  font-family: var(--mono);
}

.ai-shell { padding-bottom: 8px; }
.ai-statusbar {
  display:flex; gap:8px; overflow-x:auto; padding-bottom:8px; margin-bottom:4px;
  -webkit-overflow-scrolling:touch;
}
.ai-statusbar::-webkit-scrollbar { display:none; }
.ai-stat {
  min-width:106px; background:rgba(255,255,255,0.90); border:1px solid var(--border);
  border-radius:14px; padding:9px 10px;
}
.ai-stat-label { color:var(--muted); font-size:11px; margin-bottom:2px; }
.ai-stat-value { color:var(--text); font-size:14px; font-weight:750; }
.ai-section-title { color:var(--text); font-size:15px; font-weight:800; margin:14px 0 8px; }
.ai-task-grid { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-bottom:12px; }
.ai-task {
  background:#fff; border:1px solid var(--border); border-radius:18px; padding:12px;
  min-height:92px; box-shadow:0 10px 24px rgba(23,33,47,0.07);
}
.ai-task-icon {
  width:28px; height:28px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  background:rgba(36,107,254,0.10); color:var(--ai); font-size:15px; margin-bottom:8px;
}
.ai-task-title { color:var(--text); font-size:14px; font-weight:800; margin-bottom:3px; }
.ai-task-desc { color:var(--muted); font-size:12px; line-height:1.38; }
.ai-memory-card {
  background:#fff; border:1px solid var(--border); border-radius:18px; padding:12px; margin-bottom:12px;
  box-shadow:0 10px 24px rgba(23,33,47,0.06);
}
.ai-memory-row { display:flex; justify-content:space-between; gap:10px; align-items:center; padding:7px 0; border-bottom:1px solid var(--border); }
.ai-memory-row:last-child { border-bottom:none; }
.ai-memory-q { color:var(--text); font-size:13px; font-weight:650; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ai-memory-t { color:var(--weak); font-size:11px; font-family:var(--mono); white-space:nowrap; }
.chat-msg-user {
  background: #EAF1FF; border:1px solid #D5E2FF; border-radius:16px 16px 4px 16px;
  padding:10px 12px; margin:4px 0 10px 26px; font-size:14px; color:var(--text); line-height:1.55;
}
.chat-msg-assistant {
  background:#fff; border:1px solid var(--border); border-radius:16px 16px 16px 4px;
  padding:12px; margin:4px 22px 12px 0; font-size:14px; color:var(--text); line-height:1.62;
  box-shadow:0 8px 22px rgba(23,33,47,0.06);
}
.chat-msg-assistant p { margin:0 0 8px; }
.chat-tools { color:var(--weak); font-size:11px; margin-top:6px; font-family:var(--sans); }

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
  background: #EAF1FF; border:1px solid #D5E2FF; border-radius:16px 16px 4px 16px;
  padding: 10px 12px; margin: 4px 0 10px 26px; font-size: 14px; color: var(--text); line-height: 1.55;
}
.chat-msg-assistant {
  background: #fff; border: 1px solid var(--border); border-radius: 16px 16px 16px 4px;
  padding: 12px; margin: 4px 22px 12px 0; font-size: 14px; color: var(--text); line-height: 1.62;
  box-shadow:0 8px 22px rgba(23,33,47,0.06);
}
.chat-tools { color: var(--weak); font-size: 11px; margin-top: 6px; font-family: var(--sans); }

.ai-answer {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 10px;
  color: var(--text);
  font-size: 13px;
  line-height: 1.65;
}
.ai-section {
  margin: 12px 0 8px;
  padding: 9px 10px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(36,107,254,0.10), rgba(36,107,254,0.03));
  color: #173B8F;
  font-size: 15px;
  font-weight: 800;
}
.ai-p {
  margin: 7px 0;
  color: var(--text);
}
.ai-step {
  margin: 6px 0;
  padding: 8px 10px;
  border-left: 3px solid rgba(36,107,254,0.35);
  background: rgba(244,247,250,0.84);
  border-radius: 10px;
}
.ai-table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin: 8px 0 10px;
}
.ai-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
  min-width: 430px;
}
.ai-table th {
  text-align: left;
  color: var(--muted);
  background: #F4F7FA;
  border-bottom: 1px solid var(--border);
  padding: 7px 8px;
  font-weight: 750;
}
.ai-table td {
  border-bottom: 1px solid #E8EEF5;
  padding: 8px;
  vertical-align: top;
  color: var(--text);
}

/* Tabs */
.stTabs [role="tablist"] {
  gap: 2px;
}
.stTabs [role="tab"] {
  font-size: 13px; font-weight: 600; padding: 8px 12px;
  min-height: 40px; border-radius: 10px 10px 0 0;
}

/* checkbox */
.stCheckbox label { font-size: 13px; color: var(--text); }

@media (max-width: 400px) {
  .main .block-container { padding: 0 10px 80px 10px; }
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
st.session_state.setdefault("_last_page", cur)

cols = st.columns(len(TABS))
for i, (pid, label, icon) in enumerate(TABS):
    with cols[i]:
        is_cur = pid == cur
        if st.button(
            f"{icon} {label}", key=f"n_{pid}",
            use_container_width=True,
            type="primary" if is_cur else "secondary",
        ):
            if st.session_state.get("_last_page") == "ai_chat" and pid != "ai_chat":
                st.session_state.pop("qq", None)
                st.session_state.pop("ai_pending_prompt", None)
            st.session_state["current_page"] = pid
            st.session_state["_last_page"] = pid
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
