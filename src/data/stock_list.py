"""
全A股列表缓存 + 申万行业 + 概念板块
"""

import difflib
import json, logging, os, re, requests, unicodedata
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
H = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}
CACHE_FILE = Path(__file__).parent.parent.parent / 'data' / 'stock_cache.json'

# 申万31行业
SW_INDUSTRY = {
    "食品饮料": ["600519","000858","600809","000568","002304","600600","000596","600132","000729","600702"],
    "医药生物": ["600276","000538","300760","002001","600196","300015","000963","002007","300122","600085"],
    "电子": ["688981","688012","688008","603501","002475","300433","600703","002049","300782","688036"],
    "银行": ["601398","601939","601288","600036","600016","601328","601166","000001","002142","601818"],
    "非银金融": ["601318","600030","601688","601211","600837","000166","601236","600999","601878","300059"],
    "电力设备": ["300750","601012","600406","002459","688599","002074","300274","688223","600438","601877"],
    "汽车": ["600104","601238","000625","002594","600741","601633","000800","600418","000338","601799"],
    "计算机": ["002230","300033","600570","002410","300454","688111","300624","002415","600536","603019"],
    "通信": ["601728","600050","002281","300308","600487","002491","688009","000063","300628","300502"],
    "传媒": ["002027","300413","002555","300058","600637","002624","002131","603444","300251","002605"],
    "房地产": ["000002","001979","600048","600383","600325","600340","600606","002146","601155","600185"],
    "建筑装饰": ["601668","601390","601186","600170","601800","601618","002051","600039","601669","002310"],
    "机械设备": ["601100","688012","300124","002008","600031","300316","688188","002353","300450","688777"],
    "国防军工": ["600893","000768","002013","600760","688239","600391","002025","300395","300159","688297"],
    "基础化工": ["600309","002601","000830","600426","002064","600989","300285","603260","002648","601233"],
    "石油石化": ["601857","600028","601808","600989","600583","601975","600688","000059","002221","002828"],
    "有色金属": ["601899","603799","002460","600111","000630","000807","002466","688122","601168","600362"],
    "钢铁": ["600019","000709","000932","600010","600808","000825","600022","002110","600507","000898"],
    "煤炭": ["601088","601225","600188","000983","601898","600971","601001","601699","600395","002128"],
    "农林牧渔": ["002714","300498","600438","002385","002157","000876","002311","300087","600201","603363"],
    "纺织服饰": ["603116","002832","002291","002563","603877","002154","600398","603608","300577","601566"],
    "轻工制造": ["002191","603899","002078","600963","603833","002301","002968","603208","300729","600337"],
    "家用电器": ["000333","002032","600690","000651","002050","600060","300217","688169","000921","002429"],
    "商贸零售": ["601933","002024","002091","600415","002251","002561","603708","600729","000564","002419"],
    "社会服务": ["300144","002059","300012","603136","600258","000069","002033","600054","300662","002186"],
    "交通运输": ["601919","600029","601006","601111","600115","600009","600221","002120","603885","300873"],
    "公用事业": ["600900","601985","003816","600025","600011","600886","600674","002015","000883","600023"],
    "环保": ["300070","002573","600292","300422","603588","300815","600217","300266","688101","688501"],
    "美容护理": ["603605","300957","603983","688363","300888","603238","002832","300849","688139","002959"],
    "综合": ["600673","000009","000062","600620","600895","600082","600234","000532","002288","000833"],
    "建筑材料": ["600585","000786","002271","601636","600801","002372","600724","000401","002043","603737"],
}

# 概念板块
CONCEPTS = {
    "AI人工智能": ["002230","688111","300033","300454","300624","688981","002415","300502","300661","603019"],
    "新能源": ["300750","601012","600406","002459","688599","002074","300274","688223","600438","601877"],
    "半导体芯片": ["688981","688012","688008","688256","603501","688396","002475","688036","600703","300782"],
    "白酒": ["600519","000858","000568","002304","600809","600559","000596","600779","603369","603198"],
    "医药CRO": ["300760","300759","603259","002821","002007","603456","688202","300347","688131","688621"],
    "光伏": ["688599","601012","600438","002459","688223","300274","002129","603806","688390","300118"],
    "锂电池": ["300750","002594","300014","300073","002460","002074","688567","300450","002709","300432"],
    "低空经济": ["688122","300395","688297","002023","600760","000768","002389","600038","300159","688239"],
    "华为产业链": ["002475","300433","002230","002415","300624","688981","300502","002049","300782","002384"],
    "机器人": ["300124","688012","002008","688188","688777","300316","002353","300450","300024","600835"],
    "数据要素": ["002230","300033","300454","300624","002415","688111","300502","300378","688568","002649"],
    "国企改革": ["601857","600028","601088","600019","601668","600050","601390","600900","601985","600011"],
    "券商": ["600030","601688","601211","600837","601236","600999","601878","300059","002736","600958"],
    "军工": ["600893","000768","002013","600760","688239","600391","002025","300395","300159","688297"],
    "电力": ["600900","601985","600025","600011","600886","600674","002015","000883","003816","600023"],
    "中药": ["600085","000538","000423","002603","600332","600436","600535","002317","300026","600976"],
    "创新药": ["600276","300760","603259","002007","688180","300558","688578","688266","688302","688197"],
    "消费电子": ["002475","300433","603501","600703","002049","300782","688036","300661","002456","002241"],
    "新能源汽车": ["002594","600104","601238","000625","600741","000800","000338","600418","601633","300750"],
    "游戏": ["002555","002624","603444","300418","002425","300251","600637","002027","300494","002306"],
}

