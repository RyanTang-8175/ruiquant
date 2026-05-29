"""
新闻抓取器 - 东方财富 + 财联社（纯requests，无需akshare）
"""

import re
import logging
import requests
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://finance.eastmoney.com/',
}


def fetch_cls_news(limit: int = 20) -> List[Dict]:
    """财联社电报"""
    news = []
    try:
        # 财联社7x24快讯
        url = "https://www.cls.cn/api/sw"
        params = {"app": "CailianpressWeb", "os": "web", "sv": "7.7.5", "rn": str(limit)}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("roll_data", [])
            for item in items:
                if isinstance(item, dict):
                    content = re.sub(r'<[^>]+>', '', str(item.get("content", ""))).strip()
                    title = re.sub(r'<[^>]+>', '', str(item.get("title", "") or content[:60])).strip()
                    if title:
                        news.append({
                            "title": title,
                            "content": content,
                            "source": "cls",
                            "published_at": datetime.fromtimestamp(item.get("ctime", 0)).strftime("%Y-%m-%d %H:%M") if item.get("ctime") else "",
                        })
    except Exception as e:
        logger.warning(f"财联社抓取失败: {e}")
    return news


def fetch_eastmoney_news(limit: int = 20) -> List[Dict]:
    """东方财富财经新闻"""
    news = []
    try:
        url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        params = {
            "client": "web", "biz": "web_news_feeds", "column": "350",
            "order": "1", "page_index": "1", "page_size": str(limit),
            "req_trace": str(int(datetime.now().timestamp() * 1000)),
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        items = resp.json().get("data", {}).get("list", [])
        for item in items:
            title = re.sub(r'<[^>]+>', '', str(item.get("title", ""))).strip()
            content = re.sub(r'<[^>]+>', '', str(item.get("summary", ""))).strip()
            if title:
                news.append({
                    "title": title,
                    "content": content,
                    "source": "eastmoney",
                    "published_at": item.get("showTime", ""),
                })
    except Exception as e:
        logger.warning(f"东方财富抓取失败: {e}")
    return news


def fetch_stock_news(code: str, limit: int = 10) -> List[Dict]:
    """个股新闻（东方财富搜索）"""
    news = []
    try:
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        import json
        param = json.dumps({
            "uid": "", "keyword": code,
            "type": ["cmsArticleWebOld"],
            "client": "web", "clientType": "web", "clientVersion": "curr",
            "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default", "pageIndex": 1, "pageSize": limit, "preTag": "", "postTag": ""}}
        })
        resp = requests.get(url, params={"cb": "jQuery", "param": param}, headers=HEADERS, timeout=10)
        text = resp.text
        # 从 jsonp 中提取 json
        match = text[text.index("(") + 1:text.rindex(")")]
        data = json.loads(match)
        items = data.get("result", {}).get("cmsArticleWebOld", {}).get("list", [])
        for item in items:
            title = re.sub(r'<[^>]+>', '', str(item.get("title", ""))).strip()
            content = re.sub(r'<[^>]+>', '', str(item.get("content", ""))).strip()[:200]
            if title:
                news.append({
                    "title": title,
                    "content": content,
                    "source": item.get("mediaName", "eastmoney"),
                    "url": item.get("url", ""),
                    "published_at": item.get("date", ""),
                })
    except Exception as e:
        logger.warning(f"个股新闻抓取失败 {code}: {e}")
    return news


def fetch_all_news(limit: int = 20) -> List[Dict]:
    """抓取所有新闻"""
    all_news = []
    all_news.extend(fetch_cls_news(limit))
    all_news.extend(fetch_eastmoney_news(limit))
    return all_news[:limit]
