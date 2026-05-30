"""选股 - 实时评分排名"""

import streamlit as st
from src.scoring.engine import ScoringEngine

def render_watchlist_page():
    st.markdown("## 选股")

    c1, c2, c3 = st.columns(3)
    with c1: min_score = st.slider("最低分", 0, 100, 0)
    with c2: limit = st.number_input("数量", 5, 100, 30)
    with c3: rating_filter = st.selectbox("评级", ["全部", "强关注", "观察", "中性", "不追"])

    if "wl" not in st.session_state or not st.session_state["wl"]:
        with st.spinner("评分中..."):
            try:
                with ScoringEngine() as e:
                    st.session_state["wl"] = e.get_watchlist(min_score=0, limit=100)
            except Exception as ex:
                st.error(f"评分失败: {ex}")
                st.session_state["wl"] = []

    if st.button("刷新评分", type="primary", use_container_width=True):
        st.session_state.pop("wl", None)
        st.rerun()

    results = st.session_state.get("wl", [])
    if not results:
        st.info("暂无评分，点「刷新评分」")
        return

    if rating_filter != "全部":
        results = [r for r in results if r["rating"] == rating_filter]
    results = [r for r in results if r["total_score"] >= min_score]
    results = results[:limit]

    if not results:
        st.warning("无符合条件，降低最低分")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("强关注", sum(1 for r in results if r["rating"]=="强关注"), border=True)
    c2.metric("观察", sum(1 for r in results if r["rating"]=="观察"), border=True)
    c3.metric("中性", sum(1 for r in results if r["rating"]=="中性"), border=True)
    c4.metric("不追", sum(1 for r in results if r["rating"]=="不追"), border=True)

    st.markdown("---")

    rc = {"强关注":"#f53b47","观察":"#3399ff","中性":"#f0a030","不追":"#555"}
    fn = {"short_term_reversal":"反转","turnover_rate":"换手","volume_ratio":"量比","trend":"趋势","rsi":"RSI","macd":"MACD","kdj":"KDJ","blast_rate":"爆量","limit_up_streak":"连板","boll_position":"布林","market_temperature":"温度"}

    for i, s in enumerate(results):
        score = s["total_score"]
        rating = s["rating"]
        clr = rc.get(rating, "#888")
        name = s.get("name", s["code"])
        code = s["code"]
        factors = s.get("factors", {})
        top = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:5]
        ft = " · ".join(f"{fn.get(k,k)}:{v:.0f}" for k,v in top)

        st.markdown(f'<div style="display:flex;align-items:center;padding:0.5rem 0.7rem;background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:0.3rem;"><div style="color:var(--muted);font-size:0.78rem;width:28px;text-align:center;font-weight:600;">{i+1}</div><div style="flex:1;margin-left:0.4rem;"><span style="color:var(--text);font-weight:600;font-size:0.92rem;">{name}</span><span style="color:var(--muted);font-size:0.7rem;margin-left:0.3rem;">{code}</span><br><span style="color:var(--muted);font-size:0.72rem;">{ft}</span></div><div style="text-align:center;"><div style="font-size:1.3rem;font-weight:900;color:{clr};">{score:.0f}</div><span style="background:{clr};color:#fff;padding:1px 8px;border-radius:10px;font-size:0.7rem;">{rating}</span></div></div>', unsafe_allow_html=True)

        if st.button(f"查看 {name}", key=f"w_{code}_{i}"):
            st.session_state["selected_stock"] = code
            st.session_state["current_page"] = "stock_detail"
            st.rerun()
