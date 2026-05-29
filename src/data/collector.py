"""
数据采集模块
使用 baostock 获取 A 股数据（更稳定）
"""

import os
import time
import logging
import baostock as bs
import pandas as pd
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.data.models import StockBasic, DailyQuote
from src.utils.database import SessionLocal

logger = logging.getLogger(__name__)


class DataCollector:
    """数据采集器"""

    def __init__(self):
        self.db = SessionLocal()
        self._login()

    def _login(self):
        """登录 baostock"""
        try:
            lg = bs.login()
            if lg.error_code != '0':
                logger.error(f"baostock 登录失败: {lg.error_msg}")
        except Exception as e:
            logger.error(f"baostock 登录异常: {e}")

    def _logout(self):
        """登出 baostock"""
        try:
            bs.logout()
        except Exception:
            pass

    def close(self):
        """关闭连接"""
        self._logout()
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
            self._logout()
            self.db.close()
        except Exception:
            pass

    def get_stock_list(self) -> pd.DataFrame:
        """获取所有 A 股股票列表"""
        try:
            rs = bs.query_stock_basic()
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            df = pd.DataFrame(data, columns=rs.fields)
            # 只保留 A 股
            df = df[df['type'] == '1']
            logger.info(f"获取到 {len(df)} 只股票")
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_daily_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取单只股票的历史日线数据"""
        try:
            # 转换代码格式：000001 -> sh.000001 或 sz.000001
            if code.startswith('6'):
                bs_code = f"sh.{code}"
            else:
                bs_code = f"sz.{code}"

            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,amount,turn,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2"  # 前复权
            )

            data = []
            while rs.next():
                data.append(rs.get_row_data())

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data, columns=rs.fields)
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'pctChg']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.rename(columns={
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量',
                'amount': '成交额',
                'turn': '换手率',
                'pctChg': '涨跌幅'
            })
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
                name = row.get('code_name', '')

                if not code or pd.isna(code):
                    continue

                # 去掉前缀 sh. 或 sz.
                if '.' in code:
                    code = code.split('.')[1]

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
            self.db.rollback()

            for _, row in df.iterrows():
                trade_date = pd.to_datetime(row['日期']).date()

                existing = self.db.query(DailyQuote).filter(
                    DailyQuote.code == code,
                    DailyQuote.trade_date == trade_date
                ).first()

                # 处理 NaN 值
                volume = row.get('成交量', 0)
                if pd.isna(volume):
                    volume = 0
                else:
                    volume = int(volume)

                if existing:
                    existing.open = row.get('开盘') if not pd.isna(row.get('开盘')) else None
                    existing.high = row.get('最高') if not pd.isna(row.get('最高')) else None
                    existing.low = row.get('最低') if not pd.isna(row.get('最低')) else None
                    existing.close = row.get('收盘') if not pd.isna(row.get('收盘')) else None
                    existing.volume = volume
                    existing.amount = row.get('成交额') if not pd.isna(row.get('成交额')) else None
                    existing.change_pct = row.get('涨跌幅') if not pd.isna(row.get('涨跌幅')) else None
                    existing.turnover_rate = row.get('换手率') if not pd.isna(row.get('换手率')) else None
                else:
                    quote = DailyQuote(
                        code=code,
                        trade_date=trade_date,
                        open=row.get('开盘') if not pd.isna(row.get('开盘')) else None,
                        high=row.get('最高') if not pd.isna(row.get('最高')) else None,
                        low=row.get('最低') if not pd.isna(row.get('最低')) else None,
                        close=row.get('收盘') if not pd.isna(row.get('收盘')) else None,
                        volume=volume,
                        amount=row.get('成交额') if not pd.isna(row.get('成交额')) else None,
                        change_pct=row.get('涨跌幅') if not pd.isna(row.get('涨跌幅')) else None,
                        turnover_rate=row.get('换手率') if not pd.isna(row.get('换手率')) else None
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
        end_date = date.today().strftime("%Y-%m-%d")
        start_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")

        total = len(stock_list)
        success = 0
        fail = 0

        for i, (_, row) in enumerate(stock_list.iterrows()):
            code = row['code']
            if '.' in code:
                code = code.split('.')[1]

            if (i + 1) % 100 == 0:
                logger.info(f"  进度: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

            df = self.get_daily_history(code, start_date, end_date)
            if not df.empty:
                result = self.save_daily_quotes(code, df)
                if result > 0:
                    success += 1
                else:
                    fail += 1
            else:
                fail += 1

            time.sleep(0.1)

        logger.info(f"采集完成: 成功 {success}, 失败 {fail}")

    def get_market_snapshot(self) -> dict:
        """获取市场快照（使用 SQL 聚合优化）"""
        today = date.today()

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
