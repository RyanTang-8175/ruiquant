"""
行情中心 - 参考同花顺/东方财富设计
实时数据 + 板块热点 + 涨跌榜 + 新闻
"""

import streamlit as st
from datetime import datetime
from src.data.realtime import get_top_stocks, get_market_overview, get_realtime_quote


def _c(v):
    """涨跌颜色"""
    v = v or 0
    if v > 0: return "#FF4444"
    if v < 0: return "#00E676"
    return "#888"


def _amt(v):
    """成交额格式化"""
    if not v: return "-"
    if v >= 1e8: return f"{v/1e8:.1f}亿"
    if v >= 1e4: return f"{v/1e4:.0f}万"
    return f"{v:.0f}"


def render_market_page():
    # ===== 搜索栏 =====
    c1, c2 = st.columns([5, 1])
    with c1:
        code = st.text_input("", placeholder="🔍 输入股票代码或名称搜索，如 600519", key="search_input", label_visibility="collapsed")
    with c2:
        if st.button("查询", key="go_search", use_container_width=True, type="primary"):
            if code.strip():
                st.session_state["selected_stock"] = code.strip()
                st.session_state["current_page"] = "stock_detail"
                st.rerun()

    # ===== 大盘指数 =====
    overview = get_market_overview()
    indices = overview.get("indices", [])
    if indices:
        idx_html = '<div class="index-strip">'
        for idx in indices:
            pct = idx.get("change_pct", 0)
            color = _c(pct)
            sign = "+" if pct > 0 else ""
            idx_html += f'''
            <div class="index-item">
                <div class="name">{idx.get("name","")}</div>
                <div class="price" style="color:{color}">{idx.get("price",0):.2f}</div>
                <div class="pct" style="color:{color}">{sign}{pct:.2f}%</div>
            </div>'''
        idx_html += '</div>'
        st.markdown(idx_html, unsafe_allow_html=True)

    st.caption(f"数据更新: {datetime.now().strftime('%H:%M:%S')} | 非交易时间显示上一交易日数据")

    # ===== 涨跌榜 =====
    tab1, tab2, tab3, tab4 = st.tabs(["涨幅榜", "跌幅榜", "成交额", "换手率"])

    def _render(stocks, value_key="change_pct", value_fmt="pct"):
        if not stocks:
            st.info("暂无数据")
            return
        for i, s in enumerate(stocks):
            pct = s.get("change_pct", 0) or 0
            color = _c(pct)
            price = s.get("price", 0) or 0
            name = s.get("name", s.get("code", ""))
            code = s.get("code", "")
            vol = _amt(s.get("amount", 0))

            # 点击跳转
            btn_key = f"stk_{code}_{i}_{value_key}"
            if st.button(f"  {i+1}   {name}  {code}   ¥{price:.2f}   {pct:+.2f}%   {vol}",
                        key=btn_key, use_container_width=True):
                st.session_state["selected_stock"] = code
                st.session_state["current_page"] = "stock_detail"
                st.rerun()

    with tab1:
        _render(get_top_stocks(sort_field="f3", asc=False, limit=20))
    with tab2:
        _render(get_top_stocks(sort_field="f3", asc=True, limit=20))
    with tab3:
        _render(get_top_stocks(sort_field="f6", asc=False, limit=20))
    with tab4:
        _render(get_top_stocks(sort_field="f8", asc=False, limit=20))

    st.markdown("---")

    # ===== 财经快讯 =====
    st.subheader("📰 财经快讯")

    if st.button("刷新新闻", key="refresh_news"):
        st.session_state.pop("cached_news", None)
        st.rerun()

    if "cached_news" not in st.session_state:
        try:
            from src.news.fetcher import fetch_all_news
            with st.spinner("加载中..."):
                st.session_state["cached_news"] = fetch_all_news(20)
        except Exception as e:
            st.session_state["cached_news"] = []

    news = st.session_state.get("cached_news", [])
    if not news:
        st.info("暂无新闻")
    else:
        for item in news:
            title = item.get("title", "")
            src = {"cls": "财联社", "eastmoney": "东方财富"}.get(item.get("source", ""), "")
            t = item.get("published_at", "")
            content = item.get("content", "")

            # 新闻标签
            tag = ""
            if any(k in title for k in ["涨", "牛", "利好", "突破"]):
                tag = '<span class="news-tag hot">利好</span>'
            elif any(k in title for k in ["跌", "利空", "风险", "暴"]):
                tag = '<span class="news-tag hot" style="background:#00E67630;color:#00E676">利空</span>'
            elif any(k in title for k in ["政策", "监管", "央行", "国务院"]):
                tag = '<span class="news-tag policy">政策</span>'

            st.markdown(f"""
            <div class="news-item">
                <div class="title">{tag}{title}</div>
                <div class="meta">{src} · {t}</div>
            </div>
            """, unsafe_allow_html=True)

            if content and content != title:
                with st.expander("展开详情"):
                    st.markdown(content)
