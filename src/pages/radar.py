"""AlphaEye v6 雷达页"""

import html
import json
import streamlit as st
from datetime import datetime
from functools import lru_cache
from pathlib import Path


def render_radar_page():
    now = datetime.now()

    # ── 搜索 ──
    from src.ui.search import render_search_bar
    code = render_search_bar(key="radar")
    if code:
        st.session_state["selected_stock"] = code
        st.session_state["previous_page"] = "radar"
        st.session_state["current_page"] = "stock_detail"
        st.rerun()

    # ── 环境 ──
    from src.data.realtime import get_market_overview
    ov = get_market_overview()
    indices = ov.get("indices", [])
    if indices:
        main = next((i for i in indices if "上证" in i.get("name", "")), indices[0])
        chg = main.get("change_pct", 0)
        env, clr, msg = (
            ("适合", "var(--green)", "大盘稳定") if chg > 0.5 else
            ("一般", "var(--amber)", "大盘震荡，精选个股") if chg > -0.5 else
            ("谨慎", "var(--red)", "大盘偏弱") if chg > -1.5 else
            ("不适合", "var(--red)", "建议观望")
        )
        index_html = "".join(
            f'<div class="idx-cell"><div class="n">{i.get("name","")}</div>'
            f'<div class="p">{i.get("price",0):.2f}</div>'
            f'<div class="c">{"+" if i.get("change_pct",0)>0 else ""}{i.get("change_pct",0):.2f}%</div></div>'
            for i in indices
        )
        st.markdown(
            f'<div class="card" style="margin-bottom:12px">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:10px">'
            f'<span style="font-weight:700;font-size:17px">今日短线</span>'
            f'<span style="font-weight:700;font-size:16px;color:{clr}">{env}</span>'
            f'</div><div style="font-size:13px;color:var(--muted);margin-bottom:10px">{msg}</div>'
            f'<div class="idx-strip" style="margin-bottom:0">{index_html}</div></div>',
            unsafe_allow_html=True)

    h, m = now.hour, now.minute
    if 14 <= h <= 15:
        phase = ("确认阶段·不追高" if m >= 50 else "观察阶段" if m >= 45 else "初筛阶段" if m >= 30 else "等待尾盘")
        st.info(f"尾盘 · {phase} · {now.strftime('%H:%M')}")

    # ── 信息雷达是主入口，不再藏进 Tab ──
    _show_info_radar()

    # ── iFinD 智能选股（配置了专业数据源时才展示）──
    _show_ifind_smart_picks()

    # ── Tab ──
    tab0, tab1, tab2 = st.tabs(["推荐选股", "风险排除", "策略扫描"])
    with tab0:
        _daily_sectors()
        _render_filter_and_results()
    with tab1:
        _show_risk_scan()
    with tab2:
        _show_strategy_scan()


# ═══════════════════════════════════════════
# iFinD 智能选股卡片
# ═══════════════════════════════════════════

