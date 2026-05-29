"""
股票详情 - 专业级K线 + 评分 + AI分析 + 新闻
"""

import streamlit as st
import pandas as pd
from src.data.realtime import get_realtime_quote, get_kline
from src.scoring.engine import ScoringEngine

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def _c(v):
    v = v or 0
    if v > 0: return "#FF4444"
    if v < 0: return "#00E676"
    return "#888"


def render_stock_detail_page(code: str = None):
    if not code:
        code = st.session_state.get("selected_stock", "")
    if not code:
        st.warning("未选择股票")
        return

    # ===== 实时行情 =====
    quote = get_realtime_quote(code)
    if not quote:
        st.error(f"未找到 {code} 的数据")
        return

    name = quote.get("name", code)
    price = quote.get("price", 0)
    pct = quote.get("change_pct", 0)
    color = _c(pct)
    sign = "+" if pct > 0 else ""

    # 标题 + 价格
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:baseline;padding:0.5rem 0;">
        <div>
            <span style="font-size:1.8rem;font-weight:900;color:#E6EDF3;">{name}</span>
            <span style="color:#4a5568;margin-left:0.5rem;font-size:0.9rem;">{code}</span>
        </div>
        <div style="text-align:right;">
            <span style="font-size:2.2rem;font-weight:900;color:{color};">¥{price:.2f}</span>
            <span style="color:{color};font-size:1rem;font-weight:600;margin-left:0.5rem;">{sign}{pct:.2f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 指标卡片
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("今开", f"{quote.get('open',0):.2f}", border=True)
    m2.metric("最高", f"{quote.get('high',0):.2f}", border=True)
    m3.metric("最低", f"{quote.get('low',0):.2f}", border=True)
    m4.metric("成交量", f"{quote.get('volume',0)/10000:.0f}万", border=True)
    m5.metric("成交额", f"{quote.get('amount',0)/1e8:.1f}亿", border=True)
    m6.metric("换手率", f"{quote.get('turnover',0):.2f}%", border=True)

    st.markdown("---")

    # ===== K线图 =====
    st.subheader("K线图")

    periods = ["日线", "周线", "60分钟", "30分钟", "15分钟", "5分钟", "1分钟"]
    period_map = {"1分钟":"1","5分钟":"5","15分钟":"15","30分钟":"30","60分钟":"60","日线":"101","周线":"102"}

    sel_period = st.radio("周期", periods, horizontal=True, key="kp")
    klines = get_kline(code, period=period_map.get(sel_period, "101"), count=120)

    if klines:
        df = pd.DataFrame(klines)

        if HAS_PLOTLY:
            # 蜡烛图 + 成交量 子图
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.75, 0.25]
            )

            # K线蜡烛
            fig.add_trace(go.Candlestick(
                x=df["date"], open=df["open"], high=df["high"],
                low=df["low"], close=df["close"],
                increasing_line_color="#FF4444", decreasing_line_color="#00E676",
                increasing_fillcolor="rgba(255,68,68,0.6)",
                decreasing_fillcolor="rgba(0,230,118,0.6)",
                name="K线"
            ), row=1, col=1)

            # 均线
            for ma, color, label in [(5,"#FFB800","MA5"),(10,"#4488FF","MA10"),(20,"#9C27B0","MA20")]:
                if len(df) >= ma:
                    fig.add_trace(go.Scatter(
                        x=df["date"], y=df["close"].rolling(ma).mean(),
                        name=label, line=dict(color=color, width=1)
                    ), row=1, col=1)

            # 成交量
            colors = ["#FF4444" if c >= o else "#00E676"
                      for c, o in zip(df["close"].fillna(0), df["open"].fillna(0))]
            fig.add_trace(go.Bar(
                x=df["date"], y=df["volume"], marker_color=colors, name="成交量"
            ), row=2, col=1)

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0B0E14", plot_bgcolor="#0B0E14",
                height=550,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_rangeslider_visible=False,
                showlegend=False,
                xaxis=dict(gridcolor="#1a1f2e"), yaxis=dict(gridcolor="#1a1f2e"),
                xaxis2=dict(gridcolor="#1a1f2e"), yaxis2=dict(gridcolor="#1a1f2e"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(df.set_index("date")["close"])
    else:
        st.info("暂无K线数据")

    st.markdown("---")

    # ===== 量化评分 =====
    st.subheader("量化评分")
    try:
        with ScoringEngine() as engine:
            score_result = engine.score_stock(code)

        if score_result:
            score = score_result["total_score"]
            rating = score_result["rating"]
            factors = score_result.get("factors", {})

            rc = {"强关注":"#FF4444","观察":"#4488FF","中性":"#FFB800","不追":"#555"}.get(rating, "#888")

            st.markdown(f"""
            <div style="text-align:center;padding:1.5rem;background:linear-gradient(135deg,#151923,#111620);border-radius:12px;border:1px solid #1e2738;">
                <div style="font-size:3.5rem;font-weight:900;color:{rc};">{score:.0f}</div>
                <div style="color:#6b7280;font-size:0.9rem;">综合评分</div>
                <div style="margin-top:0.5rem;"><span style="background:{rc};color:white;padding:4px 16px;border-radius:20px;font-weight:700;">{rating}</span></div>
            </div>
            """, unsafe_allow_html=True)

            # 因子详情
            fnames = {
                "short_term_reversal":"反转","turnover_rate":"换手","volume_ratio":"量比",
                "trend":"趋势","rsi":"RSI","macd":"MACD","kdj":"KDJ","kline_pattern":"K线",
                "idio_volatility":"波动","blast_rate":"爆量","limit_up_streak":"连板",
                "market_temperature":"温度","boll_position":"布林","intraday_intensity":"强度",
            }
            sorted_f = sorted(factors.items(), key=lambda x: x[1], reverse=True)
            cols = st.columns(4)
            for i, (k, v) in enumerate(sorted_f):
                fn = fnames.get(k, k)
                pct_bar = min(100, max(0, v))
                bc = "#FF4444" if v >= 70 else "#FFB800" if v >= 50 else "#00E676"
                with cols[i % 4]:
                    st.markdown(f"""
                    <div style="padding:0.5rem;background:#151923;border-radius:8px;margin-bottom:0.4rem;border:1px solid #1a1f2e;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:0.2rem;">
                            <span style="color:#6b7280;font-size:0.75rem;">{fn}</span>
                            <span style="color:{bc};font-weight:700;font-size:0.85rem;">{v:.0f}</span>
                        </div>
                        <div style="background:#0B0E14;border-radius:3px;height:4px;">
                            <div style="background:{bc};height:100%;width:{pct_bar}%;border-radius:3px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("暂无评分，请在选股页刷新")
    except Exception as e:
        st.warning(f"评分异常: {e}")

    st.markdown("---")

    # ===== AI 分析 =====
    st.subheader("AI 分析")
    ctx = st.text_area("补充信息", placeholder="如：我持有该股1000股，成本50元，请分析是否继续持有...", key="ctx", label_visibility="collapsed")

    if st.button("AI 深度分析", key="ai_btn", type="primary", use_container_width=True):
        try:
            from src.ai.chat import AIChat
            ai = AIChat()
            prompt = f"请对 {name}（{code}）做全面分析。当前价 {price}，涨跌 {pct:+.2f}%。"
            if score_result:
                prompt += f"评分 {score_result['total_score']:.0f}，评级 {score_result['rating']}。"
            if ctx:
                prompt += f"\n用户信息：{ctx}"
            with st.spinner("AI 分析中..."):
                result = ai.chat(prompt)
            st.markdown(result)
        except Exception as e:
            st.error(f"AI 失败: {e}")

    st.markdown("---")

    # ===== 个股新闻 =====
    st.subheader(f"{name} 新闻")
    try:
        from src.news.fetcher import fetch_stock_news
        stock_news = fetch_stock_news(code, 5)
        if stock_news:
            for item in stock_news:
                st.markdown(f"""
                <div class="news-item">
                    <div class="title">{item['title']}</div>
                    <div class="meta">{item.get('source','')} · {item.get('published_at','')}</div>
                </div>
                """, unsafe_allow_html=True)
                if item.get("content") and item["content"] != item["title"]:
                    with st.expander("详情"):
                        st.markdown(item["content"])
        else:
            st.info("暂无相关新闻")
    except Exception as e:
        st.info(f"新闻异常: {e}")

    # 返回
    if st.button("← 返回行情", key="back"):
        st.session_state["current_page"] = "market"
        st.rerun()
