"""
市场概览页面 - 专业金融风格
"""

import streamlit as st
from datetime import datetime
from src.data.collector import DataCollector
from src.utils.database import SessionLocal
from src.data.models import DailyQuote, StockBasic


def render_market_page():
    """渲染市场概览页面"""
    db = SessionLocal()
    try:
        # 获取数据状态
        latest = db.query(DailyQuote).order_by(DailyQuote.trade_date.desc()).first()
        stock_count = db.query(StockBasic).count()
        quote_count = db.query(DailyQuote).count()

        # 顶部状态栏
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.8rem 1.2rem; background: #1a1f2e; border-radius: 10px; margin-bottom: 1rem;">
            <div style="display: flex; gap: 2rem;">
                <div>
                    <span style="color: #6b7280; font-size: 0.75rem;">股票数量</span><br>
                    <span style="color: #E6EDF3; font-weight: 600;">{stock_count}</span>
                </div>
                <div>
                    <span style="color: #6b7280; font-size: 0.75rem;">数据条数</span><br>
                    <span style="color: #E6EDF3; font-weight: 600;">{quote_count:,}</span>
                </div>
                <div>
                    <span style="color: #6b7280; font-size: 0.75rem;">最新数据</span><br>
                    <span style="color: #E6EDF3; font-weight: 600;">{latest.trade_date if latest else '无'}</span>
                </div>
            </div>
            <div style="display: flex; gap: 0.5rem;">
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("📥 采集数据", type="primary"):
                with st.spinner("采集中..."):
                    try:
                        collector = DataCollector()
                        collector.collect_all_stocks(days=30)
                        collector.close()
                        st.success("完成!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"失败: {e}")

        with col2:
            if st.button("🔄 刷新"):
                st.rerun()

        st.markdown("</div></div>", unsafe_allow_html=True)

        # 市场数据
        if latest:
            quotes = db.query(DailyQuote).filter(
                DailyQuote.trade_date == latest.trade_date
            ).all()

            if quotes:
                # 计算统计数据
                up_count = sum(1 for q in quotes if q.change_pct and q.change_pct > 0)
                down_count = sum(1 for q in quotes if q.change_pct and q.change_pct < 0)
                flat_count = sum(1 for q in quotes if q.change_pct is not None and q.change_pct == 0)
                limit_up = sum(1 for q in quotes if q.change_pct and q.change_pct >= 9.9)
                limit_down = sum(1 for q in quotes if q.change_pct and q.change_pct <= -9.9)
                total_amount = sum(q.amount for q in quotes if q.amount) / 1e8
                total = up_count + down_count + flat_count
                temp = up_count / total if total > 0 else 0.5

                # 市场温度
                if temp > 0.6:
                    temp_label, temp_color, temp_icon = "偏暖", "#FF4444", "☀️"
                elif temp > 0.4:
                    temp_label, temp_color, temp_icon = "中性", "#FFB800", "⛅"
                else:
                    temp_label, temp_color, temp_icon = "偏冷", "#00E676", "🌧️"

                # 温度条
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1a1f2e 0%, #151b28 100%); padding: 1.5rem; border-radius: 12px; border: 1px solid #1e2738; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="color: #6b7280; font-size: 0.85rem;">市场温度</span>
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.3rem;">
                                <span style="font-size: 2.5rem;">{temp_icon}</span>
                                <span style="font-size: 2rem; font-weight: 700; color: {temp_color};">{temp_label}</span>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: #6b7280; font-size: 0.85rem;">上涨占比</span><br>
                            <span style="font-size: 2.5rem; font-weight: 700; color: {temp_color};">{temp*100:.1f}%</span>
                        </div>
                    </div>
                    <div style="margin-top: 1rem; background: #0a0e17; border-radius: 8px; height: 8px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #00E676, #FFB800, #FF4444); height: 100%; width: {temp*100}%; border-radius: 8px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 核心指标卡片
                cols = st.columns(6)
                metrics = [
                    ("上涨", up_count, "#FF4444", "+"),
                    ("下跌", down_count, "#00E676", ""),
                    ("平盘", flat_count, "#888", ""),
                    ("涨停", limit_up, "#FF4444", ""),
                    ("跌停", limit_down, "#00E676", ""),
                    ("成交额", f"{total_amount:.0f}亿", "#FFB800", ""),
                ]

                for i, (label, value, color, prefix) in enumerate(metrics):
                    with cols[i]:
                        st.markdown(f"""
                        <div class="metric-card" style="text-align: center;">
                            <div class="metric-label">{label}</div>
                            <div style="color: {color}; font-size: 1.8rem; font-weight: 700; margin-top: 0.3rem;">{prefix}{value}</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # 涨幅榜 / 跌幅榜 / 成交额榜
                tab1, tab2, tab3 = st.tabs(["📈 涨幅榜", "📉 跌幅榜", "💰 成交额榜"])

                with tab1:
                    top_gainers = sorted(
                        [q for q in quotes if q.change_pct and q.change_pct > 0],
                        key=lambda x: x.change_pct, reverse=True
                    )[:15]

                    for i, q in enumerate(top_gainers):
                        stock = db.query(StockBasic).filter(StockBasic.code == q.code).first()
                        name = stock.name if stock else q.code
                        st.markdown(f"""
                        <div class="stock-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <span style="color: #6b7280; font-size: 0.85rem; width: 20px;">{i+1}</span>
                                    <div>
                                        <div style="color: #E6EDF3; font-weight: 600;">{name}</div>
                                        <div style="color: #6b7280; font-size: 0.8rem;">{q.code}</div>
                                    </div>
                                </div>
                                <div style="text-align: right;">
                                    <div class="price-up" style="font-size: 1.1rem;">¥{q.close:.2f}</div>
                                    <div class="price-up">+{q.change_pct:.2f}%</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                with tab2:
                    top_losers = sorted(
                        [q for q in quotes if q.change_pct and q.change_pct < 0],
                        key=lambda x: x.change_pct
                    )[:15]

                    for i, q in enumerate(top_losers):
                        stock = db.query(StockBasic).filter(StockBasic.code == q.code).first()
                        name = stock.name if stock else q.code
                        st.markdown(f"""
                        <div class="stock-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <span style="color: #6b7280; font-size: 0.85rem; width: 20px;">{i+1}</span>
                                    <div>
                                        <div style="color: #E6EDF3; font-weight: 600;">{name}</div>
                                        <div style="color: #6b7280; font-size: 0.8rem;">{q.code}</div>
                                    </div>
                                </div>
                                <div style="text-align: right;">
                                    <div class="price-down" style="font-size: 1.1rem;">¥{q.close:.2f}</div>
                                    <div class="price-down">{q.change_pct:.2f}%</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                with tab3:
                    top_volume = sorted(
                        [q for q in quotes if q.amount],
                        key=lambda x: x.amount, reverse=True
                    )[:15]

                    for i, q in enumerate(top_volume):
                        stock = db.query(StockBasic).filter(StockBasic.code == q.code).first()
                        name = stock.name if stock else q.code
                        st.markdown(f"""
                        <div class="stock-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <span style="color: #6b7280; font-size: 0.85rem; width: 20px;">{i+1}</span>
                                    <div>
                                        <div style="color: #E6EDF3; font-weight: 600;">{name}</div>
                                        <div style="color: #6b7280; font-size: 0.8rem;">{q.code}</div>
                                    </div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="color: #FFB800; font-size: 1.1rem;">{q.amount/1e8:.1f}亿</div>
                                    <div style="color: {'#FF4444' if q.change_pct and q.change_pct > 0 else '#00E676'};">{q.change_pct:+.2f}%</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

            else:
                st.warning("暂无数据，请先采集")
        else:
            st.warning("暂无数据，请先采集")

    finally:
        db.close()
