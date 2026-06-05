"""AI 工具执行器 — 每个工具独立超时保护"""

import json, logging
from src.research.harness import ResearchHarness
from src.research.evaluator import ResearchEvaluator
from src.research.strategy import StrategyExplorer, StrategyGovernor
from src.scoring.evidence import IFindEvidenceScorer

logger = logging.getLogger(__name__)

class ToolExecutor:
    def __init__(self): pass
    def close(self): pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False

    def execute(self, tool_name: str, arguments: dict) -> str:
        handlers = {
            "get_stock_quote": self._get_stock_quote,
            "get_technical_analysis": self._get_technical_analysis,
            "get_scoring_result": self._get_scoring_result,
            "get_market_snapshot": self._get_market_snapshot,
            "get_sector_candidates": self._get_sector_candidates,
            "get_watchlist": self._get_watchlist,
            "get_news": self._get_news,
            "get_financial_data": self._get_financial_data,
            "get_positions": self._get_positions,
            "get_kline_data": self._get_kline_data,
            "get_info_radar": self._get_info_radar,
            "ifind_smart_stock_picking": self._ifind_smart_stock_picking,
            "ifind_company_research": self._ifind_company_research,
            "ifind_market_radar": self._ifind_market_radar,
            "get_research_memory": self._get_research_memory,
            "ifind_evidence_score": self._ifind_evidence_score,
            "get_research_score_comparison": self._get_research_score_comparison,
            "govern_strategy_tier": self._govern_strategy_tier,
            "sweep_strategy_values": self._sweep_strategy_values,
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
        if not q:
            return {"error": f"无{code}行情", "data_quality": "unavailable",
                    "source": "none"}
        quality = q.get("_quality", {})
        return {
            "code": q.get("code"), "name": q.get("name"),
            "price": q.get("price"), "change_pct": q.get("change_pct"),
            "open": q.get("open"), "high": q.get("high"), "low": q.get("low"),
            "pre_close": q.get("prev_close"), "amplitude": q.get("amplitude"),
            "volume": q.get("volume"),
            "amount_display": f"{(q.get('amount',0) or 0)/1e8:.1f}亿",
            "turnover": q.get("turnover"), "volume_ratio": q.get("volume_ratio", 1.0),
            "pe_ratio": q.get("pe_ratio"),
            "heat_label": (
                "放量拉升" if (q.get("volume_ratio",0) or 0) > 1.2 and (q.get("change_pct",0) or 0) > 2
                else "缩量下跌" if (q.get("volume_ratio",0) or 0) < 0.8 and (q.get("change_pct",0) or 0) < 0
                else "温和放量" if (q.get("volume_ratio",0) or 0) > 1.0
                else "正常"),
            "data_quality": quality.get("quality_level", "unknown"),
            "data_source": quality.get("source", "unknown"),
            "is_delayed": quality.get("is_delayed", True),
        }

    def _get_technical_analysis(self, code: str, days: int = 60) -> dict:
        from src.data.realtime import get_kline, get_realtime_quote; import pandas as pd
        kl = get_kline(code, period="101", count=days)
        if not kl: return {"error":f"无{code}K线数据"}
        df = pd.DataFrame(kl); c = df['close']
        ma5 = round(float(c.rolling(5).mean().iloc[-1]),2) if len(c)>=5 else 0
        ma10 = round(float(c.rolling(10).mean().iloc[-1]),2) if len(c)>=10 else 0
        ma20 = round(float(c.rolling(20).mean().iloc[-1]),2) if len(c)>=20 else 0
        trend = "多头排列" if ma5>ma10>ma20 else "空头排列" if ma5<ma10<ma20 else "交叉整理"

        live = get_realtime_quote(code)
        live_price = live.get("price", 0) if live else 0
        kline_close = float(c.iloc[-1])
        note = ""
        if live_price > 0 and abs(live_price - kline_close) > 0.01:
            note = f"K线均线基于历史收盘(最新{kline_close:.2f})计算，与实时价({live_price:.2f})可能不同。分析请以实时行情为准。"

        return {"code":code,"trend":trend,"ma5":ma5,"ma10":ma10,"ma20":ma20,
                "kline_latest_close":kline_close,"live_price":live_price,
                "note":note,"data_points":len(kl)}

    def _get_scoring_result(self, code: str) -> dict:
        from src.scoring.engine import V6ScoringEngine
        with V6ScoringEngine() as e:
            r = e.score_stock(code)
        if not r:
            return {"error": f"无{code}评分", "data_quality": "unavailable"}
        quo = None
        try:
            from src.data.realtime import get_realtime_quote
            quo = get_realtime_quote(code)
        except: pass
        quality = quo.get("_quality", {}) if quo else {}
        d = r.to_dict()
        return {
            "code": d["code"], "name": d.get("name", ""),
            "total_score": d["total_score"],
            "status_label": d["status_label"],
            "risk_level": d["risk_level"],
            "dimensions": {
                "heat": {"score": d["heat"]["score"], "detail": r.heat.explanation},
                "support": {"score": d["support"]["score"], "detail": r.support.explanation},
                "theme": {"score": d["theme"]["score"], "detail": r.theme.explanation},
                "continuation": {"score": d["continuation"]["score"], "detail": r.continuation.explanation},
                "strategy_match": {"score": d["strategy_match"]["score"], "detail": r.strategy_match.explanation},
            },
            "anti_quant": d["anti_quant"],
            "matched_strategies": d.get("matched_strategies", []),
            "data_quality": quality.get("quality_level", "unknown"),
            "quote_source": quality.get("source", "unknown"),
        }

    def _get_market_snapshot(self) -> dict:
        from src.data.realtime import get_market_overview, get_top_stocks
        ov = get_market_overview()
        up = get_top_stocks(sort_field="changepercent",asc=False,limit=5)
        dn = get_top_stocks(sort_field="changepercent",asc=True,limit=5)
        return {"indices":ov.get("indices",[]),"top_gainers":[{"name":g["name"],"code":g["code"],"pct":g["change_pct"]} for g in up],"top_losers":[{"name":g["name"],"code":g["code"],"pct":g["change_pct"]} for g in dn]}

    def _get_watchlist(self, limit: int = 10) -> dict:
        from src.scoring.engine import V6ScoringEngine
        with V6ScoringEngine() as e:
            r = e.get_watchlist_v6(min_score=45, limit=limit)
        return {
            "count": len(r),
            "stocks": [
                {
                    "code": s["code"],
                    "name": s.get("name", ""),
                    "score": s["total_score"],
                    "status": s.get("status_label", ""),
                    "risk": s.get("risk_level", ""),
                    "anti_quant": s.get("anti_quant", {}),
                }
                for s in r
            ],
        }

    def _get_sector_candidates(self, query: str, limit: int = 5) -> dict:
        """按行业/概念返回具名候选，供 AI 直接回答，不再让用户自己去雷达页找。"""
        from src.data.stock_list import detect_stock_groups, resolve_stock_name
        from src.data.realtime import get_realtime_quote
        from src.scoring.engine import V6ScoringEngine

        groups = detect_stock_groups(query)[:4]
        if not groups:
            return {"groups": [], "note": "未识别到行业或概念关键词"}

        payload = []
        with V6ScoringEngine() as engine:
            for kind, name, codes in groups:
                items = []
                for code in codes[:12]:
                    quote = None
                    result = None
                    try:
                        quote = get_realtime_quote(code)
                        if quote:
                            quote["name"] = resolve_stock_name(code, quote.get("name", ""))
                            result = engine.score_stock(code, quote=quote)
                    except Exception:
                        quote = None
                    if result:
                        d = result.to_dict()
                        anti = d.get("anti_quant", {})
                        items.append({
                            "code": code,
                            "name": resolve_stock_name(code, d.get("name", "")),
                            "score": round(float(d.get("total_score", 0)), 1),
                            "change_pct": quote.get("change_pct", 0) if quote else None,
                            "status": d.get("status_label", ""),
                            "risk": d.get("risk_level", ""),
                            "anti_quant_level": anti.get("level") or anti.get("risk_level", ""),
                            "triggers": anti.get("triggers", [])[:3],
                            "role": self._candidate_role(name, code),
                            "action": self._candidate_action(anti.get("level") or anti.get("risk_level", "")),
                        })
                    else:
                        items.append({
                            "code": code,
                            "name": resolve_stock_name(code),
                            "score": None,
                            "change_pct": None,
                            "status": "待实时确认",
                            "risk": "未知",
                            "anti_quant_level": "未知",
                            "triggers": [],
                            "role": self._candidate_role(name, code),
                            "action": "等待实时确认",
                        })
                items.sort(key=lambda x: (x["score"] is not None, x["score"] or 0), reverse=True)
                payload.append({
                    "kind": kind,
                    "name": name,
                    "candidates": self._prioritize_representative_candidates(name, items, max(1, limit)),
                })

        return {
            "groups": payload,
            "answer_rule": "必须直接给候选表、优先顺序、参与条件、放弃条件、资金纪律，不要让用户自己去雷达页找。",
        }

    @staticmethod
    def _candidate_role(group_name: str, code: str) -> str:
        if group_name in ("电力", "公用事业"):
            if code in {"600900", "601985", "600011", "600886"}:
                return "稳健观察"
            return "弹性备选"
        if group_name in ("半导体芯片", "电子"):
            if code in {"688981", "688012", "688008", "603501"}:
                return "主线弹性"
            return "高弹备选"
        if group_name == "白酒":
            return "消费权重"
        return "短线候选"

    @staticmethod
    def _prioritize_representative_candidates(group_name: str, items: list, limit: int) -> list:
        """保证行业代表股不会因公开源临时报价缺失而被前三名挤掉。"""
        preferred_map = {
            "半导体芯片": ["688981", "688012", "688008"],
            "电子": ["688981", "688012", "688008"],
            "电力": ["600900", "601985", "003816"],
            "公用事业": ["600900", "601985", "003816"],
        }
        preferred = preferred_map.get(group_name, [])
        by_code = {item.get("code"): item for item in items}
        picked = []
        for code in preferred:
            item = by_code.get(code)
            if item:
                picked.append(item)
                break
        for item in items:
            if item not in picked:
                picked.append(item)
        return picked[:limit]

    @staticmethod
    def _candidate_action(risk_level: str) -> str:
        if risk_level in ("高", "极高"):
            return "只观察不追"
        if risk_level in ("低", "中"):
            return "低吸验证"
        return "等待实时确认"

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

    def _get_info_radar(self, code: str, limit: int = 10) -> dict:
        from src.news.radar import fetch_radar_for_stock
        try:
            result = fetch_radar_for_stock(code, limit=limit)
            return result
        except Exception as e:
            return {"error": f"雷达获取失败: {str(e)[:80]}", "code": code, "total": 0}

    def _ifind_smart_stock_picking(self, query: str, limit: int = 10) -> dict:
        try:
            from src.data.providers.registry import get_provider, provider_status

            provider = get_provider()
            status = provider_status()
            if provider.source_name != "ifind" or not hasattr(provider, "smart_stock_picking"):
                return {
                    "query": query,
                    "count": 0,
                    "stocks": [],
                    "data_quality": "unavailable",
                    "message": "当前未启用 iFinD，不能使用智能选股；请基于公开源低置信度回答。",
                    "provider_status": status,
                }
            rows = provider.smart_stock_picking(query, limit=min(int(limit or 10), 20))
            return {
                "query": query,
                "count": len(rows),
                "stocks": rows,
                "data_quality": "professional" if rows else "empty",
                "data_source": "ifind_smart_stock_picking",
                "usage_note": "智能选股按低频缓存调用，候选只代表研究入口，仍需行情、公告、反量化风险交叉验证。",
                "provider_status": status,
            }
        except Exception as e:
            return {"query": query, "count": 0, "stocks": [], "error": f"iFinD智能选股失败: {str(e)[:80]}"}

    def _ifind_company_research(self, code: str, profile: str = "quick") -> dict:
        try:
            return ResearchHarness().company_research(code, profile=profile or "quick")
        except Exception as e:
            return {
                "code": code,
                "profile": profile,
                "error": f"iFinD公司研究失败: {str(e)[:100]}",
                "data_quality": "unavailable",
            }

    def _ifind_market_radar(self, queries: list = None) -> dict:
        try:
            return ResearchHarness().market_radar(queries=queries)
        except Exception as e:
            return {
                "queries": queries or [],
                "themes": [],
                "error": f"iFinD市场雷达失败: {str(e)[:100]}",
                "data_quality": "unavailable",
            }

    def _get_research_memory(self, limit: int = 8) -> dict:
        try:
            return ResearchHarness().knowledge_context(limit=min(int(limit or 8), 20))
        except Exception as e:
            return {"runs": [], "insights": [], "error": f"研究记忆读取失败: {str(e)[:100]}"}

    def _ifind_evidence_score(self, code: str, profile: str = "quick") -> dict:
        try:
            research = ResearchHarness().company_research(code, profile=profile or "quick")
            return IFindEvidenceScorer().score(research)
        except Exception as e:
            return {
                "code": code,
                "profile": profile,
                "error": f"iFinD证据评分失败: {str(e)[:100]}",
                "opportunity_score": 0,
                "risk_score": 100,
                "confidence": "低",
                "action": "只观察",
                "dimensions": {},
                "evidence_summary": [],
            }

    def _get_research_score_comparison(self) -> dict:
        try:
            from src.memory.analysis_memory import AnalysisMemory

            with AnalysisMemory() as memory:
                rows = memory.get_verification_results()
            return ResearchEvaluator().compare_score_systems(rows)
        except Exception as e:
            return {"error": f"新旧评分对比失败: {str(e)[:100]}", "ifind": {}, "legacy": {}}

    def _govern_strategy_tier(self, metrics: dict = None) -> dict:
        try:
            return StrategyGovernor().decide(metrics or {})
        except Exception as e:
            return {"tier": "进入观察", "error": f"四档策略判断失败: {str(e)[:100]}", "allow_real_trade": False}

    def _sweep_strategy_values(self, base_config: dict = None, dimension: str = "risk_limit", values: list = None) -> dict:
        try:
            values = values or [55, 65, 75]
            return StrategyExplorer().sweep_filter_values(base_config or {"universe": "A股", "holding": "1-2天"}, dimension, values)
        except Exception as e:
            return {"executed": 0, "skipped_duplicates": 0, "error": f"策略探索失败: {str(e)[:100]}"}
