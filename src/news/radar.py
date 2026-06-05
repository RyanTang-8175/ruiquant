"""
信息雷达增强 —— 互动易 + 公告 + 政策触发采集
把新闻从 "5源财经" 升级为 "5源财经 + 互动易 + 公告 + 政策"
"""

import re
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
H = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
    'Accept': 'application/json',
}


# ═══════════════════════════════════════════
# 1. 互动易 — 上市公司问答平台 (irm.cninfo.com.cn)
# ═══════════════════════════════════════════

def fetch_irm_questions(code: str, limit: int = 10) -> List[Dict]:
    """获取特定股票的互动易问答"""
    items = []
    try:
        r = requests.get(
            'https://irm.cninfo.com.cn/ircs/search',
            params={'keyword': code, 'pageNum': 1, 'pageSize': limit},
            headers=H, timeout=10,
        )
        data = r.json()
        for item in data if isinstance(data, list) else data.get('data', []):
            title = item.get('question', '') or item.get('title', '')
            answer = item.get('answer', '') or item.get('content', '')
            if title:
                items.append({
                    'title': re.sub(r'<[^>]+>', '', str(title))[:200],
                    'content': re.sub(r'<[^>]+>', '', str(answer))[:500],
                    'source': '互动易',
                    'type': 'investor_qa',
                    'published_at': item.get('updatedAt', '') or item.get('publishDate', ''),
                })
    except Exception as e:
        logger.warning(f"互动易 {code}: {e}")

    if not items:
        try:
            r = requests.get(
                f'https://irm.cninfo.com.cn/ircs/company/companyQuestion?stockCode={code}',
                headers=H, timeout=10,
            )
            qas = re.findall(
                r'<div[^>]*class="question[^"]*"[^>]*>(.*?)</div>.*?<div[^>]*class="answer[^"]*"[^>]*>(.*?)</div>',
                r.text, re.DOTALL | re.IGNORECASE,
            )
            for q, a in qas[:limit]:
                title = re.sub(r'<[^>]+>', '', q).strip()
                answer = re.sub(r'<[^>]+>', '', a).strip()
                if title:
                    items.append({
                        'title': title[:200], 'content': answer[:500],
                        'source': '互动易', 'type': 'investor_qa', 'published_at': '',
                    })
        except Exception as e:
            logger.warning(f"互动易回退 {code}: {e}")

    return items[:limit]


def fetch_irm_hot(limit: int = 20) -> List[Dict]:
    """互动易热门问答（全市场）"""
    items = []
    try:
        r = requests.get(
            'https://irm.cninfo.com.cn/ircs/search',
            params={'keyword': '', 'pageNum': 1, 'pageSize': limit},
            headers=H, timeout=10,
        )
        data = r.json()
        data_list = data if isinstance(data, list) else data.get('data', [])
        for item in data_list:
            title = item.get('question', '') or item.get('title', '')
            if title:
                items.append({
                    'title': re.sub(r'<[^>]+>', '', str(title))[:200],
                    'content': re.sub(r'<[^>]+>', '', str(item.get('answer', '')))[:300],
                    'source': '互动易', 'type': 'investor_qa',
                    'published_at': item.get('updatedAt', ''),
                })
    except Exception as e:
        logger.warning(f"互动易热门: {e}")
    return _dedup_by_title(items)[:limit]


# ═══════════════════════════════════════════
# 2. 巨潮资讯/深交所公告
# ═══════════════════════════════════════════