# 高频短线候选的标准名称兜底。服务器首次部署、行情源错名或缓存污染时，
# AI/雷达仍应以代码映射为准，不能把“中芯国际002304”这类错配展示给用户。
STANDARD_STOCK_NAMES = {
    "600519": "贵州茅台", "000858": "五粮液", "000568": "泸州老窖",
    "002304": "洋河股份", "600809": "山西汾酒", "600559": "老白干酒",
    "000596": "古井贡酒", "600779": "水井坊", "603369": "今世缘",
    "603198": "迎驾贡酒",
    "600900": "长江电力", "601985": "中国核电", "003816": "中国广核",
    "600025": "华能水电", "600011": "华能国际", "600886": "国投电力",
    "600674": "川投能源", "002015": "协鑫能科", "000883": "湖北能源",
    "600023": "浙能电力",
    "002475": "立讯精密", "688981": "中芯国际", "688036": "传音控股",
    "603501": "豪威集团", "600703": "三安光电", "688256": "寒武纪",
    "688008": "澜起科技", "688012": "中微公司", "688396": "华润微",
    "300782": "卓胜微", "000725": "京东方A",
}

GROUP_ALIASES = {
    "半导体": ("概念", "半导体芯片"),
    "芯片": ("概念", "半导体芯片"),
    "电力": ("概念", "电力"),
    "白酒": ("概念", "白酒"),
    "AI": ("概念", "AI人工智能"),
    "人工智能": ("概念", "AI人工智能"),
}


_CATALOG_CACHE: list[dict] | None = None
_A_SHARE_PREFIXES = (
    "000", "001", "002", "003",
    "300", "301", "302",
    "600", "601", "603", "605",
    "688", "689", "920",
)


def normalize_stock_text(value: str) -> str:
    """统一全角/半角、大小写和空白。"""
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", "", normalized).upper()


def normalize_stock_code(value: str) -> str:
    """从纯代码或带交易所后缀的值中提取合法 6 位 A 股代码。"""
    normalized = normalize_stock_text(value)
    normalized = re.sub(r"^(SH|SZ|BJ)", "", normalized)
    normalized = re.sub(r"\.(SH|SZ|BJ)$", "", normalized)
    return normalized if is_valid_stock_code(normalized) else ""


def is_valid_stock_code(value: str) -> bool:
    code = str(value or "").strip()
    if not re.fullmatch(r"\d{6}", code):
        return False
    return code.startswith(_A_SHARE_PREFIXES) or code.startswith(("4", "8"))


def cached_stock_catalog() -> list[dict]:
    """读取本地股票目录，不触发外部网络。"""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE

    rows: list[dict] = []
    if CACHE_FILE.exists():
        try:
            payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            rows = payload.get("stocks", []) if isinstance(payload, dict) else []
        except Exception:
            rows = []

    by_code = {}
    for item in rows:
        code = normalize_stock_code(item.get("code", ""))
        name = str(item.get("name") or "").strip()
        if code and name:
            by_code[code] = {**item, "code": code, "name": name}
    for code, name in STANDARD_STOCK_NAMES.items():
        by_code.setdefault(code, {"code": code, "name": name, "price": 0, "change_pct": 0})

    _CATALOG_CACHE = list(by_code.values())
    return _CATALOG_CACHE


def resolve_stock_query(query: str, stocks: list | None = None, fuzzy: bool = True) -> dict | None:
    """把代码或股票名称解析成唯一标的，只使用本地目录。"""
    raw = str(query or "").strip()
    direct_code = normalize_stock_code(raw)
    catalog = stocks if stocks is not None else cached_stock_catalog()
    if direct_code:
        match = next((item for item in catalog if normalize_stock_code(item.get("code")) == direct_code), None)
        return dict(match) if match else {
            "code": direct_code,
            "name": STANDARD_STOCK_NAMES.get(direct_code, direct_code),
            "price": 0,
            "change_pct": 0,
        }

    needle = normalize_stock_text(raw)
    if not needle:
        return None

    for item in catalog:
        code = normalize_stock_code(item.get("code", ""))
        name = normalize_stock_text(item.get("name", ""))
        if code and needle == name:
            return dict(item)

    if not fuzzy or len(needle) < 4:
        return None

    best = None
    best_ratio = 0.0
    for item in catalog:
        name = normalize_stock_text(item.get("name", ""))
        if len(name) != len(needle):
            continue
        mismatches = sum(a != b for a, b in zip(needle, name))
        if mismatches > 1:
            continue
        ratio = difflib.SequenceMatcher(None, needle, name).ratio()
        if ratio >= 0.75 and ratio > best_ratio:
            best = item
            best_ratio = ratio
    return dict(best) if best else None


