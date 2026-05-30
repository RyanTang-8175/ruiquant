"""
实时行情 — 腾讯/新浪/东方财富 多源融合
API 1(主): qt.gtimg.cn — 腾讯行情
API 2(备): hq.sinajs.cn — 新浪行情
API 3(K线): web.ifzq.gtimg.cn — 腾讯分时
API 4(备): push2.eastmoney.com — 东财
"""

import logging, requests, re, json
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ═══════════ 腾讯行情 (qt.gtimg.cn) ═══════════
# 返回: v_sh600519="1~茅台~600519~1326.00~1275.98~..."

def _tc_code(code: str) -> str:
    return f"sh{code}" if code.startswith('6') else f"sz{code}"

def _parse_gtimg(raw: str) -> Optional[Dict]:
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
            "source": "tencent",
        }
    except: return None

# ═══════════ 新浪行情 (hq.sinajs.cn) ═══════════
# 返回: var hq_str_sh600519="贵州茅台,1270.600,1275.980,1326.000,...

def _parse_sina(raw: str) -> Optional[Dict]:
    try:
        m = re.search(r'="(.+)"', raw)
        if not m: return None
        p = m.group(1).split(',')
        if len(p) < 32: return None
        v = lambda i: float(p[i]) if p[i] else 0.0
        return {
            "code": p[0].split('_')[-1] if '_' in p[0] else "",
            "name": p[0].split('_')[0] if '_' in p[0] else "",
            "price": v(3), "prev_close": v(2), "open": v(1),
            "high": v(4), "low": v(5), "volume": int(v(8)),
            "amount": int(v(9)), "change_pct": v(3)/v(2)*100-100 if v(2)>0 else 0,
            "turnover": v(38) if len(p)>38 else 0,
            "source": "sina",
        }
    except: return None

# ═══════════ 东财行情 (push2.eastmoney.com) ═══════════
def _parse_east(raw: dict) -> Optional[Dict]:
    d = raw.get("data")
    if not d: return None
    f = lambda v: (v or 0)/100 if isinstance(v,(int,float)) else 0
    return {
        "code": str(d.get("f57","")), "name": d.get("f58",""),
        "price": f(d.get("f43")), "high": f(d.get("f44")),
        "low": f(d.get("f45")), "open": f(d.get("f46")),
        "volume": d.get("f47",0), "amount": d.get("f48",0),
        "prev_close": f(d.get("f60")), "change_pct": f(d.get("f170")),
        "turnover": f(d.get("f168")), "source": "eastmoney",
    }

# ═══════════ 公开 API ═══════════

def get_realtime_quote(code: str) -> Optional[Dict]:
    """单股实时行情 — 腾讯→新浪→东财 三源顺序"""
    sources = [
        ("tencent", lambda: requests.get(f'http://qt.gtimg.cn/q={_tc_code(code)}', headers=HEADERS, timeout=5),
         _parse_gtimg),
        ("sina", lambda: requests.get(f'http://hq.sinajs.cn/list={_tc_code(code)}',
                 headers={**HEADERS, 'Referer':'https://finance.sina.com.cn'}, timeout=5),
         _parse_sina),
        ("eastmoney", lambda: requests.get(
            f'http://push2.eastmoney.com/api/qt/stock/get?secid={1 if code.startswith("6") else 0}.{code}&fields=f43,f44,f45,f46,f47,f48,f57,f58,f60,f168,f170&ut=fa5fd1943c7b386f172d6893dbfba10b',
            headers=HEADERS, timeout=5), lambda r: _parse_east(r.json())),
    ]
    for name, fetch, parse in sources:
        try:
            q = parse(fetch())
            if q and q.get("price", 0) > 0: return q
        except: continue
    return None

def get_market_overview() -> Dict:
    """大盘指数 — 三源"""
    indices = []
    for cc,nm in [("sh000001","上证"),("sz399001","深证"),("sz399006","创业板")]:
        try:
            # 腾讯
            r = requests.get(f'http://qt.gtimg.cn/q={cc}', headers=HEADERS, timeout=5)
            p = r.text.split('~')
            if len(p)>32: indices.append({"name":nm,"price":float(p[3]),"change_pct":float(p[32])}); continue
        except: pass
        try:
            # 新浪
            r = requests.get(f'http://hq.sinajs.cn/list=s_{cc}', headers={**HEADERS, 'Referer':'https://finance.sina.com.cn'}, timeout=5)
            p = r.text.split(',')
            if len(p)>3: indices.append({"name":nm,"price":float(p[3]),"change_pct":float(p[3])/float(p[2])*100-100 if float(p[2])>0 else 0})
        except: pass
    return {"indices": indices}

def get_top_stocks(sort_field: str = "f3", asc: bool = False, limit: int = 15) -> List[Dict]:
    """排行榜 — 东财 clist"""
    try:
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {"pn":"1","pz":str(limit),"po":"0" if asc else "1","np":"1","fltt":"2","invt":"2","fid":sort_field,"fs":"m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23","fields":"f2,f3,f4,f5,f6,f7,f8,f12,f14,f15,f16,f17,f18","ut":"fa5fd1943c7b386f172d6893dbfba10b"}
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        return [{"code":str(i.get("f12","")),"name":i.get("f14",""),"price":i.get("f2",0)or 0,"change_pct":i.get("f3",0)or 0,"volume":i.get("f5",0)or 0,"amount":i.get("f6",0)or 0,"turnover":i.get("f8",0)or 0,"high":i.get("f15",0)or 0,"low":i.get("f16",0)or 0,"open":i.get("f17",0)or 0} for i in r.json().get('data',{}).get('diff',[])]
    except Exception as e:
        logger.warning(f"排行榜失败: {e}")
        return []

def get_kline(code: str, period: str = "101", count: int = 100) -> List[Dict]:
    """K线 — 腾讯分时→东财 两源"""
    # 源1: 腾讯分时
    try:
        tc = _tc_code(code)
        pt = {"1":"1","5":"5","15":"15","30":"30","60":"60","101":"day","102":"week"}.get(period,"day")
        url = "http://web.ifzq.gtimg.cn/appstock/app/kline/mkline"
        params = {"param": f"{tc},m{pt},,{count}", "_var": "kline_data"}
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = r.json()
        lines = data.get("data",{}).get(tc,{}).get(f"m{pt}",[]) or data.get("data",{}).get(tc,{}).get(pt,[])
        if lines:
            return [{"date":l[0],"open":float(l[1]),"close":float(l[2]),"high":float(l[3]),"low":float(l[4]),"volume":int(float(l[5])),"change_pct":(float(l[2])-float(l[1]))/float(l[1])*100 if float(l[1])>0 else 0} for l in lines]
    except Exception as e: logger.warning(f"腾讯K线失败 {code}: {e}")

    # 源2: 东财
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
        logger.warning(f"东财K线失败 {code}: {e}")
        return []
