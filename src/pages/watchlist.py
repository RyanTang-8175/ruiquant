"""选股 — 排行榜数据 + 行业/概念筛选 + 评分"""

import streamlit as st
from src.scoring.engine import ScoringEngine
from src.data.realtime import get_top_stocks
from src.data.stock_list import SW_INDUSTRY, CONCEPTS

def render_watchlist_page():
    st.markdown("## 选股")

    kw = st.text_input("", placeholder="搜索代码/名称 如茅台、600519、平安...", key="sk", label_visibility="collapsed")

    c1, c2, c3, c4 = st.columns(4)
    with c1: sel_ind = st.selectbox("行业", ["全部"] + sorted(SW_INDUSTRY.keys()), key="ind")
    with c2: sel_con = st.selectbox("概念", ["全部"] + sorted(CONCEPTS.keys()), key="con")
    with c3: mn = st.slider("最低分", 0, 100, 0, key="mn")
    with c4: lm = st.number_input("数量", 5, 100, 30, key="lm")

    if st.button("搜索 / 刷新", type="primary", use_container_width=True):
        st.session_state.pop("sr", None); st.rerun()

    if "sr" not in st.session_state:
        with st.spinner("评分中..."):
            stocks = get_top_stocks(sort_field="amount", asc=False, limit=100)

            if sel_ind != "全部":
                ind_codes = set(SW_INDUSTRY.get(sel_ind, []))
                stocks = [s for s in stocks if s['code'] in ind_codes]
            if sel_con != "全部":
                con_codes = set(CONCEPTS.get(sel_con, []))
                stocks = [s for s in stocks if s['code'] in con_codes]

            if kw.strip():
                kwu = kw.strip().upper()
                stocks = [s for s in stocks if kwu in s.get('code','') or kwu in s.get('name','').upper()]

            results = []
            try:
                with ScoringEngine() as e:
                    for s in stocks:
                        r = e.score_stock(s['code'])
                        if r: r['name'] = s.get('name', r.get('code','')); results.append(r)
            except Exception as ex: st.error(f"评分失败: {ex}")

            results.sort(key=lambda x: x['total_score'], reverse=True)
            st.session_state["sr"] = results

    results = st.session_state.get("sr", [])
    if not results: st.info("无匹配"); return

    results = [r for r in results if r['total_score'] >= mn][:lm]
    if not results: st.warning("无符合条件"); return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("强关注", sum(1 for r in results if r['rating']=="强关注"), border=True)
    c2.metric("观察", sum(1 for r in results if r['rating']=="观察"), border=True)
    c3.metric("中性", sum(1 for r in results if r['rating']=="中性"), border=True)
    c4.metric("不追", sum(1 for r in results if r['rating']=="不追"), border=True)

    st.markdown("---")

    rc = {"强关注":"#FF3B30","观察":"#3399FF","中性":"#FFB800","不追":"#555"}
    fn = {"momentum":"动","turnover":"换","volatility":"波","volume_ratio":"量","trend":"趋"}

    for i, s in enumerate(results):
        score = s["total_score"]; rating = s["rating"]
        clr = rc.get(rating, "#888")
        name = s.get("name", s["code"]); code = s["code"]
        factors = s.get("factors", {})
        top = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:5]
        ft = " . ".join(f"{fn.get(k,k)}:{v:.0f}" for k, v in top)

        st.markdown(f'<div style="display:flex;align-items:center;padding:.5rem .7rem;background:#131510;border:1px solid #2A2B26;margin-bottom:.2rem;"><div style="color:#6B6C68;font-family:JetBrains Mono,monospace;font-size:.72rem;width:26px;text-align:center;">{i+1}</div><div style="flex:1;margin-left:.4rem;"><span style="color:#E8E8E5;font-weight:600;font-size:.9rem;">{name}</span><span style="color:#6B6C68;font-family:JetBrains Mono,monospace;font-size:.68rem;margin-left:.3rem;">{code}</span><div style="color:#6B6C68;font-size:.72rem;margin-top:.1rem;">{ft}</div></div><div style="text-align:center;"><div style="font-size:1.3rem;font-weight:700;color:{clr};font-family:JetBrains Mono,monospace;">{score:.0f}</div><span style="background:{clr};color:#fff;padding:1px 8px;font-family:JetBrains Mono,monospace;font-size:.7rem;">{rating}</span></div></div>', unsafe_allow_html=True)

        if st.button(f"VIEW {name}", key=f"wl_{code}_{i}"):
            st.session_state["selected_stock"] = code
            st.session_state["current_page"] = "stock_detail"
            st.rerun()
