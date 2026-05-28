"""
数据采集模块
使用 AKShare 获取 A 股数据
"""

import time
import logging
import akshare as ak
import pandas as pd
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.data.models import StockBasic, DailyQuote
from src.utils.database import SessionLocal

logger = logging.getLogger(__name__)

# AKShare 列名映射（兼容不同版本）
COLUMN_MAP = {
    '日期': 'trade_date',
    '开盘': 'open',
    '收盘': 'close',
    '最高': 'high',
    '最低': 'low',
    '成交量': 'volume',
    '成交额': 'amount',
    '涨跌幅': 'change_pct',
    '换手率': 'turnover_rate',
}


class DataCollector:
    """数据采集器"""

    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        """关闭数据库连接"""
        try:
            self.db.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.db.close()
        except Exception:
            pass

    def get_stock_list(self) -> pd.DataFrame:
        """获取所有 A 股股票列表"""
        try:
            df = ak.stock_info_a_code_name()
            logger.info(f"获取到 {len(df)} 只股票")
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_realtime_quotes(self) -> pd.DataFrame:
        """获取所有 A 股实时行情"""
        try:
            df = ak.stock_zh_a_spot_em()
            logger.info(f"获取到 {len(df)} 只股票的实时行情")
            return df
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return pd.DataFrame()

    def get_daily_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取单只股票的历史日线数据"""
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            return df
        except Exception as e:
            logger.error(f"获取 {code} 历史数据失败: {e}")
            return pd.DataFrame()

    def save_stock_basic(self, stock_list: pd.DataFrame):
        """保存股票基础信息到数据库"""
        saved = 0
        try:
            for _, row in stock_list.iterrows():
                code = row.get('code', '')
                name = row.get('name', '')

                if not code or pd.isna(code):
                    continue

                existing = self.db.query(StockBasic).filter(StockBasic.code == code).first()
                if existing:
                    existing.name = str(name)[:50]
                    existing.is_st = 'ST' in str(name) or '*ST' in str(name)
                    existing.updated_at = datetime.now()
                else:
                    stock = StockBasic(
                        code=str(code),
                        name=str(name)[:50],
                        is_st='ST' in str(name) or '*ST' in str(name),
                        is_active=True
                    )
                    self.db.add(stock)
                saved += 1

            self.db.commit()
            logger.info(f"保存了 {saved} 只股票的基础信息")
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存股票基础信息失败: {e}")
            return 0

        return saved

    def save_daily_quotes(self, code: str, df: pd.DataFrame):
        """保存日线数据到数据库"""
        saved = 0
        try:
            # 开始前先清理可能的脏数据
            self.db.rollback()

            for _, row in df.iterrows():
                # 列名兼容处理
                trade_date = pd.to_datetime(row.get('日期', row.get('trade_date', None))).date()

                existing = self.db.query(DailyQuote).filter(
                    DailyQuote.code == code,
                    DailyQuote.trade_date == trade_date
                ).first()

                if existing:
                    existing.open = row.get('开盘', row.get('open', None))
                    existing.high = row.get('最高', row.get('high', None))
                    existing.low = row.get('最低', row.get('low', None))
                    existing.close = row.get('收盘', row.get('close', None))
                    existing.volume = int(row.get('成交量', row.get('volume', 0)))
                    existing.amount = row.get('成交额', row.get('amount', None))
                    existing.change_pct = row.get('涨跌幅', row.get('change_pct', None))
                    existing.turnover_rate = row.get('换手率', row.get('turnover_rate', None))
                else:
                    quote = DailyQuote(
                        code=code,
                        trade_date=trade_date,
                        open=row.get('开盘', row.get('open', None)),
                        high=row.get('最高', row.get('high', None)),
                        low=row.get('最低', row.get('low', None)),
                        close=row.get('收盘', row.get('close', None)),
                        volume=int(row.get('成交量', row.get('volume', 0))),
                        amount=row.get('成交额', row.get('amount', None)),
                        change_pct=row.get('涨跌幅', row.get('change_pct', None)),
                        turnover_rate=row.get('换手率', row.get('turnover_rate', None))
                    )
                    self.db.add(quote)
                saved += 1

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存 {code} 数据失败: {e}")
            return 0

        return saved

    def collect_all_stocks(self, days: int = 30):
        """采集所有股票数据"""
        logger.info("=" * 50)
        logger.info("开始采集数据...")
        logger.info("=" * 50)

        # 1. 获取股票列表
        logger.info("1. 获取股票列表...")
        stock_list = self.get_stock_list()
        if stock_list.empty:
            logger.error("获取股票列表失败，终止采集")
            return

        # 2. 保存基础信息
        logger.info("2. 保存股票基础信息...")
        self.save_stock_basic(stock_list)

        # 3. 获取历史日线数据
        logger.info(f"3. 获取最近 {days} 天的历史数据...")
        end_date = date.today().strftime("%Y%m%d")
        start_date = (date.today() - timedelta(days=days)).strftime("%Y%m%d")

        total = len(stock_list)
        success = 0
        fail = 0
        consecutive_fails = 0

        for i, (_, row) in enumerate(stock_list.iterrows()):
            code = row['code']

            if (i + 1) % 100 == 0:
                logger.info(f"  进度: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

            df = self.get_daily_history(code, start_date, end_date)
            if not df.empty:
                result = self.save_daily_quotes(code, df)
                if result > 0:
                    success += 1
                    consecutive_fails = 0
                else:
                    fail += 1
                    consecutive_fails += 1
            else:
                fail += 1
                consecutive_fails += 1

            # 连续失败过多时增加等待时间
            if consecutive_fails > 10:
                logger.warning(f"连续失败 {consecutive_fails} 次，等待 5 秒...")
                time.sleep(5)
                consecutive_fails = 0
            else:
                time.sleep(0.3)

        logger.info(f"采集完成: 成功 {success}, 失败 {fail}")

    def get_market_snapshot(self) -> dict:
        """获取市场快照（使用 SQL 聚合优化）"""
        today = date.today()

        # 先尝试今天的数据
        result = self.db.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN change_pct > 0 THEN 1 ELSE 0 END) as up_count,
                SUM(CASE WHEN change_pct < 0 THEN 1 ELSE 0 END) as down_count,
                SUM(CASE WHEN change_pct = 0 THEN 1 ELSE 0 END) as flat_count,
                SUM(CASE WHEN change_pct >= 9.9 THEN 1 ELSE 0 END) as limit_up,
                SUM(CASE WHEN change_pct <= -9.9 THEN 1 ELSE 0 END) as limit_down,
                SUM(amount) / 1e8 as total_amount_yi
            FROM daily_quote
            WHERE trade_date = :today
        """), {"today": today}).fetchone()

        if result[0] == 0:
            # 没有今天的数据，获取最近一天
            latest = self.db.execute(text("""
                SELECT trade_date FROM daily_quote
                ORDER BY trade_date DESC LIMIT 1
            """)).fetchone()

            if latest:
                result = self.db.execute(text("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN change_pct > 0 THEN 1 ELSE 0 END) as up_count,
                        SUM(CASE WHEN change_pct < 0 THEN 1 ELSE 0 END) as down_count,
                        SUM(CASE WHEN change_pct = 0 THEN 1 ELSE 0 END) as flat_count,
                        SUM(CASE WHEN change_pct >= 9.9 THEN 1 ELSE 0 END) as limit_up,
                        SUM(CASE WHEN change_pct <= -9.9 THEN 1 ELSE 0 END) as limit_down,
                        SUM(amount) / 1e8 as total_amount_yi
                    FROM daily_quote
                    WHERE trade_date = :today
                """), {"today": latest[0]}).fetchone()
                today = latest[0]

        if result[0] == 0:
            return {"error": "没有数据"}

        return {
            "date": str(today),
            "up_count": int(result[1] or 0),
            "down_count": int(result[2] or 0),
            "flat_count": int(result[3] or 0),
            "limit_up_count": int(result[4] or 0),
            "limit_down_count": int(result[5] or 0),
            "total_amount_yi": round(float(result[6] or 0), 2)
        }
