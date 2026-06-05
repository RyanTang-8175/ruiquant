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
/* ═══════════════════════════════════════════
   White research desk — clean, airy, evidence-first
   Pure white background, muted borders, compact shadows, no noisy decoration.
   ═══════════════════════════════════════════ */
:root {
  --bg: #FFFFFF;           --surface: #F7F7F8;
  --card: #FFFFFF;         --border: #D8D9DB;
  --text: #111111;         --muted: #6B6B6B;
  --ink: #111111;          --hint: #8C8C8C;
  --ai: #002FA7;           --red: #CF0011;
  --green: #007348;        --amber: #C74E00;
  --cyan: #006B7A;         --risk: #C74E00;
  --mono: 'SF Mono','DIN Alternate','Menlo',monospace;
  --sans: 'PingFang SC','HarmonyOS Sans','Noto Sans SC',-apple-system,BlinkMacSystemFont,sans-serif;
}
* { font-family: var(--sans); box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main {
  background: #FFFFFF !important;
}
.stApp { background: #FFFFFF !important; color: var(--text); }
.stApp > header { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
section[data-testid="stSidebar"] { display: none; }

.main .block-container {
  padding: 0 20px 96px 20px;
  max-width: 1120px; margin: 0 auto;
}

/* ── Numeric data → tabular-nums ── */
.price-num, .sr .pr, .sr .ch, .idx-cell .p, .idx-cell .c, .tv, .score-pill,
.watch-score, [data-testid="stMetricValue"] {
  font-family: var(--mono) !important;
  font-variant-numeric: tabular-nums;
}

/* ── Topbar ── */
.topbar {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 18px 0 10px; margin-bottom: 10px;
  position: sticky; top: 0; z-index: 10;
  background: #FFFFFF;
}
.logo {
  font-family: var(--sans); font-size: 22px; font-weight: 800;
  color: #111111; letter-spacing: -0.6px;
}
.logo span { font-weight: 500; }
.top-chip {
  font-family: var(--mono); font-size: 10px; color: var(--muted);
  border-bottom: 1px solid var(--border); padding-bottom: 3px;
  letter-spacing: 0.4px; text-transform: uppercase;
}

/* ── Ticker ── */
.ticker {
  overflow-x: auto; white-space: nowrap; padding: 0 0 10px;
  margin-bottom: 6px; font-size: 12px;
  -webkit-overflow-scrolling: touch;
  border-bottom: 1px solid var(--border);
}
.ticker::-webkit-scrollbar { display: none; }
.ti { display: inline-block; margin-right: 16px; }
.tn { color: var(--muted); }
.tv { font-family: var(--mono); font-weight: 600; }
.ti:not(:last-child)::after {
  content: ""; display: inline-block; width: 1px; height: 10px;
  background: var(--border); margin-left: 14px; vertical-align: middle;
}

/* ── Bottom nav ── */
.nav-wrap {
  position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
  width: calc(100% - 24px); max-width: 1120px;
  background: #FFFFFF; border-top: 1px solid #111111;
  padding: 4px 8px max(4px, env(safe-area-inset-bottom));
  z-index: 100; min-height: 64px;
}
.nav-wrap [data-testid="stHorizontalBlock"] { gap: 2px !important; }
.nav-wrap .stButton > button {
  min-height: 48px !important; padding: 4px 2px !important;
  border: none !important; border-radius: 0 !important;
  box-shadow: none !important;
  font-size: 11px !important; line-height: 1.15 !important;
  white-space: pre-line !important;
  background: transparent !important; color: var(--muted) !important;
  font-weight: 500 !important; letter-spacing: 0.2px;
}
.nav-wrap .stButton > button:hover {
  color: #111111 !important;
}
.nav-wrap .stButton > button[kind="primary"] {
  color: #111111 !important; font-weight: 700 !important;
  border-bottom: 2px solid #111111 !important;
}

/* ── Segmented control ── */
[data-testid="stSegmentedControl"] {
  background: #FFFFFF !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 !important; padding: 0 !important;
  margin: 0 0 18px !important;
  box-shadow: none !important;
  display: flex !important; gap: 0 !important;
}
[data-testid="stSegmentedControl"] label {
  min-height: 42px !important; border-radius: 0 !important;
  font-size: 12px !important; font-weight: 500 !important;
  color: var(--muted) !important; border-right: 1px solid var(--border) !important;
  margin: 0 !important;
}
[data-testid="stSegmentedControl"] label:last-child { border-right: none !important; }
[data-testid="stSegmentedControl"] label[data-checked="true"],
[data-testid="stSegmentedControl"] label[aria-checked="true"] {
  background: #111111 !important; color: #FFFFFF !important;
  font-weight: 600 !important;
}

/* ── Cards: flat, 1px border, 2px radius ── */
.card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}
.card.risk-low  { border-left: 3px solid var(--green); }
.card.risk-mid  { border-left: 3px solid var(--amber); }
.card.risk-high { border-left: 3px solid var(--red); }

.card-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-bottom: 1px solid var(--border);
}
.card-row:last-child { border-bottom: none; }

/* ── Index strip ── */
.idx-strip {
  display: flex; gap: 0; margin-bottom: 16px;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
}
.idx-strip::-webkit-scrollbar { display: none; }
.idx-cell {
  flex: 1; min-width: 106px; background: var(--card);
  border: 1px solid var(--border); border-radius: 8px;
  padding: 12px 14px; text-align: left;
  margin-right: -1px;
}
.idx-cell:last-child { margin-right: 0; }
.idx-cell .n { color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: 0.6px; }
.idx-cell .p { font-size: 20px; font-weight: 700; margin: 4px 0; }
.idx-cell .c { font-size: 13px; font-weight: 600; }

/* ── Stock row ── */
.sr {
  display: flex; align-items: center; padding: 10px 0;
  border-bottom: 1px solid var(--border); cursor: pointer;
}
.sr:last-child { border-bottom: none; }
.sr:active { background: var(--surface); }
.sr .inf { flex: 1; margin-left: 10px; }
.sr .nm { color: var(--text); font-weight: 600; font-size: 15px; }
.sr .cd { color: var(--muted); font-size: 11px; font-family: var(--mono); }
.sr .pr { font-weight: 600; font-size: 15px; text-align: right; min-width: 72px; }
.sr .ch { font-weight: 600; font-size: 13px; text-align: right; min-width: 56px; }

/* ── Search result items ── */
.search-results-grid [data-testid="stHorizontalBlock"] {
  display: grid !important; grid-template-columns: 1fr !important; gap: 0 !important;
}
.ni {
  background: #fff; border-bottom: 1px solid var(--border);
  padding: 12px 0;
}
.ni:last-child { border-bottom: none; }
.nt { color: var(--text); font-size: 14px; font-weight: 600; line-height: 1.45; }
.ni .nm { color: var(--muted); font-size: 11px; margin-top: 4px; }

/* ── Buttons ── */
.stButton > button {
  font-family: var(--sans); font-size: 13px; font-weight: 600;
  border: 1px solid #111111; background: #FFFFFF !important;
  color: #111111 !important; padding: 8px 16px;
  min-height: 44px; border-radius: 8px;
  -webkit-tap-highlight-color: transparent; touch-action: manipulation;
  box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}
.stButton > button:hover { background: #111111 !important; color: #FFFFFF !important; }
.stButton > button:active { background: #333333 !important; color: #FFFFFF !important; }
.stButton > button[kind="primary"] {
  background: #111111 !important; color: #FFFFFF !important;
  border-color: #111111 !important; font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover { background: #002FA7 !important; border-color: #002FA7 !important; }
.stButton > button[kind="secondary"] {
  background: #FFFFFF !important; color: #111111 !important;
  border-color: var(--border) !important;
}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
  background: #FFFFFF !important; border: 1px solid var(--border) !important;
  color: var(--text) !important; font-family: var(--sans) !important;
  font-size: 14px !important; padding: 10px 12px !important;
  border-radius: 8px !important; min-height: 44px;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: #111111 !important; outline: none !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  padding: 12px 14px !important; border-radius: 8px !important;
  box-shadow: 0 1px 2px rgba(17,17,17,0.04) !important;
}
[data-testid="stMetric"] label {
  font-family: var(--sans) !important; font-size: 10px !important;
  text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted) !important;
  font-weight: 500 !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-size: 20px !important; font-weight: 700 !important; color: var(--text) !important;
}

/* ── Badges ── */
.badge {
  display: inline-block; padding: 2px 6px;
  font-family: var(--sans); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.4px;
  border-radius: 999px;
}
.badge-low  { color: var(--green); border-bottom: 1px solid var(--green); }
.badge-mid  { color: var(--amber); border-bottom: 1px solid var(--amber); }
.badge-high { color: var(--red);   border-bottom: 1px solid var(--red); }
.badge-ai   { color: var(--ai);    border-bottom: 1px solid var(--ai); }

/* ── Section header ── */
.sec-h {
  font-family: var(--sans); font-size: 12px; font-weight: 600;
  color: #475569; margin: 20px 0 10px;
  border-bottom: 1px solid var(--border); padding-bottom: 6px;
  text-transform: uppercase; letter-spacing: 0.6px;
}

/* ── Chat ── */
[data-testid="stChatMessage"] {
  background: #FFFFFF !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; padding: 14px !important; margin: 0 0 8px 0 !important;
  color: var(--text) !important; font-size: 14px !important; line-height: 1.65 !important;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
  color: var(--text) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
  background: #FFFFFF !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; margin: 10px 0 !important; overflow: hidden !important;
}
[data-testid="stExpander"] details summary {
  padding: 11px 14px !important; font-size: 13px !important;
  font-weight: 600 !important; color: var(--text) !important;
  cursor: pointer !important; min-height: 44px !important;
}
[data-testid="stExpander"] details summary:hover { background: var(--surface) !important; }
[data-testid="stExpander"] details[open] summary {
  border-bottom: 1px solid var(--border) !important; font-weight: 700 !important;
}

/* ── Typography ── */
hr { border: none; border-top: 1px solid var(--border) !important; margin: 18px 0 !important; }
h2 {
  color: var(--text); font-weight: 700; font-size: 16px;
  margin: 18px 0 8px; font-family: var(--sans);
  border-bottom: 1px solid var(--border); padding-bottom: 6px;
  letter-spacing: -0.2px;
}
h3 {
  color: var(--text); font-weight: 600; font-size: 13px;
  font-family: var(--sans); text-transform: uppercase;
  letter-spacing: 0.4px;
}
small { color: var(--muted) !important; font-family: var(--sans) !important; }
code {
  color: var(--red); background: var(--surface); font-family: var(--mono);
  padding: 1px 4px; border-radius: 2px; font-size: 12px;
}

.page-kicker { color: var(--muted); font-size: 12px; margin: -4px 0 14px; line-height: 1.5; }

/* ── Soft card / Hero ── */
.soft-card {
  background: #FFFFFF; border: 1px solid var(--border);
  border-radius: 8px; padding: 16px; margin-bottom: 14px;
  box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}
.ai-hero {
  background: #FFFFFF; border: 1px solid var(--border);
  border-left: 4px solid var(--ai);
  border-radius: 8px; padding: 20px; margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}
.ai-hero-title { color: var(--text); font-size: 24px; font-weight: 800; margin-bottom: 6px; letter-spacing: -0.4px; }
.ai-hero-sub { color: var(--muted); font-size: 13px; line-height: 1.6; }

/* ── Skill cards ── */
.skill-card {
  background: #FFFFFF; border: 1px solid var(--border); border-radius: 8px;
  padding: 14px; margin-bottom: 8px;
  box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}
.skill-title { color: var(--text); font-size: 14px; font-weight: 700; margin-bottom: 4px; }
.skill-desc  { color: var(--muted); font-size: 12px; line-height: 1.45; }

/* ── Recommend card ── */
.recommend-card {
  background: #FFFFFF; border: 1px solid var(--border);
  border-radius: 8px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}

/* ── Score ── */
.score-row { display:flex; gap:4px; flex-wrap:wrap; margin-top:8px; }
.score-pill {
  color: var(--muted); border: 1px solid var(--border); border-radius: 8px;
  padding: 2px 6px; font-size: 10px; background: #FFFFFF;
  font-family: var(--mono);
}

/* ── AI page ── */
.ai-shell { padding-bottom: 8px; }
.ai-statusbar {
  display:flex; gap:0; overflow-x:auto; padding-bottom:0; margin-bottom:14px;
  -webkit-overflow-scrolling:touch;
  border-bottom: 1px solid var(--border);
}
.ai-statusbar::-webkit-scrollbar { display:none; }
.ai-stat {
  min-width:106px; background:#FFFFFF; border-right: 1px solid var(--border);
  padding: 10px 12px;
}
.ai-stat:last-child { border-right: none; }
.ai-stat-label { color:var(--muted); font-size:10px; margin-bottom:2px; text-transform:uppercase; letter-spacing:0.5px; }
.ai-stat-value { color:var(--text); font-size:15px; font-weight:750; }
.ai-section-title { color:var(--text); font-size:13px; font-weight:700; margin:16px 0 8px; text-transform:uppercase; letter-spacing:0.4px; }
.ai-task-grid { display:grid; grid-template-columns:1fr 1fr; gap:0; margin-bottom:14px; }
.ai-task {
  background:#fff; border:1px solid var(--border); margin-right:-1px; margin-bottom:-1px;
  border-radius:8px; padding:14px; min-height:88px; box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}
.ai-task-icon { display:none; }
.ai-task-title { color:var(--text); font-size:14px; font-weight:700; margin-bottom:3px; }
.ai-task-desc  { color:var(--muted); font-size:12px; line-height:1.4; }
.ai-memory-card {
  background:#fff; border:1px solid var(--border); border-radius:8px;
  padding:14px; margin-bottom:14px; box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}
.ai-memory-row {
  display:flex; justify-content:space-between; gap:8px; align-items:center;
  padding:8px 0; border-bottom:1px solid var(--border);
}
.ai-memory-row:last-child { border-bottom:none; }
.ai-memory-q { color:var(--text); font-size:13px; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ai-memory-t { color:var(--hint); font-size:10px; font-family:var(--mono); white-space:nowrap; }

/* ── Chat bubbles ── */
.chat-msg-user {
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px; margin: 4px 0 12px 20px; font-size: 14px; color: var(--text); line-height: 1.6;
}
.chat-msg-assistant {
  background: #fff; border: 1px solid #111111; border-radius: 8px;
  padding: 14px; margin: 4px 16px 14px 0; font-size: 14px; color: var(--text); line-height: 1.65;
}
.chat-msg-assistant p { margin: 0 0 10px; }
.chat-tools { color: var(--hint); font-size: 10px; margin-top: 6px; font-family: var(--sans); text-transform: uppercase; letter-spacing: 0.4px; }

/* ── Chip filter ── */
.chip-row { display: flex; gap: 0; flex-wrap: wrap; margin-bottom: 14px; }
.chip-item {
  padding: 6px 14px; border: 1px solid var(--border); margin-right: -1px; margin-bottom: -1px;
  font-size: 12px; cursor: pointer; white-space: nowrap;
  background: var(--card); color: var(--muted);
  user-select: none;
}
.chip-item:hover { color: var(--text); }
.chip-item.active { background: #111111; color: #fff; border-color: #111111; }

/* ── Trade buttons ── */
.btn-buy  button { background: var(--red)   !important; border-color: var(--red)   !important; color: #fff !important; font-weight: 700 !important; border-radius: 8px !important; }
.btn-sell button { background: var(--green) !important; border-color: var(--green) !important; color: #fff !important; font-weight: 700 !important; border-radius: 8px !important; }

.tab-divider { border-bottom: 1px solid var(--border); margin-bottom: 12px; }

/* ── AI answer ── */
.ai-answer {
  background: #FFFFFF; border: 1px solid var(--border); border-radius: 8px;
  padding: 14px; color: var(--text); font-size: 13px; line-height: 1.7;
}
.ai-section {
  margin: 14px 0 8px; padding: 10px 12px;
  background: #FFFFFF; border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); font-size: 13px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.4px;
}
.ai-p { margin: 8px 0; color: var(--text); }
.ai-step {
  margin: 6px 0; padding: 10px 12px;
  border-left: 2px solid #111111;
  background: #FFFFFF; border-top: 1px solid var(--border);
  border-right: 1px solid var(--border); border-bottom: 1px solid var(--border);
  border-radius: 8px;
}

/* ── AI tables ── */
.ai-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 10px 0 12px; }
.ai-table {
  width: 100%; border-collapse: collapse; border-spacing: 0;
  font-size: 12px; min-width: 400px;
}
.ai-table th {
  text-align: left; color: var(--muted); background: var(--surface);
  border-bottom: 2px solid #111111; padding: 8px 10px;
  font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;
}
.ai-table td {
  border-bottom: 1px solid var(--border); padding: 9px 10px;
  vertical-align: top; color: var(--text);
}

/* ── Score explainer ── */
.score-explainer { display: grid; grid-template-columns: 1fr; gap: 0; margin: 12px 0 14px; }
.score-explainer-card {
  background: #fff; border: 1px solid var(--border); border-radius: 8px;
  padding: 12px 14px; margin-bottom: -1px;
}
.score-explainer-title { color: var(--text); font-size: 13px; font-weight: 700; margin-bottom: 3px; }
.score-explainer-copy  { color: var(--muted); font-size: 12px; line-height: 1.5; }

/* ── Watch card ── */
.watch-card {
  background: #fff; border: 1px solid var(--border); border-radius: 8px;
  padding: 14px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}
.watch-rank {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  background: #111111; color: #FFFFFF; font-family: var(--mono); font-size: 12px; font-weight: 700;
}
.watch-title { color: var(--text); font-size: 15px; font-weight: 700; line-height: 1.25; }
.watch-code  { color: var(--muted); font-family: var(--mono); font-size: 11px; margin-left: 6px; }
.watch-sub   { color: var(--muted); font-size: 12px; line-height: 1.45; margin-top: 4px; }
.watch-score { font-family: var(--mono); font-size: 24px; font-weight: 800; color: var(--text); line-height: 1; }

/* ── Audit hero ── */
.audit-hero {
  background: #FFFFFF; border: 1px solid var(--border); border-left: 4px solid #111111; border-radius: 8px;
  padding: 18px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(17,17,17,0.04);
}
.audit-title { color: var(--text); font-size: 18px; font-weight: 800; margin-bottom: 6px; }
.audit-copy  { color: var(--muted); font-size: 13px; line-height: 1.55; }

/* ── Tabs ── */
.stTabs [role="tablist"] { gap: 0; border-bottom: 1px solid var(--border); }
.stTabs [role="tab"] {
  font-size: 12px; font-weight: 600; padding: 10px 16px;
  min-height: 42px; border-radius: 8px 8px 0 0; border: 1px solid var(--border);
  border-bottom: none; margin-right: -1px; background: var(--surface);
  color: var(--muted);
}
.stTabs [role="tab"][aria-selected="true"] {
  background: #FFFFFF; color: #111111; font-weight: 700;
  border-bottom: 2px solid #FFFFFF; margin-bottom: -1px;
}

.stCheckbox label { font-size: 13px; color: var(--text); }

/* ── Select ── */
.stSelectbox div[data-baseweb="select"] > div {
  border-radius: 8px !important; border-color: var(--border) !important;
}

@media (max-width: 400px) {
  .main .block-container { padding: 0 12px 80px 12px; }
}

@media (min-width: 900px) {
  .score-explainer,
  .ai-statusbar {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
  .score-explainer-card,
  .ai-stat {
    margin-bottom: 0 !important;
    border-radius: 8px;
  }
  .ai-statusbar {
    border-bottom: none;
  }
  .ai-task-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
}

@media (min-width: 1200px) {
  .main .block-container {
    max-width: 1180px;
  }
}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# Login
# ═══════════════════════════════════════════
from src.config import get_setting

# 页面导航只保留主页，股票详情等子页走单独路由，避免被顶部导航覆盖。
from src.ui.navigation import resolve_main_navigation
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
    f'<div class="top-chip">RESEARCH OS · {get_setting("phone","","")[:11]}</div>'
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
    ("research", "研究", "▣"),
    ("ai_chat", "AI", "◇"),
    ("lab", "审计", "✓"),
    ("profile", "我的", "⚙"),
]
cur = st.session_state["current_page"]
st.session_state.setdefault("_last_page", cur)

_tab_ids = [pid for pid, _, _ in TABS]
_labels = {pid: label for pid, label, icon in TABS}
nav_state = resolve_main_navigation(
    current_page=cur,
    selected_nav=st.session_state.get("main_nav"),
    last_nav_page=st.session_state.get("_last_nav_page", "market"),
    tab_pages=_tab_ids,
)

if nav_state["show_main_nav"]:
    selected_nav = st.segmented_control(
        "主导航",
        options=_tab_ids,
        default=nav_state["selected_nav"],
        format_func=lambda pid: _labels.get(pid, pid),
        key="main_nav",
        label_visibility="collapsed",
    )
    if selected_nav and selected_nav != cur:
        if st.session_state.get("_last_page") == "ai_chat" and selected_nav != "ai_chat":
            st.session_state.pop("qq", None)
            st.session_state.pop("ai_pending_prompt", None)
        st.session_state["current_page"] = selected_nav
        st.session_state["_last_page"] = selected_nav
        st.session_state["_last_nav_page"] = selected_nav
        st.rerun()
else:
    st.caption(f"当前子页：{cur} · 可用底部返回键回到上一页")

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

elif p == "research":
    from src.pages.research import render_research_page
    render_research_page()

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
