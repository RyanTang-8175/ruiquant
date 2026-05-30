"""AlphaEye v5 — A股反量化AI助手 · Industrial"""

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="AlphaEye",page_icon="📊",layout="wide",initial_sidebar_state="collapsed")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

:root{--bg:#0B0C0A;--card:#131510;--border:#2A2B26;--text:#E8E8E5;--muted:#6B6C68;--red:#FF3B30;--green:#00D26A;--amber:#FFB800;--blue:#3399FF;--mono:'JetBrains Mono',monospace;--sans:'Inter',-apple-system,'PingFang SC',sans-serif}
*{font-family:var(--sans);box-sizing:border-box}
.stApp{background:var(--bg)}.stApp>header{background:transparent!important}
#MainMenu,footer,header{visibility:hidden}.stDeployButton{display:none}
section[data-testid="stSidebar"]{display:none}
.main .block-container{padding:.4rem 1rem;max-width:800px;margin:0 auto}

.topbar{display:flex;justify-content:space-between;align-items:center;padding:.5rem 0;border-bottom:1px solid var(--border);margin-bottom:.5rem}
.logo{font-family:var(--mono);font-size:1.2rem;font-weight:700;color:var(--red);letter-spacing:-.5px}
.logo span{color:var(--text);font-weight:500}

.ticker{overflow-x:auto;white-space:nowrap;padding:.4rem 0;border-bottom:1px solid var(--border);margin-bottom:.5rem;font-family:var(--mono);font-size:.78rem;-webkit-overflow-scrolling:touch}.ticker::-webkit-scrollbar{display:none}
.ti{display:inline-block;margin-right:1.2rem;font-family:var(--mono)}.tn{color:var(--muted);font-family:var(--mono)}.tv{font-family:var(--mono);font-weight:600}

.tab-nav{display:flex;border-bottom:1px solid var(--border);margin-bottom:.6rem}
.tab-nav div{flex:1;text-align:center;padding:.55rem 0;font-size:.8rem;font-weight:600;color:var(--muted);border-bottom:2px solid transparent;font-family:var(--mono);text-transform:uppercase;letter-spacing:.5px}
.tab-nav div:hover{color:var(--text)}.tab-nav .on{color:var(--amber);border-bottom-color:var(--amber)}

.idx-row{display:flex;gap:.4rem;margin-bottom:.6rem;overflow-x:auto;-webkit-overflow-scrolling:touch}.idx-row::-webkit-scrollbar{display:none}
.idx-cell{flex:1;min-width:110px;background:var(--card);border:1px solid var(--border);padding:.6rem .7rem;text-align:center}
.idx-cell .n{color:var(--muted);font-size:.7rem;font-family:var(--mono);text-transform:uppercase;letter-spacing:.5px}
.idx-cell .p{font-size:1.1rem;font-weight:700;font-family:var(--mono);margin:.15rem 0}.idx-cell .c{font-size:.8rem;font-weight:600;font-family:var(--mono)}

.sr{display:flex;align-items:center;padding:.55rem 1px;border-bottom:1px solid var(--border)}.sr:active{background:var(--card)}
.sr .rk{color:var(--muted);font-family:var(--mono);font-size:.72rem;width:26px;text-align:center}.sr .inf{flex:1;margin-left:.4rem}
.sr .nm{color:var(--text);font-weight:600;font-size:.9rem}.sr .cd{color:var(--muted);font-size:.68rem;font-family:var(--mono)}
.sr .pr{font-family:var(--mono);font-weight:600;font-size:.9rem;text-align:right;min-width:75px}.sr .ch{font-family:var(--mono);font-weight:600;font-size:.82rem;text-align:right;min-width:65px}

.ni{padding:.55rem 0;border-bottom:1px solid var(--border)}.ni .nt{color:var(--text);font-size:.85rem;line-height:1.4}.ni .nm{color:var(--muted);font-size:.7rem;margin-top:.15rem;font-family:var(--mono)}
.bg{display:inline-block;padding:1px 5px;font-size:.65rem;font-weight:700;font-family:var(--mono);text-transform:uppercase;letter-spacing:.5px;margin-right:.3rem}

.stButton>button{font-family:var(--mono);font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px;border:1px solid var(--border);background:var(--card);color:var(--text);padding:.35rem .9rem;transition:all .1s}
.stButton>button:hover{border-color:#3D3E39;background:#181A15}
.stButton>button[kind="primary"]{background:var(--amber);color:#000;border-color:var(--amber);font-weight:700}
.stButton>button[kind="primary"]:hover{background:#FFCC33;border-color:#FFCC33}

.stTabs [data-baseweb="tab-list"]{gap:0;background:transparent;border-bottom:1px solid var(--border)}
.stTabs [data-baseweb="tab"]{font-family:var(--mono);font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);padding:.4rem .8rem;border-radius:0}
.stTabs [aria-selected="true"]{color:var(--amber);border-bottom:2px solid var(--amber);background:transparent}

.stTextInput input{background:var(--card)!important;border:1px solid var(--border)!important;color:var(--text)!important;font-family:var(--mono)!important;font-size:.85rem!important;padding:.45rem .7rem!important}
.stTextInput input:focus{border-color:var(--amber)!important}

[data-testid="stMetric"]{background:var(--card)!important;border:1px solid var(--border)!important;padding:.5rem!important}
[data-testid="stMetric"] label{font-family:var(--mono)!important;font-size:.65rem!important;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)!important}
[data-testid="stMetric"] [data-testid="stMetricValue"]{font-family:var(--mono)!important;font-size:1.1rem!important;font-weight:700!important}

[data-testid="stExpander"]{background:var(--card)!important;border:1px solid var(--border)!important}
[data-testid="stChatMessage"]{background:var(--card);border:1px solid var(--border);font-size:.85rem}

hr{border-color:var(--border)!important;margin:.5rem 0!important}
h2{color:var(--text);font-weight:700;font-size:1.05rem;margin:.6rem 0 .3rem;font-family:var(--mono);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);padding-bottom:.3rem}
h3{color:var(--text);font-weight:600;font-size:.9rem;font-family:var(--mono);text-transform:uppercase;letter-spacing:.5px}
small{color:var(--muted)!important;font-family:var(--mono)!important}
code{color:var(--amber);background:var(--card);font-family:var(--mono);padding:1px 3px}
@media(max-width:500px){.main .block-container{padding:.3rem .6rem}}
</style>""",unsafe_allow_html=True)

# ── 登录持久化 ──
from src.config import get_setting
st.session_state.setdefault("logged_in",bool(get_setting("phone","","")))
if not st.session_state["logged_in"]:
    from src.pages.login import render_login_page
    render_login_page()
    st.stop()

# ── 顶栏 ──
st.markdown(f'<div class="topbar"><div class="logo">A<span>lphaEye</span></div><div style="font-family:var(--mono);font-size:.7rem;color:var(--muted)">{get_setting("phone","","")[:11]}</div></div>',unsafe_allow_html=True)

# ── 滚动行情条 ──
from src.data.realtime import get_market_overview
ov = get_market_overview()
indices = ov.get("indices",[])
if indices:
    t = '<div class="ticker">'
    for idx in indices:
        p = idx.get("change_pct",0)
        c = "#FF3B30" if p>0 else "#00D26A" if p<0 else "#6B6C68"
        s = "+" if p>0 else ""
        t += f'<span class="ti"><span class="tn">{idx.get("name")}</span><span class="tv" style="color:{c}">{idx.get("price",0):.2f} {s}{p:.2f}%</span></span>'
    t += '</div>'
    st.markdown(t,unsafe_allow_html=True)

# ── 状态 ──
st.session_state.setdefault("current_page","market")
st.session_state.setdefault("selected_stock","")

# ── 导航 ──
tabs=[("market","行情"),("watchlist","选股"),("ai_chat","AI"),("profile","我的")]
cur=st.session_state["current_page"]
th='<div class="tab-nav">'
for pid,label in tabs:
    th+=f'<div class="tab-nav-item {"on" if pid==cur else ""}">{label}</div>'
th+='</div>'
st.markdown(th,unsafe_allow_html=True)

cols=st.columns(len(tabs))
for i,(pid,label) in enumerate(tabs):
    with cols[i]:
        if st.button(label,key=f"n_{pid}",use_container_width=True,type="primary" if pid==cur else "secondary"):
            st.session_state["current_page"]=pid;st.rerun()

# ── 路由 ──
p=st.session_state["current_page"]
if p=="market":
    from src.pages.market import render_market_page;render_market_page()
elif p=="watchlist":
    from src.pages.watchlist import render_watchlist_page;render_watchlist_page()
elif p=="stock_detail":
    c=st.session_state.get("selected_stock","")
    if c:
        from src.pages.stock_detail import render_stock_detail_page;render_stock_detail_page(c)
    else:st.warning("请先选择股票")
elif p=="ai_chat":
    from src.pages.ai_chat import render_ai_chat_page;render_ai_chat_page()
elif p=="trading":
    from src.pages.trading import render_trading_page;render_trading_page()
elif p=="profile":
    from src.pages.profile import render_profile_page;render_profile_page()