def extract_stock_references(text: str, stocks: list | None = None, limit: int = 4) -> list[str]:
    """从自然语言中识别明确出现的代码或股票名称，不根据旧会话猜标的。"""
    raw = str(text or "")
    found = []
    for match in re.findall(r"(?<!\d)(\d{6})(?!\d)", normalize_stock_text(raw)):
        code = normalize_stock_code(match)
        if code and code not in found:
            found.append(code)

    normalized = normalize_stock_text(raw)
    catalog = stocks if stocks is not None else cached_stock_catalog()
    named = []
    for item in catalog:
        code = normalize_stock_code(item.get("code", ""))
        name = normalize_stock_text(item.get("name", ""))
        if code and len(name) >= 3 and name in normalized:
            named.append((len(name), code))
    for _, code in sorted(named, reverse=True):
        if code not in found:
            found.append(code)
        if len(found) >= limit:
            break
    return found[:limit]


def resolve_stock_name(code: str, fallback: str = "") -> str:
    """用标准代码表和本地股票目录解析股票名。"""
    code = normalize_stock_code(code) or str(code or "")
    if code in STANDARD_STOCK_NAMES:
        return STANDARD_STOCK_NAMES[code]
    for item in cached_stock_catalog():
        if item.get("code") == code and item.get("name"):
            return unicodedata.normalize("NFKC", str(item["name"]))
    return str(fallback or "") or code


def detect_stock_groups(text: str) -> list:
    """从用户问题中识别行业/概念分组，返回 (kind, name, codes)。"""
    normalized = str(text or "").replace("，", " ").replace("、", " ").replace("/", " ")
    groups = []
    for name, codes in SW_INDUSTRY.items():
        if name in normalized:
            groups.append(("行业", name, codes))
    for name, codes in CONCEPTS.items():
        if name in normalized:
            groups.append(("概念", name, codes))
    for alias, (kind, target) in GROUP_ALIASES.items():
        if alias in normalized:
            codes = CONCEPTS.get(target, []) if kind == "概念" else SW_INDUSTRY.get(target, [])
            if codes:
                groups.append((kind, target, codes))

    dedup, seen = [], set()
    for kind, name, codes in groups:
        key = (kind, name)
        if key not in seen:
            seen.add(key)
            dedup.append((kind, name, codes))
    return dedup

def fetch_all_stocks() -> list:
    """从新浪拉取全A股列表并缓存"""
    os.makedirs(CACHE_FILE.parent, exist_ok=True)
    # 检查缓存
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                age = datetime.now().timestamp() - cache.get('ts', 0)
                if age < 86400:  # 24小时内
                    return cache.get('stocks', [])
        except: pass

    # 从新浪分页拉取
    stocks = []
    for page in range(1, 80):  # 80页覆盖全A股~5600只(300750在49页)
        try:
            r = requests.get(
                'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData',
                params={'page': page, 'num': 200, 'sort': 'symbol', 'asc': 1, 'node': 'hs_a'},
                headers=H, timeout=15)
            items = r.json()
            if not items: break
            for item in items:
                stocks.append({
                    'code': str(item.get('code', '')),
                    'name': item.get('name', ''),
                    'price': float(item.get('trade', 0) or 0),
                    'change_pct': float(item.get('changepercent', 0) or 0),
                })
            logger.info(f"拉取第{page}页, {len(items)}条, 累计{len(stocks)}条")
        except Exception as e:
            logger.warning(f"拉取第{page}页失败: {e}")
            break

    # 缓存
    if stocks:
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump({'ts': datetime.now().timestamp(), 'stocks': stocks}, f, ensure_ascii=False)
            logger.info(f"缓存{len(stocks)}只股票")
        except: pass
    return stocks

def search_stocks(keyword: str, stocks: list = None) -> list:
    """模糊搜索"""
    if not stocks:
        stocks = fetch_all_stocks()
    kw = keyword.strip().upper()
    results = []
    for s in stocks:
        if kw in s['code'] or kw in s['name'].upper():
            results.append(s)
        elif kw and all(c in s['name'] for c in kw):
            results.append(s)
    return results[:30]

def get_industry_stocks(industry: str) -> list:
    """获取行业股票代码列表"""
    return SW_INDUSTRY.get(industry, [])

def get_concept_stocks(concept: str) -> list:
    """获取概念板块股票代码列表"""
    return CONCEPTS.get(concept, [])
