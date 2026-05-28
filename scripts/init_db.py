"""
初始化数据库
创建所有数据表
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DATABASE_URL, DATABASE_PATH, BASE_DIR
from src.utils.database import engine, Base, SessionLocal
from src.data.models import StockBasic, DailyQuote, TechnicalIndicator
from src.scoring.models import ScoreRecord
from src.prediction.models import Prediction
from src.trading.models import PaperAccount, Position, Trade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库"""
    db_path = BASE_DIR / DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"正在创建数据库: {db_path}")

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    logger.info("数据库表创建完成:")
    for table in Base.metadata.tables:
        logger.info(f"  - {table}")

    # 创建默认模拟盘账户
    db = SessionLocal()
    try:
        from src.config import INITIAL_CAPITAL
        existing = db.query(PaperAccount).first()
        if not existing:
            account = PaperAccount(
                name="默认账户",
                initial_capital=INITIAL_CAPITAL,
                cash=INITIAL_CAPITAL
            )
            db.add(account)
            db.commit()
            logger.info(f"创建默认模拟盘账户: {INITIAL_CAPITAL:,.0f} 元")
        else:
            logger.info("模拟盘账户已存在")
    except Exception as e:
        logger.error(f"创建账户失败: {e}")
        db.rollback()
    finally:
        db.close()

    logger.info("数据库初始化完成!")


if __name__ == "__main__":
    init_database()
