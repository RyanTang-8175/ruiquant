"""iFinD 研究工作台。"""

from __future__ import annotations

import html
import json
from datetime import datetime

import streamlit as st

from src.research.harness import ResearchHarness
from src.scoring.evidence import IFindEvidenceScorer
from src.data.market_board import board_label, board_scope_note


def render_research_page():
    st.markdown(
        '<div class="ai-hero">'
        '<div class="ai-hero-title">研究工作台</div>'
        '<div class="ai-hero-sub">把 iFinD 的行情、公告、K 线、基础数据和智能选股重新组织成一份可审计的研究底稿。</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    _provider_hint()
    code, requested = _query_bar()
    last = st.session_state.get("research_last") or {}
    if requested or (last and last.get("code") == code):
        _render_research(code)
    else:
        _empty_state()
        _workflow_panel("", {}, allowed_ids={"thematic_market"})


def _provider_hint():
    try:
        from src.data.providers.registry import provider_status

        status = provider_status()
        source = "iFinD" if status.get("provider") == "ifind" else "公开源"
        st.caption(f"当前数据源：{source} · {status.get('message', '')}")
    except Exception:
        pass


def _query_bar() -> tuple[str, bool]:
    st.session_state.setdefault("research_code", st.session_state.get("selected_stock", ""))
    st.session_state.setdefault("research_profile", "quick")
    st.session_state.setdefault("research_requested", False)

    c1, c2, c3 = st.columns([1.35, 0.45, 0.5])
    with c1:
        code = st.text_input(
            "股票代码",
            value=st.session_state.get("research_code", ""),
            placeholder="输入 6 位代码，如 600900",
            label_visibility="collapsed",
        )
    with c2:
        profile = st.selectbox("深度", ["quick", "deep"], index=0 if st.session_state.get("research_profile", "quick") == "quick" else 1, label_visibility="collapsed")
    with c3:
        run = st.button("生成", use_container_width=True)

    if run and code.strip():
        from src.data.stock_list import normalize_stock_code, resolve_stock_query

        matched = resolve_stock_query(code.strip(), fuzzy=True)
        resolved_code = normalize_stock_code((matched or {}).get("code", "") or code.strip())
        if not resolved_code:
            st.warning("未识别到有效 A 股代码或名称，研究任务没有调用 iFinD。")
            st.session_state["research_requested"] = False
            return "", False
        st.session_state["research_code"] = resolved_code
        st.session_state["research_profile"] = profile
        st.session_state["research_requested"] = True
        st.rerun()

    from src.data.stock_list import normalize_stock_code

    st.session_state["research_code"] = normalize_stock_code(code.strip())
    st.session_state["research_profile"] = profile

    return st.session_state.get("research_code", ""), bool(st.session_state.get("research_requested"))


def _render_research(code: str):
    profile = st.session_state.get("research_profile", "quick")
    force_refresh = st.button("刷新研究", use_container_width=True)
    should_generate = force_refresh or st.session_state.get("research_requested") or st.session_state.get("research_last") is None
    if should_generate:
        st.session_state["research_requested"] = False
        with st.spinner("正在生成研究底稿…"):
            try:
                harness = ResearchHarness()
                research = harness.company_research(code, profile=profile, force=force_refresh)
                if research.get("error"):
                    st.warning(research.get("message") or "研究任务未执行。")
                    st.session_state["research_last"] = research
                    return
                score = IFindEvidenceScorer().score(research)
                research["evidence_score"] = score
                research["legacy_score"] = _legacy_score(code)
                st.session_state["research_last"] = research
            except Exception as exc:
                st.error(f"研究生成失败: {exc}")
                return

    research = st.session_state.get("research_last") or {}
    score = research.get("evidence_score") or {}
    evidence = research.get("evidence") or {}
    summary_cards = research.get("summary_cards") or []

    _header(research, score)
    _summary_cards(summary_cards, research)
    _action_bar(code, research, score)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        ["证据", "评分", "情景", "SOP", "管理", "记忆", "审计", "原始"]
    )
    with tab1:
        _evidence_panel(evidence)
    with tab2:
        _score_panel(score, research)
    with tab3:
        _scenario_panel(research.get("scenario_report") or [])
    with tab4:
        _workflow_panel(code, research)
    with tab5:
        _strategy_management_panel(score, research)
    with tab6:
        _memory_panel()
    with tab7:
        _audit_panel(research, score)
    with tab8:
        _raw_panel(research)


