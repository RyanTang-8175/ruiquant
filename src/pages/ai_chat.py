"""移动端 AI 助手页 — 折叠对话"""

from __future__ import annotations
import html, re
from datetime import datetime
import streamlit as st
from src.ai.chat import AIChat


def _quick_tasks(code: str) -> list:
    if code:
        return [
            ("深度审查", f"全面分析 {code} 风险与机会",
             f"请对 {code} 做完整深度分析。先调行情/评分/技术三个工具，然后按风险→机会→条件→周期顺序输出。每个专业术语附白话解释。最后用一句话总结。"),
            ("能不能买", f"{code} 现在能参与吗",
             f"请直接判断 {code} 现在能不能参与。回答：能/不能/有条件能。列出参与前必须满足的 3 个条件和 3 个离场红线。不要长篇大论，只给关键判断和数字。"),
            ("持股多久", f"{code} 适合持有多久",
             f"判断 {code} 适合隔夜、1-2天还是2-3天。给出继续持有条件、离场条件、明早要盯的 3 个关键点。"),
            ("反量化扫描", f"{code} 有被收割风险吗",
             f"对 {code} 做完整反量化扫描：尾盘诱多/高位接盘/分时脉冲/放量滞涨/板块背离。每条用大白话解释它是什么、为什么触发、对散户意味着什么。"),
        ]
    return [
        ("今日选股", "今天有哪些短线机会",
         "基于市场环境和六维评分框架，推荐今天值得研究的 3-5 个短线方向或板块，说明逻辑和风险。"),
        ("大盘解读", "今天适合做短线吗",
         "分析今天大盘和板块环境。适不适合做短线？什么板块强？什么在退潮？给出操作纪律提醒。"),
        ("交易复盘", "我的交易表现如何",
         "复盘我最近的模拟交易。区分策略胜率、AI 准确度、我的执行偏差。数据不足时告诉我需要什么。"),
        ("学习模式", "教我理解一个概念",
         "用新手能听懂的方式解释：1)反量化风险是什么，散户怎么识别 2)尾盘隔夜策略的核心逻辑。每个概念配实例说明。"),
    ]


