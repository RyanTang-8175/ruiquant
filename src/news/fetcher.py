"""
新闻抓取器
使用 AKShare 获取财联社电报 + 东方财富新闻
"""

import logging
import re
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


def fetch_cls_news(limit: int = 30) -> List[Dict]:
    """获取财联社电报快讯（最权威的A股实时新闻）"""
    try:
        import akshare as ak
        df = ak.stock_info_global_cls()
        if df is None or df.empty:
            return []

        news = []
        for _, row in df.head(limit).iterrows():
            title = str(row.get("标题", "") or row.get("内容", ""))[:100]
            content = str(row.get("内容", "") or "")
            # 清理HTML标签
            title = re.sub(r'<[^>]+>', '', title).strip()
            content = re.sub(r'<[^>]+>', '', content).strip()

            if title:
                news.append({
                    "title": title,
                    "content": content,
                    "source": "cls",
                    "published_at": str(row.get("时间", "")),
                    "category": "macro",
                })
        logger.info(f"财联社: 抓取 {len(news)} 条")
        return news
    except ImportError:
        logger.warning("akshare 未安装，跳过财联社新闻")
        return []
    except Exception as e:
        logger.warning(f"财联社抓取失败: {e}")
        return []


def fetch_stock_news(code: str, limit: int = 10) -> List[Dict]:
    """获取个股新闻（东方财富）"""
    try:
        import akshare as ak
        df = ak.stock_news_em(symbol=code)
        if df is None or df.empty:
            return []

        news = []
        for _, row in df.head(limit).iterrows():
            title = str(row.get("新闻标题", ""))[:100]
            content = str(row.get("新闻内容", ""))
            url = str(row.get("新闻链接", ""))
            source = str(row.get("文章来源", ""))
            pub_time = str(row.get("发布时间", ""))

            title = re.sub(r'<[^>]+>', '', title).strip()
            content = re.sub(r'<[^>]+>', '', content).strip()

            if title:
                news.append({
                    "title": title,
                    "content": content[:200],
                    "source": source or "eastmoney",
                    "url": url,
                    "published_at": pub_time,
                    "category": "company",
                })
        logger.info(f"个股新闻 {code}: {len(news)} 条")
        return news
    except Exception as e:
        logger.warning(f"个股新闻抓取失败 {code}: {e}")
        return []


def fetch_eastmoney_news(limit: int = 20) -> List[Dict]:
    """东方财富财经新闻（备用）"""
    import requests
    news = []
    try:
        url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        params = {
            "client": "web",
            "biz": "web_news_feeds",
            "column": "357",
            "order": "1",
            "page_index": "1",
            "page_size": str(limit),
            "req_trace": str(int(datetime.now().timestamp() * 1000)),
        }
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.eastmoney.com/'}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        items = resp.json().get("data", {}).get("list", [])

        for item in items:
            title = re.sub(r'<[^>]+>', '', str(item.get("title", ""))).strip()
            content = re.sub(r'<[^>]+>', '', str(item.get("summary", ""))).strip()
            if title:
                news.append({
                    "title": title,
                    "content": content,
                    "source": "eastmoney",
                    "url": item.get("uniqueUrl", ""),
                    "published_at": item.get("showTime", ""),
                    "category": "macro",
                })
        logger.info(f"东方财富: 抓取 {len(news)} 条")
    except Exception as e:
        logger.warning(f"东方财富抓取失败: {e}")
    return news


def fetch_all_news(limit: int = 30) -> List[Dict]:
    """抓取所有新闻源"""
    all_news = []
    all_news.extend(fetch_cls_news(limit))
    if len(all_news) < 5:
        all_news.extend(fetch_eastmoney_news(limit))
    return all_news[:limit]
