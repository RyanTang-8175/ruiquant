"""
新闻抓取器
多源抓取：东方财富、新浪财经、财联社
"""

import logging
import hashlib
import requests
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
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
                "biz": "web_home_channel",
                "column": "350",
                "order": "1",
                "needInteractData": "0",
                "page_index": "1",
                "page_size": str(limit),
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            data = resp.json()
            items = data.get("data", {}).get("list", [])
            for item in items:
                pub_time = item.get("showtime", "")
                try:
                    pub_dt = datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    pub_dt = datetime.now()

                news.append({
                    "title": item.get("title", "").strip(),
                    "content": item.get("digest", "").strip(),
                    "source": "eastmoney",
                    "url": item.get("url_unique", ""),
                    "published_at": pub_dt,
                    "category": "macro",
                })
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
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            data = resp.json()
            items = data.get("result", {}).get("data", [])
            for item in items:
                pub_ts = int(item.get("ctime", 0))
                pub_dt = datetime.fromtimestamp(pub_ts) if pub_ts > 0 else datetime.now()

                news.append({
                    "title": item.get("title", "").strip(),
                    "content": item.get("intro", "").strip(),
                    "source": "sina",
                    "url": item.get("url", ""),
                    "published_at": pub_dt,
                    "category": "macro",
                })
        except Exception as e:
            logger.warning(f"新浪财经抓取失败: {e}")
        return news

    def fetch_cls(self, limit: int = 30) -> List[Dict]:
        """从财联社抓取快讯"""
        news = []
        try:
            url = "https://www.cls.cn/api/sw"
            params = {
                "app": "CailianpressWeb",
                "os": "web",
                "sv": "8.4.6",
                "type": "telegram",
                "rn": str(limit),
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            data = resp.json()
            items = data.get("data", {}).get("roll_data", [])
            for item in items:
                pub_ts = item.get("ctime", 0)
                pub_dt = datetime.fromtimestamp(pub_ts) if pub_ts > 0 else datetime.now()
                content = item.get("content", "").strip()
                title = item.get("title", "").strip() or content[:50]

                news.append({
                    "title": title,
                    "content": content,
                    "source": "cls",
                    "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
                    "published_at": pub_dt,
                    "category": "macro",
                    "is_important": item.get("level", 0) >= 2,
                })
        except Exception as e:
            logger.warning(f"财联社抓取失败: {e}")
        return news

    def fetch_all(self, limit_per_source: int = 20) -> List[Dict]:
        """从所有源抓取并去重"""
        all_news = []
        all_news.extend(self.fetch_eastmoney(limit_per_source))
        all_news.extend(self.fetch_sina(limit_per_source))
        all_news.extend(self.fetch_cls(limit_per_source))

        return self._deduplicate(all_news)

    def _deduplicate(self, news: List[Dict]) -> List[Dict]:
        """根据标题去重"""
        seen = set()
        unique = []
        for item in news:
            title = item.get("title", "")
            if not title:
                continue
            # 用标题前 20 字符做去重 key
            key = hashlib.md5(title[:20].encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique
