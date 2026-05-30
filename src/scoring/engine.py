"""
评分引擎 — 实时行情快速评分
"""

import logging, numpy as np, pandas as pd
from datetime import datetime
from src.data.models import DailyQuote, TechnicalIndicator, StockBasic
from src.scoring.models import ScoreRecord
from src.utils.database import SessionLocal

logger = logging.getLogger(__name__)

QUICK_WEIGHTS = {
    'momentum': 0.25, 'turnover': 0.20, 'volatility': 0.20,
    'volume_ratio': 0.20, 'trend': 0.15,
}

class ScoringEngine:
    def __init__(self):
        self.db = SessionLocal()
        self.weights = QUICK_WEIGHTS

    def close(self):
        try: self.db.close()
        except: pass
    def __enter__(self): return self
    def __exit__(self, *a): self.close()

    def quick_score(self, q: dict) -> dict:
        p=q.get("price",0); o=q.get("open",0); h=q.get("high",0)
        l=q.get("low",0); chg=q.get("change_pct",0); turn=q.get("turnover",0)

        f={}
        # momentum
        if chg>5: f['momentum']=85
        elif chg>2: f['momentum']=70
        elif chg>0: f['momentum']=55
        elif chg>-2: f['momentum']=45
        elif chg>-5: f['momentum']=30
        else: f['momentum']=15
        # turnover
        if turn>20: f['turnover']=25
        elif turn>10: f['turnover']=40
        elif turn>3: f['turnover']=65
        elif turn>1: f['turnover']=80
        elif turn>.3: f['turnover']=60
        else: f['turnover']=40
        # volatility
        if h!=l:
            body=abs(p-o)/(h-l)
            if body>.7: f['volatility']=80 if p>o else 30
            elif body>.4: f['volatility']=65
            elif body>.15: f['volatility']=50
            else: f['volatility']=40
        else: f['volatility']=50
        # volume
        if turn>5: f['volume_ratio']=70
        elif turn>2: f['volume_ratio']=60
        elif turn>.8: f['volume_ratio']=50
        else: f['volume_ratio']=40
        # trend
        if h!=l:
            pos=(p-l)/(h-l)
            if pos>.8: f['trend']=80
            elif pos>.6: f['trend']=65
            elif pos>.4: f['trend']=50
            elif pos>.2: f['trend']=35
            else: f['trend']=20
        else: f['trend']=50

        tw=sum(self.weights.get(k,.1) for k in f)
        total=sum(f[k]*self.weights.get(k,.1) for k in f)/tw if tw>0 else 50
        total=min(100,max(0,total))
        rating="强关注" if total>=80 else "观察" if total>=65 else "中性" if total>=50 else "不追"
        return {'code':q.get('code',''),'total_score':round(total,1),'rating':rating,'factors':f,'quick':True,'calculated_at':datetime.now()}

    def score_stock(self, code: str) -> dict:
        from src.data.realtime import get_realtime_quote
        q=get_realtime_quote(code)
        if q and q.get("price",0)>0:
            r=self.quick_score(q); r['name']=q.get('name',''); return r
        return None

    def score_all_stocks(self, limit: int = 80) -> list:
        from src.data.realtime import get_top_stocks
        stocks=get_top_stocks(sort_field="amount",asc=False,limit=limit)
        results=[]
        for s in (stocks or []):
            cd=s.get("code","")
            if not cd: continue
            r=self.score_stock(cd)
            if r: r['name']=s.get("name",cd); results.append(r)
        results.sort(key=lambda x: x['total_score'], reverse=True)
        logger.info(f"评分: {len(results)} 只")
        return results

    def save_scores(self,results:list):
        if not results: return 0
        s=0
        try:
            for r in results:
                f=r.get('factors',{})
                rec=ScoreRecord(code=r['code'],name=r.get('name',''),score_date=r['calculated_at'],
                    total_score=r['total_score'],rating=r['rating'],
                    trend_score=f.get('trend'),reversal_score=f.get('short_term_reversal'),
                    volume_ratio_score=f.get('volume_ratio'),turnover_score=f.get('turnover'),
                    volatility_score=f.get('volatility'),factors_json=f,factor_weights=self.weights)
                self.db.add(rec); s+=1
            self.db.commit()
        except Exception as e: self.db.rollback(); logger.error(f"save: {e}")
        return s

    def get_watchlist(self, min_score: float = 0, limit: int = 30) -> list:
        try:
            results=self.score_all_stocks(limit=max(limit*3,80))
            if results:
                try: self.save_scores(results)
                except: pass
            return [r for r in results if r['total_score']>=min_score][:limit]
        except Exception as e:
            logger.error(f"watchlist: {e}")
            return []
