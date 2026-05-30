"""
实时行情 — 腾讯财经（主）+ 东方财富（备）
"""

import logging, requests, re
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def _tcode(code: str) -> str:
    return f"sh{code}" if code.startswith('6') else f"sz{code}"

def _parse_tencent(raw: str) -> Optional[Dict]:
    """解析 v_sh600519="...~name~code~price~prev~..." """
    try:
        m = re.search(r'="(.+)"', raw)
        if not m: return None
        p = m.group(1).split('~')
        if len(p) < 40: return None
        v = lambda i: float(p[i]) if p[i] else 0.0
        return {
            "code": p[2], "name": p[1], "price": v(3), "prev_close": v(4),
            "open": v(5), "volume": int(v(6)), "amount": int(v(37))*10000,
            "high": v(33), "low": v(34), "change_pct": v(32),
            "turnover": v(38), "pe_ratio": v(39),
        }
    except Exception as e:
        logger.warning(f"腾讯解析失败: {e}")
        return None

def _parse_east(raw: dict) -> Optional[Dict]:
    d = raw.get("data");
    if not d: return None
    f = lambda v: (v or 0)/100 if isinstance(v,(int,float)) else 0
    return {"code":str(d.get("f57","")),"name":d.get("f58",""),"price":f(d.get("f43")),"high":f(d.get("f44")),"low":f(d.get("f45")),"open":f(d.get("f46")),"volume":d.get("f47",0),"amount":d.get("f48",0),"prev_close":f(d.get("f60")),"change_pct":f(d.get("f170")),"turnover":f(d.get("f168"))}

def get_realtime_quote(code: str) -> Optional[Dict]:
    try:
        r = requests.get(f'http://qt.gtimg.cn/q={_tcode(code)}', headers=HEADERS, timeout=5)
        q = _parse_tencent(r.text)
        if q: return q
    except: pass
    try:
        m = 1 if code.startswith('6') else 0
        r = requests.get(f'http://push2.eastmoney.com/api/qt/stock/get?secid={m}.{code}&fields=f43,f44,f45,f46,f47,f48,f57,f58,f60,f168,f170&ut=fa5fd1943c7b386f172d6893dbfba10b', headers=HEADERS, timeout=5)
        return _parse_east(r.json())
    except: return None

def get_market_overview() -> Dict:
    indices = []
    for cc,nm in [("sh000001","上证"),("sz399001","深证"),("sz399006","创业板")]:
        try:
            r = requests.get(f'http://qt.gtimg.cn/q={cc}', headers=HEADERS, timeout=5)
            p = r.text.split('~')
            if len(p)>32: indices.append({"name":nm,"price":float(p[3]),"change_pct":float(p[32])})
        except: pass
    return {"indices": indices}

def get_top_stocks(sort_field: str = "f3", asc: bool = False, limit: int = 15) -> List[Dict]:
    try:
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {"pn":"1","pz":str(limit),"po":"0" if asc else "1","np":"1","fltt":"2","invt":"2","fid":sort_field,"fs":"m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23","fields":"f2,f3,f4,f5,f6,f7,f8,f12,f14,f15,f16,f17,f18","ut":"fa5fd1943c7b386f172d6893dbfba10b"}
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        return [{"code":str(i.get("f12","")),"name":i.get("f14",""),"price":i.get("f2",0)or 0,"change_pct":i.get("f3",0)or 0,"volume":i.get("f5",0)or 0,"amount":i.get("f6",0)or 0,"turnover":i.get("f8",0)or 0,"high":i.get("f15",0)or 0,"low":i.get("f16",0)or 0,"open":i.get("f17",0)or 0} for i in r.json().get('data',{}).get('diff',[])]
    except Exception as e:
        logger.warning(f"排行榜失败: {e}")
        return []

def get_kline(code: str, period: str = "101", count: int = 100) -> List[Dict]:
    try:
        m = 1 if code.startswith('6') else 0
        url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {"secid":f"{m}.{code}","fields1":"f1,f2,f3,f4,f5,f6,f7,f8","fields2":"f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61","klt":period,"fqt":"1","beg":"0","end":"20500101","lmt":str(count),"ut":"fa5fd1943c7b386f172d6893dbfba10b"}
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        results = []
        for k in r.json().get('data',{}).get('klines',[]):
            p = k.split(',')
            if len(p)>=11: results.append({"date":p[0],"open":float(p[1]),"close":float(p[2]),"high":float(p[3]),"low":float(p[4]),"volume":int(float(p[5])),"amount":float(p[6]),"change_pct":float(p[8])})
        return results
    except Exception as e:
        logger.warning(f"K线失败 {code}: {e}")
        return []
