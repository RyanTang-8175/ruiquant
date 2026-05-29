"""
我的页面
"""

import streamlit as st
from src.config import get_setting, save_settings


def render_profile_page():
    """渲染我的页面"""
    st.markdown("## 我的")

    # 交易统计
    st.subheader("交易统计")
    try:
        from src.trading.engine import TradingEngine
        with TradingEngine() as engine:
            stats = engine.get_stats()
    except Exception:
        stats = {}

    m1, m2, m3 = st.columns(3)
    m1.metric("总交易", f"{stats.get('total_trades', 0)} 笔", border=True)
    win_rate = stats.get('win_rate', 0)
    m2.metric("胜率", f"{win_rate:.1%}" if stats.get('total_trades') else "N/A", border=True)
    pl = stats.get('profit_loss_ratio', 0)
    m3.metric("盈亏比", f"{pl:.2f}" if stats.get('total_trades') else "N/A", border=True)

    st.markdown("---")

    # AI 配置
    st.subheader("AI 模型配置")
    st.caption("支持 DeepSeek / OpenAI / 智谱 / 月之暗面等 OpenAI 兼容接口")

    current_key = get_setting("api_key", "DEEPSEEK_API_KEY", "")
    current_url = get_setting("base_url", "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    current_model = get_setting("model", "DEEPSEEK_MODEL", "deepseek-chat")

    with st.form("ai_config"):
        new_key = st.text_input("API Key", value=current_key, type="password")
        new_url = st.text_input("API 地址", value=current_url)
        new_model = st.text_input("模型名称", value=current_model)

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("保存", use_container_width=True, type="primary"):
                save_settings({"api_key": new_key, "base_url": new_url, "model": new_model})
                if "ai_chat" in st.session_state:
                    del st.session_state["ai_chat"]
                st.success("保存成功！")
                st.rerun()
        with col2:
            if st.form_submit_button("测试连接", use_container_width=True):
                if not new_key:
                    st.error("请填写 API Key")
                else:
                    with st.spinner("测试中..."):
                        try:
                            from openai import OpenAI
                            client = OpenAI(api_key=new_key, base_url=new_url)
                            resp = client.chat.completions.create(
                                model=new_model,
                                messages=[{"role": "user", "content": "你好，请回复'连接成功'"}],
                                max_tokens=20,
                            )
                            st.success(f"连接成功！{resp.choices[0].message.content}")
                        except Exception as e:
                            st.error(f"连接失败: {e}")

    st.markdown("---")

    # 关于
    with st.expander("关于"):
        st.write("**RuiQuant** v3.0 - 个人 A 股 AI 研究助手")
        st.write("技术栈: Python + Streamlit + DeepSeek + 东方财富API")
        st.write("GitHub: https://github.com/RyanTang-8175/ruiquant")

    st.markdown("---")

    # 退出登录
    if st.button("退出登录", type="secondary"):
        st.session_state["logged_in"] = False
        st.session_state.pop("phone", None)
        st.rerun()
