"""
RuiQuant 配置管理
支持 .env 文件和 app 内设置（settings.json 优先）
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 设置文件路径
SETTINGS_FILE = BASE_DIR / "data" / "settings.json"


def _load_settings() -> dict:
    """从 settings.json 加载设置"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def save_settings(settings: dict):
    """保存设置到 settings.json"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 合并已有设置
    current = _load_settings()
    current.update(settings)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(current, f, indent=2, ensure_ascii=False)


def get_setting(key: str, env_key: str = None, default: str = "") -> str:
    """获取设置值，优先级：settings.json > 环境变量 > 默认值"""
    settings = _load_settings()
    if key in settings and settings[key]:
        return settings[key]
    if env_key:
        val = os.getenv(env_key, "")
        if val:
            return val
    return default


# 数据库配置
DATABASE_PATH = get_setting("database_path", "DATABASE_PATH", "data/ruiquant.db")
DATABASE_URL = f"sqlite:///{BASE_DIR / DATABASE_PATH}"

# AI 配置（可从 app 内修改）
DEEPSEEK_API_KEY = get_setting("api_key", "DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = get_setting("base_url", "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = get_setting("model", "DEEPSEEK_MODEL", "deepseek-chat")

# 模拟盘配置
INITIAL_CAPITAL = float(get_setting("initial_capital", "INITIAL_CAPITAL", "100000"))

# 交易规则
COMMISSION_RATE = 0.00025  # 佣金万2.5
COMMISSION_MIN = 5.0       # 佣金最低5元
STAMP_TAX_RATE = 0.0005    # 印花税千0.5
TRANSFER_FEE_RATE = 0.00002  # 过户费万0.2

# 仓位限制
MAX_POSITION_PCT = 0.30  # 单票最大仓位30%
MAX_TOTAL_POSITION = 0.80  # 总仓位最大80%

# 止损规则
STOP_LOSS_PCT = -0.08  # 单票亏损8%提醒
FORCE_SELL_PCT = -0.15  # 单票亏损15%强制卖出
DAILY_LOSS_LIMIT = -0.05  # 单日亏损5%暂停交易
CONSECUTIVE_LOSS_LIMIT = 3  # 连续3笔亏损暂停

# 日志配置
LOG_LEVEL = get_setting("log_level", "LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
