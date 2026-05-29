"""
市场概览 - 实时行情 + 财经快讯 + 股票搜索
"""

import streamlit as st
from datetime import datetime
from src.data.realtime import get_top_stocks, get_market_overview, get_realtime_quote


def _color_pct(v):
    v = v or 0
    if v > 0: return "#FF4444"
    if v < 0: return "#00E676"
    return "#888"


def _fmt_amount(v):
    if not v: return "0"
    if v >= 1e8: return f"{v/1e8:.1f}亿"
    if v >= 1e4: return f"{v/1e4:.0f}万"
    return f"{v:.0f}"


def render_market_page():
    """市场概览"""
    st.markdown("## 行情中心")

    # 股票搜索
    search_col1, search_col2 = st.columns([4, 1])
    with search_col1:
        search_code = st.text_input("搜索股票", placeholder="输入股票代码，如 600519", key="stock_search", label_visibility="collapsed")
    with search_col2:
        if st.button("查询", key="search_btn", use_container_width=True):
            if search_code.strip():
                st.session_state["selected_stock"] = search_code.strip()
                st.session_state["current_page"] = "stock_detail"
                st.rerun()

    # 大盘指数
    overview = get_market_overview()
    indices = overview.get("indices", [])
    if indices:
        cols = st.columns(len(indices))
        for i, idx in enumerate(indices):
            with cols[i]:
                pct = idx.get("change_pct", 0)
                st.metric(
                    idx.get("name", ""),
                    f"{idx.get('price', 0):.2f}",
                    f"{pct:+.2f}%",
                    delta_color="off",
                )

    # 数据更新时间
    st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    st.markdown("---")

    # 涨跌榜
    tab1, tab2, tab3, tab4 = st.tabs(["涨幅榜", "跌幅榜", "成交额榜", "换手率榜"])

    def _render_list(stocks):
        if not stocks:
            st.info("暂无数据（非交易时间显示上一交易日数据）")
            return
        for i, s in enumerate(stocks):
            pct = s.get("change_pct", 0)
            color = _color_pct(pct)
            amt = _fmt_amount(s.get("amount", 0))

            c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
            with c1:
                st.markdown(f"<div style='color:#6b7280;font-size:0.85rem;text-align:center;padding-top:8px;'>{i+1}</div>", unsafe_allow_html=True)
            with c2:
                name = s.get("name", s.get("code", ""))
                if st.button(f"{name} {s.get('code', '')}", key=f"stk_{s.get('code','')}_{i}", use_container_width=True):
                    st.session_state["selected_stock"] = s.get("code", "")
                    st.session_state["current_page"] = "stock_detail"
                    st.rerun()
            with c3:
                st.markdown(f"<div style='text-align:right;color:{color};font-weight:700;font-size:1.1rem;'>¥{s.get('price', 0):.2f}</div>", unsafe_allow_html=True)
            with c4:
                st.markdown(f"<div style='text-align:right;color:{color};font-weight:600;'>{pct:+.2f}%</div>", unsafe_allow_html=True)
                st.caption(f"成交 {amt}")

    with tab1:
        _render_list(get_top_stocks(sort_field="f3", asc=False, limit=20))
    with tab2:
        _render_list(get_top_stocks(sort_field="f3", asc=True, limit=20))
    with tab3:
        _render_list(get_top_stocks(sort_field="f6", asc=False, limit=20))
    with tab4:
        _render_list(get_top_stocks(sort_field="f8", asc=False, limit=20))

    st.markdown("---")

    # 财经快讯
    st.subheader("财经快讯")

    if st.button("刷新新闻", key="refresh_news"):
        st.session_state.pop("cached_news", None)
        st.rerun()

    if "cached_news" not in st.session_state:
        try:
            from src.news.fetcher import fetch_all_news
            with st.spinner("加载新闻..."):
                st.session_state["cached_news"] = fetch_all_news(20)
        except Exception as e:
            st.session_state["cached_news"] = []
            st.warning(f"新闻加载失败: {e}")

    news_list = st.session_state.get("cached_news", [])
    if not news_list:
        st.info("暂无新闻，点击「刷新新闻」获取")
    else:
        for item in news_list:
            title = item.get("title", "")
            source = {"cls": "财联社", "eastmoney": "东方财富"}.get(item.get("source", ""), item.get("source", ""))
            pub_time = item.get("published_at", "")
            content = item.get("content", "")

            with st.expander(f"📰 {title}", expanded=False):
                st.caption(f"{source} | {pub_time}")
                if content and content != title:
                    st.markdown(content)
