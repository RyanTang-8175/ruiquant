"""个股作战卡 —— 移动端优先"""

import streamlit as st
from src.data.realtime import get_kline, get_realtime_quote
from src.scoring.engine import V6ScoringEngine


def render_stock_detail_page(code: str | None = None):
    code = code or st.session_state.get("selected_stock", "")
    if not code:
        st.warning("请先选择股票")
        _back(); return

    quote = get_realtime_quote(code)
    if not quote:
        st.error(f"无法获取 {code} 行情，请稍后刷新")
        _back(); return

    result = _score(code, quote)

    _header(code, quote, result)
    _quote_grid(quote)
    if result:
        _score_detail(result)
        _antiquant_detail(result)
    else:
        st.info("六维评分暂不可用")
    _kline_chart(code)
    _ai_bar(code, quote)
    _back()


def _score(code, quote):
    try:
        with V6ScoringEngine() as e:
            return e.score_stock(code, quote=quote)
    except Exception as ex:
        st.warning(f"评分不可用: {ex}"); return None


def _header(code, quote, result):
    name = quote.get("name", code); price = quote.get("price", 0); pct = quote.get("change_pct", 0)
    c = "#E53935" if pct > 0 else "#0A9B66" if pct < 0 else "#5D6B7C"
    status = result.status_label if result else "待评分"
    risk = result.anti_quant.risk_level if result else ""
    st.markdown(
        f'<div style="background:#fff;border:1px solid #D8E1EA;border-radius:12px;padding:14px;margin-bottom:10px">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        f'<div style="flex:1"><span style="font-size:18px;font-weight:700;color:#17212F">{name}</span>'
        f'<span style="font-size:11px;color:#5D6B7C;margin-left:6px;font-family:monospace">{code}</span>'
        f'<div style="margin-top:6px">'
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:rgba(36,107,254,0.10);color:#246BFE">{status}</span> '
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;'
        f'background:{"rgba(229,57,53,0.10)" if risk in ("高","极高") else "rgba(216,131,18,0.10)" if risk=="中" else "rgba(10,155,102,0.10)"};'
        f'color:{"#E53935" if risk in ("高","极高") else "#D88312" if risk=="中" else "#0A9B66"}">{risk}风险</span>'
        f'</div></div>'
        f'<div style="text-align:right"><div style="font-size:24px;font-weight:800;color:{c};font-family:monospace">{price:.2f}</div>'
        f'<div style="font-size:14px;font-weight:700;color:{c};font-family:monospace">{pct:+.2f}%</div></div></div></div>',
        unsafe_allow_html=True)


