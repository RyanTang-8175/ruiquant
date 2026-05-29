"""
我的页面
"""

import streamlit as st
from src.config import DEEPSEEK_API_KEY, INITIAL_CAPITAL


def render_profile_page():
    """渲染我的页面"""
    st.markdown('<div class="main-header">👤 我的</div>', unsafe_allow_html=True)

    # AI 预测记录
    st.subheader("🤖 AI 预测记录")
    try:
        from src.prediction.predictor import PredictionEngine
        pred_engine = PredictionEngine()
        pred_stats = pred_engine.get_stats()
        pred_engine.close()
    except Exception:
        pred_stats = {}

    col1, col2, col3 = st.columns(3)
    with col1:
        total_pred = pred_stats.get('total', 0)
        st.markdown(f"""
        <div class="metric-card" style="text-align: center;">
            <div class="metric-label">总预测</div>
            <div class="metric-value">{total_pred} 次</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        hit_rate = pred_stats.get('t1_hit_rate') or pred_stats.get('hit_rate_t1')
        hit_text = f"{hit_rate:.1%}" if hit_rate else "N/A"
        st.markdown(f"""
        <div class="metric-card" style="text-align: center;">
            <div class="metric-label">命中率 (T+1)</div>
            <div class="metric-value">{hit_text}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        avg_ret = pred_stats.get('avg_return_t1')
        ret_text = f"{avg_ret:+.2f}%" if avg_ret is not None else "N/A"
        st.markdown(f"""
        <div class="metric-card" style="text-align: center;">
            <div class="metric-label">平均收益 (T+1)</div>
            <div class="metric-value">{ret_text}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 交易统计
    st.subheader("📊 交易统计")
    try:
        from src.trading.engine import TradingEngine
        trade_engine = TradingEngine()
        trade_stats = trade_engine.get_stats()
        trade_engine.close()
    except Exception:
        trade_stats = {}

    col1, col2, col3 = st.columns(3)
    with col1:
        total_trades = trade_stats.get('total_trades', 0)
        st.markdown(f"""
        <div class="metric-card" style="text-align: center;">
            <div class="metric-label">总交易</div>
            <div class="metric-value">{total_trades} 笔</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        win_rate = trade_stats.get('win_rate', 0)
        win_text = f"{win_rate:.1%}" if total_trades > 0 else "N/A"
        st.markdown(f"""
        <div class="metric-card" style="text-align: center;">
            <div class="metric-label">胜率</div>
            <div class="metric-value">{win_text}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        pl_ratio = trade_stats.get('profit_loss_ratio', 0)
        pl_text = f"{pl_ratio:.2f}" if total_trades > 0 else "N/A"
        st.markdown(f"""
        <div class="metric-card" style="text-align: center;">
            <div class="metric-label">盈亏比</div>
            <div class="metric-value">{pl_text}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 每日复盘
    st.subheader("📝 每日复盘")
    if st.button("生成今日复盘", key="gen_review_btn"):
        try:
            from src.ai.chat import AIChat
            from src.data.collector import DataCollector
            collector = DataCollector()
            market_data = collector.get_market_snapshot()
            collector.close()
            ai = AIChat()
            with st.spinner("AI 正在撰写复盘..."):
                review = ai.generate_daily_review(market_data)
                st.markdown(review)
        except Exception as e:
            st.error(f"复盘生成失败: {e}")

    st.markdown("---")

    # 设置
    st.subheader("⚙️ 设置")

    with st.expander("DeepSeek API 配置"):
        masked_key = ("*" * 8) if DEEPSEEK_API_KEY else "未配置"
        st.write(f"API Key: {masked_key}")
        st.caption("在 .env 文件中配置 DEEPSEEK_API_KEY")

    with st.expander("模拟盘配置"):
        st.write(f"初始资金: ¥{INITIAL_CAPITAL:,.0f}")
        st.caption("在 .env 文件中配置 INITIAL_CAPITAL")

    with st.expander("关于"):
        st.write("**RuiQuant** - 个人 A 股 AI 研究助手")
        st.write("版本: v0.2.0")
        st.write("技术栈: Python + Streamlit + DeepSeek + baostock")
        st.write("GitHub: https://github.com/RyanTang-8175/ruiquant")
        st.caption("仅供研究学习，不构成投资建议")
