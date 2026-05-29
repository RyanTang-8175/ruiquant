"""
市场概览页 - 实时数据 + 财经快讯
"""

import streamlit as st
from src.data.realtime import get_top_stocks, get_market_overview


def _fmt_amount(v):
    """格式化成交额"""
    if v is None or v == 0:
        return "0"
    if v >= 1e8:
        return f"{v/1e8:.1f}亿"
    elif v >= 1e4:
        return f"{v/1e4:.0f}万"
    return f"{v:.0f}"


def _color_pct(v):
    """涨跌幅颜色"""
    v = v or 0
    if v > 0:
        return "#FF4444"
    elif v < 0:
        return "#00E676"
    return "#888"


def render_market_page():
    """渲染市场概览"""
    st.markdown("## 行情中心")

    # ========== 大盘指数 ==========
    overview = get_market_overview()
    indices = overview.get("indices", [])

    if indices:
        cols = st.columns(len(indices))
        for i, idx in enumerate(indices):
            with cols[i]:
                pct = idx.get("change_pct", 0)
                color = _color_pct(pct)
                st.metric(
                    idx.get("name", ""),
                    f"{idx.get('price', 0):.2f}",
                    f"{pct:+.2f}%",
                    delta_color="off" if pct == 0 else ("normal" if pct > 0 else "inverse"),
                )

    st.markdown("---")

    # ========== 涨跌榜 ==========
    tab1, tab2, tab3, tab4 = st.tabs(["涨幅榜", "跌幅榜", "成交额榜", "换手率榜"])

    def _render_stock_list(stocks, show_field="change_pct", field_label="涨跌幅"):
        if not stocks:
            st.info("暂无数据")
            return
        for i, s in enumerate(stocks):
            pct = s.get("change_pct", 0)
            color = _color_pct(pct)
            amt = _fmt_amount(s.get("amount", 0))

            col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
            with col1:
                st.markdown(f"<div style='color:#6b7280;font-size:0.85rem;text-align:center;padding-top:8px;'>{i+1}</div>", unsafe_allow_html=True)
            with col2:
                name = s.get("name", s.get("code", ""))
                st.markdown(f"**{name}** `{s.get('code', '')}`")
            with col3:
                st.markdown(f"<div style='text-align:right;color:{color};font-weight:700;font-size:1.1rem;'>¥{s.get('price', 0):.2f}</div>", unsafe_allow_html=True)
            with col4:
                st.markdown(f"<div style='text-align:right;color:{color};font-weight:600;'>{pct:+.2f}%</div>", unsafe_allow_html=True)
                st.caption(f"成交 {amt}")

    with tab1:
        gainers = get_top_stocks(sort_field="f3", asc=False, limit=20)
        _render_stock_list(gainers)

    with tab2:
        losers = get_top_stocks(sort_field="f3", asc=True, limit=20)
        _render_stock_list(losers)

    with tab3:
        volume = get_top_stocks(sort_field="f6", asc=False, limit=20)
        _render_stock_list(volume)

    with tab4:
        turnover = get_top_stocks(sort_field="f8", asc=False, limit=20)
        _render_stock_list(turnover)

    st.markdown("---")

    # ========== 财经快讯 ==========
    st.subheader("财经快讯")

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("刷新新闻", key="refresh_news"):
            st.session_state.pop("cached_news", None)
            st.rerun()

    # 获取新闻
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
            source = item.get("source", "")
            pub_time = item.get("published_at", "")
            content = item.get("content", "")

            source_tag = {"cls": "财联社", "eastmoney": "东方财富"}.get(source, source)

            with st.expander(f"📰 {title}", expanded=False):
                st.markdown(f"**来源**: {source_tag} | **时间**: {pub_time}")
                if content and content != title:
                    st.markdown(content)
