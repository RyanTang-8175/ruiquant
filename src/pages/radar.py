"""AlphaEye v6 雷达页 —— 一眼看风险，一眼看机会"""

import streamlit as st
from datetime import datetime


def render_radar_page():
    now = datetime.now()

    # ── 全局搜索 ──
    from src.ui.search import render_search_bar
    code = render_search_bar(key="radar")
    if code:
        st.session_state["selected_stock"] = code
        st.session_state["current_page"] = "stock_detail"
        st.rerun()

    # ── 今日环境 ──
    from src.data.realtime import get_market_overview
    ov = get_market_overview()
    indices = ov.get("indices", [])
    if indices:
        main = next((i for i in indices if "上证" in i.get("name", "")), indices[0])
        chg = main.get("change_pct", 0)
        if chg > 0.5:
            env, color, msg = "适合", "var(--green)", "大盘稳定，短线环境良好"
        elif chg > -0.5:
            env, color, msg = "一般", "var(--amber)", "大盘震荡，精选个股"
        elif chg > -1.5:
            env, color, msg = "谨慎", "var(--red)", "大盘偏弱，控制仓位"
        else:
            env, color, msg = "不适合", "var(--red)", "大盘走弱，建议观望"

        idx_html = "".join(
            f'<div class="idx-cell">'
            f'<div class="n">{i.get("name","")}</div>'
            f'<div class="p">{i.get("price",0):.2f}</div>'
            f'<div class="c">{"+" if i.get("change_pct",0)>0 else ""}{i.get("change_pct",0):.2f}%</div>'
            f'</div>' for i in indices
        )
        st.markdown(
            f'<div class="card" style="margin-bottom:12px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
            f'<div style="font-weight:700;font-size:17px;color:var(--text)">今日短线</div>'
            f'<div style="font-weight:700;font-size:16px;color:{color}">{env}</div>'
            f'</div>'
            f'<div style="font-size:13px;color:var(--muted);margin-bottom:10px">{msg}</div>'
            f'<div class="idx-strip" style="margin-bottom:0">{idx_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    h, m = now.hour, now.minute
    if 14 <= h <= 15:
        phase = "确认阶段·不追高" if m >= 50 else ("观察阶段·等待确认" if m >= 45 else ("初筛阶段·开始选股" if m >= 30 else "等待尾盘"))
        st.info(f"尾盘时段 · {phase} · {now.strftime('%H:%M')}")

    # ── 只跑一次评分，结果缓存到 session_state，compact 和 tab 复用 ──
    fresh = _ensure_recommendations()

    # ── 首屏摘要 ──
    _show_recommendations(fresh, compact=True)

    # ── 三个 Tab ──
    tab0, tab1, tab2 = st.tabs(["推荐选股", "风险排除", "策略扫描"])
    with tab0:
        st.caption("按六维评分排序，反量化风险自动扣分。")
        _show_recommendations(fresh, compact=False)
    with tab1:
        _show_risk_scan()
    with tab2:
        _show_strategy_scan()


# ═══════════════════════════════════════════
# 数据缓存层：只拉一次数据，compact 和 full 共享
# ═══════════════════════════════════════════

@st.cache_data(ttl=30)
def _fetch_stocks_for_filter(_filter_key: str) -> list:
    """根据筛选条件拉取股票列表（30秒缓存避免重复API调用）"""
    filter_type, filter_key = _filter_key.split("::", 1) if "::" in _filter_key else ("all", "")
    from src.data.realtime import get_realtime_quote, get_top_stocks
    from src.data.stock_list import SW_INDUSTRY, CONCEPTS

    if filter_key and filter_type == "industry":
        codes = SW_INDUSTRY.get(filter_key, [])
    elif filter_key and filter_type == "concept":
        codes = CONCEPTS.get(filter_key, [])
    else:
        codes = None

    seen = set()
    stocks = []

    if codes:
        # 批量拉取行业/概念行情
        for cd in codes:
            q = get_realtime_quote(cd)
            if q and q.get("price", 0) > 0:
                seen.add(cd)
                stocks.append({
                    "code": cd, "name": q.get("name", cd),
                    "price": q.get("price", 0), "change_pct": q.get("change_pct", 0),
                    "volume": q.get("volume", 0), "amount": q.get("amount", 0),
                    "turnover": q.get("turnover", 0), "open": q.get("open", 0),
                    "high": q.get("high", 0), "low": q.get("low", 0),
                    "volume_ratio": q.get("volume_ratio", 1.0),
                })
    else:
        # 综合：从排行榜拉
        raw = (get_top_stocks(sort_field="amount", asc=False, limit=40) or []) + \
              (get_top_stocks(sort_field="changepercent", asc=False, limit=40) or [])
        for s in raw:
            cd = s.get("code", "")
            if cd and cd not in seen:
                seen.add(cd)
                stocks.append(s)

    return stocks


def _ensure_recommendations() -> list:
    """确保评分结果已缓存，返回 [(stock_dict, SixDimensionResult)]"""
    from src.data.stock_list import SW_INDUSTRY, CONCEPTS

    mode_key = "radar_filter_mode"
    industry_key = "radar_filter_industry"
    concept_key = "radar_filter_concept"
    st.session_state.setdefault(mode_key, "综合")
    st.session_state.setdefault(industry_key, list(SW_INDUSTRY.keys())[0])
    st.session_state.setdefault(concept_key, list(CONCEPTS.keys())[0])

    mode = st.session_state[mode_key]
    if mode == "行业":
        fk = st.session_state[industry_key]
        filter_type, filter_key = "industry", fk
    elif mode == "概念":
        fk = st.session_state[concept_key]
        filter_type, filter_key = "concept", fk
    else:
        filter_type, filter_key = "all", ""

    # 用 session_state 存评分结果，key 变化时重算
    result_key = f"radar_results_{filter_type}_{filter_key}"
    if result_key not in st.session_state or st.session_state.get("radar_dirty"):
        st.session_state.pop("radar_dirty", None)
        stocks = _fetch_stocks_for_filter(f"{filter_type}::{filter_key}")
        from src.scoring.engine import V6ScoringEngine
        engine = V6ScoringEngine()
        try:
            results = []
            for s in stocks:
                cd = s.get("code", "")
                if not cd:
                    continue
                r = engine.score_stock(cd, quote=s)
                if not r or r.status_label in ("不建议参与", "已排除"):
                    continue
                results.append((s, r))
            results.sort(key=lambda x: x[1].total_score, reverse=True)
            st.session_state[result_key] = results
        finally:
            engine.close()

    return st.session_state.get(result_key, [])


# ═══════════════════════════════════════════
# 推荐展示
# ═══════════════════════════════════════════

def _show_recommendations(fresh: list, compact: bool = True):
    from src.data.stock_list import SW_INDUSTRY, CONCEPTS

    mode_key = "radar_filter_mode"
    industry_key = "radar_filter_industry"
    concept_key = "radar_filter_concept"

    title = "今日选股推荐" if compact else "六维评分候选"

    # ── 筛选器 UI（仅 full 模式渲染）──
    if not compact:
        c1, c2, c3 = st.columns(3)
        for label, col, m in [("综合", c1, "综合"), ("行业", c2, "行业"), ("概念", c3, "概念")]:
            with col:
                if st.button(label, key=f"fm_{label}", use_container_width=True,
                             type="primary" if st.session_state[mode_key] == m else "secondary"):
                    st.session_state[mode_key] = m
                    st.session_state["radar_dirty"] = True
                    st.rerun()

    mode = st.session_state[mode_key]
    if mode == "行业":
        selected = st.session_state[industry_key]
        if not compact:
            selected = st.selectbox("行业", list(SW_INDUSTRY.keys()),
                                    index=list(SW_INDUSTRY.keys()).index(selected),
                                    key="ind_sel", label_visibility="collapsed")
        st.session_state[industry_key] = selected
        filter_label = selected
        if st.session_state.get("radar_dirty"):
            _ensure_recommendations()
    elif mode == "概念":
        selected = st.session_state[concept_key]
        if not compact:
            selected = st.selectbox("概念", list(CONCEPTS.keys()),
                                    index=list(CONCEPTS.keys()).index(selected),
                                    key="con_sel", label_visibility="collapsed")
        st.session_state[concept_key] = selected
        filter_label = selected
        if st.session_state.get("radar_dirty"):
            _ensure_recommendations()
    else:
        filter_label = "综合"
        if st.session_state.get("radar_dirty"):
            _ensure_recommendations()

    st.markdown(
        f'<div class="sec-h">{title} · {filter_label}</div>'
        f'<div class="page-kicker">机会分 = 热度 + 承接 + 题材 + 延续 + 策略匹配 - 反量化扣分</div>',
        unsafe_allow_html=True,
    )

    if not fresh:
        st.info(f"{filter_label} 暂无候选，可能是非交易时段或网络问题")
        return

    limit = 3 if compact else 15
    st.caption(f"{len(fresh)} 只候选，显示前 {min(limit, len(fresh))} 只")
    for s, r in fresh[:limit]:
        _render_recommend_card(s, r, compact=compact)


def _render_recommend_card(stock: dict, result, compact: bool = True):
    # 确保 code 一致
    code = stock.get("code", result.code)
    name = stock.get("name", result.name)
    chg = stock.get("change_pct", 0)
    chg_color = "var(--red)" if chg > 0 else "var(--green)" if chg < 0 else "var(--muted)"
    risk = result.anti_quant.risk_level
    risk_cls = "badge-high" if risk in ("高", "极高") else "badge-mid" if risk == "中" else "badge-low"
    border = "var(--green)" if result.total_score >= 72 and risk in ("低", "中") else "var(--amber)" if result.total_score >= 60 else "var(--border)"
    triggers_list = result.anti_quant.triggers if result.anti_quant.triggers else []
    triggers = " · ".join(triggers_list[:2]) if triggers_list else "暂无显著反量化触发项"
    strategy_names = [s["strategy"] if isinstance(s, dict) else str(s) for s in (result.matched_strategies or [])]
    strategies = " / ".join(strategy_names[:2]) if strategy_names else "综合短线"
    plain = _plain_verdict(result)

    html = (
        f'<div class="recommend-card" style="border-left:3px solid {border}">'
        f'<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start">'
        f'<div style="flex:1;min-width:0">'
        f'<div style="font-size:15px;font-weight:750;color:var(--text)">{name}'
        f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:7px">{code}</span></div>'
        f'<div style="font-size:12px;color:var(--muted);margin-top:2px">{strategies} · {result.status_label}</div>'
        f'</div>'
        f'<div style="text-align:right;min-width:82px">'
        f'<div style="font-family:var(--mono);font-size:18px;font-weight:800;color:var(--ai)">{result.total_score:.0f}</div>'
        f'<div style="font-family:var(--mono);font-size:12px;color:{chg_color}">{chg:+.2f}%</div>'
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
        f'<div style="font-size:12px;color:var(--muted);line-height:1.45">{triggers}</div>'
        f'<span class="badge {risk_cls}">{risk}风险</span>'
        f'</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    if not compact:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("查看", key=f"rv_{code}", use_container_width=True):
                st.session_state["selected_stock"] = code
                st.session_state["current_page"] = "stock_detail"
                st.rerun()
        with c2:
            if st.button("AI分析", key=f"ra_{code}", use_container_width=True):
                st.session_state["selected_stock"] = code
                st.session_state["current_page"] = "ai_chat"
                st.session_state["qq"] = f"请对 {code} 做完整深度分析。先调行情/评分/技术三个工具，按风险→机会→条件→周期输出，每个专业术语附白话解释。最后用一句话总结。"
                st.rerun()
        with c3:
            if st.button("验证", key=f"rl_{code}", use_container_width=True):
                try:
                    from src.memory.analysis_memory import AnalysisMemory
                    am = AnalysisMemory()
                    am.create_verification(source_type="strategy", stock_code=code,
                                           stock_name=name, signal_date=datetime.now(),
                                           suggested_period="1-2天")
                    am.close()
                    st.success("已加入实验室")
                except Exception as e:
                    st.warning(f"失败: {e}")


def _plain_verdict(result) -> str:
    risk = result.anti_quant.risk_level
    heat, support, theme, cont = result.heat.score, result.support.score, result.theme.score, result.continuation.score
    parts = []
    if heat >= 65: parts.append("资金关注度高")
    elif heat >= 50: parts.append("热度适中")
    else: parts.append("资金关注偏弱")
    if support >= 65: parts.append("承接良好")
    elif support >= 50: parts.append("承接尚可")
    else: parts.append("承接不足，小心冲高回落")
    if theme >= 60: parts.append("属今日主线")
    elif theme >= 45: parts.append("板块不算强")
    else: parts.append("板块偏弱")
    if cont >= 65: parts.append("可延至2-3天")
    elif cont >= 50: parts.append("适合隔夜到1-2天")
    else: parts.append("不建议延长")
    if risk in ("高", "极高"): parts.append("反量化风险偏高")
    elif risk == "中": parts.append("反量化风险可控")
    else: parts.append("反量化风险低")
    return "。".join(parts) + "。"


# ═══════════════════════════════════════════
# 风险排除 & 策略扫描
# ═══════════════════════════════════════════

def _show_risk_scan():
    try:
        from src.scoring.engine import V6ScoringEngine
        from src.data.realtime import get_top_stocks
        engine = V6ScoringEngine()
        try:
            stocks = get_top_stocks(sort_field="amount", asc=False, limit=50)
            risky = []
            for s in (stocks or []):
                cd = s.get("code", "")
                if not cd: continue
                r = engine.score_stock(cd, quote=s)
                if r and r.anti_quant.total_risk >= 30:
                    risky.append({"code": cd, "name": s.get("name", cd),
                                  "chg": s.get("change_pct", 0),
                                  "risk": r.anti_quant.total_risk,
                                  "level": r.anti_quant.risk_level,
                                  "triggers": r.anti_quant.triggers[:3]})
            if risky:
                risky.sort(key=lambda x: x["risk"], reverse=True)
                for item in risky[:12]:
                    lvl = item["level"]
                    border = "var(--red)" if lvl in ("高", "极高") else "var(--amber)"
                    badge = "badge-high" if lvl in ("高", "极高") else "badge-mid"
                    trig = " · ".join(item["triggers"][:3]) if item["triggers"] else ""
                    clr = "#F04438" if item["chg"] > 0 else "#12B76A"
                    st.markdown(
                        f'<div class="card" style="border-left:3px solid {border};margin-bottom:8px">'
                        f'<div style="display:flex;justify-content:space-between">'
                        f'<div><span style="font-weight:600;font-size:15px">{item["name"]}</span>'
                        f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{item["code"]}</span></div>'
                        f'<div style="text-align:right"><span style="font-family:var(--mono);color:{clr}">{item["chg"]:+.2f}%</span>'
                        f'<span class="badge {badge}" style="margin-left:6px">{lvl}风险</span></div>'
                        f'</div><div style="font-size:12px;color:var(--muted);margin-top:4px">{trig}</div></div>',
                        unsafe_allow_html=True)
                    if st.button("查看", key=f"risk_{item['code']}"):
                        st.session_state["selected_stock"] = item["code"]
                        st.session_state["current_page"] = "stock_detail"
                        st.rerun()
            else:
                st.success("当前未检测到显著风险股票")
        finally:
            engine.close()
    except Exception as e:
        st.warning(f"风险扫描暂不可用: {e}")


def _show_strategy_scan():
    choice = st.radio("策略", ["尾盘隔夜雷达", "短持延续雷达"],
                      horizontal=True, label_visibility="collapsed")
    if choice == "尾盘隔夜雷达":
        _show_overnight()
    else:
        _show_continuation()


def _show_overnight():
    st.markdown('<div style="font-size:11px;color:var(--muted);margin-bottom:8px">'
                '条件：涨幅2.5-5.5% · 量比≥1.2 · 换手5-10% · MA多头 · 分时均线上方≥70%</div>',
                unsafe_allow_html=True)
    try:
        from src.data.realtime import get_top_stocks
        from src.strategies.overnight import OvernightRadar
        radar = OvernightRadar()
        stocks = get_top_stocks(sort_field="change_pct", asc=False, limit=60)
        candidates = []
        for s in (stocks or []):
            cd = s.get("code", "")
            if not cd: continue
            passed, _ = radar.check_hard_filters(s)
            if passed:
                m = radar.compute_match(s)
                candidates.append({"code": cd, "name": s.get("name", cd),
                                   "chg": s.get("change_pct", 0),
                                   "match": m["match"], "status": m["status"]})
        if candidates:
            candidates.sort(key=lambda x: x["match"], reverse=True)
            for c in candidates[:10]:
                border = "var(--green)" if c["match"] >= 80 else "var(--amber)" if c["match"] >= 60 else "var(--border)"
                clr = "#F04438" if c["chg"] > 0 else "#12B76A"
                st.markdown(
                    f'<div class="card" style="border-left:3px solid {border};margin-bottom:8px">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div><span style="font-weight:600;font-size:15px">{c["name"]}</span>'
                    f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{c["code"]}</span></div>'
                    f'<div style="text-align:right"><span style="font-family:var(--mono);font-weight:700;color:{clr}">{c["chg"]:+.2f}%</span>'
                    f'<div style="font-size:12px;color:var(--muted)">匹配{c["match"]:.0f}%·{c["status"]}</div></div>'
                    f'</div></div>', unsafe_allow_html=True)
        else:
            st.info("当前无符合尾盘隔夜条件的候选")
    except Exception as e:
        st.warning(f"扫描暂不可用: {e}")


def _show_continuation():
    st.markdown('<div style="font-size:11px;color:var(--muted);margin-bottom:8px">'
                '条件：价>MA5>MA10 · 近5日涨幅≤15% · 量价健康 · 压力可控</div>',
                unsafe_allow_html=True)
    try:
        from src.data.realtime import get_top_stocks
        from src.scoring.engine import V6ScoringEngine
        engine = V6ScoringEngine()
        try:
            stocks = get_top_stocks(sort_field="change_pct", asc=False, limit=40)
            results = []
            for s in (stocks or []):
                cd = s.get("code", "")
                if not cd: continue
                r = engine.score_stock(cd, quote=s)
                if r and r.continuation.score >= 60 and r.status_label in ("可执行", "等待确认"):
                    results.append({"code": cd, "name": s.get("name", cd),
                                    "chg": s.get("change_pct", 0),
                                    "cont": r.continuation.score,
                                    "status": r.status_label})
            if results:
                results.sort(key=lambda x: x["cont"], reverse=True)
                for c in results[:10]:
                    border = "var(--green)" if c["cont"] >= 75 else "var(--amber)"
                    clr = "#F04438" if c["chg"] > 0 else "#12B76A"
                    st.markdown(
                        f'<div class="card" style="border-left:3px solid {border};margin-bottom:8px">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'<div><span style="font-weight:600;font-size:15px">{c["name"]}</span>'
                        f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{c["code"]}</span></div>'
                        f'<div style="text-align:right"><span style="font-family:var(--mono);font-weight:700;color:{clr}">{c["chg"]:+.2f}%</span>'
                        f'<div style="font-size:12px;color:var(--muted)">延续{c["cont"]:.0f}·{c["status"]}</div></div>'
                        f'</div></div>', unsafe_allow_html=True)
            else:
                st.info("当前无符合短持延续条件的候选")
        finally:
            engine.close()
    except Exception as e:
        st.warning(f"扫描暂不可用: {e}")
