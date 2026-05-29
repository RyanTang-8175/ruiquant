"""
AI 工具执行器
将工具调用映射到实际的数据查询和分析
"""

import json
import logging
from datetime import datetime
from src.utils.database import SessionLocal
from src.data.models import DailyQuote, TechnicalIndicator, StockBasic
from src.scoring.models import ScoreRecord

logger = logging.getLogger(__name__)


class ToolExecutor:
    """工具执行器 — 为 AI 提供数据查询能力"""

    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass

    def execute(self, tool_name: str, arguments: dict) -> str:
        """执行工具调用，返回 JSON 字符串"""
        handlers = {
            "get_stock_quote": self._get_stock_quote,
            "get_technical_analysis": self._get_technical_analysis,
            "get_scoring_result": self._get_scoring_result,
            "get_market_snapshot": self._get_market_snapshot,
            "get_watchlist": self._get_watchlist,
            "get_news": self._get_news,
            "get_financial_data": self._get_financial_data,
            "get_positions": self._get_positions,
            "get_kline_data": self._get_kline_data,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
        try:
            result = handler(**arguments)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _get_stock_quote(self, code: str) -> dict:
        """获取个股最新行情"""
        quote = self.db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).first()
        stock = self.db.query(StockBasic).filter(StockBasic.code == code).first()
        if not quote:
            return {"error": f"未找到 {code} 的行情数据"}
        return {
            "code": code,
            "name": stock.name if stock else "",
            "close": quote.close,
            "open": quote.open,
            "high": quote.high,
            "low": quote.low,
            "volume": quote.volume,
            "amount": round(quote.amount / 1e8, 2) if quote.amount else 0,
            "change_pct": quote.change_pct,
            "turnover_rate": quote.turnover_rate,
            "trade_date": str(quote.trade_date),
        }

    def _get_technical_analysis(self, code: str, days: int = 60) -> dict:
        """获取技术指标分析"""
        indicators = self.db.query(TechnicalIndicator).filter(
            TechnicalIndicator.code == code
        ).order_by(TechnicalIndicator.trade_date.desc()).limit(days).all()

        if not indicators:
            return {"error": f"未找到 {code} 的技术指标数据"}

        latest = indicators[0]
        prev = indicators[1] if len(indicators) > 1 else None

        result = {
            "code": code,
            "date": str(latest.trade_date),
            "ma5": latest.ma5,
            "ma10": latest.ma10,
            "ma20": latest.ma20,
            "ma60": latest.ma60,
            "macd": latest.macd,
            "macd_signal": latest.macd_signal,
            "macd_hist": latest.macd_hist,
            "rsi_6": latest.rsi_6,
            "rsi_12": latest.rsi_12,
            "kdj_k": latest.kdj_k,
            "kdj_d": latest.kdj_d,
            "kdj_j": latest.kdj_j,
            "boll_upper": latest.boll_upper,
            "boll_middle": latest.boll_middle,
            "boll_lower": latest.boll_lower,
        }

        # 趋势判断
        if latest.ma5 and latest.ma10 and latest.ma20:
            if latest.ma5 > latest.ma10 > latest.ma20:
                result["trend"] = "多头排列（看涨）"
            elif latest.ma5 < latest.ma10 < latest.ma20:
                result["trend"] = "空头排列（看跌）"
            else:
                result["trend"] = "交叉整理"

        # MACD 信号
        if latest.macd and latest.macd_signal:
            if latest.macd > latest.macd_signal:
                result["macd_signal"] = "金叉（看涨）"
            else:
                result["macd_signal"] = "死叉（看跌）"

        # RSI 状态
        if latest.rsi_6:
            if latest.rsi_6 > 80:
                result["rsi_status"] = "超买"
            elif latest.rsi_6 < 20:
                result["rsi_status"] = "超卖"
            elif 50 <= latest.rsi_6 <= 70:
                result["rsi_status"] = "健康区间"
            else:
                result["rsi_status"] = "中性"

        return result

    def _get_scoring_result(self, code: str) -> dict:
        """获取量化评分结果"""
        from src.scoring.engine import ScoringEngine
        engine = ScoringEngine()
        result = engine.score_stock(code)
        engine.close()
        if not result:
            return {"error": f"无法计算 {code} 的评分"}
        return {
            "code": result["code"],
            "total_score": result["total_score"],
            "rating": result["rating"],
            "top_factors": sorted(
                result["factors"].items(),
                key=lambda x: x[1], reverse=True
            )[:8],
        }

    def _get_market_snapshot(self) -> dict:
        """获取市场概况"""
        from src.data.collector import DataCollector
        collector = DataCollector()
        snapshot = collector.get_market_snapshot()
        collector.close()
        return snapshot

    def _get_watchlist(self, limit: int = 10) -> dict:
        """获取观察池"""
        from src.scoring.engine import ScoringEngine
        engine = ScoringEngine()
        results = engine.get_watchlist(min_score=65, limit=limit)
        engine.close()
        return {
            "count": len(results),
            "stocks": [{
                "code": r["code"],
                "name": r.get("name", ""),
                "score": r["total_score"],
                "rating": r["rating"],
            } for r in results]
        }

    def _get_news(self, code: str = None, category: str = None, limit: int = 10) -> dict:
        """获取新闻"""
        from src.news.analyzer import NewsAnalyzer
        analyzer = NewsAnalyzer()
        news = analyzer.get_recent_news(limit=limit, category=category, code=code)
        analyzer.close()
        return {
            "count": len(news),
            "news": news,
        }

    def _get_financial_data(self, code: str) -> dict:
        """获取基本面数据（从 DailyQuote 推算）"""
        quotes = self.db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).limit(60).all()

        if not quotes:
            return {"error": f"未找到 {code} 的数据"}

        latest = quotes[0]
        stock = self.db.query(StockBasic).filter(StockBasic.code == code).first()

        # 计算近期涨跌
        changes = {}
        for days_label, idx in [("5d", 4), ("10d", 9), ("20d", 19), ("60d", 59)]:
            if len(quotes) > idx:
                old_price = quotes[idx].close
                if old_price and old_price > 0:
                    changes[days_label] = round((latest.close - old_price) / old_price * 100, 2)

        # 成交量趋势
        vol_5d = sum(q.volume for q in quotes[:5]) / 5 if len(quotes) >= 5 else 0
        vol_20d = sum(q.volume for q in quotes[:20]) / 20 if len(quotes) >= 20 else 0
        vol_ratio = round(vol_5d / vol_20d, 2) if vol_20d > 0 else 0

        return {
            "code": code,
            "name": stock.name if stock else "",
            "current_price": latest.close,
            "changes_pct": changes,
            "avg_turnover_5d": round(sum(q.turnover_rate or 0 for q in quotes[:5]) / 5, 2),
            "volume_ratio_5d_vs_20d": vol_ratio,
            "is_st": stock.is_st if stock else False,
        }

    def _get_positions(self) -> dict:
        """获取模拟盘持仓"""
        from src.trading.engine import TradingEngine
        engine = TradingEngine()
        account = engine.get_account()
        if not account:
            engine.close()
            return {"error": "模拟盘未初始化"}

        positions = engine.get_positions()
        stats = engine.get_stats()
        engine.close()

        return {
            "cash": round(account.cash, 2),
            "status": account.status,
            "positions": [{
                "code": p.code,
                "name": p.name or p.code,
                "quantity": p.quantity,
                "cost_price": p.cost_price,
            } for p in positions],
            "stats": stats,
        }

    def _get_kline_data(self, code: str, days: int = 30) -> dict:
        """获取 K 线数据"""
        quotes = self.db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).limit(days).all()

        if not quotes:
            return {"error": f"未找到 {code} 的 K 线数据"}

        klines = []
        for q in reversed(quotes):
            klines.append({
                "date": str(q.trade_date),
                "open": q.open,
                "high": q.high,
                "low": q.low,
                "close": q.close,
                "volume": q.volume,
                "change_pct": q.change_pct,
            })

        return {
            "code": code,
            "count": len(klines),
            "klines": klines,
        }
