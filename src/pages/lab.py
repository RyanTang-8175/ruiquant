"""短线实验室：验证 AI、策略和用户执行。"""

from __future__ import annotations

from datetime import datetime

import streamlit as st


def render_lab_page():
    st.markdown('<div class="sec-h">短线实验室</div>', unsafe_allow_html=True)
    st.caption("把想法变成可验证计划。先记录条件，再回填结果，最后复盘执行偏差。")

    _risk_banner()
    _stats_bar()

    tab1, tab2, tab3, tab4 = st.tabs(["新建计划", "待验证", "复盘结果", "执行反馈"])
    with tab1:
        _create_plan()
    with tab2:
        _pending_panel()
    with tab3:
        _results_panel()
    with tab4:
        _feedback_panel()


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
        cols[0].metric("待回填", stats["pending_backfills"])
        cols[1].metric("已完成", stats["completed_backfills"])
        cols[2].metric("+2%命中", f"{stats['hit_2pct_rate']}%")
        cols[3].metric("1日收益", f"{stats['avg_hold_1d_return']}%")
    except Exception as exc:
        st.info(f"实验室数据库暂不可用: {exc}")


def _create_plan():
    st.markdown('<div class="page-kicker">记录时必须写条件。没有失效条件的想法，不能进入验证。</div>', unsafe_allow_html=True)
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
        submitted = st.form_submit_button("加入实验室验证", use_container_width=True)

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
            st.success(f"已加入验证 #{vid}。默认只作观察/模拟记录，不代表实盘建议。")
        except Exception as exc:
            st.warning(f"保存失败: {exc}")


def _pending_panel():
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("立即回填", use_container_width=True):
            try:
                from src.lab.backfill import backfill_pending_verifications

                result = backfill_pending_verifications()
                st.success(f"检查 {result['checked']} 条，完成 {result['completed']} 条，跳过 {result['skipped']} 条")
                if result.get("errors"):
                    st.caption("；".join(result["errors"][:3]))
            except Exception as exc:
                st.warning(f"回填失败: {exc}")
    with c2:
        st.caption("公开数据源可用时自动回填；iFinD 接入后会复用同一入口。")

    try:
        from src.memory.analysis_memory import AnalysisMemory

        with AnalysisMemory() as memory:
            rows = memory.get_pending_verifications()
        if not rows:
            st.success("暂无待回填计划")
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
            st.info("暂无复盘结果")
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
            st.info("先创建一条验证计划。")
            return
        options = {f"#{r['id']} {r['stock_name']}({r['stock_code']}) · {r.get('strategy_name') or r.get('source_type')}": r["id"] for r in rows}
        label = st.selectbox("选择要反馈的计划", list(options.keys()))
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
        "ai_prediction": "AI分析",
        "strategy": "策略信号",
        "radar": "雷达候选",
    }.get(value or "", value or "未知")


def _lines(text: str) -> list[str]:
    return [line.strip(" -\t") for line in str(text or "").splitlines() if line.strip(" -\t")]
