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
    """全市场信息雷达概览：政策 + 互动易热门 + 公告动态"""
    items = []
    sources = {}

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
