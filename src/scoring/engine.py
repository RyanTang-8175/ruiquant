"""
评分引擎
35 个因子，5 大类，IC 加权，自动优化
"""

import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, date
from sqlalchemy.orm import Session
from src.data.models import DailyQuote, TechnicalIndicator, StockBasic
from src.scoring.models import ScoreRecord
from src.utils.database import SessionLocal

logger = logging.getLogger(__name__)

# 默认因子权重（基于学术研究的 IC 值）
DEFAULT_WEIGHTS = {
    # Tier 1: 最强因子（IC > 0.04）
    'short_term_reversal': 0.08,
    'turnover_rate': 0.06,
    'idio_volatility': 0.05,
    'main_capital_flow': 0.06,
    'volume_price_divergence': 0.05,
    'abnormal_turnover': 0.05,
    'ai_news_sentiment': 0.05,

    # Tier 2: 好因子（IC 0.03-0.05）
    'volume_ratio': 0.04,
    'northbound_flow': 0.04,
    'dragon_tiger_list': 0.04,
    'limit_up_streak': 0.04,
    'sector_heat': 0.04,
    'sector_limit_count': 0.04,
    'analyst_revision': 0.04,
    'sue': 0.03,
    'ep': 0.03,
    'ai_policy_impact': 0.03,

    # Tier 3: 有用但较弱（IC 0.02-0.04）
    'trend': 0.03,
    'amihud_illiquidity': 0.02,
    'margin_balance_change': 0.02,
    'market_temperature': 0.02,
    'blast_rate': 0.02,
    'roe': 0.02,
    'ai_anomaly': 0.02,
    'ai_industry': 0.02,

    # Tier 4: 较弱或小众
    'rsi': 0.01,
    'macd': 0.01,
    'kdj': 0.01,
    'boll_position': 0.01,
    'high_52w_ratio': 0.02,
    'bp': 0.01,
    'kline_pattern': 0.01,
    'intraday_intensity': 0.01,
    'ai_stock_story': 0.01,
    'volume_price_corr': 0.01,
}

# 动态权重文件路径
WEIGHTS_FILE = "data/factor_weights.json"


def _load_dynamic_weights() -> dict:
    """从文件加载动态权重，不存在则用默认"""
    try:
        with open(WEIGHTS_FILE, 'r') as f:
            weights = json.load(f)
            if weights and isinstance(weights, dict):
                return weights
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return DEFAULT_WEIGHTS.copy()


def save_dynamic_weights(weights: dict):
    """保存动态权重到文件"""
    import os
    os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
    with open(WEIGHTS_FILE, 'w') as f:
        json.dump(weights, f, indent=2)


