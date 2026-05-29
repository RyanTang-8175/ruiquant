"""
模拟盘页面 - 使用实时行情
"""

import streamlit as st
from src.trading.models import PaperAccount, Position, Trade
from src.trading.engine import TradingEngine
from src.data.realtime import get_realtime_quote


def render_trading_page():
    """渲染模拟盘"""
    st.markdown("## 模拟交易")

    with TradingEngine() as engine:
        account = engine.get_account()
        if not account:
            st.error("模拟盘账户未初始化，请运行 init_db.py")
            return

        positions = engine.get_positions()
        trades = engine.get_trades(limit=10)

        # 用实时行情计算市值
        position_value = 0
        position_data = []
        for p in positions:
            quote = get_realtime_quote(p.code)
            market_price = quote["price"] if quote else p.cost_price
            pnl = (market_price - p.cost_price) * p.quantity
            pnl_pct = ((market_price - p.cost_price) / p.cost_price * 100) if p.cost_price > 0 else 0
            position_value += p.quantity * market_price
            position_data.append({
                "pos": p, "quote": quote, "market_price": market_price,
                "pnl": pnl, "pnl_pct": pnl_pct,
            })

        total_value = account.cash + position_value
        total_pnl = total_value - account.initial_capital
        pnl_pct = (total_pnl / account.initial_capital * 100) if account.initial_capital > 0 else 0

        # 账户概览
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("总资产", f"¥{total_value:,.0f}", border=True)
        m2.metric("现金", f"¥{account.cash:,.0f}", border=True)
        m3.metric("持仓市值", f"¥{position_value:,.0f}", border=True)
        pnl_color = "normal" if total_pnl >= 0 else "inverse"
        m4.metric("总盈亏", f"¥{total_pnl:,.0f}", f"{pnl_pct:+.2f}%", delta_color=pnl_color, border=True)

        st.markdown("---")

        # 买入入口
        st.subheader("买入")
        buy_col1, buy_col2, buy_col3 = st.columns([2, 1, 1])
        with buy_col1:
            buy_code = st.text_input("股票代码", placeholder="如 600519", key="buy_code_input")
        with buy_col2:
            buy_qty = st.number_input("数量", min_value=100, step=100, value=100, key="buy_qty_input")
        with buy_col3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("买入", key="buy_btn", use_container_width=True, type="primary"):
                if buy_code:
                    quote = get_realtime_quote(buy_code.strip())
                    if quote and quote.get("price"):
                        price = quote["price"]
                        with TradingEngine() as eng:
                            result = eng.execute_buy(buy_code.strip(), price, buy_qty)
                        if result["success"]:
                            st.success(f"买入成功！{quote.get('name', buy_code)} {buy_qty}股 × {price:.2f}")
                            st.rerun()
                        else:
                            st.error(result["reason"])
                    else:
                        st.error(f"未找到 {buy_code} 的行情")
                else:
                    st.warning("请输入股票代码")

        st.markdown("---")

        # 持仓列表
        st.subheader("我的持仓")
        if not position_data:
            st.info("暂无持仓")
        else:
            for pd in position_data:
                p = pd["pos"]
                market_price = pd["market_price"]
                pnl = pd["pnl"]
                pnl_pct = pd["pnl_pct"]
                color = "#FF4444" if pnl >= 0 else "#00E676"

                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.markdown(f"**{p.name or p.code}** `{p.code}`")
                    st.caption(f"{p.quantity}股 | 成本 {p.cost_price:.2f}")
                with col2:
                    st.markdown(f"现价 **¥{market_price:.2f}**")
                with col3:
                    st.markdown(f"<span style='color:{color}'>盈亏 {pnl:+,.0f} ({pnl_pct:+.1f}%)</span>", unsafe_allow_html=True)
                with col4:
                    if st.button("卖出", key=f"sell_{p.code}"):
                        st.session_state[f"sell_{p.code}"] = True

                # 卖出表单
                if st.session_state.get(f"sell_{p.code}"):
                    s1, s2, s3 = st.columns([2, 1, 1])
                    with s1:
                        sell_qty = st.number_input("卖出数量", min_value=100, max_value=p.quantity, step=100, value=p.quantity, key=f"sq_{p.code}")
                    with s2:
                        if st.button("确认卖出", key=f"cs_{p.code}", type="primary"):
                            with TradingEngine() as eng:
                                result = eng.execute_sell(p.code, market_price, sell_qty)
                            if result["success"]:
                                st.success(f"卖出成功！盈亏 {result['pnl']:+,.0f}")
                                st.session_state.pop(f"sell_{p.code}", None)
                                st.rerun()
                            else:
                                st.error(result["reason"])
                    with s3:
                        if st.button("取消", key=f"cx_{p.code}"):
                            st.session_state.pop(f"sell_{p.code}", None)
                            st.rerun()

                st.markdown("---")

        # 交易记录
        st.subheader("最近交易")
        if not trades:
            st.info("暂无交易记录")
        else:
            for t in trades:
                emoji = "🔴" if t.direction == "buy" else "🟢"
                text = "买入" if t.direction == "buy" else "卖出"
                pnl_text = ""
                if t.direction == "sell" and t.pnl is not None:
                    pc = "#FF4444" if t.pnl >= 0 else "#00E676"
                    pnl_text = f' | <span style="color:{pc}">盈亏 ¥{t.pnl:+,.0f}</span>'
                st.markdown(f"{emoji} {text} **{t.name or t.code}** {t.quantity}股 × {t.price:.2f} = ¥{t.amount:,.0f}{pnl_text}", unsafe_allow_html=True)
                st.caption(f"{t.created_at.strftime('%Y-%m-%d %H:%M')}")
