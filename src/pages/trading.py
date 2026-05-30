"""模拟交易"""

import streamlit as st
from src.trading.engine import TradingEngine
from src.data.realtime import get_realtime_quote

def render_trading_page():
    st.markdown("## 模拟交易")

    with TradingEngine() as eng:
        acct = eng.get_account()
        if not acct: st.error("未初始化"); return

        pos = eng.get_positions()
        trd = eng.get_trades(10)

        pval = 0; pdat = []
        for p in pos:
            q = get_realtime_quote(p.code)
            mp = q["price"] if q else p.cost_price
            pnl = (mp-p.cost_price)*p.quantity
            pct = (mp-p.cost_price)/p.cost_price*100 if p.cost_price else 0
            pval += p.quantity*mp
            pdat.append({"p":p,"mp":mp,"pnl":pnl,"pct":pct})

        tv = acct.cash+pval
        tpnl = tv-acct.initial_capital
        tpc = tpnl/acct.initial_capital*100 if acct.initial_capital else 0

        mm = st.columns(4)
        mm[0].metric("总资产", f"¥{tv:,.0f}", border=True)
        mm[1].metric("现金", f"¥{acct.cash:,.0f}", border=True)
        mm[2].metric("市值", f"¥{pval:,.0f}", border=True)
        mm[3].metric("盈亏", f"¥{tpnl:,.0f}", f"{tpc:+.1f}%", border=True)

    st.markdown("---")
    st.subheader("买入")
    b1,b2,b3 = st.columns([2,1,1])
    with b1: bc = st.text_input("代码", placeholder="600519", key="bc")
    with b2: bq = st.number_input("数量", 100, 999900, 100, key="bq")
    with b3:
        st.write("")
        if st.button("买入", key="buy", type="primary", use_container_width=True):
            if bc:
                q = get_realtime_quote(bc.strip())
                if q and q.get("price"):
                    with TradingEngine() as e:
                        r = e.execute_buy(bc.strip(), q["price"], bq)
                    if r["success"]:
                        st.success(f"买入 {q.get('name',bc)} {bq}股 × ¥{q['price']:.2f}"); st.rerun()
                    else: st.error(r["reason"])
                else: st.error("无数据")

    st.markdown("---")
    st.subheader("持仓")
    if not pdat:
        st.info("暂无")
    else:
        for pd in pdat:
            p = pd["p"]; mp = pd["mp"]; pnl = pd["pnl"]; pct = pd["pct"]
            clr = "#f53b47" if pnl>=0 else "#00b468"
            c1,c2,c3,c4 = st.columns([3,2,2,1])
            c1.markdown(f"**{p.name or p.code}** `{p.code}`")
            c1.caption(f"{p.quantity}股 成本{p.cost_price:.2f}")
            c2.markdown(f"现价 **¥{mp:.2f}**")
            c3.markdown(f"<span style='color:{clr}'>盈亏 {pnl:+,.0f} ({pct:+.1f}%)</span>", unsafe_allow_html=True)
            with c4:
                if st.button("卖", key=f"s_{p.code}"):
                    st.session_state[f"sf_{p.code}"] = True
            if st.session_state.get(f"sf_{p.code}"):
                s1,s2,s3 = st.columns([2,1,1])
                with s1: sq = st.number_input("数量", 100, p.quantity, p.quantity, 100, key=f"sq_{p.code}")
                with s2:
                    if st.button("确认", key=f"cs_{p.code}", type="primary"):
                        with TradingEngine() as e: r = e.execute_sell(p.code, mp, sq)
                        if r["success"]:
                            st.success(f"盈亏 {r['pnl']:+,.0f}"); st.session_state.pop(f"sf_{p.code}",None); st.rerun()
                        else: st.error(r["reason"])
                with s3:
                    if st.button("取消", key=f"cx_{p.code}"): st.session_state.pop(f"sf_{p.code}",None); st.rerun()

    st.markdown("---")
    st.subheader("最近交易")
    if not trd: st.info("暂无")
    else:
        for t in trd:
            d = "🔴买" if t.direction=="buy" else "🟢卖"
            pn = ""
            if t.direction=="sell" and t.pnl is not None:
                pc = "#f53b47" if t.pnl>=0 else "#00b468"
                pn = f'  <span style="color:{pc}">盈 ¥{t.pnl:+,.0f}</span>'
            st.markdown(f"{d} **{t.name or t.code}** {t.quantity}股×¥{t.price:.2f}=¥{t.amount:,.0f}{pn}", unsafe_allow_html=True)
            st.caption(t.created_at.strftime("%Y-%m-%d %H:%M"))
