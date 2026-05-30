"""行情中心"""

import streamlit as st
from datetime import datetime
from src.data.realtime import get_top_stocks, get_market_overview


def _c(v):
    v = v or 0
    if v > 0: return "#f53b47"
    if v < 0: return "#00b468"
    return "#888"


def _amt(v):
    if not v: return "-"
    if v >= 1e8: return f"{v/1e8:.1f}亿"
    return f"{v:.0f}"


def render_market_page():
    # 搜索
    c1, c2 = st.columns([5, 1])
    with c1:
        q = st.text_input("", placeholder="搜索股票代码，如 600519", key="s", label_visibility="collapsed")
    with c2:
        if st.button("查询", key="go", use_container_width=True, type="primary"):
            if q.strip():
                st.session_state["selected_stock"] = q.strip()
                st.session_state["current_page"] = "stock_detail"
                st.rerun()

    # 大盘指数
    ov = get_market_overview()
    indices = ov.get("indices", [])
    if indices:
        html = '<div class="index-bar">'
        for idx in indices:
            p = idx.get("change_pct", 0)
            clr = _c(p)
            s = "+" if p > 0 else ""
            html += f'<div class="idx-card"><div class="idx-name">{idx.get("name")}</div><div class="idx-price" style="color:{clr}">{idx.get("price",0):.2f}</div><div class="idx-chg" style="color:{clr}">{s}{p:.2f}%</div></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

    st.caption(f"更新 {datetime.now().strftime('%H:%M:%S')}")

    # 排行榜
    t1, t2, t3, t4 = st.tabs(["涨幅榜", "跌幅榜", "成交额", "换手率"])

    def _show(stocks):
        if not stocks:
            st.info("暂无数据")
            return
        for i, s in enumerate(stocks):
            p = s.get("change_pct", 0) or 0
            clr = _c(p)
            nm = s.get("name") or s.get("code", "")
            cd = s.get("code", "")
            pr = s.get("price", 0) or 0
            am = _amt(s.get("amount", 0))
            st.markdown(f'<div class="stock-line"><div class="rk">{i+1}</div><div class="inf"><span class="nm">{nm}</span><span class="cd">{cd}</span></div><div class="pr" style="color:{clr}">¥{pr:.2f}</div><div class="ch" style="color:{clr}">{p:+.2f}%</div></div>', unsafe_allow_html=True)
            if st.button(f"查看 {cd}", key=f"s_{cd}_{i}"):
                st.session_state["selected_stock"] = cd
                st.session_state["current_page"] = "stock_detail"
                st.rerun()

    with t1: _show(get_top_stocks("f3", False, 20))
    with t2: _show(get_top_stocks("f3", True, 20))
    with t3: _show(get_top_stocks("f6", False, 20))
    with t4: _show(get_top_stocks("f8", False, 20))

    st.markdown("---")

    # 新闻
    st.subheader("财经快讯")
    if st.button("刷新", key="rn"):
        st.session_state.pop("news", None)
        st.rerun()

    if "news" not in st.session_state:
        try:
            from src.news.fetcher import fetch_all_news
            with st.spinner("加载中..."):
                st.session_state["news"] = fetch_all_news(18)
        except:
            st.session_state["news"] = []

    news = st.session_state.get("news", [])
    if not news:
        st.info("暂无新闻")
    else:
        for item in news:
            title = item.get("title", "")
            src = {"cls":"财联社","eastmoney":"东财"}.get(item.get("source",""),"")
            t = item.get("published_at", "")
            body = item.get("content", "")
            tag = ""
            if any(k in title for k in ["涨","牛","利好","突破"]):
                tag = '<span class="news-badge" style="background:#f53b4720;color:#f53b47;">利好</span>'
            elif any(k in title for k in ["跌","利空","风险","暴"]):
                tag = '<span class="news-badge" style="background:#00b46820;color:#00b468;">利空</span>'
            st.markdown(f'<div class="news-line"><div class="nt">{tag}{title}</div><div class="nm">{src} · {t}</div></div>', unsafe_allow_html=True)
            if body and body != title:
                with st.expander("详情"):
                    st.markdown(body)
