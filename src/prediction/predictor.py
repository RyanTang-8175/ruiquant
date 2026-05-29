"""
AI 预测系统
每天开盘前预测，收盘后回填
"""

import json
import logging
from datetime import datetime, date, timedelta
from openai import OpenAI
from sqlalchemy.orm import Session
from src.prediction.models import Prediction
from src.data.models import DailyQuote, StockBasic
from src.scoring.engine import ScoringEngine
from src.utils.database import SessionLocal
from src.config import get_setting

logger = logging.getLogger(__name__)


class PredictionEngine:
    """AI 预测引擎"""

    def __init__(self):
        self.db = SessionLocal()
        api_key = get_setting("api_key", "DEEPSEEK_API_KEY", "")
        base_url = get_setting("base_url", "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = get_setting("model", "DEEPSEEK_MODEL", "deepseek-chat")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

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

    def generate_prediction(self, code: str, name: str, score_info: dict) -> dict:
        """为单只股票生成预测"""
        # 获取最近行情
        quote = self.db.query(DailyQuote).filter(
            DailyQuote.code == code
        ).order_by(DailyQuote.trade_date.desc()).first()

        if not quote:
            return None

        prompt = f"""你是一个 A 股短线分析师。基于以下数据，预测 {name}（{code}）的走势。

## 昨日行情
- 收盘价：{quote.close} 元
- 涨跌幅：{quote.change_pct}%
- 成交量：{quote.volume}
- 换手率：{quote.turnover_rate}%

## 评分结果
- 总分：{score_info.get('total_score', 0)}/100
- 评级：{score_info.get('rating', '')}

## 因子详情
{json.dumps(score_info.get('factors', {}), ensure_ascii=False, indent=2)}

请预测：
1. 今日（T+1）走势
2. 未来3天（T+3）走势
3. 未来5天（T+5）走势

返回 JSON 格式：
{{
  "t1_direction": "up/down/neutral",
  "t1_magnitude": "2-3%",
  "t1_confidence": 0.75,
  "t3_direction": "up/down/neutral",
  "t3_magnitude": "5-8%",
  "t3_confidence": 0.65,
  "t5_direction": "up/down/neutral",
  "t5_magnitude": "8-12%",
  "t5_confidence": 0.55,
  "main_reason": "主要理由",
  "risk_factors": ["风险因素"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是 A 股短线分析师，只返回 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logger.error(f"AI 预测失败 {code}: {e}")
            return None

    def daily_prediction(self, limit: int = 20):
        """每日预测（开盘前运行）"""
        logger.info("开始每日预测...")

        # 获取观察池
        with ScoringEngine() as scoring:
            watchlist = scoring.get_watchlist(min_score=65, limit=limit)

        predictions = []
        for stock in watchlist:
            code = stock['code']
            name = stock.get('name', '')

            # 生成预测
            result = self.generate_prediction(code, name, stock)
            if not result:
                continue

            # 获取当前价格
            quote = self.db.query(DailyQuote).filter(
                DailyQuote.code == code
            ).order_by(DailyQuote.trade_date.desc()).first()

            # 保存预测
            prediction = Prediction(
                code=code,
                name=name,
                prediction_date=datetime.now(),
                prediction_type="auto",
                price_at_prediction=quote.close if quote else None,
                t1_direction=result.get('t1_direction'),
                t1_magnitude=result.get('t1_magnitude'),
                t1_confidence=result.get('t1_confidence'),
                t3_direction=result.get('t3_direction'),
                t3_magnitude=result.get('t3_magnitude'),
                t3_confidence=result.get('t3_confidence'),
                t5_direction=result.get('t5_direction'),
                t5_magnitude=result.get('t5_magnitude'),
                t5_confidence=result.get('t5_confidence'),
                quant_score=stock.get('total_score'),
                main_reason=result.get('main_reason'),
                risk_factors=result.get('risk_factors', []),
                status="pending"
            )
            self.db.add(prediction)
            predictions.append(prediction)

        self.db.commit()
        logger.info(f"预测完成: {len(predictions)} 只股票")
        return predictions

    def backfill_predictions(self):
        """回填预测结果"""
        logger.info("开始回填预测...")

        pending = self.db.query(Prediction).filter(
            Prediction.status == "pending"
        ).all()

        filled = 0
        for pred in pending:
            days_elapsed = (date.today() - pred.prediction_date.date()).days

            # 获取当前价格
            quote = self.db.query(DailyQuote).filter(
                DailyQuote.code == pred.code
            ).order_by(DailyQuote.trade_date.desc()).first()

            if not quote:
                continue

            current_price = quote.close
            base_price = pred.price_at_prediction

            if not base_price or base_price == 0:
                continue

            # T+1 回填
            if days_elapsed >= 1 and pred.actual_return_t1 is None:
                pred.actual_price_t1 = current_price
                pred.actual_return_t1 = (current_price - base_price) / base_price
                pred.hit_t1 = self._check_hit(pred.t1_direction, pred.actual_return_t1)

            # T+3 回填
            if days_elapsed >= 3 and pred.actual_return_t3 is None:
                pred.actual_price_t3 = current_price
                pred.actual_return_t3 = (current_price - base_price) / base_price
                pred.hit_t3 = self._check_hit(pred.t3_direction, pred.actual_return_t3)

            # T+5 回填
            if days_elapsed >= 5 and pred.actual_return_t5 is None:
                pred.actual_price_t5 = current_price
                pred.actual_return_t5 = (current_price - base_price) / base_price
                pred.hit_t5 = self._check_hit(pred.t5_direction, pred.actual_return_t5)
                pred.status = "completed"

            # 超过7天标记过期
            if days_elapsed > 7 and pred.status == "pending":
                pred.status = "expired"

            filled += 1

        self.db.commit()
        logger.info(f"回填完成: {filled} 条")
        return filled

    def _check_hit(self, direction: str, actual_return: float) -> bool:
        """检查预测是否命中"""
        if direction == "up":
            return actual_return > 0.02
        elif direction == "down":
            return actual_return < -0.02
        else:  # neutral
            return abs(actual_return) < 0.02

    def get_stats(self) -> dict:
        """获取预测统计"""
        completed = self.db.query(Prediction).filter(
            Prediction.status == "completed"
        ).all()

        if not completed:
            return {"total": 0, "message": "暂无已完成的预测"}

        t1_hits = sum(1 for p in completed if p.hit_t1)
        t3_hits = sum(1 for p in completed if p.hit_t3)
        t5_hits = sum(1 for p in completed if p.hit_t5)

        return {
            "total": len(completed),
            "t1_hit_rate": round(t1_hits / len(completed), 4) if completed else 0,
            "t3_hit_rate": round(t3_hits / len(completed), 4) if completed else 0,
            "t5_hit_rate": round(t5_hits / len(completed), 4) if completed else 0,
            "avg_return_t1": round(sum(p.actual_return_t1 for p in completed if p.actual_return_t1) / len(completed), 4),
            "avg_return_t3": round(sum(p.actual_return_t3 for p in completed if p.actual_return_t3) / len(completed), 4),
            "avg_return_t5": round(sum(p.actual_return_t5 for p in completed if p.actual_return_t5) / len(completed), 4),
        }
