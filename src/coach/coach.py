"""
AI 教练模块
评价交易、分析习惯、个性化建议
"""

import json
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from sqlalchemy.orm import Session
from src.trading.models import PaperAccount, Trade
from src.trading.engine import TradingEngine
from src.utils.database import SessionLocal
from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)


class AICoach:
    """AI 教练"""

    def __init__(self):
        self.db = SessionLocal()
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        self.model = DEEPSEEK_MODEL

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

    def evaluate_trade(self, trade: Trade) -> str:
        """评价单笔交易"""
        prompt = f"""你是一个股票交易教练。请评价以下交易。

## 交易信息
- 股票：{trade.name or trade.code}
- 方向：{'买入' if trade.direction == 'buy' else '卖出'}
- 价格：{trade.price} 元
- 数量：{trade.quantity} 股
- 金额：{trade.amount} 元
- 盈亏：{trade.pnl or 0} 元
- 时间：{trade.created_at.strftime('%Y-%m-%d %H:%M')}

请用 3-5 句话评价这笔交易：
1. 做得好的地方
2. 可以改进的地方
3. 总结

语言简洁直接，像一个严厉但关心你的教练。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是股票交易教练，评价简洁直接。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI 教练评价失败: {e}")
            return "AI 教练暂时无法评价。"

    def analyze_weekly_habits(self) -> str:
        """分析每周交易习惯"""
        # 获取本周交易
        week_ago = datetime.now() - timedelta(days=7)
        account = self.db.query(PaperAccount).first()
        trades = self.db.query(Trade).filter(
            Trade.account_id == account.id,
            Trade.created_at >= week_ago
        ).all()

        if not trades:
            return "本周暂无交易记录。"

        # 统计数据
        buy_trades = [t for t in trades if t.direction == "buy"]
        sell_trades = [t for t in trades if t.direction == "sell"]
        winning = [t for t in sell_trades if t.pnl and t.pnl > 0]
        losing = [t for t in sell_trades if t.pnl and t.pnl < 0]
        total_pnl = sum(t.pnl for t in sell_trades if t.pnl)
        win_rate = len(winning) / len(sell_trades) if sell_trades else 0

        prompt = f"""你是一个股票交易教练。请分析以下本周交易习惯。

## 本周统计
- 总交易：{len(trades)} 笔
- 买入：{len(buy_trades)} 笔
- 卖出：{len(sell_trades)} 笔
- 胜率：{win_rate:.1%}
- 总盈亏：{total_pnl:.2f} 元

## 交易记录
{chr(10).join([f"- {t.direction} {t.name or t.code} {t.quantity}股 × {t.price:.2f} = {t.pnl or 0:+.2f}元" for t in trades])}

请分析：
1. 交易风格是什么？（短线/波段）
2. 最大的问题是什么？
3. 哪些交易做得好？为什么？
4. 哪些交易做得差？为什么？
5. 给出 3 条具体改进建议
6. 本周评分（0-100）

语言简洁直接。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是股票交易教练，分析简洁直接。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI 教练分析失败: {e}")
            return "AI 教练暂时无法分析。"

    def compare_with_prediction(self, trade: Trade, prediction: dict = None) -> str:
        """与 AI 预测对比"""
        if not prediction:
            return "暂无相关预测记录。"

        prompt = f"""你是一个股票交易教练。请对比用户的交易决策和 AI 预测。

## 用户交易
- 股票：{trade.name or trade.code}
- 方向：{'买入' if trade.direction == 'buy' else '卖出'}
- 价格：{trade.price} 元
- 盈亏：{trade.pnl or 0} 元

## AI 预测
- T+1 方向：{prediction.get('t1_direction', 'N/A')}
- T+1 置信度：{prediction.get('t1_confidence', 'N/A')}
- 主要理由：{prediction.get('main_reason', 'N/A')}

请分析：
1. 用户的决策是否与 AI 预测一致？
2. 结果如何？
3. 给出建议。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是股票交易教练，分析简洁直接。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI 教练对比失败: {e}")
            return "AI 教练暂时无法对比分析。"

    def get_personalized_advice(self) -> str:
        """获取个性化建议"""
        # 获取所有交易记录
        account = self.db.query(PaperAccount).first()
        trades = self.db.query(Trade).filter(
            Trade.account_id == account.id
        ).all()

        if not trades:
            return "暂无交易记录，无法给出建议。"

        # 统计数据
        sell_trades = [t for t in trades if t.direction == "sell"]
        winning = [t for t in sell_trades if t.pnl and t.pnl > 0]
        losing = [t for t in sell_trades if t.pnl and t.pnl < 0]
        total_pnl = sum(t.pnl for t in sell_trades if t.pnl)
        win_rate = len(winning) / len(sell_trades) if sell_trades else 0

        prompt = f"""你是一个股票交易教练。基于以下交易记录，给出个性化建议。

## 总体统计
- 总交易：{len(trades)} 笔
- 胜率：{win_rate:.1%}
- 总盈亏：{total_pnl:.2f} 元
- 平均盈利：{sum(t.pnl for t in winning) / len(winning) if winning else 0:.2f} 元
- 平均亏损：{sum(t.pnl for t in losing) / len(losing) if losing else 0:.2f} 元

请给出：
1. 这个交易者的优势是什么？
2. 最大的弱点是什么？
3. 针对性训练建议（3条）
4. 总体评分（0-100）

语言简洁直接。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是股票交易教练，建议简洁直接。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI 教练建议失败: {e}")
            return "AI 教练暂时无法给出建议。"
