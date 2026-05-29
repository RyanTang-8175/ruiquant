"""
选股/观察池页面 - 自动加载评分
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

    # 自动加载评分（如果还没有数据）
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

    # 显示股票列表
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
            volume = quote.volume if quote else 0
            amount = quote.amount if quote else 0
        finally:
            db.close()

        # 显示卡片
        st.markdown(f"""
        <div style="background: {bg_color}; padding: 1.2rem; border-radius: 12px; border: 1px solid {rating_color}30; margin-bottom: 0.8rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 1.2rem; font-weight: bold; color: #E6EDF3;">{stock.get('name', stock['code'])}</span>
                    <span style="color: #888; margin-left: 0.5rem;">{stock['code']}</span>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 1.8rem; font-weight: bold; color: {rating_color};">{score:.0f}</span>
                    <span style="color: #888; margin-left: 0.3rem;">分</span>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 0.8rem; flex-wrap: wrap; gap: 0.5rem;">
                <div style="flex: 1; min-width: 120px;">
                    <div style="color: #888; font-size: 0.8rem;">现价</div>
                    <div style="color: #E6EDF3; font-size: 1.1rem;">¥{price:.2f}</div>
                </div>
                <div style="flex: 1; min-width: 120px;">
                    <div style="color: #888; font-size: 0.8rem;">涨跌幅</div>
                    <div style="color: {'#FF4444' if change_pct > 0 else '#00E676'}; font-size: 1.1rem;">{change_pct:+.2f}%</div>
                </div>
                <div style="flex: 1; min-width: 120px;">
                    <div style="color: #888; font-size: 0.8rem;">成交额</div>
                    <div style="color: #FFB800; font-size: 1.1rem;">{amount/1e8:.1f}亿</div>
                </div>
                <div style="flex: 1; min-width: 120px;">
                    <div style="color: #888; font-size: 0.8rem;">评级</div>
                    <div><span style="background: {rating_color}; color: white; padding: 2px 10px; border-radius: 12px;">{rating}</span></div>
                </div>
            </div>
            <div style="margin-top: 0.8rem; display: flex; gap: 0.8rem; flex-wrap: wrap;">
        """, unsafe_allow_html=True)

        # 因子详情
        factor_names = {
            'short_term_reversal': '反转',
            'turnover_rate': '换手率',
            'volume_ratio': '量比',
            'abnormal_turnover': '异常换手',
            'volume_price_divergence': '量价背离',
            'trend': '均线趋势',
            'rsi': 'RSI',
            'macd': 'MACD',
            'kdj': 'KDJ',
            'kline_pattern': 'K线形态',
            'intraday_intensity': '日内强度',
            'idio_volatility': '波动率',
            'high_52w_ratio': '52周高点',
            'volume_price_corr': '量价相关',
        }

        factor_items = []
        for k, v in sorted(factors.items(), key=lambda x: x[1], reverse=True)[:8]:
            name = factor_names.get(k, k)
            if v >= 70:
                color = '#FF4444'
            elif v >= 50:
                color = '#FFB800'
            else:
                color = '#00E676'
            factor_items.append(f'<span style="color: {color}; font-size: 0.85rem;">{name}: {v:.0f}</span>')

        st.markdown(" | ".join(factor_items), unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)
