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
            ("观察计划", f"{code} 现在能观察吗",
             f"请判断 {code} 现在是否适合加入观察/模拟验证。回答只能是：可观察、仅模拟、等待触发、暂停。列出参与前必须满足的 3 个条件和 3 个离场红线。不要长篇大论，只给关键判断和数字。"),
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
        st.session_state["previous_page"] = "ai_chat"
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

    _render_memory_panel(selected_code)

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

    # ── 功能横条 ──
    st.markdown('<div class="sec-h">工具箱</div>', unsafe_allow_html=True)
    actions = [
        ("盘前早报", "mb", lambda: ai.morning_briefing(), "开盘前了解今日方向"),
        ("收盘总结", "cs", lambda: ai.closing_summary(), "复盘今日交易和AI判断"),
        ("账户诊断", "ad", lambda: ai.account_diagnosis(), "分析你的交易行为"),
        ("尾盘扫描", "ts", lambda: ai.tail_session_scan()[1], "14:30查看隔夜候选"),
        ("对比分析", "cp", None, "两只股票并排比较"),
    ]
    for row in range(3):
        cols = st.columns(2)
        for i in range(2):
            idx = row * 2 + i
            if idx >= len(actions): break
            name, kid, fn, hint = actions[idx]
            with cols[i]:
                if st.button(name, key=f"tool_{kid}", use_container_width=True, help=hint):
                    if name == "对比分析":
                        st.session_state["ai_compare"] = True; st.rerun()
                    else:
                        with st.spinner(f"{name}生成中..."):
                            result = fn()
                        if result:
                            ai.history.append({
                                "question": f"生成{name}",
                                "answer": result,
                                "timestamp": datetime.now().isoformat(),
                                "tools_used": [],
                            })
                            ai.save_to_disk(); st.rerun()

    # ── 底部 ──
    if history:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("清空对话", use_container_width=True):
                ai.clear_history(); st.rerun()
        with c2:
            if st.button("逐条管理", use_container_width=True):
                st.session_state["ai_mgr"] = not st.session_state.get("ai_mgr", False)
                st.rerun()

    # 对比分析
    if st.session_state.pop("ai_compare", False):
        st.markdown('<div class="sec-h">对比分析</div>', unsafe_allow_html=True)
        ca = st.text_input("股票A", placeholder="600519", key="cmp_a")
        cb = st.text_input("股票B", placeholder="000858", key="cmp_b")
        if ca and cb and st.button("开始对比", use_container_width=True):
            with st.spinner("对比中..."):
                result = ai.compare_stocks(ca.strip(), cb.strip())
            ai.history.append({
                "question": f"对比 {ca} 和 {cb}", "answer": result,
                "timestamp": datetime.now().isoformat(), "tools_used": [],
            })
            ai.save_to_disk(); st.rerun()

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
    """渲染一条对话：用户消息气泡 + AI 可折叠回复 + 智能追问"""
    q_text = html.escape(str(item.get("question", "")))
    a_text = str(item.get("answer", ""))
    title = _extract_title(a_text)

    # 用户消息
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

        # ── 智能追问按钮 ──
        followups = AIChat.follow_up_questions(q_text, a_text)
        if followups:
            st.markdown("<br>", unsafe_allow_html=True)
            for fu in followups:
                if st.button(fu, key=f"fu_{idx}_{hash(fu) % 10000}",
                             use_container_width=True):
                    st.session_state["qq"] = fu
                    st.rerun()


def _render_memory_panel(selected_code: str):
    with st.expander("研究记忆", expanded=False):
        try:
            from src.memory.conversation_memory import ConversationMemory

            memory = ConversationMemory()
            try:
                tabs = st.tabs(["最近", "当前股票", "搜索"])
                with tabs[0]:
                    rows = memory.list_recent_threads(limit=8)
                    if not rows:
                        st.caption("暂无数据库会话。新的对话会自动保存到这里。")
                    for row in rows:
                        _memory_row(row, prefix="recent")
                with tabs[1]:
                    if not selected_code:
                        st.caption("先选择股票，或在问题中输入 6 位代码。")
                    else:
                        rows = memory.get_stock_conversations(selected_code, limit=8)
                        if not rows:
                            st.caption(f"暂无 {selected_code} 的历史对话。")
                        for row in rows:
                            _memory_row(row, prefix="stock")
                with tabs[2]:
                    kw = st.text_input("搜索历史", placeholder="例如：止损 / 半导体 / 600900", key="ai_memory_search")
                    if kw.strip():
                        rows = memory.search_messages(kw, limit=10)
                        if not rows:
                            st.caption("没有匹配结果")
                        for row in rows:
                            _memory_row(row, prefix="search")
            finally:
                memory.close()
        except Exception as exc:
            st.caption(f"研究记忆暂不可用: {exc}")