def render_ai_chat_page():
    ai = _get_ai()
    history = ai.get_history()
    selected_code = st.session_state.get("selected_stock", "")

    # 搜索
    from src.ui.search import render_search_bar
    code = render_search_bar(key="ai")
    if code:
        st.session_state["selected_stock"] = code
        st.session_state["current_page"] = "stock_detail"; st.rerun()

    # 状态条
    env = _market_label()
    stock = selected_code or "未选择"
    st.markdown(
        f'<div style="display:flex;gap:8px;margin:6px 0 10px;font-size:12px;color:#5D6B7C">'
        f'<span>市场 {env}</span><span>|</span>'
        f'<span>股票 {stock}</span><span>|</span>'
        f'<span>对话 {len(history)} 条</span></div>',
        unsafe_allow_html=True)

    if selected_code:
        st.markdown(
            f'<div style="background:rgba(36,107,254,0.04);border:1px solid rgba(36,107,254,0.10);'
            f'border-radius:10px;padding:8px 12px;margin-bottom:10px;font-size:13px;color:#17212F">'
            f'当前 <strong>{selected_code}</strong> · AI 自动注入评分、K线和反量化详情</div>',
            unsafe_allow_html=True)

    # ── 快捷任务 ──
    st.markdown('<div class="sec-h">快捷任务</div>', unsafe_allow_html=True)
    tasks = _quick_tasks(selected_code)
    for row in range(2):
        cols = st.columns(2)
        for i in range(2):
            title, subtitle = tasks[row * 2 + i][:2]
            with cols[i]:
                if st.button(f"{title}\n{subtitle}", key=f"qt_{row}_{i}",
                             use_container_width=True):
                    st.session_state["qq"] = tasks[row * 2 + i][2]
                    st.rerun()

    st.markdown("---")

    # 快捷提问
    if "qq" in st.session_state:
        q = st.session_state.pop("qq")
        with st.spinner("分析中..."):
            ai.chat(_with_context(q))
        st.rerun()

    # ═══════════════════════════════════
    # 对话记录：每条 AI 回复可折叠，自动提取标题
    # ═══════════════════════════════════
    if history:
        st.markdown('<div class="sec-h">对话</div>', unsafe_allow_html=True)
        # 默认展开最新2条
        for idx, item in enumerate(history):
            is_recent = idx >= len(history) - 2
            _render_item(item, idx, is_recent=is_recent)
    else:
        st.markdown(
            '<div style="text-align:center;padding:24px 12px;color:#5D6B7C;font-size:13px">'
            '点击快捷任务开始，或直接输入问题<br>'
            f'{"可以问「分析 " + selected_code + "」" if selected_code else "可以问「今天适合做短线吗」"}'
            '</div>', unsafe_allow_html=True)

    # 输入
    ph = f"问 {selected_code} 的任何问题..." if selected_code else "输入股票代码或直接提问..."
    u = st.chat_input(ph)
    if u:
        with st.spinner("分析中..."):
            ai.chat(_with_context(u))
        st.rerun()

    # 底部
    if history:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("清空全部", use_container_width=True):
                ai.clear_history(); st.rerun()
        with c2:
            if st.button("保存", use_container_width=True, type="primary"):
                ai.save_to_disk(); st.success("已保存")
        with c3:
            if st.button("逐条删除", use_container_width=True):
                st.session_state["ai_mgr"] = not st.session_state.get("ai_mgr", False)
                st.rerun()

    # 逐条删除
    if st.session_state.get("ai_mgr") and history:
        st.markdown('<div class="sec-h">选择删除</div>', unsafe_allow_html=True)
        kills = []
        for idx, item in enumerate(history):
            q = str(item.get("question", ""))[:50]
            t = str(item.get("timestamp", ""))[:16] if item.get("timestamp") else ""
            if st.checkbox(f"[{idx}] {q} ({t})", key=f"ck_{idx}"):
                kills.append(idx)
        if kills:
            if st.button(f"删除 {len(kills)} 条", use_container_width=True):
                for i in sorted(kills, reverse=True):
                    ai.delete_history_item(i)
                st.session_state["ai_mgr"] = False; st.rerun()
        if st.button("取消", use_container_width=True):
            st.session_state["ai_mgr"] = False; st.rerun()


# ══════════════════════════════
# 单条对话渲染
# ══════════════════════════════

def _render_item(item: dict, idx: int, is_recent: bool = False):
    """渲染一条对话：用户消息气泡 + AI 可折叠回复"""
    q_text = html.escape(str(item.get("question", "")))
    a_text = str(item.get("answer", ""))
    title = _extract_title(a_text)

    # 用户消息：紧凑气泡
    st.markdown(
        f'<div style="background:rgba(36,107,254,0.05);border-radius:8px;'
        f'padding:6px 10px;margin:6px 0 4px 16px;font-size:13px;'
        f'color:#17212F;line-height:1.45">{q_text}</div>',
        unsafe_allow_html=True)

    # AI 回复：折叠 expander
    with st.expander(title, expanded=is_recent):
        st.markdown(_fmt(a_text), unsafe_allow_html=True)
        tools = item.get("tools_used", [])
        if tools:
            nm = {"get_stock_quote":"行情","get_technical_analysis":"技术",
                  "get_scoring_result":"评分","get_market_snapshot":"大盘",
                  "get_news":"新闻","get_positions":"持仓","get_kline_data":"K线",
                  "get_watchlist":"选股","get_financial_data":"财务"}
            st.caption(" · ".join(nm.get(t, t) for t in tools))


def _extract_title(text: str) -> str:
    """从 AI 回复中提取折叠标题"""
    # 取第一个 ## 或 ### 标题
    m = re.search(r'#{2,3}\s+(.+?)(?:\n|<br>)', text)
    if m:
        return m.group(1).strip()[:50]

    # 取第一个 **粗体**
    m = re.search(r'\*\*(.+?)\*\*', text)
    if m:
        return m.group(1).strip()[:50]

    # 取第一行有意义文字
    first = text.strip().split("\n")[0]
    first = re.sub(r'<[^>]+>', '', first)
    first = re.sub(r'[*#]', '', first).strip()
    if len(first) > 5:
        return first[:50]

    return "分析结果"


