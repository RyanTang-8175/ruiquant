"""新闻 - 新浪财经 (阿里云ECS兼容)"""

import re, logging, requests
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
     'Referer': 'https://finance.sina.com.cn/'}

def fetch_sina_news(limit: int = 20) -> List[Dict]:
    """新浪财经滚动新闻 — 用HTTP不用HTTPS"""
    news = []
    try:
        # HTTP fallback for Alibaba Cloud ECS
        url = "http://feed.mix.sina.com.cn/api/roll/get"
        params = {"pageid":"153","lid":"2516","num":str(limit),"page":"1"}
        r = requests.get(url, params=params, headers=H, timeout=15)
        data = r.json().get('result',{}).get('data',[])
        for item in data:
            ts = int(item.get('ctime',0))
            dt = datetime.fromtimestamp(ts).strftime('%m-%d %H:%M') if ts>1000000000 else ''
            title = re.sub(r'<[^>]+>','',str(item.get('title',''))).strip()
            if title:
                news.append({"title":title,
                            "content":re.sub(r'<[^>]+>','',str(item.get('intro',''))).strip(),
                            "source":"sina","published_at":dt})
    except Exception as e:
        logger.warning(f"新浪HTTP失败，试HTTPS: {e}")
        try:
            r = requests.get("https://feed.mix.sina.com.cn/api/roll/get",
                params={"pageid":"153","lid":"2516","num":str(limit),"page":"1"},
                headers=H, timeout=15)
            data = r.json().get('result',{}).get('data',[])
            for item in data:
                ts = int(item.get('ctime',0))
                dt = datetime.fromtimestamp(ts).strftime('%m-%d %H:%M') if ts>1000000000 else ''
                title = re.sub(r'<[^>]+>','',str(item.get('title',''))).strip()
                if title:
                    news.append({"title":title,
                                "content":re.sub(r'<[^>]+>','',str(item.get('intro',''))).strip(),
                                "source":"sina","published_at":dt})
        except Exception as e2: logger.warning(f"新浪HTTPS也失败: {e2}")

    # 去重
    seen = set(); unique = []
    for item in news:
        k = item.get("title","")[:30]
        if k not in seen: seen.add(k); unique.append(item)
    return unique[:limit]

def fetch_eastmoney_news(limit: int = 10) -> List[Dict]:
    """东财备用"""
    news = []
    try:
        url = "http://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        params = {"client":"web","biz":"web_news_feeds","column":"350","order":"1",
                  "page_index":"1","page_size":str(limit),
                  "req_trace":str(int(datetime.now().timestamp()*1000))}
        r = requests.get(url, params=params, headers=H, timeout=10)
        for item in r.json().get('data',{}).get('list',[]):
            title = re.sub(r'<[^>]+>','',str(item.get('title',''))).strip()
            if title:
                news.append({"title":title,
                            "content":re.sub(r'<[^>]+>','',str(item.get('summary',''))).strip(),
                            "source":"eastmoney","published_at":item.get('showTime','')})
    except: pass
    return news

def fetch_stock_news(code: str, limit: int = 5) -> List[Dict]:
    """个股新闻 — 新浪搜索"""
    news = []
    try:
        tc = f"sh{code}" if code.startswith('6') else f"sz{code}"
        r = requests.get(f'http://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{tc}.phtml',
                        headers=H, timeout=10)
        titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*target="_blank"[^>]*>([^<]+)</a>', r.text)
        for url, title in titles[:limit]:
            t = re.sub(r'\s+','',title).strip()
            if t and len(t)>8: news.append({"title":t,"content":"","source":"sina","url":url,"published_at":""})
    except Exception as e: logger.warning(f"个股新闻失败 {code}: {e}")
    return news

def fetch_all_news(limit: int = 20) -> List[Dict]:
    """全源融合"""
    all_news = fetch_sina_news(limit) + fetch_eastmoney_news(limit//2)
    seen = set(); unique = []
    for item in all_news:
        k = item.get("title","")[:30]
        if k not in seen: seen.add(k); unique.append(item)
    return unique[:limit]
