"""
模拟盘页面
"""

import streamlit as st
from src.trading.models import PaperAccount, Position, Trade
from src.utils.database import SessionLocal


def render_trading_page():
    """渲染模拟盘页面"""
    st.markdown('<div class="main-header">💰 模拟盘</div>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        account = db.query(PaperAccount).first()
        if not account:
            st.error("模拟盘账户未初始化，请运行 init_db.py")
            return

        positions = db.query(Position).filter(Position.account_id == account.id).all()
        trades = db.query(Trade).filter(Trade.account_id == account.id).order_by(Trade.created_at.desc()).limit(10).all()

        # 账户概览
        position_value = sum(p.quantity * p.cost_price for p in positions)
        total_value = account.cash + position_value
        total_pnl = total_value - account.initial_capital
        pnl_pct = (total_pnl / account.initial_capital * 100) if account.initial_capital > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总资产", f"¥{total_value:,.0f}")
        with col2:
            st.metric("现金", f"¥{account.cash:,.0f}")
        with col3:
            st.metric("持仓市值", f"¥{position_value:,.0f}")
        with col4:
            st.metric("总盈亏", f"¥{total_pnl:,.0f}", delta=f"{pnl_pct:+.2f}%")

        st.markdown("---")

        # 持仓列表
        st.subheader("我的持仓")
        if not positions:
            st.info("暂无持仓")
        else:
            for pos in positions:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        st.write(f"**{pos.name or pos.code}**")
                        st.caption(f"{pos.quantity} 股 | 成本 {pos.cost_price:.2f}")
                    with col2:
                        st.write(f"当前价: {pos.cost_price:.2f}")
                    with col3:
                        pnl = (pos.cost_price - pos.cost_price) * pos.quantity  # 需要实时价格
                        st.write(f"盈亏: -")
                    with col4:
                        if st.button("卖出", key=f"sell_{pos.code}"):
                            st.info("卖出功能开发中...")
                    st.markdown("---")

        # 交易记录
        st.subheader("最近交易")
        if not trades:
            st.info("暂无交易记录")
        else:
            for trade in trades:
                direction_emoji = "🔴" if trade.direction == "buy" else "🟢"
                direction_text = "买入" if trade.direction == "buy" else "卖出"
                st.write(f"{direction_emoji} {direction_text} {trade.name or trade.code} | {trade.quantity}股 × {trade.price:.2f} = ¥{trade.amount:,.0f}")
                st.caption(f"{trade.created_at.strftime('%Y-%m-%d %H:%M')} | 佣金 ¥{trade.commission:.2f}")

    finally:
        db.close()
