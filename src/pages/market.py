"""行情中心"""

import streamlit as st
from datetime import datetime
from src.data.realtime import get_top_stocks, get_market_overview
from src.data.quality import get_quality_badge, fmt_freshness, render_quality_html, FALLBACK_WARNING
from src.data.market_board import BOARD_FILTERS, board_label, is_code_in_board_filter


def _c(v):
    v = v or 0
    if v > 0: return "#CF0011"
    if v < 0: return "#007348"
    return "#9AA4B2"


def _sentiment_bar(stocks_up: list, stocks_dn: list):
    """市场情绪条：根据涨跌榜前20统计情绪，显示涨跌停数量和多空比"""
    limit_up = sum(1 for s in stocks_up if s.get("change_pct", 0) >= 9.8)
    limit_dn = sum(1 for s in stocks_dn if s.get("change_pct", 0) <= -9.8)
    up_avg = sum(s.get("change_pct", 0) for s in stocks_up) / max(len(stocks_up), 1)
    dn_avg = sum(s.get("change_pct", 0) for s in stocks_dn) / max(len(stocks_dn), 1)

    # 情绪判断
    if limit_up >= 5 or up_avg >= 5:
        mood, mood_color, mood_tip = "偏热", "var(--red)", "涨停多，情绪较强，注意追高风险"
    elif limit_up >= 2 or up_avg >= 3:
        mood, mood_color, mood_tip = "温和", "var(--amber)", "结构分化，精选个股"
    elif limit_dn >= 5 or abs(dn_avg) >= 5:
        mood, mood_color, mood_tip = "偏弱", "var(--green)", "跌停多，避免抄底冲动"
    else:
        mood, mood_color, mood_tip = "平稳", "var(--muted)", "震荡市，观望为主"

    # 宽度比例
    total = max(len(stocks_up) + len(stocks_dn), 1)
    up_pct = int(len(stocks_up) / total * 100)
    dn_pct = 100 - up_pct

    st.markdown(
        f'<div class="card" style="padding:12px 14px;margin-bottom:12px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
        f'<span style="font-size:13px;font-weight:700;color:var(--text)">今日情绪</span>'
        f'<span style="font-size:13px;font-weight:700;color:{mood_color}">{mood}</span>'
        f'</div>'
        f'<div style="display:flex;height:6px;border-radius:3px;overflow:hidden;margin-bottom:8px">'
        f'<div style="width:{up_pct}%;background:#CF0011"></div>'
        f'<div style="width:{dn_pct}%;background:#007348"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted)">'
        f'<span>涨停 <strong style="color:#CF0011;font-family:var(--mono)">{limit_up}</strong>'
        f' · 涨均 <strong style="color:#CF0011;font-family:var(--mono)">{up_avg:+.1f}%</strong></span>'
        f'<span style="color:var(--muted);font-size:11px">{mood_tip}</span>'
        f'<span>跌停 <strong style="color:#007348;font-family:var(--mono)">{limit_dn}</strong>'
        f' · 跌均 <strong style="color:#007348;font-family:var(--mono)">{dn_avg:+.1f}%</strong></span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _filter_stocks_by_board(stocks: list[dict], board_filter: str) -> list[dict]:
    return [s for s in stocks or [] if is_code_in_board_filter(s.get("code", ""), board_filter)]


def render_market_page():
    # ── 全局模糊搜索 ──
    from src.ui.search import render_search_bar
    code = render_search_bar(key="market")
    if code:
        st.session_state["selected_stock"] = code
        st.session_state["previous_page"] = "market"
        st.session_state["current_page"] = "stock_detail"
        st.rerun()

    # ── 指数条 ──
    with st.spinner("加载行情..."):
        ov = get_market_overview()
    indices = ov.get("indices", [])

    if ov.get("_fallback"):
        st.warning(FALLBACK_WARNING, icon="⚠️")
    elif ov.get("source"):
        badge = get_quality_badge(ov["source"])
        ts = ov.get("_ts")
        freshness = f" · {fmt_freshness(ts)}" if ts else ""
        st.caption(f"📡 {badge['label']} · 质量{badge['level']}{freshness}")

    if indices:
        h = '<div class="idx-strip">'
        for idx in indices:
            p = idx.get("change_pct", 0)
            cl = _c(p)
            s = "+" if p > 0 else ""
            h += (
                f'<div class="idx-cell">'
                f'<div class="n">{idx.get("name")}</div>'
                f'<div class="p" style="color:{cl}">{idx.get("price",0):.2f}</div>'
                f'<div class="c" style="color:{cl}">{s}{p:.2f}%</div>'
                f'</div>'
            )
        h += '</div>'
        st.markdown(h, unsafe_allow_html=True)

    now_str = datetime.now().strftime('%H:%M:%S')
    c1, c2 = st.columns([3, 1])
    with c1:
        st.caption(f"更新 {now_str}")
    with c2:
        if st.button("刷新", key="mkt_refresh", use_container_width=True):
            st.rerun()

    st.session_state.setdefault("market_board_filter", "全A")
    st.markdown('<div class="sec-h">板块行情</div>', unsafe_allow_html=True)
    board_cols = st.columns(3)
    for idx, option in enumerate(BOARD_FILTERS):
        with board_cols[idx % 3]:
            if st.button(
                option,
                key=f"market_board_{option}",
                use_container_width=True,
                type="primary" if st.session_state["market_board_filter"] == option else "secondary",
            ):
                st.session_state["market_board_filter"] = option
                st.rerun()
    board_filter = st.session_state["market_board_filter"]
    st.caption(
        "行情榜单按板块过滤；默认全A。主板拆成沪市主板/深市主板，创业板、科创板、北交所独立查看。"
    )

    # ── 四大榜单（一次性获取，避免重复消耗额度）──
    with st.spinner("加载榜单..."):
        stocks_up = get_top_stocks("changepercent", False, 20)
        stocks_dn = get_top_stocks("changepercent", True, 20)
        stocks_amt = get_top_stocks("amount", False, 20)
        stocks_tr = get_top_stocks("turnoverratio", False, 20)

    if board_filter != "全A":
        stocks_up = _filter_stocks_by_board(stocks_up, board_filter)
        stocks_dn = _filter_stocks_by_board(stocks_dn, board_filter)
        stocks_amt = _filter_stocks_by_board(stocks_amt, board_filter)
        stocks_tr = _filter_stocks_by_board(stocks_tr, board_filter)

    # ── 情绪条（用已获取数据，不额外调用）──
    if stocks_up or stocks_dn:
        _sentiment_bar(stocks_up, stocks_dn)

    t1, t2, t3, t4 = st.tabs(["涨幅榜 🔴", "跌幅榜 🟢", "成交额", "换手率"])

    def _stock_list(stocks, prefix):
        if not stocks:
            st.info("暂无数据")
            return
        if stocks and stocks[0].get("_fallback"):
            st.warning(FALLBACK_WARNING, icon="⚠️")
        for i, s in enumerate(stocks):
            p = s.get("change_pct", 0) or 0
            cl = _c(p)
            nm = s.get("name") or s.get("code", "")
            cd = s.get("code", "")
            bd = board_label(cd)
            pr = s.get("price", 0) or 0
            amt = s.get("amount", 0) or 0
            q_html = render_quality_html(s)

            # 涨跌停标记
            limit_tag = ""
            if p >= 9.8:
                limit_tag = '<span style="background:#CF0011;color:#fff;font-size:9px;font-weight:700;padding:1px 4px;border-radius:2px;margin-left:4px">涨停</span>'
            elif p <= -9.8:
                limit_tag = '<span style="background:#007348;color:#fff;font-size:9px;font-weight:700;padding:1px 4px;border-radius:2px;margin-left:4px">跌停</span>'

            amt_str = f'{amt/1e8:.1f}亿' if amt >= 1e8 else (f'{amt/1e4:.0f}万' if amt > 0 else "")
            amt_span = ('<span style="font-size:10px;color:var(--muted);margin-left:4px">' + amt_str + '</span>') if amt_str else ""

            st.markdown(
                f'<div class="sr">'
                f'<div style="color:var(--muted);font-family:var(--mono);font-size:12px;width:24px;text-align:center">{i+1}</div>'
                f'<div class="inf"><div><span class="nm">{nm}</span>{limit_tag}</div>'
                f'<div><span class="cd">{cd}</span>'
                f'<span style="font-size:10px;color:var(--muted);margin-left:4px">{bd}</span>'
                f'{amt_span}'
                f' {q_html}</div></div>'
                f'<div style="text-align:right">'
                f'<div class="pr" style="color:{cl}">{pr:.2f}</div>'
                f'<div class="ch" style="color:{cl}">{p:+.2f}%</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("查看", key=f"{prefix}{cd}_{i}"):
                st.session_state["selected_stock"] = cd
                st.session_state["previous_page"] = "market"
                st.session_state["current_page"] = "stock_detail"
                st.rerun()

    with t1:
        _stock_list(stocks_up, "up_")
    with t2:
        _stock_list(stocks_dn, "dn_")
    with t3:
        _stock_list(stocks_amt, "am_")
    with t4:
        _stock_list(stocks_tr, "tr_")

    # ── 快讯 ──
    st.markdown("---")
    st.markdown('<div class="sec-h">快讯</div>', unsafe_allow_html=True)

    srcs = ["全部", "新浪", "东财", "财联社", "腾讯", "华尔街见闻"]
    src_key = "ns_src"
    st.session_state.setdefault(src_key, "全部")
    scols = st.columns(6)
    for i, s in enumerate(srcs):
        with scols[i]:
            if st.button(s, key=f"nss_{s}", use_container_width=True,
                         type="primary" if st.session_state[src_key] == s else "secondary"):
                st.session_state[src_key] = s; st.rerun()

    cats = ["全部", "政策", "板块", "公司", "宏观"]
    cat_key = "ns_cat"
    st.session_state.setdefault(cat_key, "全部")
    ccols = st.columns(5)
    for i, c in enumerate(cats):
        with ccols[i]:
            if st.button(c, key=f"nsc_{c}", use_container_width=True,
                         type="primary" if st.session_state[cat_key] == c else "secondary"):
                st.session_state[cat_key] = c; st.rerun()

    if "nsd" not in st.session_state:
        with st.spinner("加载中..."):
            from src.news.fetcher import fetch_all_news
            st.session_state["nsd"] = fetch_all_news(60)
    ns = st.session_state["nsd"]

    src = st.session_state[src_key]
    cat = st.session_state[cat_key]
    if src != "全部": ns = [n for n in ns if n.get("source") == src]
    if cat != "全部": ns = [n for n in ns if n.get("category") == cat]

    if not ns:
        st.info("暂无新闻")
    else:
        st.caption(f"{len(ns)} 条")
        for it in ns[:30]:
            t = it.get("title", ""); s = it.get("source", "")
            pt = it.get("published_at", ""); body = it.get("content", "")
            cn = it.get("category", ""); codes = it.get("related_codes", [])

            tags = []
            if cn == "policy": tags.append('<span class="badge badge-ai">政策</span>')
            elif cn == "sector": tags.append('<span class="badge badge-low">板块</span>')
            elif cn == "company": tags.append('<span class="badge badge-mid">公司</span>')
            if any(k in t for k in ["涨", "牛", "利好", "突破", "涨停"]):
                tags.append('<span class="badge badge-low">利好</span>')
            elif any(k in t for k in ["跌", "利空", "风险", "暴雷", "退市"]):
                tags.append('<span class="badge badge-high">利空</span>')

            cs = ""
            if codes:
                cs = '<div style="margin-top:4px">' + " ".join(
                    f'<span style="font-family:var(--mono);font-size:10px;color:var(--ai)">{c}</span>'
                    for c in codes[:3]) + '</div>'

            st.markdown(
                f'<div class="ni"><div class="nt">{" ".join(tags)} {t}</div>'
                f'<div class="nm">{s} · {pt}</div>{cs}</div>',
                unsafe_allow_html=True)
            if body and body != t:
                with st.expander(t[:40] + "..."):
                    st.caption(body)

    if st.button("刷新新闻", key="rn2", use_container_width=True):
        st.session_state.pop("nsd", None); st.rerun()
