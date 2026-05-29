"""
市场概览页面 - 重新设计
"""

import streamlit as st
from datetime import datetime
from src.data.collector import DataCollector
from src.utils.database import SessionLocal
from src.data.models import DailyQuote, StockBasic


def render_market_page():
    """渲染市场概览页面"""
    st.markdown('<div class="main-header">📊 市场概览</div>', unsafe_allow_html=True)

    # 获取数据状态
    db = SessionLocal()
    try:
        # 获取最新数据日期
        latest = db.query(DailyQuote).order_by(DailyQuote.trade_date.desc()).first()
        stock_count = db.query(StockBasic).count()
        quote_count = db.query(DailyQuote).count()

        # 数据状态栏
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("股票总数", f"{stock_count}")
        with col2:
            st.metric("数据条数", f"{quote_count:,}")
        with col3:
            if latest:
                st.metric("最新数据", str(latest.trade_date))
            else:
                st.metric("最新数据", "无")
        with col4:
            if latest:
                days_old = (datetime.now().date() - latest.trade_date).days
                if days_old == 0:
                    st.metric("数据状态", "✅ 今日")
                elif days_old == 1:
                    st.metric("数据状态", "⚠️ 昨日")
                else:
                    st.metric("数据状态", f"❌ {days_old}天前")
            else:
                st.metric("数据状态", "❌ 无数据")

        st.markdown("---")

        # 采集按钮
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📥 采集最新数据", use_container_width=True, type="primary"):
                with st.spinner("正在采集数据..."):
                    try:
                        collector = DataCollector()
                        collector.collect_all_stocks(days=30)
                        collector.close()
                        st.success("数据采集完成！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"采集失败: {e}")

        with col2:
            if st.button("🔄 刷新页面", use_container_width=True):
                st.rerun()

        with col3:
            if st.button("📊 计算评分", use_container_width=True):
                with st.spinner("正在计算评分..."):
                    try:
                        from src.scoring.engine import ScoringEngine
                        engine = ScoringEngine()
                        results = engine.get_watchlist(min_score=0, limit=100)
                        engine.close()
                        st.session_state['watchlist'] = results
                        st.success(f"评分完成！共 {len(results)} 只股票")
                    except Exception as e:
                        st.error(f"评分失败: {e}")

        st.markdown("---")

        # 市场数据
        if latest:
            # 获取今日数据
            quotes = db.query(DailyQuote).filter(
                DailyQuote.trade_date == latest.trade_date
            ).all()

            if quotes:
                # 计算涨跌统计
                up_count = sum(1 for q in quotes if q.change_pct and q.change_pct > 0)
                down_count = sum(1 for q in quotes if q.change_pct and q.change_pct < 0)
                flat_count = sum(1 for q in quotes if q.change_pct and q.change_pct == 0)
                limit_up = sum(1 for q in quotes if q.change_pct and q.change_pct >= 9.9)
                limit_down = sum(1 for q in quotes if q.change_pct and q.change_pct <= -9.9)
                total_amount = sum(q.amount for q in quotes if q.amount) / 1e8

                # 市场温度
                total = up_count + down_count + flat_count
                temp = up_count / total if total > 0 else 0.5

                if temp > 0.6:
                    temp_label = "☀️ 偏暖"
                    temp_color = "#FF4444"
                elif temp > 0.4:
                    temp_label = "⛅ 中性"
                    temp_color = "#FFB800"
                else:
                    temp_label = "🌧️ 偏冷"
                    temp_color = "#00E676"

                # 市场温度显示
                st.markdown(f"""
                <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%); border-radius: 12px; border: 1px solid #2D3748;">
                    <span style="font-size: 1rem; color: #888;">市场温度</span><br>
                    <span style="font-size: 3rem; color: {temp_color};">{temp_label}</span><br>
                    <span style="color: #666; font-size: 1.2rem;">上涨占比 {temp*100:.1f}%</span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # 核心指标
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                with col1:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: #1A1A2E; border-radius: 8px;">
                        <div style="color: #888; font-size: 0.8rem;">上涨家数</div>
                        <div style="color: #FF4444; font-size: 1.8rem; font-weight: bold;">{up_count}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: #1A1A2E; border-radius: 8px;">
                        <div style="color: #888; font-size: 0.8rem;">下跌家数</div>
                        <div style="color: #00E676; font-size: 1.8rem; font-weight: bold;">{down_count}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: #1A1A2E; border-radius: 8px;">
                        <div style="color: #888; font-size: 0.8rem;">平盘</div>
                        <div style="color: #888; font-size: 1.8rem; font-weight: bold;">{flat_count}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: #1A1A2E; border-radius: 8px;">
                        <div style="color: #888; font-size: 0.8rem;">涨停</div>
                        <div style="color: #FF4444; font-size: 1.8rem; font-weight: bold;">{limit_up}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col5:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: #1A1A2E; border-radius: 8px;">
                        <div style="color: #888; font-size: 0.8rem;">跌停</div>
                        <div style="color: #00E676; font-size: 1.8rem; font-weight: bold;">{limit_down}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col6:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background: #1A1A2E; border-radius: 8px;">
                        <div style="color: #888; font-size: 0.8rem;">成交额</div>
                        <div style="color: #FFB800; font-size: 1.8rem; font-weight: bold;">{total_amount:.0f}亿</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # 涨幅榜和跌幅榜
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📈 涨幅榜 TOP 10")
                    top_gainers = sorted(
                        [q for q in quotes if q.change_pct and q.change_pct > 0],
                        key=lambda x: x.change_pct,
                        reverse=True
                    )[:10]

                    for i, q in enumerate(top_gainers):
                        stock = db.query(StockBasic).filter(StockBasic.code == q.code).first()
                        name = stock.name if stock else q.code
                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; padding: 0.5rem; border-bottom: 1px solid #2D3748;">
                            <span style="color: #E6EDF3;">{i+1}. {name}</span>
                            <span style="color: #FF4444; font-weight: bold;">+{q.change_pct:.2f}%</span>
                        </div>
                        """, unsafe_allow_html=True)

                with col2:
                    st.subheader("📉 跌幅榜 TOP 10")
                    top_losers = sorted(
                        [q for q in quotes if q.change_pct and q.change_pct < 0],
                        key=lambda x: x.change_pct
                    )[:10]

                    for i, q in enumerate(top_losers):
                        stock = db.query(StockBasic).filter(StockBasic.code == q.code).first()
                        name = stock.name if stock else q.code
                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; padding: 0.5rem; border-bottom: 1px solid #2D3748;">
                            <span style="color: #E6EDF3;">{i+1}. {name}</span>
                            <span style="color: #00E676; font-weight: bold;">{q.change_pct:.2f}%</span>
                        </div>
                        """, unsafe_allow_html=True)

                # 成交额榜
                st.subheader("💰 成交额榜 TOP 10")
                top_volume = sorted(
                    [q for q in quotes if q.amount],
                    key=lambda x: x.amount,
                    reverse=True
                )[:10]

                cols = st.columns(5)
                for i, q in enumerate(top_volume):
                    stock = db.query(StockBasic).filter(StockBasic.code == q.code).first()
                    name = stock.name if stock else q.code
                    with cols[i % 5]:
                        st.markdown(f"""
                        <div style="text-align: center; padding: 0.8rem; background: #1A1A2E; border-radius: 8px;">
                            <div style="color: #E6EDF3; font-size: 0.9rem;">{name}</div>
                            <div style="color: #FFB800; font-size: 1rem;">{q.amount/1e8:.1f}亿</div>
                        </div>
                        """, unsafe_allow_html=True)

            else:
                st.warning("暂无数据，请先采集数据")
        else:
            st.warning("暂无数据，请先点击「采集最新数据」按钮")

    finally:
        db.close()
