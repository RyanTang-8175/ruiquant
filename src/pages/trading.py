"""模拟交易 — 持仓盈亏追踪 + 收益曲线"""

import streamlit as st
from src.trading.engine import TradingEngine
from src.data.realtime import get_realtime_quote
from src.data.market_board import board_label


def _discipline_card():
    st.markdown(
        '<div class="card" style="border-left:3px solid var(--amber);margin-bottom:12px">'
        '<div style="font-weight:780;color:var(--text);font-size:15px">模拟交易纪律</div>'
        '<div style="font-size:12px;color:var(--muted);line-height:1.55;margin-top:4px">'
        '这里记录研究验证，不等同实盘下单。买入前应先有：最新行情/新闻证据、风险闸门、审计假设、失效条件；'
        '默认主板优先，创业板/科创板只作为联动参考，除非你主动切换策略范围。</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_trading_page():
    with TradingEngine() as eng:
        acct = eng.get_account()
        if not acct:
            st.error("无账户"); return
        pos = eng.get_positions()
        trd = eng.get_trades(30)

    _discipline_card()

    # ── 资产总览 ──
    pval = 0
    pdat = []
    for p in pos:
        q = get_realtime_quote(p.code)
        mp = q["price"] if q else p.cost_price
        pnl = (mp - p.cost_price) * p.quantity
        pct = (mp - p.cost_price) / p.cost_price * 100 if p.cost_price else 0
        pval += p.quantity * mp
        pdat.append({"code": p.code, "name": p.name or p.code, "qty": p.quantity,
                      "cost": p.cost_price, "price": mp, "pnl": pnl, "pct": pct})
    tv = acct.cash + pval
    tpnl = tv - acct.initial_capital
    tpc = tpnl / acct.initial_capital * 100 if acct.initial_capital else 0

    st.markdown('<div class="sec-h">资产总览</div>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("总资产", f"{tv:,.0f}", f"{tpc:+.1f}%")
    m2.metric("现金", f"{acct.cash:,.0f}")
    m3.metric("持仓市值", f"{pval:,.0f}")
    m4.metric("浮动盈亏", f"{tpnl:+,.0f}")
    m5.metric("收益率", f"{tpc:+.2f}%")

    # ── 收益曲线 ──
    sells = [t for t in trd if t.direction == "sell" and t.pnl is not None]
    if sells:
        st.markdown('<div class="sec-h">收益走势</div>', unsafe_allow_html=True)
        try:
            import plotly.graph_objects as go
            sells.sort(key=lambda t: t.created_at)
            curve = [0]
            cumulative = 0
            for t in sells:
                cumulative += t.pnl
                curve.append(cumulative)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=curve, mode="lines+markers",
                line=dict(color="#002FA7", width=1.5),
                marker=dict(size=4, color=["#CF0011" if v < 0 else "#007348" for v in curve]),
                fill="tozeroy", fillcolor="rgba(0,47,167,0.06)",
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="#9AA4B2", opacity=0.5)
            fig.update_layout(
                height=160, margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, visible=False),
                yaxis=dict(showgrid=True, gridcolor="#E7EEF6", tickfont=dict(size=9, color="#5D6B7C")),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        except Exception:
            pass

    # ── 买入 ──
    st.markdown('<div class="sec-h">买入</div>', unsafe_allow_html=True)
    b1, b2, b3 = st.columns([3, 1, 1])
    with b1:
        bc = st.text_input("代码", placeholder="600519", key="bc", label_visibility="collapsed")
    with b2:
        bq = st.number_input("数量", 100, 999900, 100, key="bq", label_visibility="collapsed")
    with b3:
        st.write("")
        st.markdown('<div class="btn-buy">', unsafe_allow_html=True)
        if st.button("买入", key="buy", use_container_width=True):
            if bc:
                q = get_realtime_quote(bc.strip())
                if q and q.get("price"):
                    with TradingEngine() as e:
                        r = e.execute_buy(bc.strip(), q.get("name", bc.strip()), q["price"], bq)
                    if r["success"]:
                        st.success(f"已买 {q.get('name', bc)} {bq}股 @{q['price']:.2f}")
                        st.rerun()
                    else:
                        st.error(r["reason"])
                else:
                    st.error("无行情")
        st.markdown('</div>', unsafe_allow_html=True)
    if bc:
        st.caption(f"板块识别：{board_label(bc)} · 买入前请确认已在研究/审计页形成证据链。")

    # ── 持仓 ──
    st.markdown('<div class="sec-h">持仓</div>', unsafe_allow_html=True)
    if not pdat:
        st.caption("暂无持仓")
    else:
        for pd_item in pdat:
            code = pd_item["code"]
            name = pd_item["name"]
            qty = pd_item["qty"]
            cost = pd_item["cost"]
            price = pd_item["price"]
            pnl = pd_item["pnl"]
            pct_val = pd_item["pct"]
            clr = "var(--red)" if pnl >= 0 else "var(--green)"
            mkt_val = qty * price
            pos_pct = mkt_val / tv * 100 if tv > 0 else 0

            c1, c2, c3, c4, c5 = st.columns([2.5, 1.5, 2, 1, 1])
            with c1:
                st.markdown(f"**{name}** <span style='font-size:11px;color:var(--muted)'>{code}</span>",
                            unsafe_allow_html=True)
                st.caption(f"{board_label(code)} · {qty}股 · 成本{cost:.2f} · 市值{mkt_val:,.0f} · 占比{pos_pct:.0f}%")
            with c2:
                st.markdown(
                    f'<span style="font-family:var(--mono);font-size:15px;font-weight:700;color:{clr}">{price:.2f}</span>',
                    unsafe_allow_html=True)
            with c3:
                st.markdown(
                    f'<span style="color:{clr};font-family:var(--mono);font-weight:600;font-size:15px">'
                    f'{pnl:+,.0f}</span> '
                    f'<span style="color:{clr};font-family:var(--mono);font-size:12px">({pct_val:+.1f}%)</span>',
                    unsafe_allow_html=True)
            with c4:
                if st.button("卖出", key=f"s_{code}"):
                    st.session_state[f"sf_{code}"] = True
            with c5:
                if st.button("加仓", key=f"ac_{code}"):
                    st.session_state["ac_code"] = code
                    st.session_state["ac_price"] = price
                    st.rerun()

            if st.session_state.get(f"sf_{code}"):
                s1, s2, s3 = st.columns([2, 1, 1])
                with s1:
                    sq = st.number_input("数量", 100, qty, qty, 100, key=f"sq_{code}", label_visibility="collapsed")
                with s2:
                    st.markdown('<div class="btn-sell">', unsafe_allow_html=True)
                    if st.button("确认", key=f"cs_{code}", use_container_width=True):
                        with TradingEngine() as e:
                            r = e.execute_sell(code, price, sq)
                        if r["success"]:
                            st.success(f"盈亏{r['pnl']:+,.0f}")
                            st.session_state.pop(f"sf_{code}", None)
                            st.rerun()
                        else:
                            st.error(r["reason"])
                    st.markdown('</div>', unsafe_allow_html=True)
                with s3:
                    if st.button("取消", key=f"cx_{code}"):
                        st.session_state.pop(f"sf_{code}", None)
                        st.rerun()

    # ── 成交记录 ──
    st.markdown('<div class="sec-h">成交记录</div>', unsafe_allow_html=True)
    if not trd:
        st.caption("暂无成交")
    else:
        for t in trd[:20]:
            d = "买入" if t.direction == "buy" else "卖出"
            pn = ""
            if t.direction == "sell" and t.pnl is not None:
                pc = "var(--red)" if t.pnl >= 0 else "var(--green)"
                pn = f' <span style="color:{pc};font-family:var(--mono);font-weight:600">{t.pnl:+,.0f}</span>'
            st.markdown(f'{d} **{t.name or t.code}** {t.quantity}股 @{t.price:.2f} = {t.amount:,.0f}{pn}',
                        unsafe_allow_html=True)
            t_ts = t.created_at.strftime("%m-%d %H:%M") if hasattr(t, "created_at") and t.created_at else ""
            if t_ts:
                st.caption(t_ts)
