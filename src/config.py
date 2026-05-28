"""
RuiQuant 配置管理
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据库配置
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/ruiquant.db")
DATABASE_URL = f"sqlite:///{BASE_DIR / DATABASE_PATH}"

# DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 模拟盘配置
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "100000"))

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
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