def _show_ifind_smart_picks():
    """iFinD 智能选股入口卡片 — 仅当 iFinD 已配置且可用时展示。"""
    try:
        from src.data.providers.registry import get_provider, provider_status

        provider = get_provider()
        if provider.source_name != "ifind":
            return
        status = provider_status()
        if not status.get("ready"):
            return
    except Exception:
        return

    st.markdown(
        '<div class="sec-h">iFinD 智能选股</div>'
        '<div style="font-size:11px;color:var(--muted);margin-bottom:8px">主力资金流入、涨幅居前、换手率活跃 — 低频缓存，按月度额度控制调用</div>',
        unsafe_allow_html=True,
    )

    queries = [
        ("主力资金流入 涨幅居前", "主力资金"),
        ("换手率 活跃 成交额居前", "换手活跃"),
        ("连续上涨", "强势延续"),
    ]

    cols = st.columns(len(queries))
    for idx, (query, label) in enumerate(queries):
        with cols[idx]:
            if st.button(label, key=f"ifind_sp_{idx}", use_container_width=True):
                with st.spinner(f"iFinD 智能选股：{label}…"):
                    try:
                        rows = provider.smart_stock_picking(query, limit=10)
                        if rows:
                            st.session_state["ifind_picks"] = {"label": label, "rows": rows}
                        else:
                            st.info(f"「{label}」暂无候选")
                    except Exception as exc:
                        st.warning(f"iFinD 查询失败: {str(exc)[:80]}")

    picks = st.session_state.get("ifind_picks")
    if picks:
        rows = picks.get("rows", [])
        label = picks.get("label", "")
        st.caption(f"「{label}」返回 {len(rows)} 只")
        for row in rows[:8]:
            code = row.get("code", "")
            name = row.get("name", code)
            chg = row.get("change_pct", 0)
            price = row.get("price", 0)
            chg_c = "var(--red)" if chg > 0 else "var(--green)" if chg < 0 else "var(--muted)"
            sign = "+" if chg > 0 else ""
            st.markdown(
                f'<div class="card" style="margin-bottom:6px;padding:10px 14px">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<div><span style="font-weight:600;font-size:14px">{html.escape(str(name))}</span>'
                f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{html.escape(code)}</span></div>'
                f'<div style="text-align:right">'
                f'<span style="font-family:var(--mono);font-weight:700;font-size:15px;color:{chg_c}">{sign}{chg:.2f}%</span>'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )
            c1, c2, _ = st.columns([1, 1, 2])
            with c1:
                if st.button("查看", key=f"ifind_v_{code}", use_container_width=True):
                    st.session_state["selected_stock"] = code
                    st.session_state["previous_page"] = "radar"
                    st.session_state["current_page"] = "stock_detail"
                    st.rerun()
            with c2:
                if st.button("研究", key=f"ifind_r_{code}", use_container_width=True):
                    st.session_state["selected_stock"] = code
                    st.session_state["research_code"] = code
                    st.session_state["current_page"] = "research"
                    st.rerun()
            with _:
                if st.button("AI分析", key=f"ifind_a_{code}", use_container_width=True):
                    st.session_state["selected_stock"] = code
                    st.session_state["current_page"] = "ai_chat"
                    st.session_state["qq"] = f"请对 {code} {name} 做完整深度分析。先调行情/评分/技术三个工具，按风险→机会→条件→周期输出。"
                    st.rerun()


# ═══════════════════════════════════════════
# 推荐选股（合并筛选 + 结果渲染，消除 stale data）
# ═══════════════════════════════════════════

def _render_filter_and_results():
    from src.data.stock_list import SW_INDUSTRY, CONCEPTS

    st.session_state.setdefault("rf_mode", "综合")

    c1, c2, c3 = st.columns(3)
    for label, col, val in [("综合", c1, "综合"), ("行业", c2, "行业"), ("概念", c3, "概念")]:
        with col:
            if st.button(label, key=f"rfb_{val}", use_container_width=True,
                         type="primary" if st.session_state["rf_mode"] == val else "secondary"):
                st.session_state["rf_mode"] = val
                st.rerun()

    mode = st.session_state["rf_mode"]
    if mode == "行业":
        cur = st.selectbox("行业", list(SW_INDUSTRY.keys()), key="rfi", label_visibility="collapsed")
        filter_type, filter_key, flabel = "industry", cur, cur
    elif mode == "概念":
        cur = st.selectbox("概念", list(CONCEPTS.keys()), key="rfc", label_visibility="collapsed")
        filter_type, filter_key, flabel = "concept", cur, cur
    else:
        filter_type, filter_key, flabel = "all", "", "综合"

    results = _fetch_and_score(filter_type, filter_key)

    st.markdown(
        f'<div class="sec-h">六维评分候选 · {flabel}</div>'
        f'<div class="page-kicker">机会分 = 热度 + 承接 + 题材 + 延续 + 策略匹配 - 反量化扣分</div>',
        unsafe_allow_html=True)

    if not results:
        st.info(f"{flabel} 暂无候选")
        return

    st.caption(f"{len(results)} 只，显示前 {min(15, len(results))} 只")
    scope = f"{filter_type}:{filter_key or 'all'}"
    for index, (stock, result) in enumerate(results[:15]):
        _render_card(stock, result, scope=scope, index=index)


