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

    tab2, tab3, tab5, tab6, tab7, tab4, tab1, tab8 = st.tabs(
        ["待审计", "审计结果", "归因画像", "评分对比", "策略探索", "一键反馈", "手动补录", "仓位计算"]
    )
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
    with tab8:
        _kelly_calculator()


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


def _kelly_calculator():
    """凯利公式仓位计算器 — 输入胜率/盈亏比/本金，输出建议仓位和资金曲线"""
    st.markdown(
        '<div class="page-kicker">凯利公式: f = p - q/r，其中 p=胜率 q=1-p r=盈亏比。'
        '半凯利(f/2)更保守，适合实盘。记住：盈亏比远比胜率重要，仓位管理远比单次收益重要。</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        win_rate = st.number_input("胜率", 0.0, 1.0, 0.55, 0.01, help="你过去盈利交易的比例，0.55=55%")
        profit_ratio = st.number_input("预期收益率", 0.01, 2.0, 0.10, 0.01, help="单笔盈利的预期收益比例，0.10=10%")
    with c2:
        loss_ratio = st.number_input("止损比例", 0.01, 1.0, 0.05, 0.01, help="单笔亏损的最大止损比例，0.05=5%")
        capital = st.number_input("初始本金", 1000, 100000000, 100000, 1000)
    with c3:
        kelly_coef = st.selectbox("凯利系数", [0.25, 0.5, 0.75, 1.0], index=1,
                                   help="半凯利(0.5)更保守，适合实盘")
        max_pos = st.number_input("最大仓位上限", 0.1, 1.0, 0.3, 0.05, help="单票最大仓位占本金比例")
        n_trades = st.number_input("模拟交易次数", 10, 500, 100, 10)

    # 计算
    q = 1 - win_rate
    r = profit_ratio / loss_ratio if loss_ratio > 0 else 0
    raw_f = (win_rate * r - q) / r if r > 0 else 0
    raw_f = max(raw_f, 0)
    kelly_position = min(raw_f * kelly_coef, max_pos)

    # 资金曲线模拟
    import random
    random.seed(42)
    balance = capital
    curve = [capital]
    for _ in range(n_trades):
        bet = balance * kelly_position
        if random.random() < win_rate:
            balance += bet * profit_ratio
        else:
            balance -= bet * loss_ratio
        curve.append(balance)

    final_capital = balance
    total_return = (final_capital / capital - 1) * 100 if capital > 0 else 0
    max_dd = 0
    peak = capital
    for v in curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("原始凯利仓位", f"{raw_f*100:.1f}%")
    col2.metric("建议仓位", f"{kelly_position*100:.1f}%",
                f"系数×{kelly_coef}" if kelly_coef < 1 else None)
    col3.metric("最终资金", f"{final_capital:,.0f}",
                f"{total_return:+.1f}%")
    col4.metric("最大回撤", f"{max_dd:.1f}%")

    # 资金曲线图
    st.markdown('<div class="page-kicker">资金曲线模拟（随机种子42，每次结果相同）</div>', unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=curve, mode="lines",
            line=dict(color="#002FA7", width=1.5),
            fill="tozeroy", fillcolor="rgba(0,47,167,0.06)",
            name="资金曲线",
        ))
        fig.add_hline(y=capital, line_dash="dash", line_color="#9AA4B2", opacity=0.5,
                       annotation_text=f"初始 {capital:,.0f}")
        fig.update_layout(
            height=240, margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, title="交易次数"),
            yaxis=dict(showgrid=True, gridcolor="#E7EEF6", title="资金"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except Exception:
        st.line_chart(curve, height=200)

    # 白话结论
    if kelly_position <= 0:
        advice = "当前参数下凯利仓位为0或负——说明你的策略没有正期望值。除非提高胜率或盈亏比，否则不应该下注。"
    elif kelly_position < 0.1:
        advice = f"建议仓位 {kelly_position*100:.1f}%，偏保守。小仓位试错，先验证胜率和盈亏比是否真实。"
    elif kelly_position < 0.25:
        advice = f"建议仓位 {kelly_position*100:.1f}%，适中。仓位合理，严格执行止损纪律是关键。"
    else:
        advice = f"建议仓位 {kelly_position*100:.1f}%，偏高。虽然数学上合理，但注意最大回撤 {max_dd:.1f}%，实盘时建议减半执行。"
    st.info(f"📊 {advice}")
