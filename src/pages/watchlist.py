"""
选股/观察池页面 - 重新设计
"""

import streamlit as st
from datetime import datetime
from src.scoring.engine import ScoringEngine
from src.utils.database import SessionLocal
from src.data.models import StockBasic, DailyQuote


def render_watchlist_page():
    """渲染观察池页面"""
    st.markdown('<div class="main-header">🔍 选股</div>', unsafe_allow_html=True)

    # 数据状态
    db = SessionLocal()
    try:
        stock_count = db.query(StockBasic).count()
        quote_count = db.query(DailyQuote).count()
        latest = db.query(DailyQuote).order_by(DailyQuote.trade_date.desc()).first()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("股票数量", f"{stock_count}")
        with col2:
            st.metric("数据条数", f"{quote_count:,}")
        with col3:
            if latest:
                st.metric("最新数据", str(latest.trade_date))
            else:
                st.metric("最新数据", "无")
    finally:
        db.close()

    st.markdown("---")

    # 筛选条件
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        min_score = st.slider("最低评分", 0, 100, 60)
    with col2:
        limit = st.number_input("显示数量", 5, 100, 30)
    with col3:
        rating_filter = st.selectbox("评级筛选", ["全部", "强关注", "观察", "中性", "不追"])
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 计算评分", use_container_width=True, type="primary"):
            with st.spinner("正在计算评分..."):
                try:
                    engine = ScoringEngine()
                    results = engine.get_watchlist(min_score=min_score, limit=limit)
                    engine.close()
                    st.session_state['watchlist'] = results
                    st.success(f"评分完成！共 {len(results)} 只股票")
                except Exception as e:
                    st.error(f"评分失败: {e}")

    st.markdown("---")

    # 显示观察池
    results = st.session_state.get('watchlist', [])

    if not results:
        st.info("暂无评分数据，请点击「计算评分」按钮")
        return

    # 评级筛选
    if rating_filter != "全部":
        results = [r for r in results if r['rating'] == rating_filter]

    if not results:
        st.warning("没有符合条件的股票")
        return

    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        strong_count = len([r for r in results if r['rating'] == '强关注'])
        st.metric("强关注", f"{strong_count}")
    with col2:
        watch_count = len([r for r in results if r['rating'] == '观察'])
        st.metric("观察", f"{watch_count}")
    with col3:
        neutral_count = len([r for r in results if r['rating'] == '中性'])
        st.metric("中性", f"{neutral_count}")
    with col4:
        avoid_count = len([r for r in results if r['rating'] == '不追'])
        st.metric("不追", f"{avoid_count}")

    st.markdown("---")

    # 显示股票列表
    for i, stock in enumerate(results):
        score = stock['total_score']
        rating = stock['rating']
        factors = stock.get('factors', {})

        # 评级颜色
        if rating == "强关注":
            rating_color = "#FF4444"
            bg_color = "#FF444415"
        elif rating == "观察":
            rating_color = "#4488FF"
            bg_color = "#4488FF15"
        elif rating == "中性":
            rating_color = "#FFB800"
            bg_color = "#FFB80015"
        else:
            rating_color = "#888888"
            bg_color = "#88888815"

        # 获取实时价格
        db = SessionLocal()
        try:
            quote = db.query(DailyQuote).filter(
                DailyQuote.code == stock['code']
            ).order_by(DailyQuote.trade_date.desc()).first()

            price = quote.close if quote else 0
            change_pct = quote.change_pct if quote else 0
        finally:
            db.close()

        # 显示卡片
        with st.container():
            st.markdown(f"""
            <div style="background: {bg_color}; padding: 1.2rem; border-radius: 12px; border: 1px solid {rating_color}30; margin-bottom: 0.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 1.2rem; font-weight: bold; color: #E6EDF3;">{stock.get('name', stock['code'])}</span>
                        <span style="color: #888; margin-left: 0.5rem;">{stock['code']}</span>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 1.5rem; font-weight: bold; color: {rating_color};">{score:.0f}</span>
                        <span style="color: #888; margin-left: 0.5rem;">分</span>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
                    <div>
                        <span style="color: #E6EDF3;">现价: {price:.2f}</span>
                        <span style="color: {'#FF4444' if change_pct > 0 else '#00E676'}; margin-left: 1rem;">{change_pct:+.2f}%</span>
                    </div>
                    <div>
                        <span style="background: {rating_color}; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.9rem;">{rating}</span>
                    </div>
                </div>
                <div style="margin-top: 0.8rem; display: flex; gap: 1rem; flex-wrap: wrap;">
            """, unsafe_allow_html=True)

            # 因子详情
            factor_items = []
            for k, v in sorted(factors.items(), key=lambda x: x[1], reverse=True)[:6]:
                factor_name = {
                    'short_term_reversal': '反转',
                    'turnover_rate': '换手',
                    'volume_ratio': '量比',
                    'trend': '趋势',
                    'rsi': 'RSI',
                    'macd': 'MACD',
                    'sector_heat': '板块',
                    'idio_volatility': '波动',
                    'kline_pattern': 'K线',
                    'intraday_intensity': '强度',
                }.get(k, k)
                color = '#FF4444' if v > 60 else '#00E676' if v < 40 else '#888'
                factor_items.append(f'<span style="color: {color}; font-size: 0.85rem;">{factor_name}: {v:.0f}</span>')

            st.markdown(" | ".join(factor_items), unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)
