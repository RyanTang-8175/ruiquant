"""
选股/观察池页面
"""

import streamlit as st
from src.scoring.engine import ScoringEngine


def render_watchlist_page():
    """渲染观察池页面"""
    st.markdown('<div class="main-header">🔍 选股</div>', unsafe_allow_html=True)

    # 筛选条件
    col1, col2, col3 = st.columns(3)
    with col1:
        min_score = st.slider("最低评分", 0, 100, 65)
    with col2:
        limit = st.number_input("显示数量", 5, 50, 20)
    with col3:
        rating_filter = st.selectbox("评级筛选", ["全部", "强关注", "观察", "中性", "不追"])

    st.markdown("---")

    # 获取观察池
    if st.button("🔄 刷新观察池", use_container_width=True):
        with st.spinner("正在计算评分..."):
            try:
                with ScoringEngine() as engine:
                    results = engine.get_watchlist(min_score=min_score, limit=limit)
                st.session_state['watchlist'] = results
            except Exception as e:
                st.error(f"计算失败: {e}")
                return

    results = st.session_state.get('watchlist', [])

    if not results:
        st.info("暂无数据，请先采集数据并刷新观察池")
        return

    # 评级筛选
    if rating_filter != "全部":
        results = [r for r in results if r['rating'] == rating_filter]

    # 显示结果
    for i, stock in enumerate(results):
        score = stock['total_score']
        rating = stock['rating']

        # 评级样式
        if rating == "强关注":
            rating_class = "rating-strong"
            score_class = "score-high"
        elif rating == "观察":
            rating_class = "rating-watch"
            score_class = "score-mid"
        else:
            rating_class = "rating-neutral"
            score_class = "score-low"

        # 因子详情
        factors = stock.get('factors', {})
        top_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:3]

        with st.container():
            col1, col2, col3, col4 = st.columns([1, 2, 1, 1])

            with col1:
                st.markdown(f"**{stock.get('name', '')}**")
                st.caption(stock['code'])

            with col2:
                factor_text = " | ".join([f"{k}: {v:.0f}" for k, v in top_factors])
                st.caption(factor_text)

            with col3:
                st.markdown(f'<span class="{score_class}">{score:.0f}</span>', unsafe_allow_html=True)

            with col4:
                st.markdown(f'<span class="{rating_class}">{rating}</span>', unsafe_allow_html=True)

            st.markdown("---")
