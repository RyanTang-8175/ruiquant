"""
AI 工具执行器
为 AI 提供实时数据查询能力
"""

import json
import logging
from src.data.realtime import get_realtime_quote, get_kline

logger = logging.getLogger(__name__)


class ToolExecutor:
    """工具执行器"""

    def __init__(self):
        self.db = None

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def execute(self, tool_name: str, arguments: dict) -> str:
        """执行工具调用"""
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
        """实时行情"""
        quote = get_realtime_quote(code)
        if not quote:
            return {"error": f"未找到 {code} 的行情数据"}
        return quote

    def _get_technical_analysis(self, code: str, days: int = 60) -> dict:
        """技术分析（从数据库读指标）"""
        try:
            from src.utils.database import SessionLocal
            from src.data.models import TechnicalIndicator
            db = SessionLocal()
            try:
                indicators = db.query(TechnicalIndicator).filter(
                    TechnicalIndicator.code == code
                ).order_by(TechnicalIndicator.trade_date.desc()).limit(days).all()

                if not indicators:
                    return {"error": f"无技术指标数据，请先采集"}

                latest = indicators[0]
                result = {
                    "code": code,
                    "date": str(latest.trade_date),
                    "ma5": latest.ma5, "ma10": latest.ma10, "ma20": latest.ma20,
                    "macd": latest.macd, "macd_signal": latest.macd_signal,
                    "rsi_6": latest.rsi_6, "rsi_12": latest.rsi_12,
                    "kdj_k": latest.kdj_k, "kdj_d": latest.kdj_d,
                    "boll_upper": latest.boll_upper, "boll_lower": latest.boll_lower,
                }

                # 趋势判断
                if latest.ma5 and latest.ma10 and latest.ma20:
                    if latest.ma5 > latest.ma10 > latest.ma20:
                        result["trend"] = "多头排列（看涨）"
                    elif latest.ma5 < latest.ma10 < latest.ma20:
                        result["trend"] = "空头排列（看跌）"
                    else:
                        result["trend"] = "交叉整理"

                if latest.rsi_6:
                    if latest.rsi_6 > 80: result["rsi_status"] = "超买"
                    elif latest.rsi_6 < 20: result["rsi_status"] = "超卖"
                    else: result["rsi_status"] = "正常"

                return result
            finally:
                db.close()
        except Exception as e:
            return {"error": str(e)}

    def _get_scoring_result(self, code: str) -> dict:
        """量化评分"""
        try:
            from src.scoring.engine import ScoringEngine
            with ScoringEngine() as engine:
                result = engine.score_stock(code)
            if not result:
                return {"error": f"无法计算 {code} 的评分"}
            return {
                "code": result["code"],
                "total_score": result["total_score"],
                "rating": result["rating"],
                "top_factors": sorted(result["factors"].items(), key=lambda x: x[1], reverse=True)[:8],
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_market_snapshot(self) -> dict:
        """市场概况"""
        try:
            from src.data.realtime import get_market_overview, get_top_stocks
            overview = get_market_overview()
            gainers = get_top_stocks(sort_field="f3", asc=False, limit=5)
            losers = get_top_stocks(sort_field="f3", asc=True, limit=5)
            return {
                "indices": overview.get("indices", []),
                "top_gainers": [{"name": g["name"], "code": g["code"], "pct": g["change_pct"]} for g in gainers],
                "top_losers": [{"name": g["name"], "code": g["code"], "pct": g["change_pct"]} for g in losers],
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_watchlist(self, limit: int = 10) -> dict:
        """观察池"""
        try:
            from src.scoring.engine import ScoringEngine
            with ScoringEngine() as engine:
                results = engine.get_watchlist(min_score=65, limit=limit)
            return {
                "count": len(results),
                "stocks": [{"code": r["code"], "name": r.get("name", ""), "score": r["total_score"], "rating": r["rating"]} for r in results],
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_news(self, code: str = None, category: str = None, limit: int = 10) -> dict:
        """新闻"""
        try:
            from src.news.fetcher import fetch_all_news, fetch_stock_news
            if code:
                news = fetch_stock_news(code, limit)
            else:
                news = fetch_all_news(limit)
            return {"count": len(news), "news": news}
        except Exception as e:
            return {"error": str(e)}

    def _get_financial_data(self, code: str) -> dict:
        """基本面数据"""
        quote = get_realtime_quote(code)
        if not quote:
            return {"error": f"未找到 {code} 的数据"}
        return {
            "code": code,
            "name": quote.get("name", ""),
            "price": quote.get("price", 0),
            "change_pct": quote.get("change_pct", 0),
            "pe_ratio": quote.get("pe_ratio", 0),
            "turnover": quote.get("turnover", 0),
            "volume": quote.get("volume", 0),
            "amount": quote.get("amount", 0),
        }

    def _get_positions(self) -> dict:
        """模拟盘持仓"""
        try:
            from src.trading.engine import TradingEngine
            with TradingEngine() as engine:
                account = engine.get_account()
                if not account:
                    return {"error": "模拟盘未初始化"}
                positions = engine.get_positions()
                stats = engine.get_stats()
            return {
                "cash": round(account.cash, 2),
                "status": account.status,
                "positions": [{"code": p.code, "name": p.name or p.code, "qty": p.quantity, "cost": p.cost_price} for p in positions],
                "stats": stats,
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_kline_data(self, code: str, days: int = 30) -> dict:
        """K线数据"""
        klines = get_kline(code, period="101", count=days)
        if not klines:
            return {"error": f"未找到 {code} 的K线数据"}
        return {"code": code, "count": len(klines), "klines": klines[-10:]}  # 只返回最近10条给AI