def _memory_row(row: dict, prefix: str):
    content = str(row.get("last_content") or row.get("content") or "").replace("\n", " ")
    role = row.get("last_role") or row.get("role") or ""
    stock = row.get("stock_code") or ""
    ts = str(row.get("updated_at") or row.get("created_at") or "")[:16]
    label = "用户" if role == "user" else "AI" if role == "assistant" else role
    title = content[:90] or row.get("title") or "空会话"
    st.markdown(
        f'<div class="ai-memory-row">'
        f'<div style="min-width:0;flex:1">'
        f'<div class="ai-memory-q">{html.escape(title)}</div>'
        f'<div style="font-size:11px;color:var(--muted);margin-top:2px">{html.escape(label)} {html.escape(stock)} · {html.escape(ts)}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    if content and st.button("带入追问", key=f"mem_{prefix}_{row.get('id', row.get('session_id'))}", use_container_width=True):
        st.session_state["qq"] = f"基于这条历史记录继续分析：{content[:800]}"
        st.rerun()


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

    # 用户画像
    try:
        from src.memory.user_profile import get_profile
        p = get_profile()
        p.record_chat()
        if stock_code: p.track_stock(stock_code)
        ctx = p.build_context()
        if ctx: parts.insert(1, ctx)
    except Exception: pass

    # 用户执行风险闸门
    try:
        from src.risk.user_state import get_user_risk_state

        state = get_user_risk_state()
        reasons = "；".join(state.get("reasons", [])[:3])
        parts.insert(1, (
            "\n[系统: 用户执行风险闸门]\n"
            f"状态: {state.get('mode')} / 风险分 {state.get('score')}\n"
            f"动作边界: {state.get('action_policy')}\n"
            f"原因: {reasons}\n"
            "AI 回答必须遵守动作边界。"
        ))
    except Exception:
        pass

    if stock_code:
        try:
            from src.ai.context_builder import AIContextBuilder
            from src.memory.stock_memory import StockMemory
            from src.memory.analysis_memory import AnalysisMemory

            sm = StockMemory()
            try:
                with AnalysisMemory() as am:
                    rich = AIContextBuilder(stock_memory=sm, analysis=am).build(text, stock_code)
                if rich:
                    parts.append(f"\n\n[系统: 股票长期记忆/历史验证]\n{rich}")
            finally:
                sm.close()
        except Exception:
            pass
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
    from src.data.stock_list import detect_stock_groups, resolve_stock_name
    groups = detect_stock_groups(text)[:4]
    if not groups: return ""
    try:
        from src.data.realtime import get_realtime_quote
        from src.scoring.engine import V6ScoringEngine
        engine = V6ScoringEngine()
        lines = [
            "用户问题是行业/概念选股，不要要求用户必须给单只股票代码。",
            "请像短线老手一样直接给候选表、优先顺序、风险、参与条件、放弃条件和资金纪律。",
            "不要把任务甩给用户去雷达页自己找；如果实时评分暂不可用，也要使用静态候选池给具体股票名和代码。",
            "\n[静态候选池，实时评分失败时直接引用]",
        ]
        for kind, name, codes in groups:
            named = "、".join(f"{resolve_stock_name(cd)}({cd})" for cd in codes[:6])
            lines.append(f"- {kind}：{name}：{named}")
        try:
            for kind, name, codes in groups:
                scored = []
                for cd in codes[:10]:
                    q = get_realtime_quote(cd)
                    if not q: continue
                    q["name"] = resolve_stock_name(cd, q.get("name", ""))
                    r = engine.score_stock(cd, quote=q)
                    if not r: continue
                    scored.append((r.total_score, q, r))
                scored.sort(key=lambda x: x[0], reverse=True)
                lines.append(f"\n[实时六维候选] {kind}：{name}")
                for _, q, r in scored[:5]:
                    t = "、".join(r.anti_quant.triggers[:2]) if r.anti_quant.triggers else "无"
                    lines.append(f"- {resolve_stock_name(r.code, q.get('name', r.code))}({r.code})：机会分{r.total_score:.0f} 涨幅{q.get('change_pct',0):+.2f}% 状态{r.status_label} 反量化{r.anti_quant.risk_level} 触发:{t}")
                if not scored:
                    lines.append("- 实时行情暂不可用，请直接引用上方静态候选池，不要只给代码。")
        finally: engine.close()
        return "\n".join(lines)
    except:
        names = "、".join(f"{kind}:{name}" for kind, name, _ in groups)
        return (
            f"用户问题是行业/概念选股，不要要求用户必须给单只股票代码。目标：{names}。"
            "实时评分暂不可用，也要直接给候选表、优先顺序、风险条件、时间表和资金纪律。"
        )


def _extract_code(text: str) -> str:
    m = re.search(r"\b(\d{6})\b", text)
    return m.group(1) if m else ""


def _fmt(text: str) -> str:
    lines = str(text or "").splitlines()
    out = ['<div class="ai-answer">']
    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        line = raw.strip()
        if not line:
            i += 1
            continue

        if line.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= {"|", "-", " "}:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            out.append(_markdown_table_to_html(table_lines))
            continue

        heading = re.match(r"^#{2,4}\s*(.+)$", line)
        if heading:
            out.append(f'<div class="ai-section">{_inline(heading.group(1))}</div>')
            i += 1
            continue

        if re.match(r"^(\d+[.。]|[-*])\s*", line):
            out.append(f'<div class="ai-step">{_inline(line)}</div>')
        else:
            out.append(f'<div class="ai-p">{_inline(line)}</div>')
        i += 1
    out.append("</div>")
    return "".join(out)


def _inline(text: str) -> str:
    safe = html.escape(str(text or ""))
    safe = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", safe)
    return safe


def _markdown_table_to_html(lines: list[str]) -> str:
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and all(set(c) <= {"-", " "} for c in cells):
            continue
        rows.append(cells)
    if not rows:
        return ""

    html_rows = ['<div class="ai-table-wrap"><table class="ai-table">']
    header = rows[0]
    html_rows.append("<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in header) + "</tr></thead><tbody>")
    for row in rows[1:]:
        html_rows.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
    html_rows.append("</tbody></table></div>")
    return "".join(html_rows)
