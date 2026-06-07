"""
全局模糊搜索 —— 股票代码/名称/拼音首字母 均可搜索
"""

import streamlit as st
from src.data.stock_list import (
    fetch_all_stocks,
    normalize_stock_code,
    normalize_stock_text,
    resolve_stock_query,
)


@st.cache_data(ttl=3600)
def _load_all_stocks():
    return fetch_all_stocks()


def fuzzy_search(keyword: str, limit: int = 20) -> list:
    """模糊搜索：代码/名称"""
    stocks = _load_all_stocks()
    if not keyword or not keyword.strip():
        return []

    kw = normalize_stock_text(keyword)
    scored = []
    for s in stocks:
        code = normalize_stock_code(s.get("code", ""))
        name = normalize_stock_text(s.get("name", ""))
        score = 0

        if kw == code:
            score = 100
        elif code.startswith(kw):
            score = 90
        elif kw in code:
            score = 70

        if kw == name:
            score = max(score, 95)
        elif name.startswith(kw):
            score = max(score, 85)
        elif kw in name:
            score = max(score, 65)

        # 逐字匹配
        if len(kw) >= 2 and all(c in name for c in kw):
            score = max(score, 50)

        if len(kw) >= 4 and len(kw) == len(name):
            mismatches = sum(a != b for a, b in zip(kw, name))
            if mismatches == 1:
                score = max(score, 60)

        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:limit]]


def resolve_search_code(query: str) -> str:
    """只返回已验证代码，禁止把原始搜索文本直接送进数据源。"""
    direct = normalize_stock_code(query)
    if direct:
        return direct
    result = resolve_stock_query(query, stocks=_load_all_stocks(), fuzzy=True)
    return normalize_stock_code((result or {}).get("code", ""))


def render_search_bar(placeholder: str = "搜索代码或名称 如 茅台 / 600519",
                      key: str = "search") -> str:
    """全局搜索栏 —— 带下拉建议 + GO按钮

    返回: selected_code 或 ""
    用法:
        code = render_search_bar()
        if code:
            st.session_state["selected_stock"] = code
            st.session_state["current_page"] = "stock_detail"
            st.rerun()
    """
    c1, c2 = st.columns([5, 1])
    with c1:
        query = st.text_input(
            "股票搜索", placeholder=placeholder,
            key=f"q_{key}", label_visibility="collapsed",
        )
    with c2:
        go = st.button("GO", key=f"go_{key}",
                       use_container_width=True, type="primary")

    # 实时下拉建议
    if query and len(query.strip()) >= 1:
        try:
            results = fuzzy_search(query.strip(), limit=6)
            if results:
                st.caption(f"{len(results)} 只匹配")
                for i, s in enumerate(results):
                    chg = s.get("change_pct", 0) or 0
                    clr = "#F04438" if chg > 0 else "#12B76A" if chg < 0 else "#9AA4B2"
                    st.markdown(
                        f'<div class="sr" style="padding:7px 0">'
                        f'<div class="inf" style="margin-left:0">'
                        f'<div class="nm">{s["name"]}</div>'
                        f'<div class="cd">{s["code"]}</div></div>'
                        f'<div class="ch" style="color:{clr}">{chg:+.2f}%</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        f"打开 {s['name']}({s['code']})",
                        key=f"hit_{key}_{s['code']}_{i}",
                        use_container_width=True,
                    ):
                        return s["code"]
        except Exception:
            pass

    if go and query and query.strip():
        try:
            code = resolve_search_code(query.strip())
            if not code:
                st.warning("未识别到有效 A 股代码或名称，请从搜索结果中选择。")
            return code
        except Exception:
            st.warning("股票目录暂不可用，请输入有效的 6 位 A 股代码。")
            return ""

    return ""
