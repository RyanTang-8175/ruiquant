"""AlphaEye v6 雷达页 —— 一眼看风险，一眼看机会"""

import streamlit as st
from datetime import datetime


def render_radar_page():
    now = datetime.now()

    # ── 1. 全局搜索 ──
    from src.ui.search import render_search_bar
    code = render_search_bar(key="radar")
    if code:
        st.session_state["selected_stock"] = code
        st.session_state["current_page"] = "stock_detail"
        st.rerun()

    # ── 2. 今日环境 —— 一眼判断适不适合做短线 ──
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
            f'<div class="p" style="color:{"var(--red)" if i.get("change_pct",0)>0 else "var(--green)" if i.get("change_pct",0)<0 else "var(--muted)"}">{i.get("price",0):.2f}</div>'
            f'<div class="c">{"+" if i.get("change_pct",0)>0 else ""}{i.get("change_pct",0):.2f}%</div>'
            f'</div>'
            for i in indices
        )
        st.markdown(
            f'<div class="card" style="margin-bottom:12px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
            f'<div style="font-weight:700;font-size:17px;color:var(--text)">今日短线</div>'
            f'<div style="font-family:var(--mono);font-weight:700;font-size:16px;color:{color}">{env}</div>'
            f'</div>'
            f'<div style="font-size:13px;color:var(--muted);margin-bottom:10px">{msg}</div>'
            f'<div class="idx-strip" style="margin-bottom:0">{idx_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    h, m = now.hour, now.minute
    if 14 <= h <= 15:
        if h == 14 and m >= 50:
            phase = "确认阶段 · 不追高"
        elif h == 14 and m >= 45:
            phase = "观察阶段 · 等待确认"
        elif h == 14 and m >= 30:
            phase = "初筛阶段 · 开始选股"
        else:
            phase = "等待尾盘"
        st.info(f"尾盘时段 · {phase} · {now.strftime('%H:%M')}")

    # ── 3. 推荐系统：先给可研究候选，再给风险解释 ──
    _show_recommendations()

    # ── 4. 三个Tab：推荐选股 ｜ 风险排除 ｜ 策略扫描 ──
    tab0, tab1, tab2 = st.tabs(["推荐选股", "风险排除", "策略扫描"])

    with tab0:
        st.caption("按六维评分排序，反量化风险会自动扣分。这里不是买入指令，而是今日最值得研究的候选池。")
        _show_recommendations(compact=False)

    with tab1:
        st.caption("触发了反量化风险信号的股票，参与前请三思")
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
                        risky.append({
                            "code": cd, "name": s.get("name", cd),
                            "chg": s.get("change_pct", 0),
                            "risk": r.anti_quant.total_risk,
                            "level": r.anti_quant.risk_level,
                            "triggers": r.anti_quant.triggers[:3],
                        })
                if risky:
                    risky.sort(key=lambda x: x["risk"], reverse=True)
                    for item in risky[:12]:
                        lvl = item["level"]
                        border = "var(--red)" if lvl in ("高","极高") else "var(--amber)"
                        badge = "badge-high" if lvl in ("高","极高") else "badge-mid"
                        trig = " · ".join(item["triggers"][:3]) if item["triggers"] else ""
                        c = "#F04438" if item["chg"] > 0 else "#12B76A"
                        st.markdown(
                            f'<div class="card" style="border-left:3px solid {border};margin-bottom:8px">'
                            f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                            f'<div style="flex:1">'
                            f'<div style="font-weight:600;font-size:15px;color:var(--text)">{item["name"]}'
                            f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{item["code"]}</span></div>'
                            f'<div style="font-size:12px;color:var(--muted);margin-top:4px">{trig}</div></div>'
                            f'<div style="text-align:right;margin-left:12px">'
                            f'<div style="font-family:var(--mono);font-weight:700;font-size:15px;color:{c}">{item["chg"]:+.2f}%</div>'
                            f'<span class="badge {badge}" style="margin-top:4px">{lvl}风险</span></div>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
                        if st.button("查看", key=f"risk_{item['code']}"):
                            st.session_state["selected_stock"] = item["code"]
                            st.session_state["current_page"] = "stock_detail"
                            st.rerun()
                else:
                    st.success("当前未检测到显著风险股票，但仍需结合机会评分与分时承接判断。")
            finally:
                engine.close()
        except Exception as e:
            st.warning(f"风险扫描暂不可用: {e}")

    with tab2:
        st.caption("按策略模式筛选候选")
        choice = st.radio("策略", ["尾盘隔夜雷达", "短持延续雷达"],
                          horizontal=True, label_visibility="collapsed")
        if choice == "尾盘隔夜雷达":
            _show_overnight()
        else:
            _show_continuation()


def _show_recommendations(compact: bool = True):
    title = "今日选股推荐" if compact else "六维评分候选"
    st.markdown(
        f'<div class="sec-h">{title}</div>'
        f'<div class="page-kicker">机会分 = 热度 + 承接 + 题材 + 延续 + 策略匹配 - 反量化扣分</div>',
        unsafe_allow_html=True,
    )
    try:
        from src.data.realtime import get_top_stocks
        from src.scoring.engine import V6ScoringEngine

        # 推荐池不能只来自涨幅榜，否则会追高；成交额榜保证流动性，涨幅榜保证短线活跃。
        raw = []
        raw.extend(get_top_stocks(sort_field="amount", asc=False, limit=35) or [])
        raw.extend(get_top_stocks(sort_field="changepercent", asc=False, limit=35) or [])
        seen, stocks = set(), []
        for s in raw:
            cd = s.get("code", "")
            if cd and cd not in seen:
                seen.add(cd)
                stocks.append(s)

        engine = V6ScoringEngine()
        try:
            results = []
            for s in stocks[:55]:
                cd = s.get("code", "")
                if not cd:
                    continue
                r = engine.score_stock(cd, quote=s)
                if not r:
                    continue
                # 推荐系统保留“风险偏高”但降级展示；“不建议参与/已排除”不进入推荐池。
                if r.status_label in ("不建议参与", "已排除"):
                    continue
                results.append((s, r))

            results.sort(key=lambda x: x[1].total_score, reverse=True)
            limit = 3 if compact else 12
            if not results:
                st.info("当前没有达到推荐阈值的股票。可以看「风险排除」了解市场主要问题，或降低筛选阈值。")
                return

            for s, r in results[:limit]:
                _render_recommend_card(s, r, compact=compact)
        finally:
            engine.close()
    except Exception as e:
        st.warning(f"推荐系统暂不可用: {e}")


def _render_recommend_card(stock: dict, result, compact: bool = True):
    chg = stock.get("change_pct", 0)
    chg_color = "var(--red)" if chg > 0 else "var(--green)" if chg < 0 else "var(--muted)"
    risk = result.anti_quant.risk_level
    risk_cls = "badge-high" if risk in ("高", "极高") else "badge-mid" if risk == "中" else "badge-low"
    border = "var(--green)" if result.total_score >= 72 and risk in ("低", "中") else "var(--amber)" if result.total_score >= 60 else "var(--border)"
    triggers = " · ".join(result.anti_quant.triggers[:2]) if result.anti_quant.triggers else "暂无显著反量化触发项"
    strategies = " / ".join(result.matched_strategies[:2]) if result.matched_strategies else "综合短线"

    st.markdown(
        f'<div class="recommend-card" style="border-left:3px solid {border}">'
        f'<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start">'
        f'<div style="flex:1;min-width:0">'
        f'<div style="font-size:15px;font-weight:750;color:var(--text)">{result.name}'
        f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:7px">{result.code}</span></div>'
        f'<div style="font-size:12px;color:var(--muted);margin-top:4px">{strategies} · {result.status_label}</div>'
        f'</div>'
        f'<div style="text-align:right;min-width:82px">'
        f'<div style="font-family:var(--mono);font-size:18px;font-weight:800;color:var(--ai)">{result.total_score:.0f}</div>'
        f'<div style="font-family:var(--mono);font-size:12px;color:{chg_color}">{chg:+.2f}%</div>'
        f'</div></div>'
        f'<div class="score-row">'
        f'<span class="score-pill">热度 {result.heat.score:.0f}</span>'
        f'<span class="score-pill">承接 {result.support.score:.0f}</span>'
        f'<span class="score-pill">题材 {result.theme.score:.0f}</span>'
        f'<span class="score-pill">延续 {result.continuation.score:.0f}</span>'
        f'<span class="score-pill">策略 {result.strategy_match.score:.0f}</span>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:9px">'
        f'<div style="font-size:12px;color:var(--muted);line-height:1.45">{triggers}</div>'
        f'<span class="badge {risk_cls}">{risk}风险</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if not compact:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("查看个股", key=f"rec_view_{result.code}", use_container_width=True):
                st.session_state["selected_stock"] = result.code
                st.session_state["current_page"] = "stock_detail"
                st.rerun()
        with c2:
            if st.button("问 AI", key=f"rec_ai_{result.code}", use_container_width=True):
                st.session_state["selected_stock"] = result.code
                st.session_state["current_page"] = "ai_chat"
                st.session_state["qq"] = f"请对 {result.code} 做短线风险审查和持股周期判断"
                st.rerun()


def _show_overnight():
    st.markdown(
        '<div style="font-size:11px;color:var(--muted);margin-bottom:8px">'
        '条件：涨幅2.5-5.5% · 量比≥1.2 · 换手5-10% · MA多头 · 分时均线上方≥70%</div>',
        unsafe_allow_html=True,
    )
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
                candidates.append({
                    "code": cd, "name": s.get("name", cd),
                    "chg": s.get("change_pct", 0),
                    "match": m["match"], "status": m["status"],
                })
        if candidates:
            candidates.sort(key=lambda x: x["match"], reverse=True)
            for c in candidates[:10]:
                border = "var(--green)" if c["match"] >= 80 else "var(--amber)" if c["match"] >= 60 else "var(--border)"
                clr = "#F04438" if c["chg"] > 0 else "#12B76A"
                st.markdown(
                    f'<div class="card" style="border-left:3px solid {border};margin-bottom:8px">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div><span style="font-weight:600;font-size:15px;color:var(--text)">{c["name"]}</span>'
                    f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{c["code"]}</span></div>'
                    f'<div style="text-align:right"><div style="font-family:var(--mono);font-weight:700;font-size:15px;color:{clr}">{c["chg"]:+.2f}%</div>'
                    f'<div style="font-family:var(--mono);font-size:12px;color:var(--muted)">匹配{c["match"]:.0f}% · {c["status"]}</div></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("当前无符合尾盘隔夜条件的候选")
    except Exception as e:
        st.warning(f"扫描暂不可用: {e}")


def _show_continuation():
    st.markdown(
        '<div style="font-size:11px;color:var(--muted);margin-bottom:8px">'
        '条件：价>MA5>MA10 · 近5日涨幅≤15% · 量价健康 · 压力可控</div>',
        unsafe_allow_html=True,
    )
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
                if r and r.continuation.score >= 60 and r.status_label in ("可执行","等待确认"):
                    results.append({
                        "code": cd, "name": s.get("name", cd),
                        "chg": s.get("change_pct", 0),
                        "cont": r.continuation.score,
                        "status": r.status_label,
                    })
            if results:
                results.sort(key=lambda x: x["cont"], reverse=True)
                for c in results[:10]:
                    border = "var(--green)" if c["cont"] >= 75 else "var(--amber)"
                    clr = "#F04438" if c["chg"] > 0 else "#12B76A"
                    st.markdown(
                        f'<div class="card" style="border-left:3px solid {border};margin-bottom:8px">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'<div><span style="font-weight:600;font-size:15px;color:var(--text)">{c["name"]}</span>'
                        f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{c["code"]}</span></div>'
                        f'<div style="text-align:right"><div style="font-family:var(--mono);font-weight:700;font-size:15px;color:{clr}">{c["chg"]:+.2f}%</div>'
                        f'<div style="font-family:var(--mono);font-size:12px;color:var(--muted)">延续{c["cont"]:.0f} · {c["status"]}</div></div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("当前无符合短持延续条件的候选")
        finally:
            engine.close()
    except Exception as e:
        st.warning(f"扫描暂不可用: {e}")