# ══════════════════════════════
# 工具函数
# ══════════════════════════════

def _get_ai() -> AIChat:
    if "aic" not in st.session_state:
        ai = AIChat(); ai.load_from_disk()
        st.session_state["aic"] = ai
    return st.session_state["aic"]


def _market_label() -> str:
    try:
        from src.data.realtime import get_market_overview
        indices = get_market_overview().get("indices", [])
        if not indices: return "?"
        main = next((i for i in indices if "上证" in i.get("name", "")), indices[0])
        chg = main.get("change_pct", 0)
        return "暖" if chg > 0.5 else "震" if chg > -0.5 else "冷" if chg > -1.5 else "危"
    except: return "?"


def _with_context(text: str) -> str:
    stock_code = _extract_code(text) or st.session_state.get("selected_stock", "")
    parts = [text]
    if stock_code:
        try:
            from src.scoring.engine import V6ScoringEngine
            with V6ScoringEngine() as e:
                ctx = e.build_ai_context(stock_code)
            parts.append(f"\n\n[系统: {stock_code} 六维评分+K线]\n{ctx}")
        except: pass
        try:
            from src.news.fetcher import fetch_stock_news
            news = fetch_stock_news(stock_code, limit=3)
            if news:
                parts.append("\n[新闻]\n" + "\n".join(f"- {n.get('title','')}" for n in news[:3]))
        except: pass
    else:
        gctx = _build_group_context(text)
        if gctx: parts.append(f"\n[系统: 行业/概念候选]\n{gctx}")
    return "\n".join(parts)


def _build_group_context(text: str) -> str:
    from src.data.stock_list import CONCEPTS, SW_INDUSTRY
    groups = []
    n = text.replace("，"," ").replace("、"," ").replace("/"," ")
    for name, codes in SW_INDUSTRY.items():
        if name in n: groups.append(("行业", name, codes))
    for name, codes in CONCEPTS.items():
        if name in n: groups.append(("概念", name, codes))
    aliases = {"半导体":("概念","半导体芯片",CONCEPTS.get("半导体芯片",[])),
               "芯片":("概念","半导体芯片",CONCEPTS.get("半导体芯片",[])),
               "电力":("概念","电力",CONCEPTS.get("电力",[]))}
    for a, g in aliases.items():
        if a in n and g[2]: groups.append(g)
    dedup, seen = [], set()
    for g in groups:
        k = (g[0], g[1])
        if k not in seen: seen.add(k); dedup.append(g)
    groups = dedup[:4]
    if not groups: return ""
    try:
        from src.data.realtime import get_realtime_quote
        from src.scoring.engine import V6ScoringEngine
        engine = V6ScoringEngine()
        lines = ["用户问题是行业/概念选股，不要要求用户必须给单只股票代码。"]
        try:
            for kind, name, codes in groups:
                scored = []
                for cd in codes[:10]:
                    q = get_realtime_quote(cd)
                    if not q: continue
                    r = engine.score_stock(cd, quote=q)
                    if not r: continue
                    scored.append((r.total_score, q, r))
                scored.sort(key=lambda x: x[0], reverse=True)
                lines.append(f"\n{kind}：{name}")
                for _, q, r in scored[:5]:
                    t = "、".join(r.anti_quant.triggers[:2]) if r.anti_quant.triggers else "无"
                    lines.append(f"- {q.get('name',r.code)}({r.code})：机会分{r.total_score:.0f} 涨幅{q.get('change_pct',0):+.2f}% 状态{r.status_label} 反量化{r.anti_quant.risk_level} 触发:{t}")
        finally: engine.close()
        return "\n".join(lines)
    except: return ""


def _extract_code(text: str) -> str:
    m = re.search(r"\b(\d{6})\b", text)
    return m.group(1) if m else ""


def _fmt(text: str) -> str:
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", safe)
    safe = safe.replace("\n\n", "</p><p>").replace("\n", "<br>")
    return f"<p>{safe}</p>"
