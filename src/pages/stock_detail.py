"""
股票详情页 - K线图、技术指标、评分详情
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.data.models import DailyQuote, TechnicalIndicator, StockBasic
from src.scoring.engine import ScoringEngine
from src.utils.database import SessionLocal

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def render_stock_detail_page(code: str):
    """渲染股票详情页面"""
    db = SessionLocal()
    try:
        stock = db.query(StockBasic).filter(StockBasic.code == code).first()
        if not stock:
            st.error(f"未找到股票 {code}")
            return

        quotes = db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).limit(60).all()

        if not quotes:
            st.error(f"股票 {code} 暂无数据")
            return

        latest = quotes[0]
        change_color = '#FF4444' if latest.change_pct and latest.change_pct > 0 else '#00E676'

        # 页面标题
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem 0;">
            <div>
                <span style="font-size: 1.8rem; font-weight: bold; color: #E6EDF3;">{stock.name}</span>
                <span style="color: #888; margin-left: 0.5rem; font-size: 1.2rem;">{code}</span>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 2rem; font-weight: bold; color: {change_color};">¥{latest.close:.2f}</span>
                <br>
                <span style="color: {change_color}; font-size: 1.2rem;">
                    {latest.change_pct:+.2f}% {latest.close - latest.open:+.2f}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 核心指标卡片
        metrics = [
            ("开盘", f"{latest.open:.2f}"),
            ("最高", f"{latest.high:.2f}"),
            ("最低", f"{latest.low:.2f}"),
            ("成交量", f"{latest.volume/10000:.0f}万"),
            ("成交额", f"{latest.amount/1e8:.1f}亿"),
            ("换手率", f"{latest.turnover_rate:.2f}%"),
        ]
        cols = st.columns(6)
        for i, (label, value) in enumerate(metrics):
            with cols[i]:
                st.markdown(f"""
                <div class="metric-card" style="text-align: center;">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value" style="font-size: 1.2rem;">{value}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # K 线图
        st.subheader("📈 K 线图")

        chart_data = pd.DataFrame([{
            '日期': q.trade_date,
            '开盘': q.open,
            '最高': q.high,
            '最低': q.low,
            '收盘': q.close,
            '成交量': q.volume,
            '涨跌': q.change_pct
        } for q in reversed(quotes)])

        tab1, tab2, tab3 = st.tabs(["K 线", "成交量", "技术指标"])

        with tab1:
            if HAS_PLOTLY:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_data['日期'],
                    open=chart_data['开盘'],
                    high=chart_data['最高'],
                    low=chart_data['最低'],
                    close=chart_data['收盘'],
                    increasing_line_color='#FF4444',
                    decreasing_line_color='#00E676',
                    increasing_fillcolor='rgba(255,68,68,0.5)',
                    decreasing_fillcolor='rgba(0,230,118,0.5)',
                )])
                fig.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='#0a0e17',
                    plot_bgcolor='#0a0e17',
                    xaxis_rangeslider_visible=False,
                    height=500,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis=dict(gridcolor='#1e2738'),
                    yaxis=dict(gridcolor='#1e2738'),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(chart_data.set_index('日期')['收盘'], use_container_width=True)

        with tab2:
            if HAS_PLOTLY:
                colors = ['#FF4444' if c >= o else '#00E676'
                          for c, o in zip(chart_data['收盘'], chart_data['开盘'])]
                fig_vol = go.Figure(data=[go.Bar(
                    x=chart_data['日期'], y=chart_data['成交量'],
                    marker_color=colors
                )])
                fig_vol.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='#0a0e17',
                    plot_bgcolor='#0a0e17',
                    height=250,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis=dict(gridcolor='#1e2738'),
                    yaxis=dict(gridcolor='#1e2738'),
                )
                st.plotly_chart(fig_vol, use_container_width=True)
            else:
                st.bar_chart(chart_data.set_index('日期')['成交量'], use_container_width=True)

        with tab3:
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
                    'MACD': i.macd,
                    'MACD_Signal': i.macd_signal,
                    'MACD_Hist': i.macd_hist,
                } for i in reversed(indicators)])

                if HAS_PLOTLY:
                    col1, col2 = st.columns(2)
                    with col1:
                        fig_ma = go.Figure()
                        fig_ma.add_trace(go.Scatter(x=ind_data['日期'], y=ind_data['MA5'], name='MA5', line=dict(color='#FF4444', width=1)))
                        fig_ma.add_trace(go.Scatter(x=ind_data['日期'], y=ind_data['MA10'], name='MA10', line=dict(color='#FFB800', width=1)))
                        fig_ma.add_trace(go.Scatter(x=ind_data['日期'], y=ind_data['MA20'], name='MA20', line=dict(color='#4488FF', width=1)))
                        fig_ma.update_layout(
                            template='plotly_dark', paper_bgcolor='#0a0e17', plot_bgcolor='#0a0e17',
                            height=300, margin=dict(l=0, r=0, t=30, b=0),
                            title='均线', title_font_size=14,
                            xaxis=dict(gridcolor='#1e2738'), yaxis=dict(gridcolor='#1e2738'),
                        )
                        st.plotly_chart(fig_ma, use_container_width=True)
                    with col2:
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(x=ind_data['日期'], y=ind_data['RSI'], name='RSI', line=dict(color='#FFB800', width=1.5)))
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="rgba(255,68,68,0.5)")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="rgba(0,230,118,0.5)")
                        fig_rsi.update_layout(
                            template='plotly_dark', paper_bgcolor='#0a0e17', plot_bgcolor='#0a0e17',
                            height=300, margin=dict(l=0, r=0, t=30, b=0),
                            title='RSI(6)', title_font_size=14,
                            xaxis=dict(gridcolor='#1e2738'), yaxis=dict(gridcolor='#1e2738'),
                        )
                        st.plotly_chart(fig_rsi, use_container_width=True)
                else:
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
                    'blast_rate': '爆量率',
                    'amihud_illiquidity': '非流动性',
                    'limit_up_streak': '连板',
                    'market_temperature': '市场温度',
                }

                cols = st.columns(4)
                for i, (k, v) in enumerate(sorted(factors.items(), key=lambda x: x[1], reverse=True)):
                    name = factor_names.get(k, k)
                    with cols[i % 4]:
                        # 因子分数用进度条展示
                        bar_pct = min(100, max(0, v))
                        if v >= 70:
                            bar_color = '#FF4444'
                        elif v >= 50:
                            bar_color = '#FFB800'
                        else:
                            bar_color = '#00E676'
                        st.markdown(f"""
                        <div style="padding: 0.8rem; background: #1A1A2E; border-radius: 8px; margin-bottom: 0.5rem;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                                <span style="color: #888; font-size: 0.8rem;">{name}</span>
                                <span style="color: {bar_color}; font-weight: bold;">{v:.0f}</span>
                            </div>
                            <div style="background: #0a0e17; border-radius: 4px; height: 6px; overflow: hidden;">
                                <div style="background: {bar_color}; height: 100%; width: {bar_pct}%; border-radius: 4px;"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("暂无评分数据")
        except Exception as e:
            st.error(f"评分计算失败: {e}")

        st.markdown("---")

        # AI 分析按钮
        if st.button("🤖 AI 深度分析", key="ai_analyze_btn"):
            try:
                from src.ai.chat import AIChat
                ai = AIChat()
                with st.spinner("AI 正在分析..."):
                    analysis = ai.chat(f"请对 {stock.name}（{code}）做全面的技术面和消息面分析，当前价格 {latest.close}，涨跌幅 {latest.change_pct:+.2f}%")
                    st.markdown(analysis)
            except Exception as e:
                st.error(f"AI 分析失败: {e}")

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
        if st.button("← 返回", key="back_btn"):
            st.session_state['current_page'] = 'watchlist'
            st.rerun()

    finally:
        db.close()
