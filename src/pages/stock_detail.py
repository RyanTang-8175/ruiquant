"""股票详情 - Industrial"""

import streamlit as st
import pandas as pd
from src.data.realtime import get_realtime_quote, get_kline
from src.scoring.engine import ScoringEngine
try:import plotly.graph_objects as go;from plotly.subplots import make_subplots;HAS_PLOTLY=True
except:HAS_PLOTLY=False

def _c(v):
    v=v or 0
    if v>0:return"#FF3B30"
    if v<0:return"#00D26A"
    return"#888"

def render_stock_detail_page(code=None):
    if not code:code=st.session_state.get("selected_stock","")
    if not code:st.warning("SEL STOCK");return
    q=get_realtime_quote(code)
    if not q:st.error(f"NO DATA {code}");return
    nm,pr,pct=q.get("name",code),q.get("price",0),q.get("change_pct",0)
    cl=_c(pct);sg="+"if pct>0 else""
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:baseline;padding:.5rem 0;"><div><span style="font-size:1.4rem;font-weight:700;color:#E8E8E5;">{nm}</span><span style="color:#6B6C68;margin-left:.5rem;font-family:JetBrains Mono,monospace;font-size:.85rem;">{code}</span></div><div style="text-align:right;"><span style="font-size:1.8rem;font-weight:700;color:{cl};font-family:JetBrains Mono,monospace;">¥{pr:.2f}</span><span style="color:{cl};font-size:1rem;font-family:JetBrains Mono,monospace;margin-left:.5rem;">{sg}{pct:.2f}%</span></div></div>',unsafe_allow_html=True)
    mm=st.columns(6)
    mm[0].metric("OPEN",f"{q.get('open',0):.2f}",border=True)
    mm[1].metric("HIGH",f"{q.get('high',0):.2f}",border=True)
    mm[2].metric("LOW",f"{q.get('low',0):.2f}",border=True)
    mm[3].metric("VOL",f"{q.get('volume',0)/10000:.0f}万",border=True)
    mm[4].metric("AMT",f"{q.get('amount',0)/1e8:.1f}亿",border=True)
    mm[5].metric("TURN",f"{q.get('turnover',0):.2f}%",border=True)
    st.markdown("---");st.markdown("## K LINE")
    pm={"1M":"1","5M":"5","15M":"15","30M":"30","60M":"60","D":"101","W":"102"}
    sl=st.radio("",list(pm.keys()),horizontal=True,key="kp")
    kl=get_kline(code,period=pm[sl],count=120)
    if kl and HAS_PLOTLY:
        df=pd.DataFrame(kl);fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.02,row_heights=[.78,.22])
        fig.add_trace(go.Candlestick(x=df["date"],open=df["open"],high=df["high"],low=df["low"],close=df["close"],increasing_line_color="#FF3B30",decreasing_line_color="#00D26A",increasing_fillcolor="rgba(255,59,48,.4)",decreasing_fillcolor="rgba(0,210,106,.4)"),row=1,col=1)
        for ma,clr in[(5,"#FFB800"),(10,"#3399FF"),(20,"#B050E0")]:
            if len(df)>=ma:fig.add_trace(go.Scatter(x=df["date"],y=df["close"].rolling(ma).mean(),name=f"MA{ma}",line=dict(color=clr,width=1)),row=1,col=1)
        colors=["#FF3B30"if c>=o else"#00D26A"for c,o in zip(df["close"].fillna(0),df["open"].fillna(0))]
        fig.add_trace(go.Bar(x=df["date"],y=df["volume"],marker_color=colors),row=2,col=1)
        fig.update_layout(template="plotly_dark",paper_bgcolor="#0B0C0A",plot_bgcolor="#0B0C0A",height=450,margin=dict(l=0,r=0,t=10,b=0),showlegend=False,xaxis=dict(gridcolor="#2A2B26"),yaxis=dict(gridcolor="#2A2B26"),xaxis2=dict(gridcolor="#2A2B26"),yaxis2=dict(gridcolor="#2A2B26"))
        st.plotly_chart(fig,use_container_width=True)
    st.markdown("---");st.markdown("## SCORE")
    try:
        with ScoringEngine()as e:r=e.score_stock(code)
        if r:
            rc={"强关注":"#FF3B30","观察":"#3399FF","中性":"#FFB800","不追":"#555"}.get(r["rating"],"#888")
            st.markdown(f'<div style="text-align:center;padding:1rem;background:#131510;border:1px solid #2A2B26;"><div style="font-size:2.5rem;font-weight:700;color:{rc};font-family:JetBrains Mono,monospace;">{r["total_score"]:.0f}</div><div style="color:#6B6C68;font-family:JetBrains Mono,monospace;font-size:.7rem;">SCORE</div><div style="margin-top:.4rem;"><span style="background:{rc};color:#fff;padding:2px 12px;font-family:JetBrains Mono,monospace;font-size:.75rem;">{r["rating"]}</span></div></div>',unsafe_allow_html=True)
            fn={"short_term_reversal":"REV","turnover_rate":"TURN","volume_ratio":"VOL","trend":"TREND","rsi":"RSI","macd":"MACD","kdj":"KDJ","kline_pattern":"K","idio_volatility":"IVOL","blast_rate":"BLAST","limit_up_streak":"LIMIT","market_temperature":"TEMP","boll_position":"BOLL"}
            sf=sorted(r["factors"].items(),key=lambda x:x[1],reverse=True);cc=st.columns(3)
            for i,(k,v)in enumerate(sf[:18]):
                n=fn.get(k,k);bc="#FF3B30"if v>=70 else"#FFB800"if v>=50 else"#00D26A"
                with cc[i%3]:st.markdown(f'<div style="padding:.35rem .5rem;background:#131510;border:1px solid #2A2B26;margin-bottom:.2rem;"><div style="display:flex;justify-content:space-between;"><span style="color:#6B6C68;font-family:JetBrains Mono,monospace;font-size:.65rem;">{n}</span><span style="color:{bc};font-family:JetBrains Mono,monospace;font-weight:700;font-size:.75rem;">{v:.0f}</span></div><div style="background:#0B0C0A;height:2px;margin-top:.15rem;"><div style="background:{bc};height:100%;width:{min(100,v)}%;"></div></div></div>',unsafe_allow_html=True)
    except Exception as ex:st.warning(f"ERR: {ex}")
    st.markdown("---");st.markdown("## AI")
    ctx=st.text_area("",placeholder="持仓信息...",key="ctx",label_visibility="collapsed")
    if st.button("ANALYZE",key="ab",type="primary",use_container_width=True):
        try:
            from src.ai.chat import AIChat;ai=AIChat()
            pmt=f"分析 {nm}({code}) ¥{pr} {sg}{pct:.2f}%。"
            if r:pmt+=f"评分{r['total_score']:.0f} {r['rating']}。"
            if ctx:pmt+=f"\n{ctx}"
            with st.spinner("..."):st.markdown(ai.chat(pmt))
        except Exception as e:st.error(f"{e}")
    if st.button("BACK",key="bk"):st.session_state["current_page"]="market";st.rerun()
