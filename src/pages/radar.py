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
        html = "".join(
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
            f'<div class="idx-strip" style="margin-bottom:0">{html}</div></div>',
            unsafe_allow_html=True)

    h, m = now.hour, now.minute
    if 14 <= h <= 15:
        phase = ("确认阶段·不追高" if m >= 50 else "观察阶段" if m >= 45 else "初筛阶段" if m >= 30 else "等待尾盘")
        st.info(f"尾盘 · {phase} · {now.strftime('%H:%M')}")

    # ── Tab ──
    tab0, tab1, tab2 = st.tabs(["推荐选股", "风险排除", "策略扫描"])
    with tab0:
        _render_filter_and_results()
    with tab1:
        _show_risk_scan()
    with tab2:
        _show_strategy_scan()


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
                    am = AnalysisMemory()
                    am.create_verification("strategy", code, name, datetime.now(), suggested_period="1-2天")
                    am.close()
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
        from src.data.stock_list import CACHE_FILE, fetch_all_stocks

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
    lookup.update({
        "600519": "贵州茅台",
        "000858": "五粮液",
        "000568": "泸州老窖",
        "002304": "洋河股份",
        "600809": "山西汾酒",
        "600559": "老白干酒",
        "000596": "古井贡酒",
        "600779": "水井坊",
        "603369": "今世缘",
        "603198": "迎驾贡酒",
        "600900": "长江电力",
        "601985": "中国核电",
        "003816": "中国广核",
        "600025": "华能水电",
        "600011": "华能国际",
        "600886": "国投电力",
        "600674": "川投能源",
        "002015": "协鑫能科",
        "000883": "湖北能源",
        "600023": "浙能电力",
        "002475": "立讯精密",
        "688981": "中芯国际",
        "688036": "传音控股",
        "603501": "豪威集团",
        "600703": "三安光电",
        "688256": "寒武纪",
        "688008": "澜起科技",
        "688012": "中微公司",
        "688396": "华润微",
        "300782": "卓胜微",
    })
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