def _show_info_radar():
    st.markdown(
        '<div class="ai-hero">'
        '<div class="ai-hero-title">信息雷达</div>'
        '<div class="ai-hero-sub">比“推荐股票”更靠前：先看市场正在讨论什么，再判断它是真信号、假热点，还是需要等待验证。</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="score-explainer">'
        '<div class="score-explainer-card"><div class="score-explainer-title">升温信号</div>'
        '<div class="score-explainer-copy">政策、互动问答、公告、新闻里突然反复出现的主题。它只表示“值得研究”，不等于可以买。</div></div>'
        '<div class="score-explainer-card"><div class="score-explainer-title">伪热点过滤</div>'
        '<div class="score-explainer-copy">如果只有标题热闹、没有公告验证、没有板块联动、没有成交承接，就先标成噪音。</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        from src.data.providers.registry import provider_status

        status = provider_status()
        source_label = "iFinD专业源" if status.get("provider") == "ifind" and status.get("ready") else "公开源兜底"
        st.caption(f"数据源：{source_label} · {status.get('message', '')}")
    except Exception:
        pass

    code = st.session_state.get("selected_stock", "")
    c1, c2 = st.columns([2, 1])
    with c1:
        query_code = st.text_input("个股雷达", value=code, placeholder="输入 6 位代码，如 600519", label_visibility="collapsed")
    with c2:
        run_stock = st.button("查个股", use_container_width=True)

    if run_stock and query_code.strip():
        _render_stock_radar(query_code.strip()[:6])

    _render_market_radar()


def _render_market_radar():
    try:
        from src.news.radar import fetch_radar_market_overview
        radar = fetch_radar_market_overview(limit=24)
    except Exception as exc:
        st.warning(f"信息雷达暂不可用: {exc}")
        return

    sources = radar.get("sources", {})
    st.markdown('<div class="sec-h">全市场雷达源状态</div>', unsafe_allow_html=True)
    if sources:
        cols = st.columns(min(3, max(1, len(sources))))
        for i, (name, value) in enumerate(sources.items()):
            with cols[i % len(cols)]:
                ok = isinstance(value, int) and value > 0
                label = f"{value} 条" if isinstance(value, int) else str(value)
                st.metric(name, label, "可用" if ok else "待修复/无数据")

    items = radar.get("items", [])
    if not items:
        st.info("当前全市场雷达没有稳定抓到有效条目。AI 会把雷达数据标成低置信度，不能据此给明确动作。")
        return

    st.markdown('<div class="sec-h">今日升温信号</div>', unsafe_allow_html=True)
    for item in items[:12]:
        _render_info_item(item)


def _render_stock_radar(code: str):
    try:
        from src.news.radar import fetch_radar_for_stock
        radar = fetch_radar_for_stock(code, limit=8)
    except Exception as exc:
        st.warning(f"{code} 个股雷达暂不可用: {exc}")
        return

    st.markdown(f'<div class="sec-h">{code} 个股信息雷达</div>', unsafe_allow_html=True)
    sources = radar.get("sources", {})
    source_text = " · ".join(f"{k}:{v}" for k, v in sources.items()) if sources else "无来源状态"
    st.caption(source_text)
    items = radar.get("items", [])
    if not items:
        st.info("没有抓到互动易/公告/新闻有效条目。这个结论不是“没有风险”，只是“公开源暂时没有返回数据”。")
        return
    for item in items[:10]:
        _render_info_item(item)


def _render_info_item(item: dict):
    title = html.escape(str(item.get("title", "")))
    source = html.escape(str(item.get("source", "未知")))
    typ = html.escape(str(item.get("type", "")))
    published = html.escape(str(item.get("published_at", "")))
    sentiment = item.get("sentiment", "neutral")
    color = "var(--green)" if sentiment == "positive" else "var(--red)" if sentiment == "negative" else "var(--amber)"
    label = "偏利好" if sentiment == "positive" else "偏利空" if sentiment == "negative" else "待验证"
    codes = item.get("related_codes") or []
    code_text = " · ".join(codes[:3])
    st.markdown(
        f'<div class="recommend-card">'
        f'<div style="display:flex;justify-content:space-between;gap:10px">'
        f'<div style="flex:1;min-width:0"><div style="font-size:14px;font-weight:800;color:var(--text);line-height:1.45">{title}</div>'
        f'<div style="font-size:12px;color:var(--muted);margin-top:5px">{source} · {typ} · {published}</div></div>'
        f'<span class="badge" style="background:rgba(216,131,18,0.12);color:{color};white-space:nowrap">{label}</span>'
        f'</div>'
        + ('<div class="watch-sub">相关代码：' + html.escape(code_text) + '</div>' if code_text else '')
        + '</div>',
        unsafe_allow_html=True,
    )


def _fetch_and_score(filter_type: str, filter_key: str) -> list:
    """拉取股票+评分，返回 [(stock_dict, SixDimensionResult)]"""
    from src.data.realtime import get_realtime_quote, get_top_stocks
    from src.data.stock_list import SW_INDUSTRY, CONCEPTS
    from src.scoring.engine import V6ScoringEngine

    seen, stocks = set(), []

    if filter_key:
        # 行业/概念
        codes = SW_INDUSTRY.get(filter_key, CONCEPTS.get(filter_key, []))
        for cd in codes:
            q = get_realtime_quote(cd)
            if q and q.get("price", 0) > 0:
                seen.add(cd)
                name = _resolve_stock_name(cd, q.get("name", cd))
                stocks.append({
                    "code": cd, "name": name,
                    "price": q.get("price", 0), "change_pct": q.get("change_pct", 0),
                    "volume": q.get("volume", 0), "amount": q.get("amount", 0),
                    "turnover": q.get("turnover", 0), "open": q.get("open", 0),
                    "high": q.get("high", 0), "low": q.get("low", 0),
                    "volume_ratio": q.get("volume_ratio", 1.0),
                })
    else:
        # 综合
        for s in (get_top_stocks("amount", False, 40) or []) + (get_top_stocks("changepercent", False, 40) or []):
            cd = s.get("code", "")
            if cd and cd not in seen:
                seen.add(cd)
                s = dict(s)
                s["name"] = _resolve_stock_name(cd, s.get("name", cd))
                stocks.append(s)

    if not stocks:
        return []

    engine = V6ScoringEngine()
    try:
        results = []
        for s in stocks:
            cd = s.get("code", "")
            r = engine.score_stock(cd, quote=s)
            if r and r.status_label not in ("不建议参与", "已排除"):
                canonical_name = _resolve_stock_name(cd, s.get("name", ""))
                s["name"] = canonical_name
                r.name = canonical_name
                results.append((s, r))
        results.sort(key=lambda x: x[1].total_score, reverse=True)
        return results
    finally:
        engine.close()


def _render_card(stock: dict, result, scope: str = "all", index: int = 0):
    # 防御：确保 stock 和 result 的 code 一致，不一致时跳过
    scode = stock.get("code", "")
    rcode = result.code
    if scode and rcode and scode != rcode:
        return  # 数据错位，跳过此条
    code = scode or rcode
    name = _resolve_stock_name(code, stock.get("name") or result.name)
    safe_name = html.escape(name)
    safe_code = html.escape(code)
    chg = stock.get("change_pct", 0)
    chg_c = "var(--red)" if chg > 0 else "var(--green)" if chg < 0 else "var(--muted)"
    risk = result.anti_quant.risk_level
    risk_badge = "badge-high" if risk in ("高","极高") else "badge-mid" if risk == "中" else "badge-low"
    border = "var(--green)" if result.total_score >= 72 and risk in ("低","中") else "var(--amber)" if result.total_score >= 60 else "var(--border)"
    triggers_str = " · ".join(result.anti_quant.triggers[:2]) if result.anti_quant.triggers else "无显著触发"
    strat_names = [x["strategy"] if isinstance(x, dict) else str(x) for x in (result.matched_strategies or [])]
    strategies = " / ".join(strat_names[:2]) if strat_names else "综合短线"
    plain = _plain(result)

    card_key = f"{scope}:{index}:{code}:{name}"
    with st.container(key=f"radar_card_{abs(hash(card_key))}"):
        st.markdown(
            f'<!-- radar-card {html.escape(card_key)} -->'
            f'<div class="recommend-card" data-scope="{html.escape(scope)}" data-code="{safe_code}" style="border-left:3px solid {border}">'
            f'<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start">'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-size:15px;font-weight:750;color:var(--text)">{safe_name}'
            f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:7px">{safe_code}</span></div>'
            f'<div style="font-size:12px;color:var(--muted);margin-top:2px">{strategies} · {result.status_label}</div>'
            f'</div>'
            f'<div style="text-align:right;min-width:82px">'
            f'<div style="font-family:var(--mono);font-size:18px;font-weight:800;color:var(--ai)">{result.total_score:.0f}</div>'
            f'<div style="font-family:var(--mono);font-size:12px;color:{chg_c}">{chg:+.2f}%</div>'
            f'</div></div>'
            f'<div style="font-size:12px;color:var(--text);margin-top:6px;line-height:1.5">{plain}</div>'
            f'<div class="score-row">'
            f'<span class="score-pill">热度{result.heat.score:.0f}</span>'
            f'<span class="score-pill">承接{result.support.score:.0f}</span>'
            f'<span class="score-pill">题材{result.theme.score:.0f}</span>'
            f'<span class="score-pill">延续{result.continuation.score:.0f}</span>'
            f'<span class="score-pill">策略{result.strategy_match.score:.0f}</span>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:9px">'
            f'<div style="font-size:12px;color:var(--muted)">{triggers_str}</div>'
            f'<span class="badge {risk_badge}">{risk}风险</span>'
            f'</div></div>',
            unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        button_suffix = f"{scope}_{index}_{code}".replace(":", "_")
        with c1:
            if st.button("查看", key=f"rc_v_{button_suffix}", use_container_width=True):
                st.session_state["selected_stock"] = code
                st.session_state["previous_page"] = "radar"
                st.session_state["current_page"] = "stock_detail"; st.rerun()
        with c2:
            if st.button("AI分析", key=f"rc_a_{button_suffix}", use_container_width=True):
                st.session_state["selected_stock"] = code
                st.session_state["current_page"] = "ai_chat"
                st.session_state["qq"] = f"请对 {code} 做完整深度分析。先调行情/评分/技术三个工具，按风险→机会→条件→周期输出，每个专业术语附白话解释。最后用一句话总结。"
                st.rerun()
        with c3:
            if st.button("验证", key=f"rc_l_{button_suffix}", use_container_width=True):
                try:
                    from src.memory.analysis_memory import AnalysisMemory
                    with AnalysisMemory() as am:
                        am.create_verification(
                            "strategy",
                            code,
                            name,
                            datetime.now(),
                            strategy_name=strategies,
                            suggested_period="1-2天",
                            hypothesis=f"{name} 当前六维评分 {result.total_score:.0f}，状态 {result.status_label}，用于验证雷达候选是否有后续延续。",
                            entry_conditions=[
                                "分时回踩不破均价线",
                                "板块内至少 2-3 只股票同步走强",
                                "反量化风险不升至高/极高",
                            ],
                            invalidation_conditions=[
                                "放量滞涨或冲高回落",
                                "跌破昨日低点或分时均价线 10 分钟不收回",
                                "板块明显背离",
                            ],
                            stop_loss_rule="模拟验证中若 T+1 最大回撤超过 3% 记为高风险样本",
                            risk_level=result.anti_quant.risk_level,
                            confidence_level="中" if result.total_score < 72 else "高",
                            allow_real_trade=False,
                        )
                    st.success("已加入")
                except Exception as e:
                    st.warning(f"失败: {e}")


def _plain(result) -> str:
    r, h, s, t, c = result.anti_quant.risk_level, result.heat.score, result.support.score, result.theme.score, result.continuation.score
    parts = ["资金关注度高" if h >= 65 else "热度适中" if h >= 50 else "资金关注偏弱",
             "承接良好" if s >= 65 else "承接尚可" if s >= 50 else "承接不足",
             "属今日主线" if t >= 60 else "板块不强" if t >= 45 else "板块偏弱",
             "可延至2-3天" if c >= 65 else "适合隔夜-1天" if c >= 50 else "不建议延长"]
    parts.append("反量化高风险" if r in ("高","极高") else "反量化风险中" if r == "中" else "反量化风险低")
    return "。".join(parts) + "。"


@lru_cache(maxsize=1)
def _stock_name_lookup() -> dict:
    """标准股票名称表。雷达页展示名只信任代码映射，避免行情源/前端状态造成名称错位。"""
    lookup = {}
    try:
        from src.data.stock_list import CACHE_FILE, fetch_all_stocks, STANDARD_STOCK_NAMES

        if Path(CACHE_FILE).exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            for item in cache.get("stocks", []):
                code = str(item.get("code", ""))
                name = str(item.get("name", ""))
                if code and name:
                    lookup[code] = name

        if not lookup:
            for item in fetch_all_stocks():
                code = str(item.get("code", ""))
                name = str(item.get("name", ""))
                if code and name:
                    lookup[code] = name
    except Exception:
        pass

    # 兜底覆盖常用行业/概念核心股，服务器首次部署无缓存时仍能避免明显错名。
    try:
        lookup.update(STANDARD_STOCK_NAMES)
    except Exception:
        pass
    return lookup


def _resolve_stock_name(code: str, fallback: str = "") -> str:
    """根据代码解析标准名称，fallback 只用于未知股票。"""
    code = str(code or "")
    fallback = str(fallback or "")
    return _stock_name_lookup().get(code) or fallback or code


# ═══════════════════════════════════════════
# 风险排除 & 策略
# ═══════════════════════════════════════════

def _show_risk_scan():
    try:
        from src.scoring.engine import V6ScoringEngine
        from src.data.realtime import get_top_stocks
        e = V6ScoringEngine()
        try:
            stocks = get_top_stocks("amount", False, 50)
            risky = []
            for s in (stocks or []):
                cd = s.get("code", "")
                if not cd: continue
                r = e.score_stock(cd, quote=s)
                if r and r.anti_quant.total_risk >= 30:
                    risky.append({"code": cd, "name": s.get("name", cd), "chg": s.get("change_pct", 0),
                                  "risk": r.anti_quant.total_risk, "level": r.anti_quant.risk_level,
                                  "triggers": r.anti_quant.triggers[:3]})
            if risky:
                risky.sort(key=lambda x: x["risk"], reverse=True)
                for item in risky[:12]:
                    lvl = item["level"]
                    b = "var(--red)" if lvl in ("高","极高") else "var(--amber)"
                    bg = "badge-high" if lvl in ("高","极高") else "badge-mid"
                    tr = " · ".join(item["triggers"][:3]) if item["triggers"] else ""
                    clr = "#F04438" if item["chg"] > 0 else "#12B76A"
                    st.markdown(
                        f'<div class="card" style="border-left:3px solid {b};margin-bottom:8px">'
                        f'<div style="display:flex;justify-content:space-between">'
                        f'<div><span style="font-weight:600;font-size:15px">{item["name"]}</span>'
                        f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{item["code"]}</span></div>'
                        f'<div style="text-align:right"><span style="font-family:var(--mono);color:{clr}">{item["chg"]:+.2f}%</span>'
                        f'<span class="badge {bg}" style="margin-left:6px">{lvl}风险</span></div>'
                        f'</div><div style="font-size:12px;color:var(--muted);margin-top:4px">{tr}</div></div>',
                        unsafe_allow_html=True)
                    if st.button("查看", key=f"risk_{item['code']}"):
                        st.session_state["selected_stock"] = item["code"]
                        st.session_state["current_page"] = "stock_detail"; st.rerun()
            else:
                st.success("未检测到显著风险股票")
        finally:
            e.close()
    except Exception as ex:
        st.warning(f"暂不可用: {ex}")


def _show_strategy_scan():
    choice = st.radio("策略", ["尾盘隔夜雷达", "短持延续雷达"], horizontal=True, label_visibility="collapsed")
    _show_overnight() if choice == "尾盘隔夜雷达" else _show_continuation()


def _show_overnight():
    st.markdown('<div style="font-size:11px;color:var(--muted);margin-bottom:8px">条件：涨幅2.5-5.5% · 量比≥1.2 · 换手5-10% · MA多头 · 分时均线上方≥70%</div>', unsafe_allow_html=True)
    try:
        from src.data.realtime import get_top_stocks
        from src.strategies.overnight import OvernightRadar
        r = OvernightRadar()
        stocks = get_top_stocks("change_pct", False, 60)
        cand = []
        for s in (stocks or []):
            cd = s.get("code", "")
            if not cd: continue
            ok, _ = r.check_hard_filters(s)
            if ok:
                m = r.compute_match(s)
                cand.append({"code": cd, "name": s.get("name", cd), "chg": s.get("change_pct", 0),
                             "match": m["match"], "status": m["status"]})
        if cand:
            cand.sort(key=lambda x: x["match"], reverse=True)
            for c in cand[:10]:
                bo = "var(--green)" if c["match"] >= 80 else "var(--amber)" if c["match"] >= 60 else "var(--border)"
                clr = "#F04438" if c["chg"] > 0 else "#12B76A"
                st.markdown(
                    f'<div class="card" style="border-left:3px solid {bo};margin-bottom:8px">'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<div><span style="font-weight:600;font-size:15px">{c["name"]}</span>'
                    f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{c["code"]}</span></div>'
                    f'<div style="text-align:right"><span style="font-family:var(--mono);font-weight:700;color:{clr}">{c["chg"]:+.2f}%</span>'
                    f'<div style="font-size:12px;color:var(--muted)">匹配{c["match"]:.0f}% · {c["status"]}</div></div>'
                    f'</div></div>', unsafe_allow_html=True)
        else:
            st.info("无符合条件候选")
    except Exception as ex:
        st.warning(f"暂不可用: {ex}")


def _show_continuation():
    st.markdown('<div style="font-size:11px;color:var(--muted);margin-bottom:8px">条件：价>MA5>MA10 · 近5日涨幅≤15% · 量价健康 · 压力可控</div>', unsafe_allow_html=True)
    try:
        from src.data.realtime import get_top_stocks
        from src.scoring.engine import V6ScoringEngine
        e = V6ScoringEngine()
        try:
            stocks = get_top_stocks("change_pct", False, 40)
            res = []
            for s in (stocks or []):
                cd = s.get("code", "")
                if not cd: continue
                r = e.score_stock(cd, quote=s)
                if r and r.continuation.score >= 60 and r.status_label in ("可执行","等待确认"):
                    res.append({"code": cd, "name": s.get("name", cd), "chg": s.get("change_pct", 0),
                                "cont": r.continuation.score, "status": r.status_label})
            if res:
                res.sort(key=lambda x: x["cont"], reverse=True)
                for c in res[:10]:
                    bo = "var(--green)" if c["cont"] >= 75 else "var(--amber)"
                    clr = "#F04438" if c["chg"] > 0 else "#12B76A"
                    st.markdown(
                        f'<div class="card" style="border-left:3px solid {bo};margin-bottom:8px">'
                        f'<div style="display:flex;justify-content:space-between">'
                        f'<div><span style="font-weight:600;font-size:15px">{c["name"]}</span>'
                        f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{c["code"]}</span></div>'
                        f'<div style="text-align:right"><span style="font-family:var(--mono);font-weight:700;color:{clr}">{c["chg"]:+.2f}%</span>'
                        f'<div style="font-size:12px;color:var(--muted)">延续{c["cont"]:.0f} · {c["status"]}</div></div>'
                        f'</div></div>', unsafe_allow_html=True)
            else:
                st.info("无符合条件候选")
        finally:
            e.close()
    except Exception as ex:
        st.warning(f"暂不可用: {ex}")


# ═══════════════════════════════════════════
# 每日推荐行业/概念
# ═══════════════════════════════════════════

def _daily_sectors():
    from src.data.stock_list import SW_INDUSTRY, CONCEPTS
    from src.data.realtime import get_realtime_quote

    st.markdown(
        '<div class="sec-h">今日推荐板块</div>'
        '<div style="font-size:11px;color:var(--muted);margin-bottom:8px">综合涨跌幅、成交额、龙头强度筛选</div>',
        unsafe_allow_html=True)

    if "daily_recs" not in st.session_state:
        st.session_state["daily_recs"] = _compute_daily_recs()
    recs = st.session_state["daily_recs"]

    st.markdown('<div style="font-size:12px;font-weight:700;color:var(--text);margin-top:8px">推荐行业</div>', unsafe_allow_html=True)
    inds = recs.get("industries", [])[:3]
    if inds:
        cols = st.columns(3)
        for i, (name, score, reason) in enumerate(inds):
            with cols[i]:
                st.markdown(
                    f'<div class="card" style="text-align:center;padding:10px">'
                    f'<div style="font-size:14px;font-weight:700;color:var(--text)">{name}</div>'
                    f'<div style="font-size:11px;color:var(--muted);margin-top:4px">{reason}</div>'
                    f'<div style="font-family:var(--mono);font-size:12px;color:var(--ai);margin-top:4px">活跃 {score:.0f}</div></div>',
                    unsafe_allow_html=True)
    else:
        st.info("暂无行业推荐")

    st.markdown('<div style="font-size:12px;font-weight:700;color:var(--text);margin-top:8px">推荐概念</div>', unsafe_allow_html=True)
    cons = recs.get("concepts", [])[:3]
    if cons:
        cols = st.columns(3)
        for i, (name, score, reason) in enumerate(cons):
            with cols[i]:
                st.markdown(
                    f'<div class="card" style="text-align:center;padding:10px">'
                    f'<div style="font-size:14px;font-weight:700;color:var(--text)">{name}</div>'
                    f'<div style="font-size:11px;color:var(--muted);margin-top:4px">{reason}</div>'
                    f'<div style="font-family:var(--mono);font-size:12px;color:var(--ai);margin-top:4px">活跃 {score:.0f}</div></div>',
                    unsafe_allow_html=True)
    else:
        st.info("暂无概念推荐")


def _compute_daily_recs() -> dict:
    from src.data.stock_list import SW_INDUSTRY, CONCEPTS
    from src.data.realtime import get_realtime_quote

    industries = []
    for name, codes in SW_INDUSTRY.items():
        chgs, amounts, up_count = [], [], 0
        for cd in codes[:5]:
            q = get_realtime_quote(cd)
            if q and q.get("price", 0) > 0:
                chgs.append(q.get("change_pct", 0))
                amounts.append(q.get("amount", 0) or 0)
                if q.get("change_pct", 0) > 2: up_count += 1
        if chgs:
            avg = sum(chgs) / len(chgs)
            score = avg * 4 + up_count * 10 + min(sum(amounts) / 5e8, 20)
            reason = "领涨" if avg > 2 else "偏强" if avg > 0.5 else "震荡"
            industries.append((name, score, reason))
    industries.sort(key=lambda x: x[1], reverse=True)

    concepts = []
    for name, codes in CONCEPTS.items():
        chgs, up_count = [], 0
        for cd in codes[:5]:
            q = get_realtime_quote(cd)
            if q and q.get("price", 0) > 0:
                chgs.append(q.get("change_pct", 0))
                if q.get("change_pct", 0) > 2: up_count += 1
        if chgs:
            avg = sum(chgs) / len(chgs)
            score = avg * 4 + up_count * 10
            reason = "活跃" if avg > 1.5 else "波动" if avg > 0 else "偏弱"
            concepts.append((name, score, reason))
    concepts.sort(key=lambda x: x[1], reverse=True)

    return {"industries": industries, "concepts": concepts}
