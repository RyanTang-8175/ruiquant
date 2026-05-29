"""
股票详情页 - K线图、技术指标、评分详情
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.data.models import DailyQuote, TechnicalIndicator, StockBasic
from src.scoring.engine import ScoringEngine
from src.utils.database import SessionLocal


def render_stock_detail_page(code: str):
    """渲染股票详情页面"""
    db = SessionLocal()
    try:
        # 获取股票信息
        stock = db.query(StockBasic).filter(StockBasic.code == code).first()
        if not stock:
            st.error(f"未找到股票 {code}")
            return

        # 获取日线数据
        quotes = db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).limit(60).all()

        if not quotes:
            st.error(f"股票 {code} 暂无数据")
            return

        # 获取最新数据
        latest = quotes[0]
        prev = quotes[1] if len(quotes) > 1 else None

        # 页面标题
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem 0;">
            <div>
                <span style="font-size: 1.8rem; font-weight: bold; color: #E6EDF3;">{stock.name}</span>
                <span style="color: #888; margin-left: 0.5rem; font-size: 1.2rem;">{code}</span>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 2rem; font-weight: bold; color: {'#FF4444' if latest.change_pct and latest.change_pct > 0 else '#00E676'};">¥{latest.close:.2f}</span>
                <br>
                <span style="color: {'#FF4444' if latest.change_pct and latest.change_pct > 0 else '#00E676'}; font-size: 1.2rem;">
                    {latest.change_pct:+.2f}% {latest.close - latest.open:+.2f}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 核心指标
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("开盘", f"{latest.open:.2f}")
        with col2:
            st.metric("最高", f"{latest.high:.2f}")
        with col3:
            st.metric("最低", f"{latest.low:.2f}")
        with col4:
            st.metric("成交量", f"{latest.volume/10000:.0f}万")
        with col5:
            st.metric("成交额", f"{latest.amount/1e8:.1f}亿")
        with col6:
            st.metric("换手率", f"{latest.turnover_rate:.2f}%")

        st.markdown("---")

        # K 线图
        st.subheader("📈 K 线图")

        # 准备数据
        chart_data = pd.DataFrame([{
            '日期': q.trade_date,
            '开盘': q.open,
            '最高': q.high,
            '最低': q.low,
            '收盘': q.close,
            '成交量': q.volume
        } for q in reversed(quotes)])

        chart_data = chart_data.set_index('日期')

        # 显示 K 线图
        tab1, tab2, tab3 = st.tabs(["K 线", "成交量", "技术指标"])

        with tab1:
            st.line_chart(chart_data['收盘'], use_container_width=True)

        with tab2:
            st.bar_chart(chart_data['成交量'], use_container_width=True)

        with tab3:
            # 获取技术指标
            indicators = db.query(TechnicalIndicator).filter(
                TechnicalIndicator.code == code
            ).order_by(TechnicalIndicator.trade_date.desc()).limit(60).all()

            if indicators:
                ind_data = pd.DataFrame([{
                    '日期': i.trade_date,
                    'MA5': i.ma5,
                    'MA10': i.ma10,
                    'MA20': i.ma20,
                    'RSI': i.rsi_6,
                    'MACD': i.macd
                } for i in reversed(indicators)])

                ind_data = ind_data.set_index('日期')

                col1, col2 = st.columns(2)
                with col1:
                    st.line_chart(ind_data[['MA5', 'MA10', 'MA20']], use_container_width=True)
                with col2:
                    st.line_chart(ind_data[['RSI']], use_container_width=True)
            else:
                st.info("暂无技术指标数据")

        st.markdown("---")

        # 评分详情
        st.subheader("📊 评分详情")

        try:
            engine = ScoringEngine()
            score_result = engine.score_stock(code)
            engine.close()

            if score_result:
                score = score_result['total_score']
                rating = score_result['rating']
                factors = score_result.get('factors', {})

                # 评级颜色
                if rating == "强关注":
                    rating_color = "#FF4444"
                elif rating == "观察":
                    rating_color = "#4488FF"
                elif rating == "中性":
                    rating_color = "#FFB800"
                else:
                    rating_color = "#888888"

                st.markdown(f"""
                <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%); border-radius: 12px; border: 1px solid #2D3748;">
                    <div style="font-size: 3rem; font-weight: bold; color: {rating_color};">{score:.0f}</div>
                    <div style="color: #888; margin-top: 0.5rem;">总评分</div>
                    <div style="margin-top: 1rem;">
                        <span style="background: {rating_color}; color: white; padding: 4px 16px; border-radius: 20px; font-size: 1.1rem;">{rating}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # 因子详情
                factor_names = {
                    'short_term_reversal': '短期反转',
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

                cols = st.columns(4)
                for i, (k, v) in enumerate(sorted(factors.items(), key=lambda x: x[1], reverse=True)):
                    name = factor_names.get(k, k)
                    with cols[i % 4]:
                        color = '#FF4444' if v >= 70 else '#FFB800' if v >= 50 else '#00E676'
                        st.markdown(f"""
                        <div style="text-align: center; padding: 1rem; background: #1A1A2E; border-radius: 8px; margin-bottom: 0.5rem;">
                            <div style="color: #888; font-size: 0.8rem;">{name}</div>
                            <div style="color: {color}; font-size: 1.5rem; font-weight: bold;">{v:.0f}</div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("暂无评分数据")
        except Exception as e:
            st.error(f"评分计算失败: {e}")

        st.markdown("---")

        # 历史数据
        st.subheader("📋 历史行情")
        hist_df = pd.DataFrame([{
            '日期': q.trade_date,
            '开盘': q.open,
            '最高': q.high,
            '最低': q.low,
            '收盘': q.close,
            '涨跌幅': q.change_pct,
            '成交量': q.volume,
            '成交额': q.amount
        } for q in quotes[:20]])

        st.dataframe(hist_df, use_container_width=True)

        # 返回按钮
        if st.button("← 返回观察池"):
            st.session_state['current_page'] = 'watchlist'
            st.rerun()

    finally:
        db.close()
