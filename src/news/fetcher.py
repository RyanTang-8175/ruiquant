"""
新闻抓取器
多源抓取：东方财富、新浪财经
"""

import re
import logging
import hashlib
import requests
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://finance.eastmoney.com/',
}


class NewsFetcher:
    """多源财经新闻抓取器"""

    def fetch_eastmoney(self, limit: int = 30) -> List[Dict]:
        """从东方财富抓取财经新闻"""
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
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", {}).get("list", [])

            for item in items:
                pub_time = item.get("showTime", "")
                try:
                    pub_dt = datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    pub_dt = datetime.now()

                title = (item.get("title", "") or "").strip()
                content = (item.get("summary", "") or "").strip()
                if title:
                    news.append({
                        "title": title,
                        "content": content,
                        "source": "eastmoney",
                        "url": item.get("uniqueUrl", "") or item.get("url", ""),
                        "published_at": pub_dt,
                        "category": "macro",
                    })
            logger.info(f"东方财富: 抓取 {len(news)} 条")
        except Exception as e:
            logger.warning(f"东方财富抓取失败: {e}")
        return news

    def fetch_sina(self, limit: int = 30) -> List[Dict]:
        """从新浪财经抓取财经新闻"""
        news = []
        try:
            url = "https://feed.mix.sina.com.cn/api/roll/get"
            params = {
                "pageid": "153",
                "lid": "2516",
                "k": "",
                "num": str(limit),
                "page": "1",
                "r": "0.1",
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("result", {}).get("data", [])

            for item in items:
                pub_ts = int(item.get("ctime", 0))
                pub_dt = datetime.fromtimestamp(pub_ts) if pub_ts > 1000000000 else datetime.now()

                title = (item.get("title", "") or "").strip()
                if title:
                    news.append({
                        "title": title,
                        "content": (item.get("intro", "") or item.get("summary", "")).strip(),
                        "source": "sina",
                        "url": item.get("url", ""),
                        "published_at": pub_dt,
                        "category": "macro",
                    })
            logger.info(f"新浪财经: 抓取 {len(news)} 条")
        except Exception as e:
            logger.warning(f"新浪财经抓取失败: {e}")
        return news

    def fetch_all(self, limit_per_source: int = 20) -> List[Dict]:
        """从所有源抓取并去重"""
        all_news = []
        all_news.extend(self.fetch_eastmoney(limit_per_source))
        all_news.extend(self.fetch_sina(limit_per_source))

        result = self._deduplicate(all_news)
        logger.info(f"总计抓取 {len(result)} 条去重新闻")
        return result

    def _deduplicate(self, news: List[Dict]) -> List[Dict]:
        """根据标题去重"""
        seen = set()
        unique = []
        for item in news:
            title = item.get("title", "")
            if not title or len(title) < 4:
                continue
            key = hashlib.md5(title[:20].encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique
