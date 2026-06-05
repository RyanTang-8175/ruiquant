"""研究审计：自动验证 AI、策略和用户执行。"""

from __future__ import annotations

from datetime import datetime

import streamlit as st


def render_lab_page():
    st.markdown(
        '<div class="audit-hero">'
        '<div class="audit-title">研究审计</div>'
        '<div class="audit-copy">每次 AI 给出“可观察 / 仅模拟 / 等待触发”，系统会自动生成假设并回放结果。你不需要天天填表，只需要偶尔反馈“有用、太晚、风险没提示”。</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    _risk_banner()
    _stats_bar()

    tab2, tab3, tab5, tab6, tab7, tab4, tab1 = st.tabs(["待审计", "审计结果", "归因画像", "评分对比", "策略探索", "一键反馈", "手动补录"])
    with tab2:
        _pending_panel()
    with tab3:
        _results_panel()
    with tab5:
        _attribution_panel()
    with tab6:
        _score_comparison_panel()
    with tab7:
        _strategy_explorer_panel()
    with tab4:
        _feedback_panel()
    with tab1:
        _create_plan()


def _risk_banner():
    try:
        from src.risk.user_state import get_user_risk_state

        state = get_user_risk_state()
        mode = state.get("mode", "normal")
        color = {
            "cooldown": "var(--red)",
            "caution": "var(--amber)",
            "normal": "var(--green)",
        }.get(mode, "var(--muted)")
        reasons = "；".join(state.get("reasons", [])[:3])
        st.markdown(
            f'<div class="card" style="border-left:3px solid {color};margin-bottom:10px">'
            f'<div style="font-weight:750;color:var(--text);font-size:15px">执行状态：{mode} · 风险分 {state.get("score", 0)}</div>'
            f'<div style="font-size:12px;color:var(--muted);line-height:1.55;margin-top:4px">{state.get("action_policy", "")}</div>'
            f'<div style="font-size:12px;color:var(--muted);line-height:1.55;margin-top:4px">{reasons}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        pass


def _stats_bar():
    try:
        from src.memory.analysis_memory import AnalysisMemory

        with AnalysisMemory() as memory:
            stats = memory.get_stats()
        cols = st.columns(4)
        cols[0].metric("待审计", stats["pending_backfills"])
        cols[1].metric("已完成", stats["completed_backfills"])
        cols[2].metric("+2%命中", f"{stats['hit_2pct_rate']}%")
        cols[3].metric("1日收益", f"{stats['avg_hold_1d_return']}%")
    except Exception as exc:
        st.info(f"研究审计数据库暂不可用: {exc}")


def _create_plan():
    st.markdown('<div class="page-kicker">手动补录只用于你自己临时想到的假设。AI 分析会自动进入研究审计，不需要手动复制。</div>', unsafe_allow_html=True)
    with st.form("lab_create_plan"):
        c1, c2 = st.columns(2)
        code = c1.text_input("股票代码", value=st.session_state.get("selected_stock", ""), placeholder="600900")
        name = c2.text_input("股票名称", placeholder="长江电力")
        source_type = st.selectbox("来源", ["manual", "ai_prediction", "strategy", "radar"], format_func=_source_label)
        strategy_name = st.text_input("策略/主题", placeholder="尾盘隔夜 / 电力防守 / AI风险审查")
        suggested_period = st.selectbox("验证周期", ["隔夜", "1-2天", "2-3天", "5天观察"])
        hypothesis = st.text_area("研究假设", placeholder="例如：电力防守方向有承接，回踩不破均价线时更适合观察。")
        entry_conditions = st.text_area("触发条件（每行一条）", placeholder="回踩不破分时均价线\n板块至少 3 只同步走强")
        invalidation_conditions = st.text_area("失效条件（每行一条）", placeholder="放量滞涨\n跌破昨日低点")
        stop_loss_rule = st.text_input("止损/退出规则", placeholder="亏损 2.5% 或跌破均价线 10 分钟不收回")
        c3, c4 = st.columns(2)
        risk_level = c3.selectbox("风险等级", ["低", "中", "高", "极高"], index=1)
        confidence_level = c4.selectbox("置信度", ["低", "中", "高"], index=1)
        submitted = st.form_submit_button("加入研究审计", use_container_width=True)

    if submitted:
        if not code.strip() or not hypothesis.strip() or not invalidation_conditions.strip():
            st.warning("至少填写股票代码、研究假设和失效条件。")
            return
        try:
            from src.memory.analysis_memory import AnalysisMemory
            from src.data.stock_list import resolve_stock_name

            final_code = code.strip()
            final_name = name.strip() or resolve_stock_name(final_code, final_code)
            with AnalysisMemory() as memory:
                vid = memory.create_verification(
                    source_type=source_type,
                    stock_code=final_code,
                    stock_name=final_name,
                    signal_date=datetime.now(),
                    strategy_name=strategy_name.strip() or source_type,
                    suggested_period=suggested_period,
                    hypothesis=hypothesis.strip(),
                    entry_conditions=_lines(entry_conditions),
                    invalidation_conditions=_lines(invalidation_conditions),
                    stop_loss_rule=stop_loss_rule.strip(),
                    risk_level=risk_level,
                    confidence_level=confidence_level,
                    allow_real_trade=False,
                )
            st.success(f"已加入研究审计 #{vid}。默认只作观察/模拟记录，不代表实盘建议。")
        except Exception as exc:
            st.warning(f"保存失败: {exc}")


def _pending_panel():
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("立即回放", use_container_width=True):
            try:
                from src.lab.backfill import backfill_pending_verifications

                result = backfill_pending_verifications()
                st.success(f"审计 {result['checked']} 条，完成 {result['completed']} 条，跳过 {result['skipped']} 条")
                if result.get("errors"):
                    st.caption("；".join(result["errors"][:3]))
            except Exception as exc:
                st.warning(f"回填失败: {exc}")
    with c2:
        st.caption("公开源可用时自动回放；iFinD 接入后复用同一入口，审计质量会更高。")

    try:
        from src.memory.analysis_memory import AnalysisMemory

        with AnalysisMemory() as memory:
            rows = memory.get_pending_verifications()
        if not rows:
            st.success("暂无待审计记录。去 AI 页分析具体股票，系统会自动生成。")
            return
        for row in rows:
            _plan_card(row, pending=True)
    except Exception as exc:
        st.warning(f"读取失败: {exc}")


def _results_panel():
    try:
        from src.memory.analysis_memory import AnalysisMemory

        with AnalysisMemory() as memory:
            rows = memory.get_verification_results()
        if not rows:
            st.info("暂无审计结果")
            return
        for row in rows:
            _plan_card(row, pending=False)
    except Exception as exc:
        st.warning(f"读取失败: {exc}")


def _feedback_panel():
    try:
        from src.memory.analysis_memory import AnalysisMemory

        with AnalysisMemory() as memory:
            rows = memory.get_verification_results()
        if not rows:
            st.info("先让 AI 分析一只股票，或手动补录一条研究假设。")
            return
        options = {f"#{r['id']} {r['stock_name']}({r['stock_code']}) · {r.get('strategy_name') or r.get('source_type')}": r["id"] for r in rows}
        label = st.selectbox("选择要反馈的审计记录", list(options.keys()))
        fb = st.radio(
            "执行结果",
            ["按计划操作", "未操作", "提前卖出", "延后持有", "没止损", "没止盈", "反向操作", "追高"],
            horizontal=False,
        )
        if st.button("提交反馈", use_container_width=True):
            with AnalysisMemory() as memory:
                memory.save_feedback(options[label], fb)
            st.success("已记录。这个反馈会进入用户风险状态，影响后续 AI 动作边界。")
    except Exception as exc:
        st.warning(f"反馈失败: {exc}")


def _plan_card(row: dict, pending: bool):
    code = row.get("stock_code", "")
    name = row.get("stock_name") or code
    risk = row.get("risk_level") or "未知"
    status = row.get("backfill_status") or "pending"
    border = "var(--amber)" if pending else "var(--green)" if status == "complete" else "var(--border)"
    entry = "；".join(row.get("entry_conditions") or []) or "未填写"
    invalid = "；".join(row.get("invalidation_conditions") or []) or "未填写"
    st.markdown(
        f'<div class="card" style="border-left:3px solid {border};margin-bottom:10px">'
        f'<div style="display:flex;justify-content:space-between;gap:10px">'
        f'<div><div style="font-weight:750;color:var(--text);font-size:15px">{name}'
        f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:7px">{code}</span></div>'
        f'<div style="font-size:12px;color:var(--muted);margin-top:2px">{_source_label(row.get("source_type"))} · {row.get("strategy_name") or ""} · {row.get("suggested_period") or ""}</div></div>'
        f'<div style="font-size:12px;color:var(--muted);text-align:right">风险 {risk}<br>{status}</div>'
        f'</div>'
        f'<div style="font-size:13px;color:var(--text);line-height:1.55;margin-top:8px">{row.get("hypothesis") or "无假设说明"}</div>'
        f'<div style="font-size:12px;color:var(--muted);line-height:1.55;margin-top:7px">触发：{entry}</div>'
        f'<div style="font-size:12px;color:var(--muted);line-height:1.55">失效：{invalid}</div>'
        f'<div style="font-size:12px;color:var(--muted);line-height:1.55">止损：{row.get("stop_loss_rule") or "未填写"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    backfills = row.get("backfills") or []
    if backfills:
        cols = st.columns(min(3, len(backfills)))
        for idx, bf in enumerate(backfills[:3]):
            with cols[idx]:
                st.metric(
                    f"T+{bf.get('day')}",
                    f"{bf.get('hold_1d') if bf.get('day') == 1 else bf.get('high')}%",
                    f"回撤 {bf.get('max_dd')}%",
                )


def _source_label(value: str | None) -> str:
    return {
        "manual": "手动研究",
        "ai_prediction": "AI自动审计",
        "strategy": "策略信号",
        "radar": "雷达候选",
    }.get(value or "", value or "未知")


def _lines(text: str) -> list[str]:
    return [line.strip(" -\t") for line in str(text or "").splitlines() if line.strip(" -\t")]


def _attribution_panel():
    """三类归因图表 — 策略效果 · AI准确率 · 用户执行纪律"""
    st.markdown('<div class="page-kicker">三类归因帮你回答：策略有用吗？AI说得准吗？你执行有没有偏离计划？</div>', unsafe_allow_html=True)

    try:
        from src.lab.attribution import compute_attribution
        attr = compute_attribution()
    except Exception as e:
        st.warning(f"归因分析暂不可用: {e}")
        return

    if attr.get("error"):
        st.warning(attr["error"])
        return
    if attr.get("total", 0) == 0:
        st.info("暂无验证数据。先创建验证计划并回填，归因数据会在这里展示。")
        return

    # ── 策略归因 ──
    st.markdown("### 策略效果")
    strategy = attr.get("strategy", {})
    best = strategy.get("best_strategy", {})
    if best.get("total", 0) > 0:
        st.metric("最佳策略", f"{best.get('name', '')}",
                  f"命中率 {best.get('hit_rate', 0)}% · {best.get('total', 0)}次验证")

    by_source = strategy.get("by_source", [])
    if by_source:
        cols = st.columns(len(by_source))
        for i, src in enumerate(by_source):
            with cols[i]:
                st.metric(f"{src['source']}({src['total']})",
                          f"{src['hit_rate']}%", "命中率")

    # ── AI 归因 ──
    st.markdown("### AI 准确率")
    ai = attr.get("ai", {})
    if ai.get("total", 0) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("AI 验证数", ai["total"])
        c2.metric("命中率", f"{ai.get('hit_rate', 0)}%")
        c3.metric("平均1日收益", f"{ai.get('avg_1d_return', 0)}%")
        st.caption(ai.get("verdict", ""))

    # ── 用户执行归因 ──
    st.markdown("### 执行纪律")
    user = attr.get("user", {})
    if user.get("total", 0) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("有反馈记录", user["total"])
        c2.metric("按计划执行", user.get("disciplined", 0))
        c3.metric("违规操作", user.get("undisciplined", 0))
        st.caption(user.get("verdict", ""))

        top_bad = user.get("top_bad_behaviors", [])
        if top_bad:
            st.markdown("**最常犯的错误**:  " + " · ".join(f"{b}({c}次)" for b, c in top_bad))


def _score_comparison_panel():
    st.markdown('<div class="page-kicker">用真实审计回放比较 iFinD 新评分与旧六维评分，不靠感觉决定谁更可信。</div>', unsafe_allow_html=True)
    try:
        from src.memory.analysis_memory import AnalysisMemory
        from src.research.evaluator import ResearchEvaluator

        with AnalysisMemory() as memory:
            rows = memory.get_verification_results()
        report = ResearchEvaluator().compare_score_systems(rows)
    except Exception as exc:
        st.warning(f"评分对比暂不可用: {exc}")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("iFinD 新评分", f"{report.get('ifind', {}).get('hit_rate', 0)}%", f"{report.get('ifind', {}).get('total', 0)} 条")
    c2.metric("旧六维评分", f"{report.get('legacy', {}).get('hit_rate', 0)}%", f"{report.get('legacy', {}).get('total', 0)} 条")
    c3.metric("当前胜出", report.get("winner", "tie"))
    st.caption(report.get("summary", "暂无结论"))


def _strategy_explorer_panel():
    st.markdown('<div class="page-kicker">轻量探索只记录参数覆盖、去重和风险预算，不做复杂回测，不触发实盘交易。</div>', unsafe_allow_html=True)
    with st.form("strategy_explorer_form"):
        c1, c2, c3 = st.columns(3)
        universe = c1.selectbox("股票池", ["A股", "沪深300", "中证500", "中证1000"])
        holding = c2.selectbox("观察周期", ["隔夜", "1-2天", "2-3天", "5天观察"], index=1)
        dimension = c3.text_input("扫描参数", value="risk_limit")
        raw_values = st.text_input("参数值", value="55,65,75")
        submitted = st.form_submit_button("开始探索", use_container_width=True)

    if not submitted:
        return
    try:
        from src.research.strategy import StrategyExplorer

        values = [_parse_value(v) for v in raw_values.split(",") if v.strip()]
        result = StrategyExplorer().sweep_filter_values(
            base_config={"universe": universe, "holding": holding},
            dimension=dimension.strip() or "risk_limit",
            values=values,
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("新增探索", result.get("executed", 0))
        c2.metric("重复跳过", result.get("skipped_duplicates", 0))
        c3.metric("覆盖维度", len(result.get("coverage", {})))
        for item in result.get("top", [])[:8]:
            st.caption(f"{item.get('config')} · score={item.get('score')} risk={item.get('risk')}")
    except Exception as exc:
        st.warning(f"策略探索失败: {exc}")


def _parse_value(value: str):
    value = value.strip()
    try:
        return int(value)
    except Exception:
        try:
            return float(value)
        except Exception:
            return value
