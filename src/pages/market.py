"""行情中心"""

import streamlit as st
from datetime import datetime
from src.data.realtime import get_top_stocks, get_market_overview
from src.data.quality import get_quality_badge, fmt_freshness, render_quality_html, FALLBACK_WARNING


def _c(v):
    v = v or 0
    if v > 0: return "#F04438"
    if v < 0: return "#12B76A"
    return "#9AA4B2"


def render_market_page():
    # ── 全局模糊搜索 ──
    from src.ui.search import render_search_bar
    code = render_search_bar(key="market")
    if code:
        st.session_state["selected_stock"] = code
        st.session_state["previous_page"] = "market"
        st.session_state["current_page"] = "stock_detail"
        st.rerun()

    # ── 指数条 ──
    ov = get_market_overview()
    indices = ov.get("indices", [])

    # Phase 1.3: 数据源质量标签
    if ov.get("_fallback"):
        st.warning(FALLBACK_WARNING, icon="⚠️")
    elif ov.get("source"):
        badge = get_quality_badge(ov["source"])
        ts = ov.get("_ts")
        freshness = f" · {fmt_freshness(ts)}" if ts else ""
        st.caption(f"📡 {badge['label']} · 质量{badge['level']}{freshness}")

    if indices:
        h = '<div class="idx-strip">'
        for idx in indices:
            p = idx.get("change_pct", 0)
            cl = _c(p)
            s = "+" if p > 0 else ""
            h += (
                f'<div class="idx-cell">'
                f'<div class="n">{idx.get("name")}</div>'
                f'<div class="p" style="color:{cl}">{idx.get("price",0):.2f}</div>'
                f'<div class="c" style="color:{cl}">{s}{p:.2f}%</div>'
                f'</div>'
            )
        h += '</div>'
        st.markdown(h, unsafe_allow_html=True)

    st.caption(f"更新 {datetime.now().strftime('%H:%M:%S')}")

    # ── 四大榜单 ──
    t1, t2, t3, t4 = st.tabs(["涨幅榜", "跌幅榜", "成交额", "换手率"])

    def _stock_list(stocks, prefix):
        if not stocks:
            st.info("暂无数据")
            return
        # Phase 1.3: 检查是否兜底
        if stocks and stocks[0].get("_fallback"):
            st.warning(FALLBACK_WARNING, icon="⚠️")
        for i, s in enumerate(stocks):
            p = s.get("change_pct", 0) or 0
            cl = _c(p)
            nm = s.get("name") or s.get("code", "")
            cd = s.get("code", "")
            pr = s.get("price", 0) or 0
            q_html = render_quality_html(s)
            st.markdown(
                f'<div class="sr">'
                f'<div style="color:var(--muted);font-family:var(--mono);font-size:12px;width:24px;text-align:center">{i+1}</div>'
                f'<div class="inf"><span class="nm">{nm}</span>'
                f'<span class="cd">{cd}</span> {q_html}</div>'
                f'<div class="pr" style="color:{cl}">{pr:.2f}</div>'
                f'<div class="ch" style="color:{cl}">{p:+.2f}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("查看", key=f"{prefix}{cd}_{i}"):
                st.session_state["selected_stock"] = cd
                st.session_state["previous_page"] = "market"
                st.session_state["current_page"] = "stock_detail"
                st.rerun()

    with t1:
        _stock_list(get_top_stocks("changepercent", False, 20), "up_")
    with t2:
        _stock_list(get_top_stocks("changepercent", True, 20), "dn_")
    with t3:
        _stock_list(get_top_stocks("amount", False, 20), "am_")
    with t4:
        _stock_list(get_top_stocks("turnoverratio", False, 20), "tr_")

    # ── 快讯 ──
    st.markdown("---")
    st.markdown('<div class="sec-h">快讯</div>', unsafe_allow_html=True)

    # 源筛选
    srcs = ["全部","新浪","东财","财联社","腾讯","华尔街见闻"]
    src_key = "ns_src"
    st.session_state.setdefault(src_key, "全部")
    scols = st.columns(6)
    for i, s in enumerate(srcs):
        with scols[i]:
            if st.button(s, key=f"nss_{s}", use_container_width=True,
                         type="primary" if st.session_state[src_key]==s else "secondary"):
                st.session_state[src_key]=s; st.rerun()

    # 类别筛选
    cats = ["全部","政策","板块","公司","宏观"]
    cat_key = "ns_cat"
    st.session_state.setdefault(cat_key, "全部")
    ccols = st.columns(5)
    for i, c in enumerate(cats):
        with ccols[i]:
            if st.button(c, key=f"nsc_{c}", use_container_width=True,
                         type="primary" if st.session_state[cat_key]==c else "secondary"):
                st.session_state[cat_key]=c; st.rerun()

    # 拉取
    if "nsd" not in st.session_state:
        with st.spinner("加载中..."):
            from src.news.fetcher import fetch_all_news
            st.session_state["nsd"] = fetch_all_news(60)
    ns = st.session_state["nsd"]

    # 过滤
    src = st.session_state[src_key]
    cat = st.session_state[cat_key]
    if src != "全部": ns = [n for n in ns if n.get("source")==src]
    if cat != "全部": ns = [n for n in ns if n.get("category")==cat]

    if not ns:
        st.info("暂无新闻")
    else:
        st.caption(f"{len(ns)} 条")
        for it in ns[:30]:
            t = it.get("title",""); s = it.get("source","")
            pt = it.get("published_at",""); body = it.get("content","")
            cn = it.get("category",""); codes = it.get("related_codes",[])

            tags = []
            if cn=="policy": tags.append('<span class="badge badge-ai">政策</span>')
            elif cn=="sector": tags.append('<span class="badge badge-low">板块</span>')
            elif cn=="company": tags.append('<span class="badge badge-mid">公司</span>')
            if any(k in t for k in ["涨","牛","利好","突破","涨停"]):
                tags.append('<span class="badge badge-low">利好</span>')
            elif any(k in t for k in ["跌","利空","风险","暴雷","退市"]):
                tags.append('<span class="badge badge-high">利空</span>')

            cs = ""
            if codes:
                cs = '<div style="margin-top:4px">'+" ".join(
                    f'<span style="font-family:var(--mono);font-size:10px;color:var(--ai)">{c}</span>'
                    for c in codes[:3])+'</div>'

            st.markdown(
                f'<div class="ni"><div class="nt">{" ".join(tags)} {t}</div>'
                f'<div class="nm">{s} · {pt}</div>{cs}</div>',
                unsafe_allow_html=True)
            if body and body != t:
                with st.expander(t[:40]+"..."):
                    st.caption(body)

    if st.button("刷新新闻", key="rn2", use_container_width=True):
        st.session_state.pop("nsd",None); st.rerun()
