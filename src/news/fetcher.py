"""新闻多源抓取 — 新浪/东财/财联社/腾讯/华尔街见闻"""

import re, logging, requests
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)
H = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
    'Accept': 'application/json',
}

# ═══════════════════════════════
# 1. 新浪财经
# ═══════════════════════════════

def fetch_sina_news(limit: int = 20) -> List[Dict]:
    news = []
    for proto in ["http", "https"]:
        try:
            r = requests.get(f"{proto}://feed.mix.sina.com.cn/api/roll/get",
                params={"pageid":"153","lid":"2516","num":str(limit),"page":"1"},
                headers=H, timeout=10)
            data = r.json().get('result',{}).get('data',[])
            for item in data:
                ts = int(item.get('ctime',0))
                dt = datetime.fromtimestamp(ts).strftime('%m-%d %H:%M') if ts>1000000000 else ''
                title = re.sub(r'<[^>]+>','',str(item.get('title',''))).strip()
                if title:
                    news.append({"title":title,"content":re.sub(r'<[^>]+>','',str(item.get('intro',''))).strip(),
                                 "source":"新浪","published_at":dt,"url":item.get('url',''),
                                 "keywords":item.get('keywords','')})
            if news: break
        except: continue
    return _dedup(news, limit)


# ═══════════════════════════════
# 2. 东方财富
# ═══════════════════════════════

def fetch_eastmoney_news(limit: int = 15) -> List[Dict]:
    news = []
    try:
        r = requests.get("http://np-listapi.eastmoney.com/comm/web/getNewsByColumns",
            params={"client":"web","biz":"web_news_feeds","column":"350","order":"1",
                    "page_index":"1","page_size":str(limit),
                    "req_trace":str(int(datetime.now().timestamp()*1000))},
            headers=H, timeout=10)
        for item in r.json().get('data',{}).get('list',[]):
            title = re.sub(r'<[^>]+>','',str(item.get('title',''))).strip()
            if title:
                news.append({"title":title,"content":re.sub(r'<[^>]+>','',str(item.get('summary',''))).strip(),
                             "source":"东财","published_at":item.get('showTime',''),
                             "url":item.get('url',''),"keywords":''})
    except Exception as e: logger.warning(f"东财: {e}")
    return _dedup(news, limit)


# ═══════════════════════════════
# 3. CLS 财联社 — 电报快讯
# ═══════════════════════════════

def fetch_cls_news(limit: int = 20) -> List[Dict]:
    news = []
    try:
        r = requests.post("https://www.cls.cn/api/sw",
            json={"app":"CailianpressWeb","os":"web","sv":"8.4.6",
                  "sign":"","rn":str(min(limit,30))},
            headers={**H,'Content-Type':'application/json'}, timeout=10)
        data = r.json().get('data',{}).get('roll_data',[])
        if isinstance(data, list):
            for item in data:
                title = item.get('title','') or item.get('brief','')
                ctime = item.get('ctime',0)
                dt = datetime.fromtimestamp(ctime).strftime('%m-%d %H:%M') if ctime>1000000000 else ''
                if title:
                    news.append({"title":re.sub(r'<[^>]+>','',title).strip(),
                                 "content":item.get('content','') or item.get('brief',''),
                                 "source":"财联社","published_at":dt,
                                 "url":f"https://www.cls.cn/detail/{item.get('id','')}",
                                 "keywords":','.join(item.get('subjects',[]))})
    except Exception as e: logger.warning(f"财联社: {e}")
    return _dedup(news, limit)


# ═══════════════════════════════
# 4. 腾讯财经
# ═══════════════════════════════

def fetch_tencent_news(limit: int = 15) -> List[Dict]:
    news = []
    try:
        r = requests.get("https://i.news.qq.com/trpc.qqnews_web.kv_srv.kv_srv_http_proxy/list",
            params={"sub_srv_id":"finance","srv_id":"pc","offset":"0","limit":str(limit),
                    "strategy":"1",
                    "ext":'{"pool":["top","hot"],"is_filter":7,"check_type":true}'},
            headers=H, timeout=10)
        items = r.json().get('data',{}).get('list',[])
        for item in items:
            title = item.get('title','') or item.get('nlp_title','')
            if title:
                ts = item.get('publish_time','')
                try: dt = datetime.fromtimestamp(int(ts)).strftime('%m-%d %H:%M') if ts else ''
                except: dt = ''
                news.append({"title":title.strip(),
                             "content":item.get('abstract','') or item.get('nlp_abstract',''),
                             "source":"腾讯","published_at":dt,
                             "url":item.get('url','') or item.get('share_url',''),
                             "keywords":''})
    except Exception as e: logger.warning(f"腾讯: {e}")
    return _dedup(news, limit)