class ScoringEngine:
    """评分引擎"""

    def __init__(self):
        self.db = SessionLocal()
        raw_weights = _load_dynamic_weights()
        self.weights = self._normalize_weights(raw_weights)

    def _normalize_weights(self, weights: dict) -> dict:
        """归一化权重，确保总和为 1.0"""
        total = sum(weights.values())
        if total > 0:
            return {k: v / total for k, v in weights.items()}
        return weights

    def close(self):
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

    def get_stock_data(self, code: str, days: int = 60) -> pd.DataFrame:
        """获取股票数据"""
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
            'volume': q.volume,
            'amount': q.amount,
            'change_pct': q.change_pct,
            'turnover_rate': q.turnover_rate,
        } for q in quotes])

        df = df.sort_values('trade_date').reset_index(drop=True)
        return df

    def get_indicators(self, code: str, days: int = 60) -> pd.DataFrame:
        """获取技术指标"""
        indicators = self.db.query(TechnicalIndicator).filter(
            TechnicalIndicator.code == code
        ).order_by(TechnicalIndicator.trade_date.desc()).limit(days).all()

        if not indicators:
            return pd.DataFrame()

        df = pd.DataFrame([{
            'trade_date': i.trade_date,
            'ma5': i.ma5,
            'ma10': i.ma10,
            'ma20': i.ma20,
            'ma60': i.ma60,
            'macd': i.macd,
            'macd_signal': i.macd_signal,
            'macd_hist': i.macd_hist,
            'rsi_6': i.rsi_6,
            'rsi_12': i.rsi_12,
            'kdj_k': i.kdj_k,
            'kdj_d': i.kdj_d,
            'kdj_j': i.kdj_j,
            'boll_upper': i.boll_upper,
            'boll_middle': i.boll_middle,
            'boll_lower': i.boll_lower,
        } for i in indicators])

        df = df.sort_values('trade_date').reset_index(drop=True)
        return df

    # ============ 因子计算函数 ============

    def calc_short_term_reversal(self, df: pd.DataFrame) -> float:
        """短期反转因子（A股最强因子）"""
        if len(df) < 5:
            return 50
        return_5d = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
        if return_5d < -0.10:
            return 90
        elif return_5d < -0.05:
            return 75
        elif return_5d < 0:
            return 60
        elif return_5d < 0.05:
            return 45
        elif return_5d < 0.10:
            return 30
        else:
            return 15

    def calc_turnover_rate(self, df: pd.DataFrame) -> float:
        """换手率因子"""
        if len(df) < 5:
            return 50
        avg_turnover = df['turnover_rate'].iloc[-5:].mean()
        if pd.isna(avg_turnover):
            return 50
        if avg_turnover > 10:
            return 30
        elif avg_turnover > 5:
            return 45
        elif avg_turnover > 2:
            return 60
        elif avg_turnover > 1:
            return 75
        else:
            return 90

    def calc_idio_volatility(self, df: pd.DataFrame) -> float:
        """特异性波动率因子"""
        if len(df) < 20:
            return 50
        returns = df['close'].pct_change().dropna()
        vol = returns.iloc[-20:].std()
        if pd.isna(vol):
            return 50
        if vol > 0.05:
            return 30
        elif vol > 0.03:
            return 45
        elif vol > 0.02:
            return 60
        elif vol > 0.01:
            return 75
        else:
            return 90

    def calc_volume_ratio(self, df: pd.DataFrame) -> float:
        """量比因子"""
        if len(df) < 6:
            return 50
        today_vol = df['volume'].iloc[-1]
        avg_vol = df['volume'].iloc[-6:-1].mean()
        if avg_vol == 0 or pd.isna(avg_vol):
            return 50
        ratio = today_vol / avg_vol
        if ratio > 3.0:
            return 95
        elif ratio > 2.0:
            return 82
        elif ratio > 1.5:
            return 67
        elif ratio > 0.8:
            return 50
        elif ratio > 0.5:
            return 30
        else:
            return 10

    def calc_abnormal_turnover(self, df: pd.DataFrame) -> float:
        """异常换手率因子"""
        if len(df) < 20:
            return 50
        turnover = df['turnover_rate'].iloc[-20:]
        mean_t = turnover.mean()
        std_t = turnover.std()
        if pd.isna(mean_t) or pd.isna(std_t) or std_t == 0:
            return 50
        z_score = (df['turnover_rate'].iloc[-1] - mean_t) / std_t
        if z_score > 2:
            return 85
        elif z_score > 1:
            return 70
        elif z_score > 0:
            return 55
        elif z_score > -1:
            return 40
        else:
            return 25

    def calc_volume_price_divergence(self, df: pd.DataFrame) -> float:
        """量价背离因子"""
        if len(df) < 10:
            return 50
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
        vol_change = (df['volume'].iloc[-5:].mean() - df['volume'].iloc[-10:-5].mean()) / df['volume'].iloc[-10:-5].mean()
        if pd.isna(price_change) or pd.isna(vol_change):
            return 50
        if price_change > 0.03 and vol_change < -0.3:
            return 25
        elif price_change > 0.03 and vol_change > 0.3:
            return 85
        elif price_change < -0.03 and vol_change < -0.3:
            return 70
        elif price_change < -0.03 and vol_change > 0.3:
            return 20
        else:
            return 50

    def calc_trend(self, ind: pd.DataFrame) -> float:
        """均线趋势因子"""
        if ind.empty or len(ind) < 20:
            return 50
        latest = ind.iloc[-1]
        score = 50
        ma5, ma10, ma20 = latest.get('ma5'), latest.get('ma10'), latest.get('ma20')
        close = latest.get('close', ma5)
        if pd.isna(ma5) or pd.isna(ma10) or pd.isna(ma20):
            return 50
        if ma5 > ma10 > ma20:
            score += 30
        elif ma5 > ma10:
            score += 15
        elif ma5 < ma10 < ma20:
            score -= 30
        elif ma5 < ma10:
            score -= 15
        if close and close > ma5:
            score += 15
        elif close and close < ma20:
            score -= 10
        return max(0, min(100, score))

    def calc_rsi(self, ind: pd.DataFrame) -> float:
        """RSI 因子"""
        if ind.empty:
            return 50
        rsi = ind.iloc[-1].get('rsi_6', 50)
        if pd.isna(rsi):
            return 50
        if 50 <= rsi <= 70:
            return 75
        elif rsi > 80:
            return 25
        elif rsi < 20:
            return 65
        elif 30 <= rsi < 50:
            return 45
        else:
            return 50

    def calc_macd(self, ind: pd.DataFrame) -> float:
        """MACD 因子"""
        if ind.empty or len(ind) < 2:
            return 50
        macd = ind.iloc[-1].get('macd', 0)
        signal = ind.iloc[-1].get('macd_signal', 0)
        if pd.isna(macd) or pd.isna(signal):
            return 50
        score = 50
        if macd > signal:
            score += 20
        else:
            score -= 15
        if macd > 0:
            score += 10
        return max(0, min(100, score))

    def calc_kdj(self, ind: pd.DataFrame) -> float:
        """KDJ 因子"""
        if ind.empty:
            return 50
        k = ind.iloc[-1].get('kdj_k', 50)
        d = ind.iloc[-1].get('kdj_d', 50)
        if pd.isna(k) or pd.isna(d):
            return 50
        score = 50
        if k > d and k < 80:
            score += 15
        elif k > 80:
            score -= 15
        elif k < d:
            score -= 10
        return max(0, min(100, score))

    def calc_kline_pattern(self, df: pd.DataFrame) -> float:
        """K 线形态因子"""
        if len(df) < 1:
            return 50
        row = df.iloc[-1]
        o, c, h, l = row['open'], row['close'], row['high'], row['low']
        if pd.isna(o) or pd.isna(c) or pd.isna(h) or pd.isna(l):
            return 50
        total_range = h - l
        if total_range == 0:
            return 50
        body = abs(c - o)
        body_ratio = body / total_range
        score = 50
        if body_ratio > 0.7:
            score += 20 if c > o else -20
        lower_shadow = min(o, c) - l
        if lower_shadow / total_range > 0.5:
            score += 15
        upper_shadow = h - max(o, c)
        if upper_shadow / total_range > 0.5:
            score -= 15
        return max(0, min(100, score))

    def calc_intraday_intensity(self, df: pd.DataFrame) -> float:
        """日内强度因子"""
        if len(df) < 1:
            return 50
        row = df.iloc[-1]
        h, l, c = row['high'], row['low'], row['close']
        if pd.isna(h) or pd.isna(l) or pd.isna(c) or h == l:
            return 50
        position = (c - l) / (h - l)
        if position > 0.8:
            return 85
        elif position > 0.6:
            return 70
        elif position > 0.4:
            return 50
        elif position > 0.2:
            return 35
        else:
            return 20

    def calc_high_52w_ratio(self, df: pd.DataFrame) -> float:
        """52周高点比率"""
        if len(df) < 20:
            return 50
        high_52w = df['high'].max()
        current = df['close'].iloc[-1]
        if pd.isna(high_52w) or pd.isna(current) or high_52w == 0:
            return 50
        ratio = current / high_52w
        if ratio > 0.95:
            return 40
        elif ratio > 0.85:
            return 55
        elif ratio > 0.70:
            return 65
        elif ratio > 0.50:
            return 55
        else:
            return 45

    def calc_volume_price_corr(self, df: pd.DataFrame) -> float:
        """量价相关性因子"""
        if len(df) < 20:
            return 50
        returns = df['close'].pct_change().iloc[-20:]
        vol_change = df['volume'].pct_change().iloc[-20:]
        corr = returns.corr(vol_change)
        if pd.isna(corr):
            return 50
        if corr > 0.5:
            return 75
        elif corr > 0.2:
            return 60
        elif corr > -0.2:
            return 50
        elif corr > -0.5:
            return 40
        else:
            return 25

    # ============ 新增因子 ============

    def calc_blast_rate(self, df: pd.DataFrame) -> float:
        """爆量率因子 — 成交量相对 20 日均量的倍数"""
        if len(df) < 20:
            return 50
        today_vol = df['volume'].iloc[-1]
        avg_vol = df['volume'].iloc[-20:].mean()
        if pd.isna(avg_vol) or avg_vol == 0:
            return 50
        ratio = today_vol / avg_vol
        if ratio > 5.0:
            return 90
        elif ratio > 3.0:
            return 80
        elif ratio > 2.0:
            return 65
        elif ratio > 1.2:
            return 55
        elif ratio > 0.8:
            return 45
        else:
            return 30

    def calc_amihud_illiquidity(self, df: pd.DataFrame) -> float:
        """非流动性因子（Amihud）— |收益率| / 成交额"""
        if len(df) < 20:
            return 50
        recent = df.iloc[-20:]
        returns = recent['close'].pct_change().dropna()
        amounts = recent['amount'].iloc[1:]
        # 避免除零
        amounts = amounts.replace(0, np.nan)
        illiquidity = (returns.abs() / amounts).mean()
        if pd.isna(illiquidity):
            return 50
        # 低非流动性（高流动性）更好
        # 归一化到合理范围
        if illiquidity < 1e-8:
            return 70
        elif illiquidity < 5e-8:
            return 60
        elif illiquidity < 1e-7:
            return 50
        elif illiquidity < 5e-7:
            return 40
        else:
            return 30

    def calc_limit_up_streak(self, df: pd.DataFrame) -> float:
        """连板因子 — 连续涨停天数"""
        if len(df) < 2:
            return 50
        streak = 0
        for i in range(len(df) - 1, 0, -1):
            if df['change_pct'].iloc[i] is not None and df['change_pct'].iloc[i] >= 9.9:
                streak += 1
            else:
                break
        if streak >= 3:
            return 90
        elif streak == 2:
            return 75
        elif streak == 1:
            return 60
        else:
            return 45

    def calc_market_temperature(self, df: pd.DataFrame) -> float:
        """市场温度因子 — 基于近 5 日涨跌幅度"""
        if len(df) < 5:
            return 50
        recent_5d = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
        if pd.isna(recent_5d):
            return 50
        if recent_5d > 0.05:
            return 80
        elif recent_5d > 0.02:
            return 65
        elif recent_5d > -0.02:
            return 50
        elif recent_5d > -0.05:
            return 35
        else:
            return 20

    def calc_boll_position(self, ind: pd.DataFrame) -> float:
        """布林带位置因子"""
        if ind.empty:
            return 50
        latest = ind.iloc[-1]
        upper = latest.get('boll_upper')
        lower = latest.get('boll_lower')
        middle = latest.get('boll_middle')
        if pd.isna(upper) or pd.isna(lower) or pd.isna(middle) or upper == lower:
            return 50
        # 用最近的收盘价（从指标数据里没有 close，用 ma5 代替近似）
        price = latest.get('ma5', middle)
        if pd.isna(price):
            return 50
        position = (price - lower) / (upper - lower)
        if position > 0.9:
            return 25  # 接近上轨，超买
        elif position > 0.7:
            return 45
        elif position > 0.3:
            return 65  # 中间区域
        elif position > 0.1:
            return 70
        else:
            return 55  # 接近下轨，可能反弹

    # ============ 汇总评分 ============

    # 已实现的因子列表
    IMPLEMENTED_FACTORS = [
        'short_term_reversal', 'turnover_rate', 'idio_volatility',
        'volume_ratio', 'abnormal_turnover', 'volume_price_divergence',
        'trend', 'rsi', 'macd', 'kdj', 'kline_pattern',
        'intraday_intensity', 'high_52w_ratio', 'volume_price_corr',
        # 新增因子
        'blast_rate', 'amihud_illiquidity', 'limit_up_streak',
        'market_temperature', 'boll_position',
    ]

    def score_stock(self, code: str) -> dict:
        """计算单只股票的评分"""
        df = self.get_stock_data(code)
        ind = self.get_indicators(code)

        if df.empty:
            return None

        # 计算所有已实现的因子
        factors = {
            'short_term_reversal': self.calc_short_term_reversal(df),
            'turnover_rate': self.calc_turnover_rate(df),
            'idio_volatility': self.calc_idio_volatility(df),
            'volume_ratio': self.calc_volume_ratio(df),
            'abnormal_turnover': self.calc_abnormal_turnover(df),
            'volume_price_divergence': self.calc_volume_price_divergence(df),
            'trend': self.calc_trend(ind),
            'rsi': self.calc_rsi(ind),
            'macd': self.calc_macd(ind),
            'kdj': self.calc_kdj(ind),
            'kline_pattern': self.calc_kline_pattern(df),
            'intraday_intensity': self.calc_intraday_intensity(df),
            'high_52w_ratio': self.calc_high_52w_ratio(df),
            'volume_price_corr': self.calc_volume_price_corr(df),
            'blast_rate': self.calc_blast_rate(df),
            'amihud_illiquidity': self.calc_amihud_illiquidity(df),
            'limit_up_streak': self.calc_limit_up_streak(df),
            'market_temperature': self.calc_market_temperature(df),
            'boll_position': self.calc_boll_position(ind),
        }

        # 只对已实现的因子做权重归一化
        active_weights = {k: self.weights.get(k, 0.01) for k in factors}
        total_weight = sum(active_weights.values())
        if total_weight > 0:
            normalized = {k: v / total_weight for k, v in active_weights.items()}
        else:
            normalized = {k: 1.0 / len(factors) for k in factors}

        total_score = sum(factors[k] * normalized[k] for k in factors)
        total_score = min(100, max(0, total_score))

        # 确定评级
        if total_score >= 80:
            rating = "强关注"
        elif total_score >= 65:
            rating = "观察"
        elif total_score >= 50:
            rating = "中性"
        else:
            rating = "不追"

        return {
            'code': code,
            'total_score': round(total_score, 1),
            'rating': rating,
            'factors': factors,
            'calculated_at': datetime.now()
        }

    def score_all_stocks(self) -> list:
        """计算所有股票的评分"""
        stocks = self.db.query(StockBasic).filter(
            StockBasic.is_active == True,
            StockBasic.is_st == False
        ).all()

        results = []
        total = len(stocks)

        for i, stock in enumerate(stocks):
            if (i + 1) % 500 == 0:
                logger.info(f"评分进度: {i + 1}/{total}")

            result = self.score_stock(stock.code)
            if result:
                result['name'] = stock.name
                results.append(result)

        results.sort(key=lambda x: x['total_score'], reverse=True)
        logger.info(f"评分完成: {len(results)} 只股票")
        return results

    def save_scores(self, results: list):
        """保存评分结果到数据库"""
        saved = 0
        try:
            for result in results:
                record = ScoreRecord(
                    code=result['code'],
                    name=result.get('name', ''),
                    score_date=result['calculated_at'],
                    total_score=result['total_score'],
                    rating=result['rating'],
                    trend_score=result['factors'].get('trend'),
                    reversal_score=result['factors'].get('short_term_reversal'),
                    volume_ratio_score=result['factors'].get('volume_ratio'),
                    turnover_score=result['factors'].get('turnover_rate'),
                    volatility_score=result['factors'].get('idio_volatility'),
                    volume_price_corr_score=result['factors'].get('volume_price_corr'),
                    divergence_score=result['factors'].get('volume_price_divergence'),
                    kline_score=result['factors'].get('kline_pattern'),
                    rsi_score=result['factors'].get('rsi'),
                    macd_score=result['factors'].get('macd'),
                    factor_weights=self.weights
                )
                self.db.add(record)
                saved += 1

            self.db.commit()
            logger.info(f"保存了 {saved} 条评分记录")
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存评分失败: {e}")

        return saved

    def get_watchlist(self, min_score: float = 65, limit: int = 20) -> list:
        """获取观察池（从缓存读取，不重新计算）"""
        try:
            # 查最新评分日期
            latest = self.db.query(ScoreRecord.score_date).order_by(
                ScoreRecord.score_date.desc()
            ).first()

            if not latest:
                # 没有缓存，触发一次全量评分
                logger.info("无缓存评分，触发全量评分...")
                results = self.score_all_stocks()
                self.save_scores(results)
                return [r for r in results if r['total_score'] >= min_score][:limit]

            records = self.db.query(ScoreRecord).filter(
                ScoreRecord.score_date == latest[0],
                ScoreRecord.total_score >= min_score
            ).order_by(ScoreRecord.total_score.desc()).limit(limit).all()

            return [{
                'code': r.code,
                'name': r.name,
                'total_score': r.total_score,
                'rating': r.rating,
                'factors': {
                    'trend': r.trend_score or 50,
                    'short_term_reversal': r.reversal_score or 50,
                    'volume_ratio': r.volume_ratio_score or 50,
                    'turnover_rate': r.turnover_score or 50,
                    'idio_volatility': r.volatility_score or 50,
                    'volume_price_corr': r.volume_price_corr_score or 50,
                    'volume_price_divergence': r.divergence_score or 50,
                    'kline_pattern': r.kline_score or 50,
                    'rsi': r.rsi_score or 50,
                    'macd': r.macd_score or 50,
                }
            } for r in records]

        except Exception as e:
            logger.error(f"读取观察池失败: {e}")
            return []

    def rescore_all(self) -> int:
        """全量重新评分（供手动刷新和定时任务调用）"""
        results = self.score_all_stocks()
        saved = self.save_scores(results)
        return saved
