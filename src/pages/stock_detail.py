"""股票详情"""

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
    if v > 0: return "#f53b47"
    if v < 0: return "#00b468"
    return "#888"

def render_stock_detail_page(code=None):
    if not code: code = st.session_state.get("selected_stock", "")
    if not code: st.warning("请先选择股票"); return

    q = get_realtime_quote(code)
    if not q: st.error(f"无 {code} 数据"); return

    name, price, pct = q.get("name", code), q.get("price", 0), q.get("change_pct", 0)
    clr, sgn = _c(pct), "+" if pct > 0 else ""

    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:baseline;padding:0.5rem 0;"><div><span style="font-size:1.6rem;font-weight:900;color:var(--text);">{name}</span><span style="color:var(--muted);margin-left:0.5rem;font-size:0.85rem;">{code}</span></div><div style="text-align:right;"><span style="font-size:2rem;font-weight:900;color:{clr};">¥{price:.2f}</span><span style="color:{clr};font-size:1rem;margin-left:0.5rem;">{sgn}{pct:.2f}%</span></div></div>', unsafe_allow_html=True)

    mm = st.columns(6)
    mm[0].metric("今开", f"{q.get('open',0):.2f}", border=True)
    mm[1].metric("最高", f"{q.get('high',0):.2f}", border=True)
    mm[2].metric("最低", f"{q.get('low',0):.2f}", border=True)
    mm[3].metric("量(万手)", f"{q.get('volume',0)/10000:.0f}", border=True)
    mm[4].metric("额(亿)", f"{q.get('amount',0)/1e8:.1f}", border=True)
    mm[5].metric("换手", f"{q.get('turnover',0):.2f}%", border=True)

    st.markdown("---")
    st.subheader("K线图")

    pm = {"1分":"1","5分":"5","15分":"15","30分":"30","60分":"60","日":"101","周":"102"}
    sel = st.radio("", list(pm.keys()), horizontal=True, key="kp")
    kl = get_kline(code, period=pm[sel], count=120)

    if kl and HAS_PLOTLY:
        df = pd.DataFrame(kl)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.78,0.22])
        fig.add_trace(go.Candlestick(x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
            increasing_line_color="#f53b47", decreasing_line_color="#00b468",
            increasing_fillcolor="rgba(245,59,71,0.5)", decreasing_fillcolor="rgba(0,180,104,0.5)"), row=1, col=1)
        for ma,clr in [(5,"#f0a030"),(10,"#3399ff"),(20,"#b050e0")]:
            if len(df) >= ma:
                fig.add_trace(go.Scatter(x=df["date"], y=df["close"].rolling(ma).mean(), name=f"MA{ma}", line=dict(color=clr,width=1)), row=1, col=1)
        colors = ["#f53b47" if c>=o else "#00b468" for c,o in zip(df["close"].fillna(0), df["open"].fillna(0))]
        fig.add_trace(go.Bar(x=df["date"], y=df["volume"], marker_color=colors), row=2, col=1)
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0a0d14", plot_bgcolor="#0a0d14",
            height=500, margin=dict(l=0,r=0,t=10,b=0), showlegend=False,
            xaxis=dict(gridcolor="#1f2534"), yaxis=dict(gridcolor="#1f2534"),
            xaxis2=dict(gridcolor="#1f2534"), yaxis2=dict(gridcolor="#1f2534"))
        st.plotly_chart(fig, use_container_width=True)
    elif kl:
        st.line_chart(pd.DataFrame(kl).set_index("date")["close"])
    else:
        st.info("暂无K线")

    st.markdown("---")
    st.subheader("量化评分")

    try:
        with ScoringEngine() as e:
            r = e.score_stock(code)
        if r:
            rc = {"强关注":"#f53b47","观察":"#3399ff","中性":"#f0a030","不追":"#555"}.get(r["rating"],"#888")
            st.markdown(f'<div style="text-align:center;padding:1.2rem;background:var(--card);border-radius:10px;border:1px solid var(--border);"><div style="font-size:3rem;font-weight:900;color:{rc};">{r["total_score"]:.0f}</div><div style="color:var(--muted);">综合评分</div><div style="margin-top:0.5rem;"><span style="background:{rc};color:#fff;padding:3px 14px;border-radius:20px;">{r["rating"]}</span></div></div>', unsafe_allow_html=True)

            fn = {"short_term_reversal":"反转","turnover_rate":"换手","volume_ratio":"量比","trend":"趋势","rsi":"RSI","macd":"MACD","kdj":"KDJ","kline_pattern":"K线","idio_volatility":"波动","blast_rate":"爆量","limit_up_streak":"连板","market_temperature":"温度","boll_position":"布林","intraday_intensity":"强度","high_52w_ratio":"52周","volume_price_divergence":"背离","volume_price_corr":"相关","amihud_illiquidity":"流动性","abnormal_turnover":"异常换手"}
            sf = sorted(r["factors"].items(), key=lambda x: x[1], reverse=True)
            cols = st.columns(3)
            for i,(k,v) in enumerate(sf[:18]):
                n = fn.get(k, k)
                bc = "#f53b47" if v>=70 else "#f0a030" if v>=50 else "#00b468"
                with cols[i%3]:
                    st.markdown(f'<div style="padding:0.4rem 0.6rem;background:var(--card);border-radius:6px;border:1px solid var(--border);margin-bottom:0.3rem;"><div style="display:flex;justify-content:space-between;"><span style="color:var(--muted);font-size:0.72rem;">{n}</span><span style="color:{bc};font-weight:700;font-size:0.8rem;">{v:.0f}</span></div><div style="background:#0a0d14;border-radius:3px;height:3px;margin-top:0.2rem;"><div style="background:{bc};height:100%;width:{min(100,v)}%;border-radius:3px;"></div></div></div>', unsafe_allow_html=True)
        else:
            st.info("暂无评分")
    except Exception as e:
        st.warning(f"评分异常: {e}")

    st.markdown("---")
    st.subheader("AI 分析")
    ctx = st.text_area("", placeholder="补充信息：如持有1000股成本50元...", key="ctx", label_visibility="collapsed")
    if st.button("AI 深度分析", key="ai_btn", type="primary", use_container_width=True):
        try:
            from src.ai.chat import AIChat
            ai = AIChat()
            prompt = f"分析 {name}({code})，当前¥{price} {sgn}{pct:.2f}%。"
            if r: prompt += f"评分{r['total_score']:.0f} {r['rating']}。"
            if ctx: prompt += f"\n{ctx}"
            with st.spinner("分析中..."): st.markdown(ai.chat(prompt))
        except Exception as e:
            st.error(f"AI失败: {e}")

    st.markdown("---")
    st.subheader(f"{name} 新闻")
    try:
        from src.news.fetcher import fetch_stock_news
        sn = fetch_stock_news(code, 5)
        for item in (sn or []):
            st.markdown(f'<div class="news-line"><div class="nt">{item["title"]}</div><div class="nm">{item.get("source","")} · {item.get("published_at","")}</div></div>', unsafe_allow_html=True)
            if item.get("content") and item["content"]!=item["title"]:
                with st.expander("详情"): st.markdown(item["content"])
    except: st.info("新闻异常")

    if st.button("← 返回行情", key="back"):
        st.session_state["current_page"] = "market"
        st.rerun()
