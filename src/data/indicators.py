"""
技术指标计算模块
计算 MA/MACD/RSI/KDJ/BOLL 等技术指标
"""

import logging
import pandas as pd
import numpy as np
from datetime import date
from sqlalchemy.orm import Session
from src.data.models import DailyQuote, TechnicalIndicator
from src.utils.database import SessionLocal

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """技术指标计算器"""

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

    def get_daily_data(self, code: str, days: int = 120) -> pd.DataFrame:
        """获取股票日线数据"""
        quotes = self.db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).limit(days).all()

        if not quotes:
            return pd.DataFrame()

        df = pd.DataFrame([{
            'trade_date': q.trade_date,
            'open': q.open,
            'high': q.high,
            'low': q.low,
            'close': q.close,
            'volume': q.volume
        } for q in quotes])

        df = df.sort_values('trade_date').reset_index(drop=True)
        return df

    def calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算均线"""
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        return df

    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 MACD"""
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd_dif'] = ema12 - ema26
        df['macd_dea'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = 2 * (df['macd_dif'] - df['macd_dea'])
        return df

    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 RSI（带除零保护）"""
        delta = df['close'].diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()

        # 除零保护
        loss = loss.replace(0, np.nan)
        rs = gain / loss
        rs = rs.fillna(0)
        df['rsi_6'] = 100 - (100 / (1 + rs))

        gain12 = (delta.where(delta > 0, 0)).rolling(window=12).mean()
        loss12 = (-delta.where(delta < 0, 0)).rolling(window=12).mean()
        loss12 = loss12.replace(0, np.nan)
        rs12 = gain12 / loss12
        rs12 = rs12.fillna(0)
        df['rsi_12'] = 100 - (100 / (1 + rs12))

        return df

    def calculate_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 KDJ（带除零保护）"""
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()

        denominator = high_max - low_min
        denominator = denominator.replace(0, np.nan)
        rsv = (df['close'] - low_min) / denominator * 100
        rsv = rsv.fillna(50)  # 默认中性值

        df['kdj_k'] = rsv.ewm(com=2, adjust=False).mean()
        df['kdj_d'] = df['kdj_k'].ewm(com=2, adjust=False).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']

        return df

    def calculate_boll(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算布林带"""
        df['boll_middle'] = df['close'].rolling(window=20).mean()
        std = df['close'].rolling(window=20).std()
        df['boll_upper'] = df['boll_middle'] + 2 * std
        df['boll_lower'] = df['boll_middle'] - 2 * std
        return df

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        df = self.calculate_ma(df)
        df = self.calculate_macd(df)
        df = self.calculate_rsi(df)
        df = self.calculate_kdj(df)
        df = self.calculate_boll(df)
        return df

    def save_indicators(self, code: str, df: pd.DataFrame):
        """保存技术指标到数据库"""
        saved = 0
        try:
            self.db.rollback()  # 清理可能的脏数据

            for _, row in df.iterrows():
                trade_date = row['trade_date']

                existing = self.db.query(TechnicalIndicator).filter(
                    TechnicalIndicator.code == code,
                    TechnicalIndicator.trade_date == trade_date
                ).first()

                if existing:
                    existing.ma5 = row.get('ma5')
                    existing.ma10 = row.get('ma10')
                    existing.ma20 = row.get('ma20')
                    existing.ma60 = row.get('ma60')
                    existing.macd = row.get('macd_dif')
                    existing.macd_signal = row.get('macd_dea')
                    existing.macd_hist = row.get('macd_hist')
                    existing.rsi_6 = row.get('rsi_6')
                    existing.rsi_12 = row.get('rsi_12')
                    existing.kdj_k = row.get('kdj_k')
                    existing.kdj_d = row.get('kdj_d')
                    existing.kdj_j = row.get('kdj_j')
                    existing.boll_upper = row.get('boll_upper')
                    existing.boll_middle = row.get('boll_middle')
                    existing.boll_lower = row.get('boll_lower')
                else:
                    indicator = TechnicalIndicator(
                        code=code,
                        trade_date=trade_date,
                        ma5=row.get('ma5'),
                        ma10=row.get('ma10'),
                        ma20=row.get('ma20'),
                        ma60=row.get('ma60'),
                        macd=row.get('macd_dif'),
                        macd_signal=row.get('macd_dea'),
                        macd_hist=row.get('macd_hist'),
                        rsi_6=row.get('rsi_6'),
                        rsi_12=row.get('rsi_12'),
                        kdj_k=row.get('kdj_k'),
                        kdj_d=row.get('kdj_d'),
                        kdj_j=row.get('kdj_j'),
                        boll_upper=row.get('boll_upper'),
                        boll_middle=row.get('boll_middle'),
                        boll_lower=row.get('boll_lower')
                    )
                    self.db.add(indicator)
                saved += 1

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存 {code} 技术指标失败: {e}")
            return 0

        return saved

    def calculate_for_stock(self, code: str):
        """计算单只股票的技术指标"""
        df = self.get_daily_data(code)
        if df.empty:
            return 0

        df = self.calculate_all(df)
        return self.save_indicators(code, df)

    def calculate_for_all(self):
        """计算所有股票的技术指标"""
        from src.data.models import StockBasic

        stocks = self.db.query(StockBasic).filter(
            StockBasic.is_active == True
        ).all()

        total = len(stocks)
        success = 0

        for i, stock in enumerate(stocks):
            if (i + 1) % 100 == 0:
                logger.info(f"进度: {i + 1}/{total}")

            result = self.calculate_for_stock(stock.code)
            if result > 0:
                success += 1

        logger.info(f"技术指标计算完成: {success}/{total}")
        return success
