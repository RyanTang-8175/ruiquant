"""选股 — 排行榜数据 + 行业/概念筛选 + 评分"""

import streamlit as st
from src.scoring.engine import ScoringEngine
from src.data.realtime import get_top_stocks
from src.data.stock_list import SW_INDUSTRY, CONCEPTS

def render_watchlist_page():
    st.markdown("## 选股")
    st.markdown(
        '<div class="page-kicker">先筛候选，再交给 AI 做研究审计。分数越高代表越值得研究，不代表可以追高。</div>',
        unsafe_allow_html=True,
    )

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

    st.markdown(
        '<div class="score-explainer">'
        '<div class="score-explainer-card"><div class="score-explainer-title">总分怎么看？</div>'
        '<div class="score-explainer-copy">总分=动量、换手、波动、量能、趋势的综合初筛。它只说明“值得研究程度”，不是买入信号。</div></div>'
        '<div class="score-explainer-card"><div class="score-explainer-title">为什么还要研究审计？</div>'
        '<div class="score-explainer-copy">AI 会把可观察股票自动写成假设，收盘后回放 T+1/T+2/T+3，看当时判断到底对不对。</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

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

        readable_rating = {
            "强关注": "值得深入研究",
            "观察": "可加入观察",
            "中性": "先放一放",
            "不追": "不适合追高",
        }.get(rating, rating)
        st.markdown(
            f'<div class="watch-card">'
            f'<div style="display:flex;gap:10px;align-items:flex-start">'
            f'<div class="watch-rank">{i+1}</div>'
            f'<div style="flex:1;min-width:0">'
            f'<div class="watch-title">{name}<span class="watch-code">{code}</span></div>'
            f'<div class="watch-sub">{ft or "暂无因子"} · {readable_rating}</div>'
            f'</div>'
            f'<div style="text-align:right;min-width:70px">'
            f'<div class="watch-score" style="color:{clr}">{score:.0f}</div>'
            f'<span class="badge {"badge-high" if rating=="强关注" else "badge-ai" if rating=="观察" else "badge-mid" if rating=="中性" else "badge-low"}">{rating}</span>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

        c_view, c_research, c_ai = st.columns(3)
        with c_view:
            clicked = st.button(f"查看 {name}", key=f"wl_{code}_{i}", use_container_width=True)
        with c_research:
            research = st.button("研究底稿", key=f"wl_research_{code}_{i}", use_container_width=True)
        with c_ai:
            audit = st.button("AI研究审计", key=f"wl_ai_{code}_{i}", use_container_width=True)
        if clicked:
            st.session_state["selected_stock"] = code
            st.session_state["current_page"] = "stock_detail"
            st.rerun()
        if research:
            st.session_state["selected_stock"] = code
            st.session_state["research_code"] = code
            st.session_state["current_page"] = "research"
            st.rerun()
        if audit:
            st.session_state["selected_stock"] = code
            st.session_state["current_page"] = "ai_chat"
            st.session_state["qq"] = (
                f"请对 {code} 做完整研究审计。必须给机会分、风险分、置信度，并用括号解释含义；"
                "输出结论摘要、数据状态、证据表、反量化风险表、交易计划表、反证与失效条件，最后自动生成研究审计字段。"
            )
            st.rerun()
