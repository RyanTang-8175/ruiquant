"""
股票详情页 - 实时行情 + K线图 + 评分 + AI分析
"""

import streamlit as st
import pandas as pd
from src.data.realtime import get_realtime_quote, get_kline
from src.scoring.engine import ScoringEngine

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def _color(v):
    v = v or 0
    if v > 0: return "#FF4444"
    if v < 0: return "#00E676"
    return "#888"


def render_stock_detail_page(code: str = None):
    """渲染股票详情"""
    if not code:
        code = st.session_state.get("selected_stock", "")

    if not code:
        st.warning("未选择股票")
        if st.button("返回行情"):
            st.session_state["current_page"] = "market"
            st.rerun()
        return

    # ========== 实时行情 ==========
    quote = get_realtime_quote(code)
    if not quote:
        st.error(f"未找到股票 {code} 的实时数据")
        if st.button("返回"):
            st.session_state["current_page"] = "market"
            st.rerun()
        return

    name = quote.get("name", code)
    price = quote.get("price", 0)
    pct = quote.get("change_pct", 0)
    color = _color(pct)

    # 标题 + 价格
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;padding:0.5rem 0;">
        <div>
            <span style="font-size:1.6rem;font-weight:800;color:#E6EDF3;">{name}</span>
            <span style="color:#6b7280;margin-left:0.5rem;">{code}</span>
        </div>
        <div style="text-align:right;">
            <span style="font-size:2rem;font-weight:800;color:{color};">¥{price:.2f}</span>
            <br>
            <span style="color:{color};font-size:1.1rem;">{pct:+.2f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 核心指标
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("今开", f"{quote.get('open', 0):.2f}", border=True)
    m2.metric("最高", f"{quote.get('high', 0):.2f}", border=True)
    m3.metric("最低", f"{quote.get('low', 0):.2f}", border=True)
    m4.metric("成交量", f"{quote.get('volume', 0)/10000:.0f}万手", border=True)
    m5.metric("成交额", f"{quote.get('amount', 0)/1e8:.1f}亿", border=True)
    m6.metric("换手率", f"{quote.get('turnover', 0):.2f}%", border=True)

    st.markdown("---")

    # ========== K线图 ==========
    st.subheader("K线图")

    kline_period = st.radio(
        "周期", ["日线", "周线", "60分钟", "30分钟", "15分钟", "5分钟", "1分钟"],
        horizontal=True, key="kline_period"
    )
    period_map = {
        "1分钟": "1", "5分钟": "5", "15分钟": "15", "30分钟": "30",
        "60分钟": "60", "日线": "101", "周线": "102"
    }
    period = period_map.get(kline_period, "101")

    kline_count = 120 if period in ("101", "102") else 200
    klines = get_kline(code, period=period, count=kline_count)

    if klines:
        df = pd.DataFrame(klines)

        if HAS_PLOTLY:
            # K线蜡烛图
            fig = go.Figure(data=[go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                increasing_line_color="#FF4444",
                decreasing_line_color="#00E676",
                increasing_fillcolor="rgba(255,68,68,0.5)",
                decreasing_fillcolor="rgba(0,230,118,0.5)",
            )])

            # 添加均线
            if len(df) >= 5:
                df["MA5"] = df["close"].rolling(5).mean()
                fig.add_trace(go.Scatter(x=df["date"], y=df["MA5"], name="MA5",
                                        line=dict(color="#FFB800", width=1)))
            if len(df) >= 10:
                df["MA10"] = df["close"].rolling(10).mean()
                fig.add_trace(go.Scatter(x=df["date"], y=df["MA10"], name="MA10",
                                        line=dict(color="#4488FF", width=1)))
            if len(df) >= 20:
                df["MA20"] = df["close"].rolling(20).mean()
                fig.add_trace(go.Scatter(x=df["date"], y=df["MA20"], name="MA20",
                                        line=dict(color="#9C27B0", width=1)))

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0a0e17",
                plot_bgcolor="#0a0e17",
                xaxis_rangeslider_visible=False,
                height=500,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(gridcolor="#1e2738"),
                yaxis=dict(gridcolor="#1e2738"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

            # 成交量图
            colors = ["#FF4444" if c >= o else "#00E676"
                      for c, o in zip(df["close"].fillna(0), df["open"].fillna(0))]
            fig_vol = go.Figure(data=[go.Bar(
                x=df["date"], y=df["volume"], marker_color=colors
            )])
            fig_vol.update_layout(
                template="plotly_dark", paper_bgcolor="#0a0e17", plot_bgcolor="#0a0e17",
                height=200, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(gridcolor="#1e2738"), yaxis=dict(gridcolor="#1e2738"),
            )
            st.plotly_chart(fig_vol, use_container_width=True)
        else:
            st.line_chart(df.set_index("date")["close"])
    else:
        st.info("暂无K线数据")

    st.markdown("---")

    # ========== 评分 ==========
    st.subheader("量化评分")
    try:
        with ScoringEngine() as engine:
            score_result = engine.score_stock(code)

        if score_result:
            score = score_result["total_score"]
            rating = score_result["rating"]
            factors = score_result.get("factors", {})

            rating_colors = {"强关注": "#FF4444", "观察": "#4488FF", "中性": "#FFB800", "不追": "#888"}
            rc = rating_colors.get(rating, "#888")

            st.markdown(f"""
            <div style="text-align:center;padding:1.5rem;background:linear-gradient(135deg,#1A1A2E,#16213E);border-radius:12px;border:1px solid #2D3748;">
                <div style="font-size:3rem;font-weight:800;color:{rc};">{score:.0f}</div>
                <div style="color:#888;">总评分</div>
                <div style="margin-top:0.5rem;">
                    <span style="background:{rc};color:white;padding:4px 16px;border-radius:20px;">{rating}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 因子详情（进度条式）
            factor_names = {
                "short_term_reversal": "短期反转", "turnover_rate": "换手率",
                "volume_ratio": "量比", "trend": "均线趋势", "rsi": "RSI",
                "macd": "MACD", "kdj": "KDJ", "kline_pattern": "K线形态",
                "idio_volatility": "波动率", "blast_rate": "爆量率",
                "limit_up_streak": "连板", "market_temperature": "市场温度",
                "volume_price_divergence": "量价背离", "boll_position": "布林带",
            }
            sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)

            cols = st.columns(3)
            for i, (k, v) in enumerate(sorted_factors):
                fname = factor_names.get(k, k)
                bar_pct = min(100, max(0, v))
                bar_color = "#FF4444" if v >= 70 else "#FFB800" if v >= 50 else "#00E676"
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="padding:0.5rem;background:#1A1A2E;border-radius:8px;margin-bottom:0.5rem;">
                        <div style="display:flex;justify-content:space-between;">
                            <span style="color:#888;font-size:0.8rem;">{fname}</span>
                            <span style="color:{bar_color};font-weight:bold;">{v:.0f}</span>
                        </div>
                        <div style="background:#0a0e17;border-radius:4px;height:4px;margin-top:3px;">
                            <div style="background:{bar_color};height:100%;width:{bar_pct}%;border-radius:4px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("暂无评分数据，请先在选股页刷新评分")
    except Exception as e:
        st.warning(f"评分加载失败: {e}")

    st.markdown("---")

    # ========== AI 分析 ==========
    st.subheader("AI 深度分析")

    # 用户可以输入自己的持仓信息让AI分析
    user_context = st.text_area(
        "补充信息（可选）",
        placeholder="例如：我持有该股1000股，成本价50元，请帮我分析是否应该继续持有...",
        key="stock_context_input"
    )

    if st.button("AI 分析", key="ai_analyze_stock", type="primary"):
        try:
            from src.ai.chat import AIChat
            ai = AIChat()
            prompt = f"请对 {name}（{code}）做全面分析。当前价格 {price}，涨跌幅 {pct:+.2f}%。"
            if score_result:
                prompt += f"量化评分 {score_result['total_score']:.0f}，评级 {score_result['rating']}。"
            if user_context:
                prompt += f"\n用户补充信息：{user_context}"

            with st.spinner("AI 分析中..."):
                result = ai.chat(prompt)
            st.markdown(result)
        except Exception as e:
            st.error(f"AI 分析失败: {e}")

    st.markdown("---")

    # ========== 个股新闻 ==========
    st.subheader(f"{name} 相关新闻")
    try:
        from src.news.fetcher import fetch_stock_news
        stock_news = fetch_stock_news(code, limit=5)
        if stock_news:
            for item in stock_news:
                with st.expander(f"📰 {item['title']}", expanded=False):
                    st.caption(f"{item.get('source', '')} | {item.get('published_at', '')}")
                    if item.get("content") and item["content"] != item["title"]:
                        st.markdown(item["content"])
        else:
            st.info("暂无相关新闻")
    except Exception as e:
        st.info(f"新闻加载异常: {e}")

    # 返回按钮
    if st.button("← 返回", key="back_btn"):
        st.session_state["current_page"] = "market"
        st.rerun()
