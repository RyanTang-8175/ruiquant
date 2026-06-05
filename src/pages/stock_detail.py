"""个股作战卡 —— 移动端优先"""

from __future__ import annotations

import streamlit as st
from src.data.realtime import get_kline, get_realtime_quote
from src.scoring.engine import V6ScoringEngine
from src.data.quality import render_quality_html, FALLBACK_WARNING


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
        _ifind_evidence_panel(code)
    else:
        st.info("六维评分暂不可用")
    _kline_chart(code)
    if result:
        _summary_card(code, quote, result)
    _ai_bar(code, quote, result)
    _back()


def _score(code, quote):
    try:
        with V6ScoringEngine() as e:
            return e.score_stock(code, quote=quote)
    except Exception as ex:
        st.warning(f"评分不可用: {ex}"); return None


def _header(code, quote, result):
    name = quote.get("name", code); price = quote.get("price", 0); pct = quote.get("change_pct", 0)
    c = "var(--red)" if pct > 0 else "var(--green)" if pct < 0 else "var(--muted)"
    status = result.status_label if result else "待评分"
    risk = result.anti_quant.risk_level if result else ""
    risk_bg = "var(--red)" if risk in ("高","极高") else "var(--amber)" if risk=="中" else "var(--green)"
    # Phase 1.3: 数据质量标签
    q_badge = render_quality_html(quote)
    fallback_banner = f'<div style="background:#FFF7E6;border:1px solid #FAAD14;padding:6px 10px;border-radius:4px;margin-bottom:8px;font-size:12px;color:#AD6800">{FALLBACK_WARNING}</div>' if quote.get("_fallback") else ""
    st.markdown(
        f'{fallback_banner}'
        f'<div class="card">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        f'<div style="flex:1"><span style="font-size:18px;font-weight:700;color:var(--text)">{name}</span>'
        f'<span style="font-size:11px;color:var(--muted);margin-left:6px;font-family:var(--mono)">{code}</span>'
        f'<div style="margin-top:6px">'
        f'<span class="badge badge-ai">{status}</span> '
        f'<span class="badge" style="color:{risk_bg};border-color:{risk_bg}">{risk}风险</span> '
        f'{q_badge}'
        f'</div></div>'
        f'<div style="text-align:right"><div style="font-size:24px;font-weight:800;color:{c};font-family:var(--mono)">{price:.2f}</div>'
        f'<div style="font-size:14px;font-weight:700;color:{c};font-family:var(--mono)">{pct:+.2f}%</div></div></div></div>',
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
    st.markdown('<div class="sec-h">六维评分</div>', unsafe_allow_html=True)

    risk = result.anti_quant.risk_level
    sc = "var(--green)" if result.total_score >= 72 and risk in ("低","中") else "var(--amber)" if result.total_score >= 60 else "var(--red)" if result.total_score < 45 else "var(--ai)"
    plain = _plain(result)
    triggers = " · ".join(result.anti_quant.triggers[:3]) if result.anti_quant.triggers else "无显著触发"

    st.markdown(
        f'<div class="card">'
        f'<div style="display:flex;justify-content:space-between"><span style="font-size:15px;font-weight:700;color:var(--text)">机会分</span>'
        f'<span style="font-size:28px;font-weight:900;color:{sc};font-family:var(--mono)">{result.total_score:.0f}</span></div>'
        f'<div style="font-size:12px;color:var(--text);margin-top:6px;line-height:1.5">{plain}</div>'
        f'<div style="font-size:11px;color:var(--muted);margin-top:4px">{triggers}</div></div>',
        unsafe_allow_html=True)

    dims = [
        ("热度", "有资金关注吗", result.heat), ("承接", "上涨后有人接吗", result.support),
        ("题材", "是市场主线吗", result.theme), ("延续", "能多拿几天吗", result.continuation),
        ("策略", "符合哪个模式", result.strategy_match),
    ]
    for title, q, d in dims:
        clr = "var(--green)" if d.score >= 65 else "var(--amber)" if d.score >= 50 else "var(--red)"
        sub = ""
        if d.sub_scores:
            parts = []
            for k, v in d.sub_scores.items():
                if isinstance(v, (int, float)): parts.append(f'<span style="font-size:11px;color:var(--muted)">{k}</span> <span style="font-family:var(--mono);color:var(--text)">{v:.0f}</span>')
                elif isinstance(v, bool): parts.append(f'<span style="font-size:11px;color:var(--muted)">{k}</span> <span style="font-family:var(--mono);color:{"var(--green)" if v else "var(--red)"}">{"是" if v else "否"}</span>')
            sub = " · ".join(parts)
        st.markdown(
            f'<div class="card" style="margin-bottom:6px;padding:10px">'
            f'<div style="display:flex;justify-content:space-between"><div><span style="font-size:14px;font-weight:700;color:var(--text)">{title}</span>'
            f'<span style="font-size:11px;color:var(--muted);margin-left:6px">{q}</span></div>'
            f'<span style="font-size:18px;font-weight:800;color:{clr};font-family:var(--mono)">{d.score:.0f}</span></div>'
            f'<div style="margin-top:4px">{sub}</div>'
            f'<div style="font-size:11px;color:var(--hint);margin-top:3px">{d.explanation}</div></div>',
            unsafe_allow_html=True)


def _antiquant_detail(result):
    aq = result.anti_quant
    ms = [("尾盘诱多", aq.late_day_lure), ("高位接盘", aq.high_position_trap),
          ("分时脉冲", aq.intraday_pulse), ("放量滞涨", aq.volume_stall),
          ("板块背离", aq.sector_divergence)]
    st.markdown('<div class="sec-h">反量化详情</div>', unsafe_allow_html=True)
    for n, d in ms:
        sc = d.get("score", 0) if isinstance(d, dict) else 0
        lv = "高" if sc >= 70 else "中" if sc >= 40 else "低"
        tr = ", ".join(d.get("triggers", [])[:2]) if isinstance(d, dict) else ""
        clr = "var(--red)" if lv == "高" else "var(--amber)" if lv == "中" else "var(--green)"
        st.markdown(
            f'<div class="card" style="margin-bottom:6px;padding:10px">'
            f'<div style="display:flex;justify-content:space-between"><span style="font-size:13px;font-weight:600;color:var(--text)">{n}</span>'
            f'<span style="font-size:12px;font-weight:700;color:{clr};font-family:var(--mono)">{sc:.0f} {lv}</span></div>'
            f'<div style="font-size:11px;color:var(--muted);margin-top:3px">{tr if tr else "未触发"}</div></div>',
            unsafe_allow_html=True)


def _ifind_evidence_panel(code: str):
    st.markdown('<div class="sec-h">iFinD 证据评分</div>', unsafe_allow_html=True)
    key = f"ifind_evidence_{code}"
    score = st.session_state.get(key)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("生成证据评分", use_container_width=True, key=f"{key}_gen"):
            try:
                from src.research.harness import ResearchHarness
                from src.scoring.evidence import IFindEvidenceScorer

                research = ResearchHarness().company_research(code, profile="quick")
                score = IFindEvidenceScorer().score(research)
                st.session_state[key] = score
            except Exception as exc:
                st.warning(f"证据评分生成失败: {exc}")
    with c2:
        if st.button("清除缓存", use_container_width=True, key=f"{key}_clr"):
            st.session_state.pop(key, None)
            st.rerun()

    score = st.session_state.get(key)
    if not score:
        st.info("点击上方按钮生成证据评分，或者先在研究页创建研究底稿。")
        return

    cols = st.columns(3)
    cols[0].metric("机会分", f"{score.get('opportunity_score', 0):.1f}")
    cols[1].metric("风险分", f"{score.get('risk_score', 0):.1f}")
    cols[2].metric("置信度", score.get("confidence", "低"))

    for item in (score.get("evidence_summary") or [])[:3]:
        st.markdown(f'<div class="soft-card" style="margin-bottom:6px">{item}</div>', unsafe_allow_html=True)


def _kline_chart(code):
    st.markdown('<div class="sec-h">K线走势</div>', unsafe_allow_html=True)
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
        f'<div class="card" style="flex:1;text-align:center;padding:5px 2px;margin-bottom:0">'
        f'<div style="font-size:10px;color:var(--muted)">{r["date"].strftime("%m/%d")}</div>'
        f'<div style="font-family:var(--mono);font-weight:700;font-size:13px;color:{"var(--red)" if r.get("close",0)>=r.get("open",0) else "var(--green)"}">{r["close"]:.2f}</div>'
        f'<div style="font-family:var(--mono);font-size:10px;color:{"var(--red)" if r.get("change_pct",0)>0 else "var(--green)"}">{r.get("change_pct",0):+.1f}%</div></div>'
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


def _ai_bar(code, quote, result=None):
    st.markdown('<div class="sec-h">操作</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
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
        if st.button("研究底稿", use_container_width=True, key="sda"):
            st.session_state["selected_stock"] = code
            st.session_state["research_code"] = code
            st.session_state["current_page"] = "research"
            st.rerun()
    with c4:
        if st.button("加入验证", use_container_width=True, key="sdl"):
            try:
                from src.memory.analysis_memory import AnalysisMemory
                from datetime import datetime
                with AnalysisMemory() as am:
                    am.create_verification(
                        "manual",
                        code,
                        quote.get("name", code),
                        datetime.now(),
                        strategy_name="详情页手动验证",
                        suggested_period="1-2天",
                        hypothesis=f"{quote.get('name', code)} 被手动加入观察，验证当前短线结构是否有延续。",
                        entry_conditions=["回踩不破关键均线/分时均价线", "板块不退潮", "成交不出现放量滞涨"],
                        invalidation_conditions=["跌破昨日低点", "冲高回落且放量", "反量化风险升高"],
                        stop_loss_rule="模拟验证中若 T+1 最大回撤超过 3% 记为高风险样本",
                        risk_level=getattr(result.anti_quant, "risk_level", "中") if result else "中",
                        confidence_level="中",
                        allow_real_trade=False,
                    )
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


def _summary_card(code, quote, result):
    """根据六维评分生成一句话总结"""
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:#5D6B7C;margin:14px 0 6px;'
        'border-bottom:1px solid #D8E1EA;padding-bottom:4px">总结分析</div>',
        unsafe_allow_html=True)

    name = quote.get("name", code)
    price = quote.get("price", 0)
    pct = quote.get("change_pct", 0)
    direction = "上涨" if pct > 0 else "下跌"
    risk = result.anti_quant.risk_level
    heat_label = "高" if result.heat.score >= 65 else "一般" if result.heat.score >= 50 else "低"
    support_label = "好" if result.support.score >= 65 else "一般" if result.support.score >= 50 else "差"

    summary = (
        f"{name}今日{direction}{abs(pct):.1f}%，收盘{price:.2f}。"
        f"热度{heat_label}，承接{support_label}，反量化风险{risk}。"
    )

    if result.status_label == "可执行":
        summary += "信号较明确，可加入观察或模拟验证，等待触发条件确认。"
    elif result.status_label == "等待确认":
        summary += "建议等待更明确的承接信号或板块确认后再考虑。"
    elif result.status_label in ("风险偏高", "不建议参与"):
        summary += "当前不建议追高，优先观察或寻找其他机会。"
    else:
        summary += "可加入观察池，待条件更成熟时再评估。"

    if result.anti_quant.triggers:
        summary += f"主要风险点：{'；'.join(result.anti_quant.triggers[:2])}。"

    st.markdown(
        f'<div class="soft-card" style="border:1px solid var(--ai);font-size:13px;'
        f'color:var(--text);line-height:1.6">{summary}</div>',
        unsafe_allow_html=True)


def _back():
    if st.button("← 返回", key="sd_back", use_container_width=True):
        st.session_state["current_page"] = st.session_state.get("previous_page", "radar")
        st.rerun()
