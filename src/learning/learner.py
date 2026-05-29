"""
自我学习引擎
根据预测准确率自动调整因子权重
"""

import logging
import json
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.prediction.models import Prediction
from src.scoring.engine import ScoringEngine, DEFAULT_WEIGHTS
from src.data.models import DailyQuote
from src.utils.database import SessionLocal

logger = logging.getLogger(__name__)


class SelfLearningEngine:
    """自我学习引擎"""

    def __init__(self):
        self.db = SessionLocal()

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

    def analyze_prediction_accuracy(self, last_n_days: int = 30) -> dict:
        """分析预测准确率"""
        cutoff = datetime.now() - timedelta(days=last_n_days)

        completed = self.db.query(Prediction).filter(
            Prediction.status == "completed",
            Prediction.prediction_date >= cutoff
        ).all()

        if not completed:
            return {"total": 0, "message": "暂无已完成的预测"}

        # 计算各时间维度的命中率
        t1_hits = sum(1 for p in completed if p.hit_t1)
        t3_hits = sum(1 for p in completed if p.hit_t3)
        t5_hits = sum(1 for p in completed if p.hit_t5)

        # 计算平均收益
        t1_returns = [p.actual_return_t1 for p in completed if p.actual_return_t1 is not None]
        t3_returns = [p.actual_return_t3 for p in completed if p.actual_return_t3 is not None]
        t5_returns = [p.actual_return_t5 for p in completed if p.actual_return_t5 is not None]

        # 按置信度分组统计
        high_conf = [p for p in completed if p.t1_confidence and p.t1_confidence >= 0.7]
        mid_conf = [p for p in completed if p.t1_confidence and 0.5 <= p.t1_confidence < 0.7]
        low_conf = [p for p in completed if p.t1_confidence and p.t1_confidence < 0.5]

        stats = {
            "total": len(completed),
            "period_days": last_n_days,
            "t1_hit_rate": round(t1_hits / len(completed), 4),
            "t3_hit_rate": round(t3_hits / len(completed), 4),
            "t5_hit_rate": round(t5_hits / len(completed), 4),
            "avg_return_t1": round(sum(t1_returns) / len(t1_returns), 4) if t1_returns else 0,
            "avg_return_t3": round(sum(t3_returns) / len(t3_returns), 4) if t3_returns else 0,
            "avg_return_t5": round(sum(t5_returns) / len(t5_returns), 4) if t5_returns else 0,
            "confidence_analysis": {
                "high": {
                    "count": len(high_conf),
                    "hit_rate": round(sum(1 for p in high_conf if p.hit_t1) / len(high_conf), 4) if high_conf else 0
                },
                "medium": {
                    "count": len(mid_conf),
                    "hit_rate": round(sum(1 for p in mid_conf if p.hit_t1) / len(mid_conf), 4) if mid_conf else 0
                },
                "low": {
                    "count": len(low_conf),
                    "hit_rate": round(sum(1 for p in low_conf if p.hit_t1) / len(low_conf), 4) if low_conf else 0
                }
            }
        }

        return stats

    def analyze_factor_performance(self) -> dict:
        """分析各因子与实际收益的 IC（信息系数）"""
        from src.scoring.models import ScoreRecord
        import numpy as np
        cutoff = datetime.now() - timedelta(days=30)

        # 获取有评分的股票代码
        records = self.db.query(ScoreRecord).filter(
            ScoreRecord.score_date >= cutoff
        ).all()

        if not records:
            return {"message": "暂无评分记录"}

        # 获取已完成的预测
        predictions = self.db.query(Prediction).filter(
            Prediction.status == "completed",
            Prediction.prediction_date >= cutoff
        ).all()

        if not predictions:
            return {"message": "暂无已完成的预测"}

        # 建立 code -> 预测收益 的映射
        code_returns = {}
        for p in predictions:
            if p.actual_return_t1 is not None:
                code_returns[p.code] = p.actual_return_t1

        if not code_returns:
            return {"message": "暂无实际收益数据"}

        # 分析每个因子的 IC
        factor_columns = {
            'trend_score': 'trend',
            'reversal_score': 'short_term_reversal',
            'volume_ratio_score': 'volume_ratio',
            'turnover_score': 'turnover_rate',
            'volatility_score': 'idio_volatility',
            'rsi_score': 'rsi',
            'macd_score': 'macd',
            'kline_score': 'kline_pattern',
        }

        factor_ics = {}
        for col_name, factor_name in factor_columns.items():
            factor_scores = []
            actual_returns = []
            for r in records:
                score_val = getattr(r, col_name, None)
                if score_val is not None and r.code in code_returns:
                    factor_scores.append(score_val)
                    actual_returns.append(code_returns[r.code])

            if len(factor_scores) >= 10:
                # 计算 Spearman rank correlation (IC)
                from scipy import stats as scipy_stats
                try:
                    ic, _ = scipy_stats.spearmanr(factor_scores, actual_returns)
                    if not np.isnan(ic):
                        factor_ics[factor_name] = round(ic, 4)
                except Exception:
                    # 如果 scipy 不可用，用简单的 Pearson 近似
                    arr_x = np.array(factor_scores)
                    arr_y = np.array(actual_returns)
                    if arr_x.std() > 0 and arr_y.std() > 0:
                        ic = np.corrcoef(arr_x, arr_y)[0, 1]
                        if not np.isnan(ic):
                            factor_ics[factor_name] = round(ic, 4)

        return {
            "total_predictions": len(predictions),
            "total_scores": len(records),
            "matched": len(code_returns),
            "factor_ics": factor_ics,
        }

    def adjust_factor_weights(self) -> dict:
        """根据因子 IC 值动态调整权重"""
        from src.scoring.engine import DEFAULT_WEIGHTS, save_dynamic_weights
        import numpy as np

        analysis = self.analyze_factor_performance()
        factor_ics = analysis.get("factor_ics", {})

        if not factor_ics:
            logger.info("无因子 IC 数据，使用默认权重")
            return {"message": "无因子 IC 数据"}

        # 基于 IC 值调整权重
        # 策略：IC > 0 的因子增加权重，IC < 0 的因子降低权重
        new_weights = DEFAULT_WEIGHTS.copy()

        for factor_name, ic in factor_ics.items():
            if factor_name in new_weights:
                # 用 IC 值作为乘数：IC 越高权重越大
                # 限制调整幅度在 0.5x ~ 2.0x
                multiplier = max(0.5, min(2.0, 1.0 + ic * 5))
                new_weights[factor_name] = DEFAULT_WEIGHTS[factor_name] * multiplier

        # 保存新权重
        save_dynamic_weights(new_weights)
        logger.info(f"因子权重已调整，基于 {len(factor_ics)} 个因子的 IC 值")

        return {
            "adjusted_factors": len(factor_ics),
            "factor_ics": factor_ics,
            "new_weights": {k: round(v, 4) for k, v in new_weights.items()},
        }

    def calculate_market_state(self) -> str:
        """识别市场状态（牛市/熊市/震荡）"""
        # 获取上证指数近 60 天数据
        sh_index = self.db.execute(text("""
            SELECT close FROM daily_quote
            WHERE code = '000001'
            ORDER BY trade_date DESC
            LIMIT 60
        """)).fetchall()

        if len(sh_index) < 60:
            return "unknown"

        prices = [row[0] for row in sh_index]
        ma60 = sum(prices) / len(prices)
        current = prices[0]

        # 计算 MA60 趋势
        ma60_recent = sum(prices[:10]) / 10
        ma60_prev = sum(prices[10:20]) / 10
        ma60_slope = ma60_recent - ma60_prev

        if current > ma60 and ma60_slope > 0:
            return "bull"
        elif current < ma60 and ma60_slope < 0:
            return "bear"
        else:
            return "sideways"

    def adjust_strategy_params(self, market_state: str) -> dict:
        """根据市场状态调整策略参数"""
        params = {
            "position_limit": 0.6,
            "score_threshold": 70,
            "confidence_threshold": 0.7
        }

        if market_state == "bull":
            params["position_limit"] = 0.8
            params["score_threshold"] = 65
            params["confidence_threshold"] = 0.6
        elif market_state == "bear":
            params["position_limit"] = 0.4
            params["score_threshold"] = 80
            params["confidence_threshold"] = 0.8

        return params

    def generate_learning_report(self) -> str:
        """生成学习报告"""
        # 分析预测准确率
        accuracy = self.analyze_prediction_accuracy(last_n_days=30)

        # 分析市场状态
        market_state = self.calculate_market_state()
        market_state_cn = {
            "bull": "牛市",
            "bear": "熊市",
            "sideways": "震荡",
            "unknown": "未知"
        }.get(market_state, "未知")

        # 调整策略参数
        params = self.adjust_strategy_params(market_state)

        report = f"""# 自我学习报告

## 预测准确率（近30天）
- 总预测：{accuracy.get('total', 0)} 次
- T+1 命中率：{accuracy.get('t1_hit_rate', 0):.1%}
- T+3 命中率：{accuracy.get('t3_hit_rate', 0):.1%}
- T+5 命中率：{accuracy.get('t5_hit_rate', 0):.1%}
- T+1 平均收益：{accuracy.get('avg_return_t1', 0):.2%}

## 置信度分析
- 高置信度（>=70%）：{accuracy.get('confidence_analysis', {}).get('high', {}).get('count', 0)} 次，命中率 {accuracy.get('confidence_analysis', {}).get('high', {}).get('hit_rate', 0):.1%}
- 中置信度（50-70%）：{accuracy.get('confidence_analysis', {}).get('medium', {}).get('count', 0)} 次，命中率 {accuracy.get('confidence_analysis', {}).get('medium', {}).get('hit_rate', 0):.1%}
- 低置信度（<50%）：{accuracy.get('confidence_analysis', {}).get('low', {}).get('count', 0)} 次，命中率 {accuracy.get('confidence_analysis', {}).get('low', {}).get('hit_rate', 0):.1%}

## 市场状态
- 当前状态：{market_state_cn}

## 策略参数调整
- 仓位上限：{params['position_limit']:.0%}
- 评分门槛：{params['score_threshold']} 分
- 置信度门槛：{params['confidence_threshold']:.0%}

## 建议
"""
        if accuracy.get('t1_hit_rate', 0) > 0.6:
            report += "- 预测表现良好，保持当前策略\n"
        elif accuracy.get('t1_hit_rate', 0) > 0.4:
            report += "- 预测表现一般，建议优化因子权重\n"
        else:
            report += "- 预测表现较差，建议暂停自动预测，人工复盘\n"

        if market_state == "bear":
            report += "- 当前为熊市，建议降低仓位，提高选股标准\n"
        elif market_state == "bull":
            report += "- 当前为牛市，可适当提高仓位\n"

        return report

    def daily_learning_cycle(self):
        """每日学习循环"""
        logger.info("开始每日学习循环...")

        # 1. 分析预测准确率
        accuracy = self.analyze_prediction_accuracy()
        logger.info(f"预测准确率: T+1={accuracy.get('t1_hit_rate', 0):.1%}")

        # 2. 分析市场状态
        market_state = self.calculate_market_state()
        logger.info(f"市场状态: {market_state}")

        # 3. 调整策略参数
        params = self.adjust_strategy_params(market_state)
        logger.info(f"策略参数: {params}")

        # 4. 分析因子表现并调整权重
        factor_result = self.adjust_factor_weights()
        logger.info(f"因子权重调整: {factor_result.get('adjusted_factors', 0)} 个因子")

        # 5. 生成学习报告
        report = self.generate_learning_report()
        logger.info("学习报告已生成")

        return {
            "accuracy": accuracy,
            "market_state": market_state,
            "params": params,
            "factor_weights": factor_result,
            "report": report
        }
