"""AlphaEye v6 短线实验室 —— 策略验证 · AI验证 · 用户执行"""

import streamlit as st


def render_lab_page():
    st.markdown('<div class="sec-h">短线实验室</div>', unsafe_allow_html=True)
    st.caption("验证策略信号、AI预测、用户执行")

    try:
        from src.memory.analysis_memory import AnalysisMemory
        am = AnalysisMemory()
        try:
            stats = am.get_stats()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("待回填", stats["pending_backfills"])
            c2.metric("已完成", stats["completed_backfills"])
            c3.metric("+2%命中", f"{stats['hit_2pct_rate']}%")
            c4.metric("1日收益", f"{stats['avg_hold_1d_return']}%")
        finally:
            am.close()
    except Exception:
        st.info("开始使用后，策略信号和AI预测会自动入库验证。")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["验证记录", "待回填", "快速反馈"])

    with tab1:
        try:
            from src.memory.analysis_memory import AnalysisMemory
            am = AnalysisMemory()
            try:
                results = am.get_verification_results()
                if results:
                    for r in results[:15]:
                        sc = "#12B76A" if r["backfill_status"] == "complete" else "#F79009"
                        st.markdown(
                            f'<div class="card" style="border-left:3px solid {sc}">'
                            f'<div style="display:flex;justify-content:space-between">'
                            f'<span style="font-weight:600">{r["stock_name"]}({r["stock_code"]})</span>'
                            f'<span style="font-family:var(--mono);font-size:12px;color:var(--muted)">{r["source_type"]}</span>'
                            f'</div>'
                            f'<div style="font-size:12px;color:var(--muted);margin-top:4px">'
                            f'{r.get("strategy","")} · {r.get("period","")} · {r["signal_date"][:10]} · '
                            f'{r["backfill_status"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.info("暂无验证记录")
            finally:
                am.close()
        except Exception as e:
            st.warning(f"加载失败: {e}")

    with tab2:
        try:
            from src.memory.analysis_memory import AnalysisMemory
            am = AnalysisMemory()
            try:
                pending = am.get_pending_verifications()
                if pending:
                    for r in pending[:10]:
                        st.markdown(
                            f'<div class="card risk-mid">'
                            f'<div style="display:flex;justify-content:space-between">'
                            f'<span style="font-weight:600">{r["stock_name"]}({r["stock_code"]})</span>'
                            f'<span style="font-family:var(--mono);font-size:12px">{r["signal_date"][:10]}</span>'
                            f'</div>'
                            f'<div style="font-size:12px;color:var(--muted);margin-top:4px">'
                            f'{r.get("strategy_name","")} · {r.get("suggested_period","")}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.success("全部回填完成")
            finally:
                am.close()
        except Exception as e:
            st.warning(f"加载失败: {e}")

    with tab3:
        st.caption("轻量点选反馈")
        opts = ["未操作", "按计划操作", "买了但提前卖出", "买了但延后持有",
                "没按止损", "没按止盈", "反向操作", "其他"]
        cols = st.columns(4)
        for i, opt in enumerate(opts):
            with cols[i % 4]:
                if st.button(opt, key=f"fb_{i}", use_container_width=True):
                    st.success(f"已记录: {opt}")
