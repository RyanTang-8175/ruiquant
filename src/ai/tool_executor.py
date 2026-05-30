"""AI 工具执行器 — 每个工具独立超时保护"""

import json, logging

logger = logging.getLogger(__name__)

class ToolExecutor:
    def __init__(self): pass
    def close(self): pass

    def execute(self, tool_name: str, arguments: dict) -> str:
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
            return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)
        try:
            return json.dumps(handler(**arguments), ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"Tool {tool_name} error: {e}")
            return json.dumps({"error": f"工具执行失败: {str(e)[:80]}"}, ensure_ascii=False)

    def _get_stock_quote(self, code: str) -> dict:
        from src.data.realtime import get_realtime_quote
        q = get_realtime_quote(code)
        return {"error":f"无{code}行情"} if not q else {"code":q.get("code"),"name":q.get("name"),"price":q.get("price"),"change_pct":q.get("change_pct"),"open":q.get("open"),"high":q.get("high"),"low":q.get("low"),"volume":q.get("volume"),"turnover":q.get("turnover")}

    def _get_technical_analysis(self, code: str, days: int = 60) -> dict:
        from src.data.realtime import get_kline; import pandas as pd
        kl = get_kline(code, period="101", count=days)
        if not kl: return {"error":f"无{code}K线数据"}
        df = pd.DataFrame(kl); c = df['close']
        ma5 = round(float(c.rolling(5).mean().iloc[-1]),2) if len(c)>=5 else 0
        ma10 = round(float(c.rolling(10).mean().iloc[-1]),2) if len(c)>=10 else 0
        ma20 = round(float(c.rolling(20).mean().iloc[-1]),2) if len(c)>=20 else 0
        trend = "多头排列" if ma5>ma10>ma20 else "空头排列" if ma5<ma10<ma20 else "交叉整理"
        return {"code":code,"trend":trend,"ma5":ma5,"ma10":ma10,"ma20":ma20,"latest_close":float(c.iloc[-1]),"data_points":len(kl)}

    def _get_scoring_result(self, code: str) -> dict:
        from src.scoring.engine import ScoringEngine
        with ScoringEngine() as e: r = e.score_stock(code)
        return {"error":f"无{code}评分"} if not r else {"code":r['code'],"total_score":r['total_score'],"rating":r['rating'],"top_factors":sorted(r['factors'].items(),key=lambda x:x[1],reverse=True)[:5]}

    def _get_market_snapshot(self) -> dict:
        from src.data.realtime import get_market_overview, get_top_stocks
        ov = get_market_overview()
        up = get_top_stocks(sort_field="changepercent",asc=False,limit=5)
        dn = get_top_stocks(sort_field="changepercent",asc=True,limit=5)
        return {"indices":ov.get("indices",[]),"top_gainers":[{"name":g["name"],"code":g["code"],"pct":g["change_pct"]} for g in up],"top_losers":[{"name":g["name"],"code":g["code"],"pct":g["change_pct"]} for g in dn]}

    def _get_watchlist(self, limit: int = 10) -> dict:
        from src.scoring.engine import ScoringEngine
        with ScoringEngine() as e: r = e.get_watchlist(min_score=50,limit=limit)
        return {"count":len(r),"stocks":[{"code":s["code"],"name":s.get("name",""),"score":s["total_score"],"rating":s["rating"]} for s in r]}

    def _get_news(self, code: str = None, limit: int = 10) -> dict:
        from src.news.fetcher import fetch_all_news, fetch_stock_news
        news = fetch_stock_news(code, limit) if code else fetch_all_news(limit)
        return {"count":len(news),"news":news[:15]}

    def _get_financial_data(self, code: str) -> dict:
        from src.data.realtime import get_realtime_quote
        q = get_realtime_quote(code)
        return {"error":f"无{code}数据"} if not q else {"code":q.get("code"),"name":q.get("name"),"price":q.get("price"),"change_pct":q.get("change_pct"),"pe_ratio":q.get("pe_ratio"),"turnover":q.get("turnover")}

    def _get_positions(self) -> dict:
        from src.trading.engine import TradingEngine
        with TradingEngine() as e:
            a = e.get_account()
            if not a: return {"error":"模拟盘未初始化"}
            ps = e.get_positions(); st = e.get_stats()
        return {"cash":round(a.cash,2),"status":a.status,"stats":st,"positions":[{"code":p.code,"name":p.name or p.code,"qty":p.quantity,"cost":p.cost_price} for p in ps]}

    def _get_kline_data(self, code: str, days: int = 30) -> dict:
        from src.data.realtime import get_kline
        kls = get_kline(code, period="101", count=days)
        return {"code":code,"count":len(kls),"recent":kls[-5:] if kls else []}
