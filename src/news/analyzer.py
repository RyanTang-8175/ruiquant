"""
新闻情绪分析器
使用 DeepSeek 分析新闻情绪
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from openai import OpenAI
from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from src.utils.database import SessionLocal
from src.news.models import NewsItem

logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """新闻情绪分析器"""

    def __init__(self):
        self.db = SessionLocal()
        if DEEPSEEK_API_KEY:
            self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        else:
            self.client = None

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass

    def analyze_batch(self, news_items: List[Dict]) -> List[Dict]:
        """批量分析新闻情绪（用 DeepSeek）"""
        if not self.client or not news_items:
            return news_items

        # 构建批量分析 prompt
        titles = [f"{i+1}. {item['title']}" for i, item in enumerate(news_items[:20])]
        prompt = f"""分析以下 A 股财经新闻的情绪和分类。

新闻列表：
{chr(10).join(titles)}

对每条新闻返回 JSON 数组，每个元素包含：
- idx: 序号（从1开始）
- sentiment: 情绪分数（-1 到 1，-1=极度利空，0=中性，1=极度利好）
- category: 分类（policy=政策, sector=板块, company=公司, macro=宏观）
- codes: 相关股票代码数组（如 ["600519"]，不确定则为空数组）
- important: 是否重要（true/false）

只返回 JSON 数组，不要其他文字。"""

        try:
            response = self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000,
            )
            content = response.choices[0].message.content.strip()
            # 尝试解析 JSON
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            results = json.loads(content)

            # 合并结果
            for r in results:
                idx = r.get("idx", 0) - 1
                if 0 <= idx < len(news_items):
                    news_items[idx]["sentiment_score"] = r.get("sentiment", 0)
                    news_items[idx]["category"] = r.get("category", "macro")
                    news_items[idx]["related_codes"] = r.get("codes", [])
                    news_items[idx]["is_important"] = r.get("important", False)

        except Exception as e:
            logger.warning(f"新闻情绪分析失败: {e}")

        return news_items

    def save_news(self, news_items: List[Dict]) -> int:
        """保存新闻到数据库"""
        saved = 0
        try:
            for item in news_items:
                # 检查是否已存在（按标题去重）
                existing = self.db.query(NewsItem).filter(
                    NewsItem.title == item["title"]
                ).first()
                if existing:
                    continue

                record = NewsItem(
                    title=item["title"],
                    content=item.get("content", ""),
                    source=item.get("source", ""),
                    url=item.get("url", ""),
                    published_at=item.get("published_at", datetime.now()),
                    related_codes=item.get("related_codes", []),
                    sentiment_score=item.get("sentiment_score"),
                    category=item.get("category", "macro"),
                    is_important=item.get("is_important", False),
                )
                self.db.add(record)
                saved += 1

            self.db.commit()
            logger.info(f"保存了 {saved} 条新闻")
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存新闻失败: {e}")
        return saved

    def get_recent_news(self, limit: int = 20, category: str = None,
                        code: str = None) -> List[Dict]:
        """获取最近新闻"""
        query = self.db.query(NewsItem).order_by(NewsItem.published_at.desc())

        if category:
            query = query.filter(NewsItem.category == category)

        items = query.limit(limit * 3).all()  # 多取一些用于代码筛选

        results = []
        for item in items:
            news_dict = {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "source": item.source,
                "url": item.url,
                "published_at": item.published_at.isoformat() if item.published_at else "",
                "sentiment_score": item.sentiment_score,
                "category": item.category,
                "related_codes": item.related_codes or [],
                "is_important": item.is_important,
            }
            # 按股票代码筛选
            if code:
                codes = item.related_codes or []
                if code not in codes:
                    continue
            results.append(news_dict)
            if len(results) >= limit:
                break

        return results

    def get_stock_sentiment(self, code: str, days: int = 7) -> Optional[float]:
        """获取某只股票的综合情绪分数"""
        since = datetime.now() - timedelta(days=days)
        items = self.db.query(NewsItem).filter(
            NewsItem.published_at >= since,
            NewsItem.sentiment_score.isnot(None),
        ).all()

        scores = []
        for item in items:
            codes = item.related_codes or []
            if code in codes:
                scores.append(item.sentiment_score)

        if not scores:
            return None
        return sum(scores) / len(scores)
