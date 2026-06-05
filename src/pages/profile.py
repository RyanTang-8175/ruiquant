"""我的"""

import streamlit as st
from src.config import get_setting, save_settings


def render_profile_page():
    st.markdown('<div class="sec-h">账户</div>', unsafe_allow_html=True)
    try:
        from src.trading.engine import TradingEngine
        with TradingEngine() as e: s = e.get_stats()
    except: s = {}
    c1, c2, c3 = st.columns(3)
    c1.metric("交易", s.get("total_trades", 0))
    wr = s.get("win_rate", 0)
    c2.metric("胜率", f"{wr:.0%}" if s.get("total_trades") else "-")
    pl = s.get("profit_loss_ratio", 0)
    c3.metric("盈亏比", f"{pl:.2f}" if s.get("total_trades") else "-")

    st.markdown('<div class="sec-h">系统状态</div>', unsafe_allow_html=True)
    _system_status()

    st.markdown('<div class="sec-h">iFinD 额度</div>', unsafe_allow_html=True)
    _ifind_usage_panel()

    st.markdown('<div class="sec-h">偏好</div>', unsafe_allow_html=True)
    try:
        from src.memory.user_profile import get_profile
        p = get_profile()
        style = st.radio("风格", ["自动","激进","稳健","保守"],
                         index=["自动","激进","稳健","保守"].index(p.get("style","自动")),
                         horizontal=True, key="pf_st")
        if style != p.get("style"): p.set("style", style); st.rerun()
        cap = st.text_input("资金", value=p.get("capital",""), placeholder="如：1万", key="pf_cp")
        if cap != p.get("capital",""): p.set("capital", cap); st.rerun()
        top = p.top_stocks(5)
        if top:
            st.caption("常看: " + " | ".join(f"{n}({c})" for c, n, _ in top))
    except: pass

    st.markdown('<div class="sec-h">AI / 数据源配置</div>', unsafe_allow_html=True)
    cur_k = get_setting("api_key","DEEPSEEK_API_KEY","")
    cur_u = get_setting("base_url","DEEPSEEK_BASE_URL","https://api.deepseek.com")
    cur_m = get_setting("model","DEEPSEEK_MODEL","deepseek-chat")
    cur_dp = get_setting("data_provider","ALPHAEYE_DATA_PROVIDER","open")
    cur_ifind_refresh = get_setting("ifind_refresh_token","IFIND_REFRESH_TOKEN","")
    with st.form("cfg"):
        nk = st.text_input("API Key", value=cur_k, type="password", placeholder="sk-...")
        nu = st.text_input("Base URL", value=cur_u)
        nm = st.text_input("Model", value=cur_m)
        ndp = st.selectbox("数据源", ["open", "ifind"], index=0 if cur_dp != "ifind" else 1)
        ifr = st.text_input("iFinD refresh_token", value=cur_ifind_refresh, type="password")
        if st.form_submit_button("保存", use_container_width=True, type="primary"):
            save_settings({"api_key":nk,"base_url":nu,"model":nm,
                           "data_provider":ndp,
                           "ifind_refresh_token":ifr,
                           "phone":get_setting("phone","","")})
            try:
                from src.data.providers.registry import clear_provider_cache

                clear_provider_cache()
            except Exception:
                pass
            st.success("已保存"); st.rerun()

    if st.button("退出登录", use_container_width=True):
        save_settings({"phone":"","api_key":"","base_url":"","model":""})
        st.session_state["logged_in"] = False; st.rerun()


def _system_status():
    try:
        from src.ai.chat import AIChat

        ai_status = AIChat.provider_status()
        c0, c00 = st.columns(2)
        c0.metric("AI模型", "DeepSeek" if ai_status.get("ready") else "本地兜底")
        c00.metric("模型名", ai_status.get("model") or "-")
        st.caption(f"AI状态：{ai_status.get('base_url', '-')} · {ai_status.get('message', '')}")
    except Exception as exc:
        st.caption(f"AI状态不可用: {exc}")

    try:
        from src.data.providers.registry import provider_status

        status = provider_status()
        c1, c2 = st.columns(2)
        c1.metric("数据源", status.get("provider", "open"))
        c2.metric("状态", "可用" if status.get("ready") else "待配置")
        if status.get("message"):
            st.caption(status["message"])
    except Exception as exc:
        st.caption(f"数据源状态不可用: {exc}")

    try:
        from src.risk.user_state import get_user_risk_state

        state = get_user_risk_state()
        c3, c4 = st.columns(2)
        c3.metric("执行状态", state.get("mode", "-"))
        c4.metric("风险分", state.get("score", 0))
        st.caption(state.get("action_policy", ""))
    except Exception:
        pass


def _ifind_usage_panel():
    try:
        from src.data.providers.registry import get_provider, provider_status

        provider = get_provider()
        status = provider_status()
        usage = provider.usage_stats() if hasattr(provider, "usage_stats") else {}
        calls = usage.get("calls") or {}
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("数据源", status.get("provider", "open"))
        c2.metric("今日调用", usage.get("today_calls", 0))
        c3.metric("本月调用", usage.get("month_calls", 0))
        c4.metric("缓存命中", f"{float(usage.get('cache_hit_rate', 0) or 0):.0%}")
        st.caption(
            " · ".join(
                [
                    f"可用 {status.get('ready')}",
                    f"本轮调用 {sum(int(v) for v in calls.values()) if calls else 0}",
                    f"缓存 {usage.get('cache_entries', 0)}",
                    f"接口 {len(calls)}",
                    f"最近 {usage.get('last_call_at') or '-'}",
                    f"说明 {status.get('message', '')}",
                ]
            )
        )
        month_by_endpoint = usage.get("month_by_endpoint") or {}
        if month_by_endpoint:
            st.markdown('<div class="page-kicker">本月接口分布</div>', unsafe_allow_html=True)
            for endpoint, count in sorted(month_by_endpoint.items(), key=lambda x: x[1], reverse=True)[:8]:
                st.caption(f"{endpoint}: {count}")
    except Exception as exc:
        st.caption(f"iFinD 额度面板暂不可用: {exc}")

    try:
        from src.memory.conversation_memory import ConversationMemory

        memory = ConversationMemory()
        try:
            sessions = memory.list_recent_threads(limit=100)
        finally:
            memory.close()
        st.caption(f"AI 研究记忆：{len(sessions)} 个会话已入库")
    except Exception:
        pass
