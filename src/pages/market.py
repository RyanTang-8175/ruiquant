"""行情中心"""

import streamlit as st
from datetime import datetime
from src.data.realtime import get_top_stocks, get_market_overview


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
        st.session_state["current_page"] = "stock_detail"
        st.rerun()

    # ── 指数条 ──
    ov = get_market_overview()
    indices = ov.get("indices", [])
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
    titles = ["涨幅榜", "跌幅榜", "成交额", "换手率"]

    def _stock_list(stocks, prefix):
        if not stocks:
            st.info("暂无数据")
            return
        for i, s in enumerate(stocks):
            p = s.get("change_pct", 0) or 0
            cl = _c(p)
            nm = s.get("name") or s.get("code", "")
            cd = s.get("code", "")
            pr = s.get("price", 0) or 0
            st.markdown(
                f'<div class="sr">'
                f'<div style="color:var(--muted);font-family:var(--mono);font-size:12px;width:24px;text-align:center">{i+1}</div>'
                f'<div class="inf"><span class="nm">{nm}</span>'
                f'<span class="cd">{cd}</span></div>'
                f'<div class="pr" style="color:{cl}">{pr:.2f}</div>'
                f'<div class="ch" style="color:{cl}">{p:+.2f}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("查看", key=f"{prefix}{cd}_{i}"):
                st.session_state["selected_stock"] = cd
                st.session_state["current_page"] = "stock_detail"
                st.rerun()

    with t1:
        _stock_list(get_top_stocks("changepercent", True, 20), "up_")
    with t2:
        _stock_list(get_top_stocks("changepercent", False, 20), "dn_")
    with t3:
        _stock_list(get_top_stocks("amount", False, 20), "am_")
    with t4:
        _stock_list(get_top_stocks("turnoverratio", False, 20), "tr_")

    # ── 快讯 ──
    st.markdown("---")
    st.markdown('<div class="sec-h">快讯</div>', unsafe_allow_html=True)
    if st.button("刷新", key="rn"):
        st.session_state.pop("ns", None)
        st.rerun()
    if "ns" not in st.session_state:
        try:
            from src.news.fetcher import fetch_all_news
            with st.spinner("加载新闻..."):
                st.session_state["ns"] = fetch_all_news(18)
        except Exception:
            st.session_state["ns"] = []
    ns = st.session_state.get("ns", [])
    if not ns:
        st.info("暂无新闻")
    else:
        for it in ns:
            t = it.get("title", "")
            src = {"cls": "财联社", "eastmoney": "东财"}.get(it.get("source", ""), "")
            pt = it.get("published_at", "")
            tg = ""
            if any(k in t for k in ["涨", "牛", "利好", "突破"]):
                tg = '<span class="badge badge-low">利好</span> '
            elif any(k in t for k in ["跌", "利空", "风险", "暴雷"]):
                tg = '<span class="badge badge-high">利空</span> '
            st.markdown(
                f'<div class="ni"><div class="nt">{tg}{t}</div>'
                f'<div class="nm">{src} · {pt}</div></div>',
                unsafe_allow_html=True,
            )
