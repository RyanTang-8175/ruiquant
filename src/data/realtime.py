"""
实时行情 — 腾讯+新浪 双源融合 (阿里云ECS兼容)
API: qt.gtimg.cn(主) + hq.sinajs.cn + vip.stock.finance.sina.com.cn
"""

import logging, requests, re, json
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def _tc_code(code: str) -> str:
    """600xxx→sh, 000/002/300→sz, 8xx/9xx→bj (北交所)"""
    if code.startswith('6'): return f"sh{code}"
    if code.startswith(('8','9')): return f"bj{code}"
    return f"sz{code}"

# ── 腾讯行情解析 ──
def _parse_gtimg(raw: str) -> Optional[Dict]:
    try:
        m = re.search(r'="(.+)"', raw)
        if not m: return None
        p = m.group(1).split('~')
        if len(p) < 40: return None
        v = lambda i: float(p[i]) if p[i] else 0.0
        return {"code":p[2],"name":p[1],"price":v(3),"prev_close":v(4),"open":v(5),
                "volume":int(v(6)),"amount":int(v(37))*10000,"high":v(33),"low":v(34),
                "change_pct":v(32),"turnover":v(38),"pe_ratio":v(39),
                "volume_ratio":v(49),"amplitude":v(43),
                "high_limit":v(47),"low_limit":v(48)}
    except: return None

def get_realtime_quote(code: str) -> Optional[Dict]:
    """单股行情 — 腾讯→新浪"""
    try:
        r = requests.get(f'http://qt.gtimg.cn/q={_tc_code(code)}', headers=H, timeout=5)
        q = _parse_gtimg(r.text)
        if q and q.get("price",0)>0: return q
    except: pass
    try:
        r = requests.get(f'http://hq.sinajs.cn/list={_tc_code(code)}',
            headers={**H,'Referer':'https://finance.sina.com.cn'}, timeout=5)
        m = re.search(r'="(.+)"', r.text)
        if m:
            p = m.group(1).split(','); v = lambda i: float(p[i]) if p[i] else 0.0
            return {"code":code,"name":p[0],"price":v(3),"prev_close":v(2),"open":v(1),
                    "high":v(4),"low":v(5),"volume":int(v(8)),"amount":v(9),
                    "change_pct":v(3)/v(2)*100-100 if v(2)>0 else 0}
    except: return None

def get_market_overview() -> Dict:
    """大盘指数 — 腾讯"""
    indices = []
    for cc,nm in [("sh000001","上证"),("sz399001","深证"),("sz399006","创业板")]:
        try:
            r = requests.get(f'http://qt.gtimg.cn/q={cc}', headers=H, timeout=5)
            p = r.text.split('~')
            if len(p)>32: indices.append({"name":nm,"price":float(p[3]),"change_pct":float(p[32])})
        except: pass
    return {"indices":indices}

def get_top_stocks(sort_field: str = "changepercent", asc: bool = False, limit: int = 15) -> List[Dict]:
    """排行榜 — 新浪API直接按指定字段排序返回(与新浪财经/同花顺一致)"""
    try:
        url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
        params = {"page":1, "num":min(limit+10, 100), "sort":sort_field, "asc":0 if asc else 1, "node":"hs_a"}
        r = requests.get(url, params=params, headers={**H,'Referer':'https://finance.sina.com.cn'}, timeout=10)
        items = r.json()
        stocks = []
        for item in items:
            stocks.append({
                "code": str(item.get("code","")),
                "name": item.get("name",""),
                "price": float(item.get("trade",0) or 0),
                "change_pct": float(item.get("changepercent",0) or 0),
                "volume": int(item.get("volume",0) or 0),
                "amount": float(item.get("amount",0) or 0),
                "turnover": float(item.get("turnoverratio",0) or 0),
                "open": float(item.get("open",0) or 0),
                "high": float(item.get("high",0) or 0),
                "low": float(item.get("low",0) or 0),
            })
        return stocks[:limit]
    except Exception as e:
        logger.warning(f"排行榜失败: {e}")
        return []

def get_kline(code: str, period: str = "101", count: int = 100) -> List[Dict]:
    """K线 — 东财→新浪→腾讯 三源"""
    pt = {"1":"1","5":"5","15":"15","30":"30","60":"60","101":"101","102":"102"}.get(period,"101")
    # 源1: 东财 (最全历史)
    try:
        m = 1 if code.startswith('6') else 0
        r = requests.get(f'http://push2his.eastmoney.com/api/qt/stock/kline/get?secid={m}.{code}&fields1=f1,f2,f3,f4,f5,f6,f7,f8&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt={pt}&fqt=1&beg=0&end=20500101&lmt={count}&ut=fa5fd1943c7b386f172d6893dbfba10b', headers=H, timeout=10)
        kls = r.json().get('data',{}).get('klines',[])
        if kls:
            return [{"date":k.split(',')[0],"open":float(k.split(',')[1]),"close":float(k.split(',')[2]),"high":float(k.split(',')[3]),"low":float(k.split(',')[4]),"volume":int(float(k.split(',')[5])),"change_pct":float(k.split(',')[8])} for k in kls if len(k.split(','))>=11]
    except: pass
    # 源2: 新浪
    try:
        scale = {"1":"5","5":"5","15":"15","30":"30","60":"60","101":"240","102":"1200"}.get(period,"240")
        r = requests.get(f'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={_tc_code(code)}&scale={scale}&ma=no&datalen={count}', headers=H, timeout=10)
        items = r.json()
        if items:
            return [{"date":d["day"],"open":float(d["open"]),"close":float(d["close"]),"high":float(d["high"]),"low":float(d["low"]),"volume":int(d["volume"]),"change_pct":(float(d["close"])-float(d["open"]))/float(d["open"])*100 if float(d["open"])>0 else 0} for d in items]
    except: pass
    # 源3: 腾讯
    try:
        mpt = {"1":"1","5":"5","15":"15","30":"30","60":"60","101":"day","102":"week"}.get(period,"day")
        r = requests.get(f'http://web.ifzq.gtimg.cn/appstock/app/kline/mkline?param={_tc_code(code)},m{mpt},,{count}&_var=kline_data', headers=H, timeout=10)
        lines = r.json().get("data",{}).get(_tc_code(code),{}).get(f"m{mpt}",[])
        if lines: return [{"date":l[0],"open":float(l[1]),"close":float(l[2]),"high":float(l[3]),"low":float(l[4]),"volume":int(float(l[5])),"change_pct":(float(l[2])-float(l[1]))/float(l[1])*100 if float(l[1])>0 else 0} for l in lines]
    except: pass
    return []
