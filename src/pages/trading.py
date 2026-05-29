"""
模拟盘页面
"""

import streamlit as st
from src.trading.models import PaperAccount, Position, Trade
from src.trading.engine import TradingEngine
from src.data.models import DailyQuote
from src.utils.database import SessionLocal


def _get_market_prices(db, codes: list) -> dict:
    """批量获取最新市场价格"""
    prices = {}
    if not codes:
        return prices
    from sqlalchemy import func
    subq = db.query(
        DailyQuote.code,
        func.max(DailyQuote.trade_date).label('max_date')
    ).filter(DailyQuote.code.in_(codes)).group_by(DailyQuote.code).subquery()
    quotes = db.query(DailyQuote).join(
        subq,
        (DailyQuote.code == subq.c.code) & (DailyQuote.trade_date == subq.c.max_date)
    ).all()
    for q in quotes:
        prices[q.code] = q
    return prices


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

        # 批量获取市场价
        codes = [p.code for p in positions]
        market_data = _get_market_prices(db, codes)

        # 账户概览（用市场价计算真实市值）
        position_value = 0
        for p in positions:
            quote = market_data.get(p.code)
            current_price = quote.close if quote else p.cost_price
            position_value += p.quantity * current_price

        total_value = account.cash + position_value
        total_pnl = total_value - account.initial_capital
        pnl_pct = (total_pnl / account.initial_capital * 100) if account.initial_capital > 0 else 0

        # 指标卡片
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <div class="metric-label">总资产</div>
                <div class="metric-value">¥{total_value:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <div class="metric-label">现金</div>
                <div class="metric-value">¥{account.cash:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <div class="metric-label">持仓市值</div>
                <div class="metric-value">¥{position_value:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        pnl_color = "#FF4444" if total_pnl >= 0 else "#00E676"
        with col4:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <div class="metric-label">总盈亏</div>
                <div class="metric-value" style="color: {pnl_color};">¥{total_pnl:,.0f}</div>
                <div style="color: {pnl_color}; font-size: 0.85rem;">{pnl_pct:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # 买入入口
        st.subheader("📥 买入")
        buy_col1, buy_col2, buy_col3 = st.columns([2, 1, 1])
        with buy_col1:
            buy_code = st.text_input("股票代码", placeholder="如 600519", key="buy_code_input")
        with buy_col2:
            buy_qty = st.number_input("数量（股）", min_value=100, step=100, value=100, key="buy_qty_input")
        with buy_col3:
            st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
            if st.button("📥 买入", key="buy_btn", use_container_width=True):
                if buy_code:
                    engine = TradingEngine()
                    price = engine.get_current_price(buy_code.strip())
                    if price:
                        result = engine.execute_buy(buy_code.strip(), price, buy_qty)
                        if result["success"]:
                            st.success(f"买入成功！{buy_code} {buy_qty}股 × {price:.2f}")
                            st.rerun()
                        else:
                            st.error(result["reason"])
                    else:
                        st.error(f"未找到股票 {buy_code} 的行情数据")
                    engine.close()
                else:
                    st.warning("请输入股票代码")

        st.markdown("---")

        # 持仓列表
        st.subheader("我的持仓")
        if not positions:
            st.info("暂无持仓")
        else:
            for pos in positions:
                quote = market_data.get(pos.code)
                market_price = quote.close if quote else pos.cost_price
                pnl = (market_price - pos.cost_price) * pos.quantity
                pnl_pct_pos = ((market_price - pos.cost_price) / pos.cost_price * 100) if pos.cost_price > 0 else 0
                color = "#FF4444" if pnl >= 0 else "#00E676"

                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        st.write(f"**{pos.name or pos.code}**")
                        st.caption(f"{pos.quantity} 股 | 成本 {pos.cost_price:.2f}")
                    with col2:
                        st.write(f"当前价: {market_price:.2f}")
                    with col3:
                        st.markdown(f"<span style='color:{color}'>盈亏: {pnl:+,.0f} ({pnl_pct_pos:+.1f}%)</span>", unsafe_allow_html=True)
                    with col4:
                        if st.button("卖出", key=f"sell_{pos.code}"):
                            st.session_state[f'sell_form_{pos.code}'] = True

                    # 卖出表单
                    if st.session_state.get(f'sell_form_{pos.code}'):
                        with st.container():
                            sell_col1, sell_col2, sell_col3 = st.columns([2, 1, 1])
                            with sell_col1:
                                sell_qty = st.number_input(
                                    "卖出数量",
                                    min_value=100,
                                    max_value=pos.quantity,
                                    step=100,
                                    value=pos.quantity,
                                    key=f"sell_qty_{pos.code}"
                                )
                            with sell_col2:
                                st.markdown(f"<div style='height: 28px'></div>", unsafe_allow_html=True)
                                if st.button("确认卖出", key=f"confirm_sell_{pos.code}"):
                                    engine = TradingEngine()
                                    result = engine.execute_sell(pos.code, market_price, sell_qty)
                                    engine.close()
                                    if result["success"]:
                                        st.success(f"卖出成功！盈亏 {result['pnl']:+,.2f}")
                                        if f'sell_form_{pos.code}' in st.session_state:
                                            del st.session_state[f'sell_form_{pos.code}']
                                        st.rerun()
                                    else:
                                        st.error(result["reason"])
                            with sell_col3:
                                st.markdown(f"<div style='height: 28px'></div>", unsafe_allow_html=True)
                                if st.button("取消", key=f"cancel_sell_{pos.code}"):
                                    del st.session_state[f'sell_form_{pos.code}']
                                    st.rerun()

                    st.markdown("---")

        # 交易记录
        st.subheader("最近交易")
        if not trades:
            st.info("暂无交易记录")
        else:
            for trade in trades:
                direction_emoji = "🔴" if trade.direction == "buy" else "🟢"
                direction_text = "买入" if trade.direction == "buy" else "卖出"
                pnl_text = ""
                if trade.direction == "sell" and trade.pnl is not None:
                    pnl_color = "#FF4444" if trade.pnl >= 0 else "#00E676"
                    pnl_text = f' | <span style="color:{pnl_color}">盈亏 ¥{trade.pnl:+,.0f}</span>'
                st.markdown(f"{direction_emoji} {direction_text} **{trade.name or trade.code}** | {trade.quantity}股 × {trade.price:.2f} = ¥{trade.amount:,.0f}{pnl_text}", unsafe_allow_html=True)
                st.caption(f"{trade.created_at.strftime('%Y-%m-%d %H:%M')} | 佣金 ¥{trade.commission:.2f}")

    finally:
        db.close()