def _header(research: dict, score: dict):
    quote = (research.get("evidence") or {}).get("行情") or {}
    name = quote.get("name") or research.get("code", "")
    code = research.get("code", "")
    board = board_label(code)
    price = float(quote.get("price") or 0.0)
    chg = float(quote.get("change_pct") or 0.0)
    color = "var(--red)" if chg > 0 else "var(--green)" if chg < 0 else "var(--muted)"
    st.markdown(
        f'<div class="card" style="margin-bottom:12px">'
        f'<div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start">'
        f'<div style="flex:1">'
        f'<div style="font-size:20px;font-weight:800;color:var(--text)">{html.escape(str(name))}</div>'
        f'<div style="font-size:11px;color:var(--muted);font-family:var(--mono)">{html.escape(str(code))} · {html.escape(board)}</div>'
        f'<div style="margin-top:6px">'
        f'<span class="badge badge-ai">机会 {score.get("opportunity_score", 0):.0f}</span> '
        f'<span class="badge" style="color:var(--red);border-color:var(--red)">风险 {score.get("risk_score", 0):.0f}</span> '
        f'<span class="badge" style="color:var(--ai);border-color:var(--ai)">置信度 {html.escape(str(score.get("confidence", "低")))}</span> '
        f'<span class="badge" style="color:var(--green);border-color:var(--green)">{html.escape(str(score.get("action", "只观察")))}</span>'
        f'</div>'
        f'</div>'
        f'<div style="text-align:right">'
        f'<div style="font-size:24px;font-weight:900;font-family:var(--mono);color:{color}">{price:.2f}</div>'
        f'<div style="font-size:14px;font-weight:700;font-family:var(--mono);color:{color}">{chg:+.2f}%</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption(board_scope_note(st.session_state.get("radar_candidate_scope", "主板优先")))


def _summary_cards(summary_cards: list, research: dict):
    if summary_cards:
        cols = st.columns(min(4, len(summary_cards)))
        for idx, card in enumerate(summary_cards[:4]):
            with cols[idx]:
                st.metric(card.get("title", ""), card.get("value", ""), card.get("note", ""))
    usage = research.get("usage") or {}
    calls = usage.get("calls") or {}
    if usage:
        st.caption(
            " · ".join(
                [
                    f"数据源 {usage.get('source', 'unknown')}",
                    f"调用 {sum(int(v) for v in calls.values()) if calls else 0}",
                    f"缓存 {usage.get('cache_entries', 0)}",
                    f"质量 {research.get('quality', 'unknown')}",
                    f"生成 {research.get('created_at', '')}",
                ]
            )
        )


def _action_bar(code: str, research: dict, score: dict):
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("送入审计", use_container_width=True):
            _save_to_audit(code, research, score)
    with c2:
        if st.button("去 AI 分析", use_container_width=True):
            st.session_state["selected_stock"] = code
            st.session_state["qq"] = f"请基于 iFinD 研究底稿，对 {code} 做证据化分析。优先引用研究底稿里的行情、公告、K线、基本面与智能选股，再给出机会/风险/条件/失效线。"
            st.session_state["current_page"] = "ai_chat"
            st.rerun()
    with c3:
        if st.button("回到雷达", use_container_width=True):
            st.session_state["current_page"] = "radar"
            st.rerun()


def _evidence_panel(evidence: dict):
    quote = evidence.get("行情") or {}
    bars = evidence.get("K线") or []
    announcements = evidence.get("公告") or []
    raw_basics = evidence.get("基础数据") or {}
    basics = {
        key: value
        for key, value in raw_basics.items()
        if not str(key).startswith("_")
        and value not in (None, "", 0, "--")
        and not str(value).startswith("unavailable")
    }
    smart = evidence.get("智能选股") or []

    st.markdown('<div class="sec-h">行情与基础证据</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        st.metric("价格", f"{float(quote.get('price') or 0):.2f}")
    with cols[1]:
        st.metric("涨跌幅", f"{float(quote.get('change_pct') or 0):+.2f}%")
    with cols[2]:
        st.metric("换手", f"{float(quote.get('turnover') or 0):.2f}%")
    with cols[3]:
        st.metric("成交额", f"{float(quote.get('amount') or 0) / 1e8:.1f} 亿")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec-h">公告</div>', unsafe_allow_html=True)
        if announcements:
            for item in announcements[:10]:
                title = item.get("title") or item.get("name") or "未命名公告"
                st.markdown(
                    f'<div class="card" style="margin-bottom:6px;padding:10px 12px">'
                    f'<div style="font-weight:650;color:var(--text)">{html.escape(str(title))}</div>'
                    f'<div style="font-size:11px;color:var(--muted);margin-top:4px">{html.escape(str(item.get("source", "")))}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("暂无公告证据")
    with c2:
        st.markdown('<div class="sec-h">智能选股</div>', unsafe_allow_html=True)
        if smart:
            for item in smart[:10]:
                st.markdown(
                    f'<div class="card" style="margin-bottom:6px;padding:10px 12px">'
                    f'<div style="font-weight:650;color:var(--text)">{html.escape(str(item.get("name") or item.get("code") or "候选"))}</div>'
                    f'<div style="font-size:11px;color:var(--muted);margin-top:4px">涨跌幅 {float(item.get("change_pct") or 0):+.2f}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("暂无智能选股命中")

    st.markdown('<div class="sec-h">K线摘要</div>', unsafe_allow_html=True)
    if bars:
        recent = bars[-4:]
        cols = st.columns(min(4, len(recent)))
        for idx, item in enumerate(recent):
            with cols[idx]:
                st.metric(
                    item.get("date") or f"最近{len(recent) - idx}日",
                    f"{float(item.get('close') or 0):.2f}",
                    f"{float(item.get('change_pct') or 0):+.2f}%",
                )
    else:
        st.info("暂无K线证据")

    st.markdown('<div class="sec-h">基础数据</div>', unsafe_allow_html=True)
    if basics:
        cols = st.columns(min(4, max(len(basics), 1)))
        for idx, (key, value) in enumerate(list(basics.items())[:4]):
            with cols[idx]:
                st.metric(str(key), str(value))
    else:
        st.info("暂无基础数据")
    warnings = [
        str(value)
        for key, value in raw_basics.items()
        if str(key).startswith("_") and value
    ]
    unavailable = sum(
        1
        for value in raw_basics.values()
        if str(value).startswith("unavailable")
    )
    if unavailable:
        st.caption(f"{unavailable} 个基础指标本次未取得，已从可用指标中排除。")
    for warning in warnings[:2]:
        st.warning(warning)


def _score_panel(score: dict, research: dict):
    dims = score.get("dimensions") or {}
    if not dims:
        st.info("暂无新评分结果")
        return

    legacy = research.get("legacy_score") or {}
    cols = st.columns(4)
    with cols[0]:
        st.metric("机会分", f"{score.get('opportunity_score', 0):.1f}")
    with cols[1]:
        st.metric("风险分", f"{score.get('risk_score', 0):.1f}")
    with cols[2]:
        st.metric("置信度", score.get("confidence", "低"))
    with cols[3]:
        st.metric("旧评分", f"{legacy.get('total_score', 0):.1f}" if legacy else "-")

    if legacy:
        diff = float(score.get("opportunity_score", 0) or 0) - float(legacy.get("total_score", 0) or 0)
        st.caption(
            f"新评分以 iFinD 证据为主线，旧六维评分保留作参考；当前差异 {diff:+.1f}。"
        )

    for key, title in [
        ("fund_heat", "资金热度"),
        ("support_quality", "承接质量"),
        ("catalyst", "信息催化"),
        ("fundamental_safety", "基本面安全"),
        ("crowding_risk", "拥挤风险"),
        ("data_confidence", "数据置信度"),
    ]:
        item = dims.get(key) or {}
        color = "var(--green)" if float(item.get("score", 0)) >= 65 else "var(--amber)" if float(item.get("score", 0)) >= 50 else "var(--red)"
        st.markdown(
            f'<div class="card" style="margin-bottom:6px;padding:10px 12px">'
            f'<div style="display:flex;justify-content:space-between;gap:10px">'
            f'<div style="font-weight:650;color:var(--text)">{title}</div>'
            f'<div style="font-family:var(--mono);font-weight:800;color:{color}">{float(item.get("score", 0)):.1f}</div>'
            f'</div>'
            f'<div style="font-size:11px;color:var(--muted);margin-top:4px;line-height:1.55">{html.escape(str(item.get("detail", "")))}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sec-h">证据摘要</div>', unsafe_allow_html=True)
    for line in score.get("evidence_summary") or []:
        st.markdown(f'- {html.escape(str(line))}')


def _scenario_panel(scenarios: list):
    if not scenarios:
        st.info("暂无情景推演")
        return
    st.markdown('<div class="sec-h">三情景推演</div>', unsafe_allow_html=True)
    for item in scenarios:
        st.markdown(
            f'<div class="card" style="margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;gap:10px">'
            f'<div style="font-weight:750;color:var(--text)">{html.escape(str(item.get("name", "")))}</div>'
            f'<div style="font-family:var(--mono);font-weight:800;color:var(--ai)">{html.escape(str(item.get("possibility", "")))}</div>'
            f'</div>'
            f'<div style="font-size:12px;color:var(--muted);line-height:1.55;margin-top:6px">证据：{html.escape(str(item.get("evidence", "")))}</div>'
            f'<div style="font-size:12px;color:var(--text);line-height:1.55;margin-top:4px">触发：{html.escape(str(item.get("trigger", "")))}</div>'
            f'<div style="font-size:12px;color:var(--text);line-height:1.55;margin-top:4px">失效：{html.escape(str(item.get("failure", "")))}</div>'
            f'<div style="font-size:11px;color:var(--muted);margin-top:4px">观察周期：{html.escape(str(item.get("watch_window", "")))}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _workflow_panel(
    code: str,
    research: dict,
    allowed_ids: set[str] | None = None,
):
    """运行文件化金融研究 SOP；只有明确点击才会调用 Harness/iFinD。"""
    from src.research.workflow import ResearchWorkflowRunner

    st.markdown('<div class="sec-h">金融研究 SOP</div>', unsafe_allow_html=True)
    st.caption("工作流负责阶段、来源、质量门和草稿；所有产物必须人工复核，不会自动交易或发布。")

    try:
        runner = ResearchWorkflowRunner()
        workflows = runner.registry.list()
        if allowed_ids is not None:
            workflows = [
                item for item in workflows if item.get("id") in allowed_ids
            ]
    except Exception as exc:
        st.error(f"研究工作流加载失败: {exc}")
        return

    if not workflows:
        st.info("暂无可用研究工作流")
        return

    options = [item["id"] for item in workflows]
    by_id = {item["id"]: item for item in workflows}
    selected = st.selectbox(
        "研究流程",
        options=options,
        format_func=lambda value: by_id[value]["name"],
        key=(
            "research_workflow_id_theme"
            if allowed_ids is not None
            else "research_workflow_id"
        ),
    )
    default_subject = (
        f"{code} 最新财报"
        if selected == "earnings_review"
        else f"{code} 深度研究"
        if selected == "company_diligence"
        else st.session_state.get("research_workflow_theme", "")
    )
    subject = st.text_input(
        "研究主题 / 报告期",
        value=default_subject,
        placeholder="例如：电力央企改革 / 600900 2025年报",
        key=f"research_workflow_subject_{selected}",
    )
    if selected == "thematic_market":
        st.session_state["research_workflow_theme"] = subject

    preview = runner.preview(selected)
    _workflow_preview(preview)

    run_clicked = st.button(
        "运行 SOP",
        key=f"run_workflow_{selected}",
        use_container_width=True,
        disabled=not bool(subject.strip()),
    )
    if run_clicked:
        with st.spinner("正在执行研究 SOP，并核对来源与质量门…"):
            try:
                result = runner.run(
                    workflow_id=selected,
                    subject=subject,
                    code="" if selected == "thematic_market" else code,
                    seed=research if selected in {"company_diligence", "earnings_review"} else None,
                )
                st.session_state["research_workflow_last"] = result
            except Exception as exc:
                st.error(f"研究 SOP 执行失败: {exc}")
                return

    result = st.session_state.get("research_workflow_last") or {}
    if result and result.get("workflow_id") == selected:
        _render_workflow_result(runner, result)


def _workflow_preview(preview: dict):
    st.markdown(
        f'<div class="card" style="margin:8px 0 10px;padding:12px">'
        f'<div style="font-weight:750;color:var(--text)">{html.escape(str(preview.get("name", "")))}</div>'
        f'<div style="font-size:12px;color:var(--muted);line-height:1.55;margin-top:4px">'
        f'{html.escape(str(preview.get("description", "")))}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    budget = preview.get("quota_budget") or {}
    if budget:
        st.caption(
            "本次最大调用预算：" +
            " · ".join(f"{key} ≤ {value}" for key, value in budget.items())
        )
    st.caption("阶段：" + " → ".join(preview.get("stages") or []))


def _render_workflow_result(runner, result: dict):
    passed = bool((result.get("quality_gate") or {}).get("passed"))
    status_label = {
        "draft": "待人工复核",
        "blocked_quota_overrun": "额度超限，已阻断",
        "blocked_missing_evidence": "证据不足，已阻断",
    }.get(result.get("status"), str(result.get("status") or "待检查"))
    status_color = "var(--green)" if passed else "var(--red)"
    review = result.get("review") or {}

    st.markdown(
        f'<div class="card" style="margin:10px 0;border-left:3px solid {status_color}">'
        f'<div style="display:flex;justify-content:space-between;gap:12px">'
        f'<div><div style="font-size:16px;font-weight:800;color:var(--text)">'
        f'{html.escape(str(result.get("workflow_name", "")))}</div>'
        f'<div style="font-size:11px;color:var(--muted);margin-top:3px">'
        f'{html.escape(str(result.get("run_id", "")))}</div></div>'
        f'<div style="font-weight:750;color:{status_color}">{status_label}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-h">执行阶段</div>', unsafe_allow_html=True)
    stages = result.get("stages") or []
    for start in range(0, len(stages), 3):
        stage_row = stages[start:start + 3]
        stage_cols = st.columns(len(stage_row))
        for index, stage in enumerate(stage_row):
            with stage_cols[index]:
                st.metric(stage.get("name", ""), stage.get("status", "pending"))

    st.markdown('<div class="sec-h">质量门</div>', unsafe_allow_html=True)
    quality = result.get("quality_gate") or {}
    for item in quality.get("checks") or []:
        mark = "通过" if item.get("passed") else "缺失"
        st.markdown(f'- **{mark}** · {html.escape(str(item.get("name", "")))}')
    if quality.get("missing"):
        st.error("证据缺口：" + "、".join(str(item) for item in quality["missing"]))

    st.markdown('<div class="sec-h">来源账本</div>', unsafe_allow_html=True)
    sources = result.get("source_ledger") or []
    if sources:
        st.dataframe(
            [
                {
                    "编号": item.get("source_id"),
                    "类型": item.get("category"),
                    "证据": item.get("title"),
                    "来源": item.get("source"),
                    "时间": item.get("published_at"),
                    "状态": item.get("status"),
                    "链接": item.get("url"),
                }
                for item in sources
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("当前没有可追溯来源")

    quota = result.get("quota") or {}
    st.markdown('<div class="sec-h">iFinD 额度</div>', unsafe_allow_html=True)
    delta = quota.get("delta") or {}
    st.caption(
        "实际调用增量：" +
        (json.dumps(delta, ensure_ascii=False) if any(delta.values()) else "0（复用缓存或输入底稿）")
    )
    if not quota.get("within_budget", True):
        violations = quota.get("violations") or []
        st.error(
            "本次调用超过工作流预算："
            + "；".join(
                f"{item.get('endpoint')} 实际 {item.get('actual')} / 预算 {item.get('budget')}"
                for item in violations
            )
        )

    st.markdown('<div class="sec-h">研究草稿</div>', unsafe_allow_html=True)
    artifacts = result.get("artifacts") or {}
    for key, value in artifacts.items():
        with st.expander(str(key), expanded=key.endswith("note")):
            if isinstance(value, str):
                st.markdown(value)
            else:
                st.json(value)

    st.markdown('<div class="sec-h">人工复核</div>', unsafe_allow_html=True)
    st.caption(f"当前状态：{review.get('status', 'pending')}。只有这里的明确操作可以改变签核状态。")
    notes = st.text_input(
        "复核备注",
        value=str(review.get("notes") or ""),
        key=f"workflow_review_notes_{result.get('run_id')}",
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "标记通过",
            key=f"workflow_approve_{result.get('run_id')}",
            use_container_width=True,
            disabled=not passed,
        ):
            updated = runner.review(result["run_id"], "approved", notes)
            st.session_state["research_workflow_last"] = updated
            st.rerun()
    with c2:
        if st.button(
            "退回补证据",
            key=f"workflow_reject_{result.get('run_id')}",
            use_container_width=True,
        ):
            updated = runner.review(result["run_id"], "rejected", notes)
            st.session_state["research_workflow_last"] = updated
            st.rerun()
    with c3:
        if st.button(
            "发送给 AI",
            key=f"workflow_ai_{result.get('run_id')}",
            use_container_width=True,
        ):
            compact = {
                "workflow_id": result.get("workflow_id"),
                "subject": result.get("subject"),
                "status": result.get("status"),
                "quality_gate": result.get("quality_gate"),
                "source_ledger": sources[:12],
                "artifacts": artifacts,
            }
            st.session_state["qq"] = (
                "请基于以下已经运行的金融研究SOP草稿继续分析。必须引用来源编号，"
                "质量门未通过时只说明证据缺口，不得补猜，也不得声称已经人工批准：\n"
                + json.dumps(compact, ensure_ascii=False, default=str)[:9000]
            )
            st.session_state["current_page"] = "ai_chat"
            st.rerun()


def _strategy_management_panel(score: dict, research: dict):
    try:
        from src.research.strategy import StrategyGovernor

        metrics = {
            "opportunity_score": score.get("opportunity_score", 0),
            "risk_score": score.get("risk_score", 100),
            "confidence": score.get("confidence", "低"),
            "hit_rate": 0,
            "drawdown": max(0, score.get("risk_score", 100) - 60) / 2,
            "environment_match": research.get("quality") in {"medium", "high"},
        }
        decision = StrategyGovernor().decide(metrics)
    except Exception as exc:
        st.warning(f"四档管理暂不可用: {exc}")
        return

    color = {
        "继续持有": "var(--green)",
        "进入观察": "var(--ai)",
        "主动降权": "var(--amber)",
        "正式下线": "var(--red)",
    }.get(decision.get("tier"), "var(--muted)")
    st.markdown(
        f'<div class="card" style="border-left:3px solid {color}">'
        f'<div style="font-size:18px;font-weight:850;color:{color}">{html.escape(str(decision.get("tier", "")))}</div>'
        f'<div style="font-size:13px;color:var(--text);line-height:1.6;margin-top:6px">{html.escape(str(decision.get("reason", "")))}</div>'
        f'<div style="font-size:12px;color:var(--muted);line-height:1.6;margin-top:6px">动作：{html.escape(" / ".join(decision.get("allowed_actions") or []))}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption("四档管理只用于研究和模拟验证，不会触发自动交易。")


def _raw_panel(research: dict):
    st.markdown('<div class="sec-h">原始证据</div>', unsafe_allow_html=True)
    st.caption("这里展示的是裁剪后的本地研究底稿，便于排查 AI 结论是否有证据来源。")
    st.code(json.dumps(research, ensure_ascii=False, indent=2, default=str)[:12000], language="json")


def _memory_panel():
    try:
        memory = ResearchHarness().knowledge_context(limit=8)
    except Exception as exc:
        st.warning(f"研究记忆不可用: {exc}")
        return

    runs = memory.get("runs") or []
    insights = memory.get("insights") or []

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<div class="sec-h">最近研究</div>', unsafe_allow_html=True)
        if runs:
            for item in runs[:8]:
                st.markdown(
                    f'<div class="card" style="margin-bottom:6px;padding:10px 12px">'
                    f'<div style="font-weight:650;color:var(--text)">{html.escape(str(item.get("title") or item.get("code") or "研究"))}</div>'
                    f'<div style="font-size:11px;color:var(--muted);margin-top:4px">'
                    f'{html.escape(str(item.get("quality", "unknown")))} · {html.escape(", ".join(item.get("evidence_keys") or []))}'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("暂无研究记录")
    with c2:
        st.markdown('<div class="sec-h">可复用洞察</div>', unsafe_allow_html=True)
        if insights:
            for item in insights[:8]:
                st.markdown(
                    f'<div class="card" style="margin-bottom:6px;padding:10px 12px">'
                    f'<div style="font-weight:650;color:var(--text)">{html.escape(str(item.get("topic", "")))}</div>'
                    f'<div style="font-size:11px;color:var(--muted);margin-top:4px;line-height:1.55">{html.escape(str(item.get("summary", "")))}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("暂无可复用洞察")


def _audit_panel(research: dict, score: dict):
    st.markdown('<div class="page-kicker">把当前研究底稿送入审计，后续会在“审计”页回放结果。默认只做观察/模拟，不构成实盘建议。</div>', unsafe_allow_html=True)
    with st.form("research_audit_form"):
        c1, c2 = st.columns(2)
        code = c1.text_input("股票代码", value=research.get("code", ""))
        name = c2.text_input("股票名称", value=(research.get("evidence") or {}).get("行情", {}).get("name", ""))
        strategy_name = st.text_input("策略/主题", value=f"iFinD研究底稿 · {st.session_state.get('research_profile', 'quick')}")
        suggested_period = st.selectbox("验证周期", ["隔夜", "1-2天", "2-3天", "5天观察"], index=1)
        hypothesis = st.text_area(
            "研究假设",
            value=f"{code} 当前机会分 {score.get('opportunity_score', 0):.1f}、风险分 {score.get('risk_score', 0):.1f}，可围绕 {score.get('action', '只观察')} 做后续验证。",
        )
        entry = st.text_area(
            "触发条件（每行一条）",
            value="数据置信度保持中以上\n公告与行情保持一致\n板块没有明显退潮",
        )
        invalid = st.text_area(
            "失效条件（每行一条）",
            value="数据源失联\n放量滞涨\n信息催化被证伪",
        )
        stop = st.text_input("止损/退出规则", value="若次日回撤超过 3% 或信息催化失效，降低关注。")
        c3, c4 = st.columns(2)
        risk_level = c3.selectbox("风险等级", ["低", "中", "高", "极高"], index=1 if score.get("risk_score", 0) < 70 else 2)
        confidence_level = c4.selectbox("置信度", ["低", "中", "高"], index=1 if score.get("confidence") == "中" else 2 if score.get("confidence") == "高" else 0)
        submitted = st.form_submit_button("加入研究审计", use_container_width=True)

    if submitted:
        _save_to_audit(code, research, score, name=name, strategy_name=strategy_name, suggested_period=suggested_period,
                       hypothesis=hypothesis, entry=entry, invalid=invalid, stop=stop,
                       risk_level=risk_level, confidence_level=confidence_level)


def _save_to_audit(code: str, research: dict, score: dict, **overrides):
    try:
        from src.memory.analysis_memory import AnalysisMemory
        from src.data.stock_list import resolve_stock_name

        final_code = str(code or research.get("code", "")).strip()
        final_name = str(overrides.get("name") or (research.get("evidence") or {}).get("行情", {}).get("name") or resolve_stock_name(final_code, final_code))
        with AnalysisMemory() as memory:
            vid = memory.create_verification(
                source_type="ai_prediction",
                stock_code=final_code,
                stock_name=final_name,
                signal_date=datetime.now(),
                strategy_name=overrides.get("strategy_name") or f"iFinD研究底稿 · {research.get('profile', 'quick')}",
                suggested_period=overrides.get("suggested_period") or "1-2天",
                hypothesis=overrides.get("hypothesis") or f"{final_code} 的 iFinD 研究底稿已生成，可继续验证。",
                entry_conditions=_lines(overrides.get("entry")) or [
                    "数据置信度保持中以上",
                    "公告与行情保持一致",
                ],
                invalidation_conditions=_lines(overrides.get("invalid")) or [
                    "数据源失联",
                    "放量滞涨",
                ],
                stop_loss_rule=overrides.get("stop") or "若次日回撤超过 3% 或信息催化失效，降低关注。",
                risk_level=overrides.get("risk_level") or ("高" if score.get("risk_score", 0) >= 70 else "中"),
                confidence_level=overrides.get("confidence_level") or score.get("confidence", "中"),
                allow_real_trade=False,
            )
        st.success(f"已加入研究审计 #{vid}")
    except Exception as exc:
        st.warning(f"加入研究审计失败: {exc}")


def _empty_state():
    st.info("输入股票代码后，生成研究底稿。也可以从雷达页点击“研究”直接跳过来。")


def _lines(text: str) -> list[str]:
    return [line.strip(" -\t") for line in str(text or "").splitlines() if line.strip(" -\t")]


def _legacy_score(code: str) -> dict:
    try:
        from src.scoring.engine import V6ScoringEngine

        with V6ScoringEngine() as engine:
            result = engine.score_stock(code)
        if not result:
            return {}
        data = result.to_dict() if hasattr(result, "to_dict") else {}
        return {
            "total_score": float(data.get("total_score", 0) or 0),
            "status_label": data.get("status_label", ""),
            "risk_level": data.get("risk_level", ""),
            "anti_quant": data.get("anti_quant", {}),
        }
    except Exception:
        return {}
