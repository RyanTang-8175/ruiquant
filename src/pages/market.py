"""
市场概览页面
"""

import streamlit as st
from src.data.collector import DataCollector


def render_market_page():
    """渲染市场概览页面"""
    st.markdown('<div class="main-header">📊 市场概览</div>', unsafe_allow_html=True)

    # 获取市场数据
    try:
        with DataCollector() as collector:
            snapshot = collector.get_market_snapshot()
    except Exception as e:
        st.error(f"获取数据失败: {e}")
        snapshot = {}

    if "error" in snapshot:
        st.warning("暂无数据，请先运行数据采集")
        if st.button("开始采集数据"):
            with st.spinner("正在采集数据..."):
                try:
                    with DataCollector() as collector:
                        collector.collect_all_stocks(days=30)
                    st.success("数据采集完成！")
                    st.rerun()
                except Exception as e:
                    st.error(f"采集失败: {e}")
        return

    # 市场温度
    up = snapshot.get("up_count", 0)
    down = snapshot.get("down_count", 0)
    total = up + down
    temp = up / total if total > 0 else 0.5

    if temp > 0.6:
        temp_label = "☀️ 偏暖"
        temp_color = "#FF4444"
    elif temp > 0.4:
        temp_label = "⛅ 中性"
        temp_color = "#FFB800"
    else:
        temp_label = "🌧️ 偏冷"
        temp_color = "#00E676"

    # 顶部指标卡片
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("上涨家数", f"{up}", delta=f"{up/total*100:.1f}%" if total > 0 else "N/A")

    with col2:
        st.metric("下跌家数", f"{down}", delta=f"-{down/total*100:.1f}%" if total > 0 else "N/A")

    with col3:
        st.metric("涨停", f"{snapshot.get('limit_up_count', 0)}")

    with col4:
        st.metric("跌停", f"{snapshot.get('limit_down_count', 0)}")

    with col5:
        st.metric("成交额", f"{snapshot.get('total_amount_yi', 0):.0f} 亿")

    st.markdown("---")

    # 市场温度
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem;">
        <span style="font-size: 1.2rem; color: #888;">市场温度</span><br>
        <span style="font-size: 2rem; color: {temp_color};">{temp_label}</span><br>
        <span style="color: #666;">上涨占比 {temp*100:.1f}%</span>
    </div>
    """, unsafe_allow_html=True)

    # 数据采集按钮
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("📥 采集最新数据", use_container_width=True):
            with st.spinner("正在采集..."):
                try:
                    with DataCollector() as collector:
                        collector.collect_all_stocks(days=5)
                    st.success("采集完成！")
                    st.rerun()
                except Exception as e:
                    st.error(f"失败: {e}")
