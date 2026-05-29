"""
选股/观察池页面 - 可点击查看详情
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
    col1, col2, col3 = st.columns(3)
    with col1:
        min_score = st.slider("最低评分", 0, 100, 50)
    with col2:
        limit = st.number_input("显示数量", 5, 100, 30)
    with col3:
        rating_filter = st.selectbox("评级筛选", ["全部", "强关注", "观察", "中性", "不追"])

    # 自动加载评分
    if 'watchlist' not in st.session_state or not st.session_state['watchlist']:
        with st.spinner("正在计算评分..."):
            try:
                engine = ScoringEngine()
                results = engine.get_watchlist(min_score=0, limit=100)
                engine.close()
                st.session_state['watchlist'] = results
            except Exception as e:
                st.error(f"评分失败: {e}")
                st.session_state['watchlist'] = []

    # 刷新按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 刷新评分", use_container_width=True, type="primary"):
            with st.spinner("正在重新计算..."):
                try:
                    engine = ScoringEngine()
                    results = engine.get_watchlist(min_score=0, limit=100)
                    engine.close()
                    st.session_state['watchlist'] = results
                    st.success(f"评分完成！共 {len(results)} 只股票")
                except Exception as e:
                    st.error(f"评分失败: {e}")

    st.markdown("---")

    # 显示观察池
    results = st.session_state.get('watchlist', [])

    if not results:
        st.warning("暂无评分数据，请先采集数据")
        return

    # 评级筛选
    if rating_filter != "全部":
        results = [r for r in results if r['rating'] == rating_filter]

    # 评分筛选
    results = [r for r in results if r['total_score'] >= min_score]

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

    # 显示股票列表（可点击）
    for i, stock in enumerate(results[:limit]):
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
            amount = quote.amount if quote else 0
        finally:
            db.close()

        # 因子详情
        factor_names = {
            'short_term_reversal': '反转',
            'turnover_rate': '换手率',
            'volume_ratio': '量比',
            'trend': '趋势',
            'rsi': 'RSI',
            'macd': 'MACD',
            'kline_pattern': 'K线',
        }

        top_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:4]
        factor_text = " | ".join([f"{factor_names.get(k, k)}: {v:.0f}" for k, v in top_factors])

        # 显示卡片（可点击）
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"""
                <div style="padding: 0.5rem 0;">
                    <span style="font-size: 1.2rem; font-weight: bold; color: #E6EDF3;">{stock.get('name', stock['code'])}</span>
                    <span style="color: #888; margin-left: 0.5rem;">{stock['code']}</span>
                    <br>
                    <span style="color: #666; font-size: 0.85rem;">{factor_text}</span>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div style="text-align: center; padding: 0.5rem;">
                    <div style="color: {'#FF4444' if change_pct > 0 else '#00E676'}; font-size: 1.1rem;">¥{price:.2f}</div>
                    <div style="color: {'#FF4444' if change_pct > 0 else '#00E676'}; font-size: 0.9rem;">{change_pct:+.2f}%</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                <div style="text-align: center; padding: 0.5rem;">
                    <div style="font-size: 1.5rem; font-weight: bold; color: {rating_color};">{score:.0f}</div>
                    <div><span style="background: {rating_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem;">{rating}</span></div>
                </div>
                """, unsafe_allow_html=True)

            # 详情按钮
            if st.button(f"📊 查看详情", key=f"detail_{stock['code']}", use_container_width=True):
                st.session_state['current_page'] = 'stock_detail'
                st.session_state['selected_stock'] = stock['code']
                st.rerun()

            st.markdown("---")