def fetch_announcements(code: str, limit: int = 10) -> List[Dict]:
    """获取个股公告（巨潮资讯 + 新浪公告回退）"""
    items = []
    try:
        from src.data.providers.registry import get_provider

        provider = get_provider()
        if provider.source_name == "ifind":
            items.extend(provider.report_query(code, days=45, limit=limit))
    except Exception as e:
        logger.warning(f"iFinD公告 {code}: {e}")

    if items:
        return items[:limit]

    try:
        r = requests.get(
            'http://www.cninfo.com.cn/new/disclosure',
            params={
                'stock': f"{'sh' if code.startswith('6') else 'sz'}{code}",
                'pageSize': limit,
            },
            headers=H, timeout=10,
        )
        for ann in r.json().get('classifiedAnnouncements', [])[:limit]:
            title = ann.get('announcementTitle', '')
            if title:
                items.append({
                    'title': re.sub(r'<[^>]+>', '', title)[:200],
                    'content': '',
                    'source': '巨潮公告', 'type': 'announcement',
                    'published_at': ann.get('announcementTime', ''),
                    'url': f"http://www.cninfo.com.cn/new/disclosure/detail?announcementId={ann.get('announcementId','')}",
                })
    except Exception as e:
        logger.warning(f"公告 {code}: {e}")

    if not items:
        try:
            tc = f"sh{code}" if code.startswith('6') else f"sz{code}"
            r = requests.get(
                f'http://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllBulletin/stockid/{tc}.phtml',
                headers=H, timeout=10,
            )
            for match in re.findall(
                r'<a[^>]*href="([^"]*)"[^>]*target="_blank"[^>]*>([^<]*)</a>',
                r.text,
            )[:limit]:
                title = match[1].strip()
                if title and len(title) > 5:
                    items.append({
                        'title': title[:200], 'content': '',
                        'source': '新浪公告', 'type': 'announcement',
                        'published_at': '', 'url': match[0],
                    })
        except Exception as e:
            logger.warning(f"公告回退 {code}: {e}")

    return items[:limit]


# ═══════════════════════════════════════════
# 3. 政策公告
# ═══════════════════════════════════════════

def fetch_policy_updates(limit: int = 15) -> List[Dict]:
    """采集政策/监管动态（新浪政策频道聚合）"""
    items = []
    try:
        r = requests.get(
            'http://feed.mix.sina.com.cn/api/roll/get',
            params={'pageid': '153', 'lid': '2533', 'num': str(limit), 'page': '1'},
            headers=H, timeout=10,
        )
        for item in r.json().get('result', {}).get('data', []):
            title = re.sub(r'<[^>]+>', '', str(item.get('title', ''))).strip()
            if title:
                ts = int(item.get('ctime', 0))
                dt = datetime.fromtimestamp(ts).strftime('%m-%d %H:%M') if ts > 1000000000 else ''
                items.append({
                    'title': title[:200],
                    'content': re.sub(r'<[^>]+>', '', str(item.get('intro', ''))).strip()[:300],
                    'source': '政策', 'type': 'policy',
                    'published_at': dt, 'url': item.get('url', ''),
                })
    except Exception as e:
        logger.warning(f"政策采集: {e}")
    return items[:limit]


# ═══════════════════════════════════════════
# 4. 统一信息雷达接口
# ═══════════════════════════════════════════

def fetch_radar_for_stock(code: str, limit: int = 10) -> Dict:
    """单只股票完整信息雷达：新闻 + 互动易 + 公告"""
    items = []
    sources = {}

    for name, fetcher, arg in [
        ('互动易', fetch_irm_questions, code),
        ('公告', fetch_announcements, code),
    ]:
        try:
            result = fetcher(arg, limit)
            items.extend(result)
            sources[name] = len(result)
        except Exception as e:
            sources[name] = f"error: {str(e)[:40]}"

    try:
        from src.news.fetcher import fetch_stock_news
        news = fetch_stock_news(code, limit)
        items.extend(news)
        sources['财经新闻'] = len(news)
    except Exception as e:
        sources['财经新闻'] = f"error: {str(e)[:40]}"

    return {
        'code': code,
        'total': len(items),
        'sources': sources,
        'items': _dedup_by_title(items)[:limit * 2],
    }


