"""选股 - Industrial"""

import streamlit as st
from src.scoring.engine import ScoringEngine

def render_watchlist_page():
    st.markdown("## SCREENING")
    c1,c2,c3 = st.columns(3)
    with c1: mn = st.slider("MIN", 0, 100, 0)
    with c2: lm = st.number_input("NUM", 5, 100, 30)
    with c3: rf = st.selectbox("RATING", ["ALL","强关注","观察","中性","不追"])

    if "wl" not in st.session_state or not st.session_state["wl"]:
        with st.spinner("..."):
            try:
                with ScoringEngine() as e: st.session_state["wl"] = e.get_watchlist(min_score=0, limit=100)
            except Exception as ex: st.error(f"ERR: {ex}"); st.session_state["wl"] = []

    if st.button("RESCORE", type="primary", use_container_width=True):
        st.session_state.pop("wl",None); st.rerun()

    results = st.session_state.get("wl",[])
    if not results: st.info("NO DATA"); return
    if rf != "ALL": results = [r for r in results if r["rating"]==rf]
    results = [r for r in results if r["total_score"]>=mn][:lm]
    if not results: st.warning("NO MATCH"); return

    rc = {"强关注":"#FF3B30","观察":"#3399FF","中性":"#FFB800","不追":"#555"}
    fn = {"short_term_reversal":"REV","turnover_rate":"TURN","volume_ratio":"VOL","trend":"TREND","rsi":"RSI","macd":"MACD","kdj":"KDJ","blast_rate":"BLAST","limit_up_streak":"LIMIT","boll_position":"BOLL","market_temperature":"TEMP"}
    for i,s in enumerate(results):
        score=s["total_score"];rating=s["rating"];clr=rc.get(rating,"#888")
        name=s.get("name",s["code"]);code=s["code"]
        factors=s.get("factors",{})
        top=sorted(factors.items(),key=lambda x:x[1],reverse=True)[:5]
        ft=" . ".join(f"{fn.get(k,k)}:{v:.0f}" for k,v in top)
        st.markdown(f'<div style="display:flex;align-items:center;padding:.5rem .7rem;background:#131510;border:1px solid #2A2B26;margin-bottom:.2rem;"><div style="color:#6B6C68;font-family:JetBrains Mono,monospace;font-size:.72rem;width:26px;text-align:center;">{i+1}</div><div style="flex:1;margin-left:.4rem;"><span style="color:#E8E8E5;font-weight:600;font-size:.9rem;">{name}</span><span style="color:#6B6C68;font-family:JetBrains Mono,monospace;font-size:.68rem;margin-left:.3rem;">{code}</span><div style="color:#6B6C68;font-size:.72rem;margin-top:.1rem;">{ft}</div></div><div style="text-align:center;"><div style="font-size:1.3rem;font-weight:700;color:{clr};font-family:JetBrains Mono,monospace;">{score:.0f}</div><span style="background:{clr};color:#fff;padding:1px 8px;font-family:JetBrains Mono,monospace;font-size:.7rem;">{rating}</span></div></div>',unsafe_allow_html=True)
        if st.button(f"VIEW {name}",key=f"w_{code}_{i}"):
            st.session_state["selected_stock"]=code;st.session_state["current_page"]="stock_detail";st.rerun()
