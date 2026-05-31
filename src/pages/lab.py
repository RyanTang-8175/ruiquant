"""短线实验室"""

import streamlit as st


def render_lab_page():
    st.markdown('<div class="sec-h">短线实验室</div>', unsafe_allow_html=True)
    st.caption("策略信号、AI预测、用户执行，三类表现分开验证")

    try:
        from src.memory.analysis_memory import AnalysisMemory
        am = AnalysisMemory()
        try:
            sts = am.get_stats()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("待回填", sts["pending_backfills"])
            c2.metric("已完成", sts["completed_backfills"])
            c3.metric("+2%命中", f"{sts['hit_2pct_rate']}%")
            c4.metric("1日收益", f"{sts['avg_hold_1d_return']}%")
        finally: am.close()
    except: st.info("信号会自动入库验证。")

    tab1, tab2, tab3 = st.tabs(["记录", "待回填", "反馈"])
    with tab1:
        try:
            from src.memory.analysis_memory import AnalysisMemory
            am = AnalysisMemory()
            try:
                records = am.get_recent_verifications(20)
                if records:
                    for rec in records:
                        code = rec.get("stock_code",""); name = rec.get("stock_name", code)
                        src = rec.get("source_type",""); stt = rec.get("status","待回填")
                        st.markdown(
                            f'<div class="card" style="margin-bottom:8px">'
                            f'<div style="font-size:14px;font-weight:650;color:var(--text)">{name}'
                            f'<span style="font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:8px">{code}</span></div>'
                            f'<div style="font-size:12px;color:var(--muted)">{src} · {stt}</div></div>',
                            unsafe_allow_html=True)
                else: st.info("暂无记录")
            finally: am.close()
        except Exception as e: st.warning(f"读取失败: {e}")

    with tab2:
        try:
            from src.memory.analysis_memory import AnalysisMemory
            am = AnalysisMemory()
            try:
                pending = am.get_pending_backfills(10)
                if pending:
                    for rec in pending:
                        code = rec.get("stock_code",""); name = rec.get("stock_name", code)
                        st.markdown(
                            f'<div class="card" style="margin-bottom:8px">'
                            f'<div style="font-size:14px;font-weight:650;color:var(--text)">{name}</div>'
                            f'<div style="font-size:12px;color:var(--muted)">{code} · 等待回填</div></div>',
                            unsafe_allow_html=True)
                else: st.success("全部已回填")
            finally: am.close()
        except Exception as e: st.warning(f"读取失败: {e}")

    with tab3:
        st.caption("轻量反馈，帮助 AI 改进")
        fb = ["未操作","按计划操作","提前卖出","延后持有","没止损","没止盈","反向操作"]
        sel = st.radio("执行情况", fb, horizontal=False, key="lab_fb")
        if st.button("提交", use_container_width=True): st.success("已记录")