def fetch_radar_market_overview(limit: int = 30) -> Dict:
    """全市场信息雷达概览：政策 + 互动易 + 机构观点 + 行业异动 + 智能选股"""
    items = []
    sources = {}

    try:
        smart = fetch_ifind_smart_picks("主力资金流入 涨幅 居前", limit=8)
        items.extend(smart)
        sources['iFinD智能选股'] = len(smart)
    except Exception as e:
        sources['iFinD智能选股'] = f"error: {str(e)[:40]}"

    try:
        research = fetch_ifind_research_views(limit=8)
        items.extend(research)
        sources['iFinD机构观点'] = len(research)
    except Exception as e:
        sources['iFinD机构观点'] = f"error: {str(e)[:40]}"

    try:
        sectors = fetch_ifind_sector_moves(limit=8)
        items.extend(sectors)
        sources['iFinD行业异动'] = len(sectors)
    except Exception as e:
        sources['iFinD行业异动'] = f"error: {str(e)[:40]}"

    try:
        policy = fetch_policy_updates(limit // 3)
        items.extend(policy)
        sources['政策'] = len(policy)
    except Exception as e:
        sources['政策'] = f"error: {str(e)[:40]}"

    try:
        irm_hot = fetch_irm_hot(limit // 3)
        items.extend(irm_hot)
        sources['互动易热门'] = len(irm_hot)
    except Exception as e:
        sources['互动易热门'] = f"error: {str(e)[:40]}"

    try:
        from src.news.fetcher import fetch_all_news
        news = fetch_all_news(limit)
        items.extend(news)
        sources['财经新闻'] = len(news)
    except Exception as e:
        sources['财经新闻'] = f"error: {str(e)[:40]}"

    return {
        'total': len(items),
        'sources': sources,
        'items': _categorize_radar(_dedup_by_title(items)[:limit]),
    }


# ═══════════════════════════════════════════
# 工具
# ═══════════════════════════════════════════

def fetch_ifind_research_views(limit: int = 10) -> List[Dict]:
    """iFinD 机构观点/研报关注度。

    使用智能选股自然语言能力做低频入口，不额外铺满研报接口；
    返回结果只作为研究候选和机构关注度线索。
    """
    queries = [
        "近30日机构研报评级上调 A股",
        "近30日机构调研次数居前 A股",
    ]
    items: list[dict] = []
    for query in queries:
        rows = fetch_ifind_smart_picks(query, limit=max(1, limit // len(queries)))
        for row in rows:
            row = dict(row)
            row["source"] = "iFinD机构观点"
            row["type"] = "research_view"
            row["content"] = row.get("content") or "机构观点/研报关注度升温，只能作为研究线索，仍需财务、公告和成交承接交叉验证。"
            items.append(row)
    return _dedup_by_title(items)[:limit]


def fetch_ifind_sector_moves(limit: int = 10) -> List[Dict]:
    """iFinD 行业/概念异动雷达。"""
    queries = [
        "A股行业涨幅居前 成交额放大",
        "A股概念板块涨幅居前 换手活跃",
    ]
    items: list[dict] = []
    for query in queries:
        rows = fetch_ifind_smart_picks(query, limit=max(1, limit // len(queries)))
        for row in rows:
            row = dict(row)
            row["source"] = "iFinD行业异动"
            row["type"] = "sector_move"
            row["content"] = row.get("content") or "行业/概念出现价量异动，需要看板块联动、核心股承接和是否有公告/政策支撑。"
            items.append(row)
    return _dedup_by_title(items)[:limit]

def fetch_ifind_smart_picks(query: str, limit: int = 10) -> List[Dict]:
    """低频 iFinD 智能选股结果，未配置时返回空列表。"""
    try:
        from src.data.providers.registry import get_provider

        provider = get_provider()
        if provider.source_name != "ifind" or not hasattr(provider, "smart_stock_picking"):
            return []
        rows = provider.smart_stock_picking(query, limit=min(limit, 20))
    except Exception as e:
        logger.warning(f"iFinD智能选股: {e}")
        return []

    items = []
    for row in rows[:limit]:
        title = f"{row.get('name') or row.get('code')}({row.get('code')}) 智能选股命中：{query}"
        if row.get("change_pct") is not None:
            title += f"，涨跌幅 {row.get('change_pct'):+.2f}%"
        items.append({
            "title": title,
            "content": "iFinD 智能选股返回的候选，只能作为研究入口，仍需结合公告、成交承接和反量化风险验证。",
            "source": "iFinD智能选股",
            "type": "smart_pick",
            "published_at": datetime.now().strftime("%m-%d %H:%M"),
            "related_codes": [row.get("code")] if row.get("code") else [],
            "sentiment": "neutral",
        })
    return items

def _dedup_by_title(items: list, key_len: int = 40) -> list:
    seen, out = set(), []
    for x in items:
        k = x.get('title', '')[:key_len]
        if k and k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _categorize_radar(items: list) -> list:
    """对雷达条目做情绪和关联股票标记"""
    for item in items:
        t = f"{item.get('title', '')} {item.get('content', '')}"
        if any(k in t for k in ['减持', '质押', '重组', 'ST', '退市', '预亏', '违规', '处罚']):
            item['sentiment'] = 'negative'
        elif any(k in t for k in ['增持', '回购', '中标', '签约', '预增', '突破', '获批']):
            item['sentiment'] = 'positive'
        else:
            item['sentiment'] = 'neutral'

        codes = list(set(re.findall(r'\b([3689]\d{5}|0[023]\d{4})\b', t)))[:5]
        if codes:
            item['related_codes'] = codes
    return items


# ═══════════════════════════════════════════════════════════
# Phase 2.1: 分层抓取函数 — 免费源高频 + iFinD 精准低频
# ═══════════════════════════════════════════════════════════

_logger = logging.getLogger("radar")
_FREE_CACHE: dict = {}
_FREE_CACHE_TS: float = 0
_FREE_CACHE_TTL: int = 180


def fetch_free_hotspots(limit: int = 30) -> list:
    """Phase 2.1 免费层：东财人气榜 + 政策 + 互动易热门（零 iFinD 消耗）"""
    global _FREE_CACHE, _FREE_CACHE_TS
    import time
    now = time.time()
    if _FREE_CACHE and (now - _FREE_CACHE_TS) < _FREE_CACHE_TTL:
        return _FREE_CACHE[:limit]

    items = []
    # 1. 东财人气榜
    try:
        r = requests.get(
            "https://push2.eastmoney.com/api/qt/clist/get",
            params={"pn": "1", "pz": str(min(limit, 30)), "po": "1", "np": "1", "fltt": "2", "invt": "2",
                    "fid": "f3", "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                    "fields": "f2,f3,f12,f14"},
            headers=H, timeout=8,
        )
        data = r.json()
        for item in (data.get("data", {}).get("diff", []) or [])[:limit]:
            code = item.get("f12", "")
            name = item.get("f14", "")
            pct = item.get("f3", 0)
            if code:
                items.append({
                    "title": f"东财人气: {name}({code}) 涨跌幅{pct:+.2f}%",
                    "content": f"{name} 进入东财热股榜",
                    "source": "东财人气榜", "type": "hot_stock",
                    "published_at": datetime.now().strftime("%m-%d %H:%M"),
                    "related_codes": [code], "sentiment": "neutral",
                })
    except Exception as e:
        _logger.debug(f"东财人气榜: {e}")

    # 2. 政策
    try:
        items.extend(fetch_policy_updates(limit=min(limit // 3, 10)))
    except Exception as e:
        _logger.debug(f"政策: {e}")

    # 3. 互动易热门
    try:
        items.extend(fetch_irm_hot(limit=min(limit // 3, 10)))
    except Exception as e:
        _logger.debug(f"互动易: {e}")

    items = _dedup_by_title(items)
    _FREE_CACHE = items
    _FREE_CACHE_TS = now
    return items[:limit]


def fetch_radar_precision_layer(top_n: int = 30) -> int:
    """Phase 2.1 iFinD 精准层：热门票的公告（消耗额度，盘前盘后各一次）"""
    total = 0
    try:
        hot = fetch_free_hotspots(limit=top_n) if _FREE_CACHE else []
    except Exception:
        hot = []

    hot_codes = []
    for item in hot:
        codes = item.get("related_codes") or []
        hot_codes.extend(codes)
    hot_codes = list(dict.fromkeys(hot_codes))[:top_n]

    if not hot_codes:
        try:
            from src.data.realtime import get_top_stocks
            for s in (get_top_stocks("amount", False, 15) or []):
                hot_codes.append(s.get("code", ""))
            hot_codes = [c for c in hot_codes if c][:20]
        except Exception:
            pass

    for code in hot_codes[:20]:
        try:
            total += len(fetch_announcements(code, limit=5))
        except Exception as e:
            _logger.debug(f"精准公告 {code}: {e}")

    return total


def filter_fake_hotspots(items: list) -> list:
    """Phase 2.1: AI 过滤伪热点（数值规则驱动）。

    标记: clickbait(标题党) / speculation(纯炒作) / stale(旧闻)
    """
    now = datetime.now()
    for item in items:
        title = item.get("title", "")
        content = item.get("content", "") or ""
        if any(k in title for k in ("震惊", "突发", "紧急", "必看")) and len(content) < 20:
            item["fake_risk"] = "clickbait"
            item["quality"] = "low"
        if item.get("type") == "hot_stock":
            pct_m = re.search(r"涨跌幅([+-]?\d+\.?\d*)%", title)
            if pct_m and abs(float(pct_m.group(1))) > 5:
                item["fake_risk"] = "speculation"
                item["quality"] = "medium"
        pub_str = item.get("published_at", "") or ""
        try:
            pub = datetime.strptime(pub_str, "%m-%d %H:%M")
            pub = pub.replace(year=now.year)
            if (now - pub).total_seconds() > 86400:
                item["fake_risk"] = "stale"
                item["quality"] = "low"
        except (ValueError, TypeError):
            pass
    return items
