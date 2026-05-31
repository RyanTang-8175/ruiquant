"""移动端个股作战卡"""

from __future__ import annotations

import streamlit as st

from src.data.realtime import get_kline, get_realtime_quote
from src.scoring.engine import V6ScoringEngine


def render_stock_detail_page(code: str | None = None):
    code = code or st.session_state.get("selected_stock", "")
    if not code:
        st.warning("请先选择股票")
        _back_button()
        return

    quote = get_realtime_quote(code)
    if not quote:
        st.error(f"暂时无法获取 {code} 的实时行情。请稍后刷新，或回到雷达页重新选择。")
        _back_button()
        return

    result = _score_stock(code, quote)
    _render_header(code, quote, result)
    _render_quote_metrics(quote)
    _render_score_card(result)
    _render_kline_summary(code)
    _render_ai_actions(code, quote, result)
    _back_button()


def _score_stock(code: str, quote: dict):
    try:
        with V6ScoringEngine() as engine:
            return engine.score_stock(code, quote=quote)
    except Exception as exc:
        st.warning(f"六维评分暂不可用：{exc}")
        return None


def _render_header(code: str, quote: dict, result):
    name = quote.get("name", code)
    price = quote.get("price", 0) or 0
    pct = quote.get("change_pct", 0) or 0
    color = "var(--red)" if pct > 0 else "var(--green)" if pct < 0 else "var(--muted)"
    status = result.status_label if result else "待评分"
    risk = result.anti_quant.risk_level if result else "未知"

    st.markdown(
        '<div class="soft-card">'
        '<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">'
        '<div style="min-width:0;flex:1">'
        f'<div style="font-size:20px;font-weight:850;color:var(--text)">{name}</div>'
        f'<div style="font-family:var(--mono);font-size:12px;color:var(--muted);margin-top:2px">{code}</div>'
        f'<div style="margin-top:8px"><span class="badge badge-ai">{status}</span> '
        f'<span class="badge {"badge-high" if risk in ("高", "极高") else "badge-mid" if risk == "中" else "badge-low"}">{risk}风险</span></div>'
        '</div>'
        '<div style="text-align:right;min-width:112px">'
        f'<div style="font-family:var(--mono);font-size:26px;font-weight:900;color:{color}">{price:.2f}</div>'
        f'<div style="font-family:var(--mono);font-size:14px;font-weight:750;color:{color}">{pct:+.2f}%</div>'
        '</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def _render_quote_metrics(quote: dict):
    items = [
        ("开盘", f"{quote.get('open', 0) or 0:.2f}"),
        ("最高", f"{quote.get('high', 0) or 0:.2f}"),
        ("最低", f"{quote.get('low', 0) or 0:.2f}"),
        ("换手", f"{quote.get('turnover', 0) or 0:.2f}%"),
        ("成交额", f"{(quote.get('amount', 0) or 0) / 1e8:.1f}亿"),
        ("量比", f"{quote.get('volume_ratio', 0) or 0:.2f}"),
    ]
    cols = st.columns(3)
    for index, (label, value) in enumerate(items):
        with cols[index % 3]:
            st.metric(label, value)


def _render_score_card(result):
    if not result:
        st.info("暂无六维评分。")
        return

    triggers = " · ".join(result.anti_quant.triggers[:3]) if result.anti_quant.triggers else "暂无显著反量化触发项"
    st.markdown(
        '<div class="recommend-card">'
        '<div style="display:flex;justify-content:space-between;align-items:center">'
        '<div>'
        '<div style="font-size:15px;font-weight:800;color:var(--text)">六维短线评分</div>'
        f'<div style="font-size:12px;color:var(--muted);margin-top:3px">{triggers}</div>'
        '</div>'
        f'<div style="font-family:var(--mono);font-size:28px;font-weight:900;color:var(--ai)">{result.total_score:.0f}</div>'
        '</div>'
        '<div class="score-row">'
        f'<span class="score-pill">热度 {result.heat.score:.0f}</span>'
        f'<span class="score-pill">承接 {result.support.score:.0f}</span>'
        f'<span class="score-pill">题材 {result.theme.score:.0f}</span>'
        f'<span class="score-pill">延续 {result.continuation.score:.0f}</span>'
        f'<span class="score-pill">策略 {result.strategy_match.score:.0f}</span>'
        f'<span class="score-pill">反量化 {result.anti_quant.total_risk:.0f}</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def _render_kline_summary(code: str):
    st.markdown('<div class="ai-section-title">走势概览</div>', unsafe_allow_html=True)
    try:
        kline = get_kline(code, period="101", count=30)
    except Exception:
        kline = []
    if not kline:
        st.info("K 线数据暂不可用。")
        return

    last = kline[-1]
    st.markdown(
        '<div class="soft-card">'
        f'<div style="font-size:13px;color:var(--muted)">最近交易日：{last.get("date", "")}</div>'
        f'<div class="score-row">'
        f'<span class="score-pill">开 {float(last.get("open", 0)):.2f}</span>'
        f'<span class="score-pill">高 {float(last.get("high", 0)):.2f}</span>'
        f'<span class="score-pill">低 {float(last.get("low", 0)):.2f}</span>'
        f'<span class="score-pill">收 {float(last.get("close", 0)):.2f}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_ai_actions(code: str, quote: dict, result):
    st.markdown('<div class="ai-section-title">AI 操作</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("问 AI 风险", use_container_width=True, type="primary"):
            st.session_state["selected_stock"] = code
            st.session_state["qq"] = f"请审查 {quote.get('name', code)}({code}) 的短线风险、反量化风险、参与条件和放弃条件。"
            st.session_state["current_page"] = "ai_chat"
            st.rerun()
    with c2:
        if st.button("持股预测", use_container_width=True):
            st.session_state["selected_stock"] = code
            st.session_state["qq"] = f"请判断 {quote.get('name', code)}({code}) 适合隔夜、1-2天还是2-3天短持。"
            st.session_state["current_page"] = "ai_chat"
            st.rerun()


def _back_button():
    if st.button("返回雷达", key="stock_detail_back", use_container_width=True):
        st.session_state["current_page"] = "radar"
        st.rerun()