def _quote_grid(quote):
    items = [
        ("开盘", f"{quote.get('open',0) or 0:.2f}"), ("最高", f"{quote.get('high',0) or 0:.2f}"),
        ("最低", f"{quote.get('low',0) or 0:.2f}"), ("换手", f"{quote.get('turnover',0) or 0:.2f}%"),
        ("成交额", f"{(quote.get('amount',0) or 0) / 1e8:.1f}亿"), ("量比", f"{quote.get('volume_ratio',0) or 0:.2f}"),
    ]
    for i in range(0, 6, 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(items):
                with cols[j]:
                    st.metric(items[i + j][0], items[i + j][1])


def _score_detail(result):
    st.markdown('<div style="font-size:13px;font-weight:700;color:#5D6B7C;margin:14px 0 6px;border-bottom:1px solid #D8E1EA;padding-bottom:4px">六维评分</div>', unsafe_allow_html=True)

    risk = result.anti_quant.risk_level
    sc = "#0A9B66" if result.total_score >= 72 and risk in ("低","中") else "#D88312" if result.total_score >= 60 else "#E53935" if result.total_score < 45 else "#246BFE"
    plain = _plain(result)
    triggers = " · ".join(result.anti_quant.triggers[:3]) if result.anti_quant.triggers else "无显著触发"

    st.markdown(
        f'<div style="background:#fff;border:1px solid #D8E1EA;border-radius:10px;padding:12px;margin-bottom:10px">'
        f'<div style="display:flex;justify-content:space-between"><span style="font-size:15px;font-weight:700;color:#17212F">机会分</span>'
        f'<span style="font-size:28px;font-weight:900;color:{sc};font-family:monospace">{result.total_score:.0f}</span></div>'
        f'<div style="font-size:12px;color:#17212F;margin-top:6px;line-height:1.5">{plain}</div>'
        f'<div style="font-size:11px;color:#5D6B7C;margin-top:4px">{triggers}</div></div>',
        unsafe_allow_html=True)

    dims = [
        ("热度", "有资金关注吗", result.heat), ("承接", "上涨后有人接吗", result.support),
        ("题材", "是市场主线吗", result.theme), ("延续", "能多拿几天吗", result.continuation),
        ("策略", "符合哪个模式", result.strategy_match),
    ]
    for title, q, d in dims:
        clr = "#0A9B66" if d.score >= 65 else "#D88312" if d.score >= 50 else "#E53935"
        sub = ""
        if d.sub_scores:
            parts = []
            for k, v in d.sub_scores.items():
                if isinstance(v, (int, float)): parts.append(f'<span style="font-size:11px;color:#5D6B7C">{k}</span> <span style="font-family:monospace;color:#17212F">{v:.0f}</span>')
                elif isinstance(v, bool): parts.append(f'<span style="font-size:11px;color:#5D6B7C">{k}</span> <span style="font-family:monospace;color:{"#0A9B66" if v else "#E53935"}">{"是" if v else "否"}</span>')
            sub = " · ".join(parts)
        st.markdown(
            f'<div style="background:#fff;border:1px solid #D8E1EA;border-radius:8px;padding:10px;margin-bottom:6px">'
            f'<div style="display:flex;justify-content:space-between"><div><span style="font-size:14px;font-weight:700;color:#17212F">{title}</span>'
            f'<span style="font-size:11px;color:#5D6B7C;margin-left:6px">{q}</span></div>'
            f'<span style="font-size:18px;font-weight:800;color:{clr};font-family:monospace">{d.score:.0f}</span></div>'
            f'<div style="margin-top:4px">{sub}</div>'
            f'<div style="font-size:11px;color:#8B98A7;margin-top:3px">{d.explanation}</div></div>',
            unsafe_allow_html=True)


def _antiquant_detail(result):
    aq = result.anti_quant
    ms = [("尾盘诱多", aq.late_day_lure), ("高位接盘", aq.high_position_trap),
          ("分时脉冲", aq.intraday_pulse), ("放量滞涨", aq.volume_stall),
          ("板块背离", aq.sector_divergence)]
    st.markdown('<div style="font-size:13px;font-weight:700;color:#5D6B7C;margin:14px 0 6px;border-bottom:1px solid #D8E1EA;padding-bottom:4px">反量化详情</div>', unsafe_allow_html=True)
    for n, d in ms:
        sc = d.get("score", 0) if isinstance(d, dict) else 0
        lv = "高" if sc >= 70 else "中" if sc >= 40 else "低"
        tr = ", ".join(d.get("triggers", [])[:2]) if isinstance(d, dict) else ""
        clr = "#E53935" if lv == "高" else "#D88312" if lv == "中" else "#0A9B66"
        st.markdown(
            f'<div style="background:#fff;border:1px solid #D8E1EA;border-radius:8px;padding:10px;margin-bottom:6px">'
            f'<div style="display:flex;justify-content:space-between"><span style="font-size:13px;font-weight:600;color:#17212F">{n}</span>'
            f'<span style="font-size:12px;font-weight:700;color:{clr};font-family:monospace">{sc:.0f} {lv}</span></div>'
            f'<div style="font-size:11px;color:#5D6B7C;margin-top:3px">{tr if tr else "未触发"}</div></div>',
            unsafe_allow_html=True)


def _kline_chart(code):
    st.markdown('<div style="font-size:13px;font-weight:700;color:#5D6B7C;margin:14px 0 6px;border-bottom:1px solid #D8E1EA;padding-bottom:4px">K线走势</div>', unsafe_allow_html=True)
    try:
        kls = get_kline(code, period="101", count=60)
    except Exception:
        kls = []
    if not kls:
        st.info("K线数据暂不可用"); return

    import pandas as pd
    df = pd.DataFrame(kls)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    recent = df.tail(5)

    # 近5日迷你卡片
    st.markdown('<div style="display:flex;gap:4px;font-size:12px;margin-bottom:8px">' + "".join(
        f'<div style="flex:1;text-align:center;background:#fff;border:1px solid #D8E1EA;border-radius:6px;padding:5px 2px">'
        f'<div style="font-size:10px;color:#5D6B7C">{r["date"].strftime("%m/%d")}</div>'
        f'<div style="font-family:monospace;font-weight:700;font-size:13px;color:{"#E53935" if r.get("close",0)>=r.get("open",0) else "#0A9B66"}">{r["close"]:.2f}</div>'
        f'<div style="font-family:monospace;font-size:10px;color:{"#E53935" if r.get("change_pct",0)>0 else "#0A9B66"}">{r.get("change_pct",0):+.1f}%</div></div>'
        for _, r in recent.iterrows()) + '</div>', unsafe_allow_html=True)

    # Plotly K线图
    try:
        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Candlestick(
            x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
            increasing_line_color="#E53935", decreasing_line_color="#0A9B66")])
        fig.update_layout(height=240, margin=dict(l=0, r=0, t=0, b=0),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(showgrid=False, visible=False),
                          yaxis=dict(showgrid=True, gridcolor="#E7EEF6", tickfont=dict(size=10, color="#5D6B7C")),
                          showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except Exception:
        last5 = df.tail(5)
        lines = [f"{r['date'].strftime('%m/%d')} O{r['open']:.2f} H{r['high']:.2f} L{r['low']:.2f} C{r['close']:.2f} {r['change_pct']:+.1f}%" for _, r in last5.iterrows()]
        st.code("\n".join(lines), language=None)


def _ai_bar(code, quote):
    st.markdown('<div style="font-size:13px;font-weight:700;color:#5D6B7C;margin:14px 0 6px;border-bottom:1px solid #D8E1EA;padding-bottom:4px">操作</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("审查风险", use_container_width=True, key="sdr"):
            st.session_state["selected_stock"] = code
            st.session_state["qq"] = f"对 {code} 做深度风险审查，逐条解释反量化触发项和白话含义"
            st.session_state["current_page"] = "ai_chat"; st.rerun()
    with c2:
        if st.button("持股判断", use_container_width=True, key="sdh"):
            st.session_state["selected_stock"] = code
            st.session_state["qq"] = f"判断 {code} 适合隔夜/1-2天/2-3天，给出条件和离场红线"
            st.session_state["current_page"] = "ai_chat"; st.rerun()
    with c3:
        if st.button("加入验证", use_container_width=True, key="sdl"):
            try:
                from src.memory.analysis_memory import AnalysisMemory
                from datetime import datetime
                with AnalysisMemory() as am:
                    am.create_verification("manual", code, quote.get("name", code), datetime.now(), suggested_period="1-2天")
                st.success("已加入")
            except Exception as ex:
                st.warning(f"失败: {ex}")


def _plain(result) -> str:
    r, h, s, t, c = result.anti_quant.risk_level, result.heat.score, result.support.score, result.theme.score, result.continuation.score
    pp = ["热度高" if h >= 65 else "热度适中" if h >= 50 else "热度偏低",
          "承接良好" if s >= 65 else "承接尚可" if s >= 50 else "承接不足",
          "属主线" if t >= 60 else "板块一般" if t >= 45 else "板块偏弱",
          "可持2-3天" if c >= 65 else "可持1-2天" if c >= 50 else "不建议延长"]
    pp.append("反量化高风险,需谨慎" if r in ("高","极高") else "反量化中风险" if r == "中" else "反量化低风险")
    return "。".join(pp) + "。"


def _back():
    if st.button("← 返回", key="sd_back", use_container_width=True):
        st.session_state["current_page"] = "radar"
        st.rerun()
