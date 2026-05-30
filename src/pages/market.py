"""行情中心"""

import streamlit as st
from datetime import datetime
from src.data.realtime import get_top_stocks, get_market_overview

def _c(v):
    v=v or 0
    if v>0:return "#FF3B30"
    if v<0:return "#00D26A"
    return "#888"

def _a(v):
    if not v:return "-"
    if v>=1e8:return f"{v/1e8:.1f}亿"
    return f"{v:.0f}"

def render_market_page():
    c1,c2=st.columns([5,1])
    with c1:q=st.text_input("",placeholder="搜索代码 如 600519",key="s",label_visibility="collapsed")
    with c2:
        if st.button("GO",key="go",use_container_width=True,type="primary"):
            if q.strip():st.session_state["selected_stock"]=q.strip();st.session_state["current_page"]="stock_detail";st.rerun()

    ov=get_market_overview()
    indices=ov.get("indices",[])
    if indices:
        h='<div class="idx-row">'
        for idx in indices:
            p=idx.get("change_pct",0)
            cl=_c(p);s="+" if p>0 else ""
            h+=f'<div class="idx-cell"><div class="n">{idx.get("name")}</div><div class="p" style="color:{cl}">{idx.get("price",0):.2f}</div><div class="c" style="color:{cl}">{s}{p:.2f}%</div></div>'
        h+='</div>'
        st.markdown(h,unsafe_allow_html=True)

    st.caption(datetime.now().strftime("UPD %H:%M:%S"))

    t1,t2,t3,t4=st.tabs(["涨幅","跌幅","成交额","换手率"])
    def _s(stocks,prefix):
        if not stocks:st.info("暂无数据");return
        for i,s in enumerate(stocks):
            p=s.get("change_pct",0)or 0;cl=_c(p)
            nm=s.get("name")or s.get("code","");cd=s.get("code","")
            pr=s.get("price",0)or 0;am=_a(s.get("amount",0))
            st.markdown(f'<div class="sr"><div class="rk">{i+1}</div><div class="inf"><span class="nm">{nm}</span><span class="cd">{cd}</span></div><div class="pr" style="color:{cl}">¥{pr:.2f}</div><div class="ch" style="color:{cl}">{p:+.2f}%</div></div>',unsafe_allow_html=True)
            if st.button(f"VIEW {cd}",key=f"{prefix}{cd}_{i}"):
                st.session_state["selected_stock"]=cd;st.session_state["current_page"]="stock_detail";st.rerun()

    with t1:_s(get_top_stocks("f3",False,20),"up_")
    with t2:_s(get_top_stocks("f3",True,20),"dn_")
    with t3:_s(get_top_stocks("f6",False,20),"am_")
    with t4:_s(get_top_stocks("f8",False,20),"tr_")

    st.markdown("---")
    st.markdown("## 快讯")
    if st.button("REFRESH",key="rn"):
        st.session_state.pop("ns",None);st.rerun()
    if "ns" not in st.session_state:
        try:
            from src.news.fetcher import fetch_all_news
            with st.spinner("..."):st.session_state["ns"]=fetch_all_news(18)
        except:st.session_state["ns"]=[]
    ns=st.session_state.get("ns",[])
    if not ns:st.info("暂无新闻")
    else:
        for it in ns:
            t=it.get("title","");s={"cls":"CLS","eastmoney":"东财"}.get(it.get("source",""),"")
            pt=it.get("published_at","");b=it.get("content","")
            tg=""
            if any(k in t for k in ["涨","牛","利好","突破"]):tg='<span class="bg" style="background:#FF3B3020;color:#FF3B30;">BUY</span>'
            elif any(k in t for k in ["跌","利空","风险","暴"]):tg='<span class="bg" style="background:#00D26A20;color:#00D26A;">SELL</span>'
            st.markdown(f'<div class="ni"><div class="nt">{tg}{t}</div><div class="nm">{s} - {pt}</div></div>',unsafe_allow_html=True)
            if b and b!=t:
                with st.expander("DETAILS"):st.markdown(b)
