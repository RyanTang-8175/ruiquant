"""新闻 - 新浪财经 + 东方财富"""

import re, logging, requests
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','Referer':'https://finance.sina.com.cn/'}

def fetch_sina_news(limit: int = 20) -> List[Dict]:
    news = []
    try:
        url = "https://feed.mix.sina.com.cn/api/roll/get"
        params = {"pageid":"153","lid":"2516","num":str(limit),"page":"1"}
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        for item in r.json().get('result',{}).get('data',[]):
            ts = int(item.get('ctime',0))
            dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts>1000000000 else ''
            title = re.sub(r'<[^>]+>','',str(item.get('title',''))).strip()
            if title: news.append({"title":title,"content":re.sub(r'<[^>]+>','',str(item.get('intro',''))).strip(),"source":"sina","published_at":dt})
    except Exception as e: logger.warning(f"新浪新闻失败: {e}")
    return news

def fetch_eastmoney_news(limit: int = 20) -> List[Dict]:
    news = []
    try:
        url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        params = {"client":"web","biz":"web_news_feeds","column":"350","order":"1","page_index":"1","page_size":str(limit),"req_trace":str(int(datetime.now().timestamp()*1000))}
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        for item in r.json().get('data',{}).get('list',[]):
            title = re.sub(r'<[^>]+>','',str(item.get('title',''))).strip()
            if title: news.append({"title":title,"content":re.sub(r'<[^>]+>','',str(item.get('summary',''))).strip(),"source":"eastmoney","published_at":item.get('showTime','')})
    except Exception as e: logger.warning(f"东财新闻失败: {e}")
    return news

def fetch_stock_news(code: str, limit: int = 10) -> List[Dict]:
    news = []
    try:
        r = requests.get(f'https://finance.sina.com.cn/stock/s/{code}.html', headers=HEADERS, timeout=10)
        titles = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r.text)
        for url, title in titles[:limit]:
            t = re.sub(r'<[^>]+>','',title).strip()
            if t and len(t)>5: news.append({"title":t,"content":"","source":"sina","url":url,"published_at":""})
    except Exception as e: logger.warning(f"个股新闻失败 {code}: {e}")
    return news

def fetch_all_news(limit: int = 20) -> List[Dict]:
    all_news = fetch_sina_news(limit) + fetch_eastmoney_news(limit)
    seen = set(); unique = []
    for item in all_news:
        k = item.get("title","")[:20]
        if k not in seen: seen.add(k); unique.append(item)
    return unique[:limit]
