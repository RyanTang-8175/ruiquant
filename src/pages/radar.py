"""AlphaEye v6 雷达页 —— 风险优先 + 策略模式"""

import streamlit as st
from datetime import datetime


def render_radar_page():
    now = datetime.now()
    hour, minute = now.hour, now.minute
    is_tail = (hour == 14 and minute >= 30) or (hour == 15 and minute == 0)

    st.markdown('<div class="sec-h">今日短线环境</div>', unsafe_allow_html=True)

    from src.data.realtime import get_market_overview
    ov = get_market_overview()
    indices = ov.get("indices", [])

    if indices:
        main = next((i for i in indices if "上证" in i.get("name", "")), indices[0])
        chg = main.get("change_pct", 0)
        if chg > 0.5:
            env, color, msg = "偏暖", "#12B76A", "大盘稳定，短线环境尚可"
        elif chg > -0.5:
            env, color, msg = "中性", "#F79009", "大盘震荡，精选机会"
        elif chg > -1.5:
            env, color, msg = "偏冷", "#F04438", "大盘偏弱，控制仓位"
        else:
            env, color, msg = "谨慎", "#F04438", "大盘走弱，减少操作"

        c1, c2 = st.columns([1, 2])
        c1.metric("环境", env)
        c2.caption(msg)

    if is_tail:
        phase = "确认阶段" if minute >= 50 else ("观察阶段" if minute >= 45 else "初筛阶段")
        st.info(f"尾盘时段 · {phase} · {now.strftime('%H:%M')}")

    st.markdown("---")

    # ── 风险雷达 ──
    st.markdown('<div class="sec-h">风险雷达</div>', unsafe_allow_html=True)
    st.caption("先看风险，再看机会。")

    try:
        from src.scoring.engine import V6ScoringEngine
        from src.data.realtime import get_top_stocks

        engine = V6ScoringEngine()
        try:
            stocks = get_top_stocks(sort_field="amount", asc=False, limit=30)
            high_risk = []
            for s in (stocks or []):
                code = s.get("code", "")
                if not code: continue
                r = engine.score_stock(code, quote=s)
                if r and r.anti_quant.total_risk >= 40:
                    high_risk.append({
                        "code": code, "name": s.get("name", code),
                        "risk": r.anti_quant.total_risk,
                        "level": r.anti_quant.risk_level,
                        "triggers": r.anti_quant.triggers[:3],
                    })

            if high_risk:
                high_risk.sort(key=lambda x: x["risk"], reverse=True)
                for item in high_risk[:8]:
                    lvl = item["level"]
                    cls = "risk-high" if lvl in ("高", "极高") else "risk-mid"
                    badge = "badge-high" if lvl in ("高", "极高") else "badge-mid"
                    trig = " · ".join(item["triggers"][:2]) if item["triggers"] else ""
                    st.markdown(
                        f'<div class="card {cls}">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'<div><span style="font-weight:600;font-size:15px;color:var(--text)">{item["name"]}</span>'
                        f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{item["code"]}</span></div>'
                        f'<span class="badge {badge}">{lvl}风险</span></div>'
                        f'<div style="font-size:11px;color:var(--muted);margin-top:6px">{trig}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.success("当前未检测到高风险股票")
        finally:
            engine.close()
    except Exception as e:
        st.warning(f"风险扫描暂不可用: {e}")

    st.markdown("---")

    # ── 策略模式 ──
    st.markdown('<div class="sec-h">策略模式</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="card" style="border-left:3px solid var(--amber)">'
            '<div style="font-weight:700;font-size:15px;color:var(--text)">尾盘隔夜雷达</div>'
            '<div style="font-size:12px;color:var(--muted);margin:6px 0">一夜持股法 · 目标次日+2%</div>'
            f'<div style="font-size:11px;color:var(--weak)">今日: {"高" if is_tail else "等待尾盘"}</div>'
            '</div>', unsafe_allow_html=True)

    with c2:
        st.markdown(
            '<div class="card" style="border-left:3px solid var(--ai)">'
            '<div style="font-weight:700;font-size:15px;color:var(--text)">短持延续雷达</div>'
            '<div style="font-size:12px;color:var(--muted);margin:6px 0">隔夜→1-3天短持</div>'
            '</div>', unsafe_allow_html=True)

    # ── 快速审查 ──
    st.markdown('<div class="sec-h">快速审查</div>', unsafe_allow_html=True)
    code = st.text_input("股票代码", placeholder="如 600519", key="radar_in", label_visibility="collapsed")
    if code and st.button("风险审查", key="btn_risk", use_container_width=True):
        try:
            engine = V6ScoringEngine()
            try:
                r = engine.score_stock(code.strip())
                if r:
                    d = r.to_dict()
                    st.markdown(f"### {d['name']}({d['code']})")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("机会分", f"{d['total_score']}/100")
                    c2.metric("风险", d['risk_level'])
                    c3.metric("状态", d['status_label'])

                    st.markdown("**六维评分**")
                    for name, score, desc in [
                        ("热度", d['heat']['score'], "资金关注"),
                        ("承接", d['support']['score'], "上涨承接"),
                        ("题材", d['theme']['score'], "主线匹配"),
                        ("延续", d['continuation']['score'], "可持续"),
                        ("策略", d['strategy_match']['score'], "模式匹配"),
                    ]:
                        color = "#12B76A" if score >= 65 else "#F79009" if score >= 45 else "#F04438"
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                            f'border-bottom:1px solid var(--border)">'
                            f'<span style="color:var(--text)">{name}</span>'
                            f'<span style="color:var(--muted);font-size:12px">{desc}</span>'
                            f'<span style="font-family:var(--mono);font-weight:700;color:{color}">{score:.0f}</span>'
                            f'</div>', unsafe_allow_html=True)

                    if d['anti_quant'].get('triggers'):
                        st.markdown("**反量化触发**")
                        for t in d['anti_quant']['triggers']:
                            st.markdown(f"- {t}")
                else:
                    st.warning("无法获取评分，请检查股票代码")
            finally:
                engine.close()
        except Exception as e:
            st.error(f"评分失败: {e}")