# ═══════════════════════════════
# 5. 华尔街见闻
# ═══════════════════════════════

def fetch_wallstreetcn_news(limit: int = 15) -> List[Dict]:
    news = []
    try:
        r = requests.get("https://api-one.wallstcn.com/apiv1/content/lives",
            params={"channel":"global-channel","client":"pc","limit":str(limit),"first_page":"true"},
            headers=H, timeout=10)
        items = r.json().get('data',{}).get('items',[])
        for item in items:
            title = item.get('title','') or item.get('content_text','')
            if title:
                ts = item.get('display_time',0)
                dt = datetime.fromtimestamp(ts).strftime('%m-%d %H:%M') if ts>1000000000 else ''
                news.append({"title":re.sub(r'<[^>]+>','',title)[:200].strip(),
                             "content":item.get('content_text','') or item.get('content',''),
                             "source":"华尔街见闻","published_at":dt,
                             "url":f"https://wallstreetcn.com/livenews/{item.get('id','')}",
                             "keywords":''})
    except Exception as e: logger.warning(f"华尔街见闻: {e}")
    return _dedup(news, limit)


# ═══════════════════════════════
# 公共接口
# ═══════════════════════════════

SOURCES = {"新浪":fetch_sina_news,"东财":fetch_eastmoney_news,
           "财联社":fetch_cls_news,"腾讯":fetch_tencent_news,
           "华尔街见闻":fetch_wallstreetcn_news}


def fetch_all_news(limit: int = 40) -> List[Dict]:
    """5源融合"""
    all_news = []
    for name, fn in SOURCES.items():
        try:
            n = fn(limit // 3)
            all_news.extend(n)
            logger.info(f"{name}: {len(n)}条")
        except Exception as e: logger.warning(f"{name}: {e}")
    return _categorize(_dedup(all_news, limit))


def fetch_news_by_source(source: str, limit: int = 15) -> List[Dict]:
    fn = SOURCES.get(source)
    return _categorize(fn(limit)) if fn else []


def fetch_stock_news(code: str, limit: int = 8) -> List[Dict]:
    news = []
    # ── iFinD 公告优先 ──
    try:
        from src.data.providers.registry import get_provider
        provider = get_provider()
        if provider.source_name == "ifind":
            items = provider.report_query(code, days=60, limit=limit)
            for item in items:
                item.setdefault("category", "company")
            news.extend(items)
    except Exception:
        pass

    if not news:
        try:
            tc = f"sh{code}" if code.startswith('6') else f"sz{code}"
            r = requests.get(
                f'http://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{tc}.phtml',
                headers=H, timeout=10)
            for url, title in re.findall(r'<a[^>]*href="([^"]*)"[^>]*target="_blank"[^>]*>([^<]+)</a>', r.text)[:limit]:
                t = re.sub(r'\s+','',title).strip()
                if t and len(t)>8: news.append({"title":t,"content":"","source":"新浪","url":url,"published_at":""})
        except: pass
        for item in fetch_all_news(50):
            if code in (item.get("title","")+item.get("content","")+item.get("keywords","")):
                news.append(item)
    return _dedup(news, limit)


def _dedup(items, limit):
    seen, out = set(), []
    for x in items:
        k = x.get("title","")[:40]
        if k not in seen and k: seen.add(k); out.append(x)
    return out[:limit]


def _categorize(items):
    for item in items:
        t = item.get("title","")+item.get("content","")
        codes = list(set(re.findall(r'\b([3689]\d{5}|0[023]\d{4})\b', t)))[:5]
        if codes: item["related_codes"] = codes
        if any(k in t for k in ["央行","证监会","国务院","政治局","降息","降准",
                                 "LPR","财政部","发改委","金管局"]):
            item["category"] = "policy"
        elif any(k in t for k in ["板块","概念","产业链","赛道","新能","光伏",
                                   "芯片","医药","地产","银行","券商","煤炭","钢铁",
                                   "AI","人工智能","机器人","算力","低空"]):
            item["category"] = "sector"
        elif any(k in t for k in ["涨停","跌停","业绩","财报","公告","减持","增持",
                                   "重组","ST","退市","回购","分红"]):
            item["category"] = "company"
        else:
            item["category"] = "macro"
    return items
