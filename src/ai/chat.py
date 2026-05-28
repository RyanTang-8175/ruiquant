"""
AI 对话模块
使用 DeepSeek 实现股票分析对话
"""

import json
import logging
from datetime import datetime
from openai import OpenAI
from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

# 系统 Prompt
SYSTEM_PROMPT = """你是 RuiQuant AI 股票助手，一个专业的 A 股短线分析师。

你的职责：
1. 基于程序计算好的数值数据，撰写分析解释文字
2. 回答用户关于股票、市场、板块的问题
3. 帮助用户理解技术指标和评分结果

规则：
1. 不要自行计算任何数值指标，只使用提供的数据
2. 不要给出明确的"买入"或"卖出"建议，只做客观分析
3. 使用中文，语言简洁专业
4. 如果用户要求执行模拟交易操作，提醒用户确认

你可以帮助用户：
- 分析个股的技术面和基本面
- 解读市场走势和板块轮动
- 理解评分引擎的结果
- 查看观察池和模拟盘状态
"""


class AIChat:
    """AI 对话管理器"""

    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        self.model = DEEPSEEK_MODEL
        self.history = []  # 对话历史

    def chat(self, user_message: str, context: dict = None) -> str:
        """与 AI 对话"""
        try:
            # 构建消息
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            # 添加上下文（如果有）
            if context:
                context_text = self._format_context(context)
                messages.append({"role": "system", "content": f"当前数据上下文：\n{context_text}"})

            # 添加历史对话
            for h in self.history[-10:]:  # 保留最近 10 轮
                messages.append({"role": "user", "content": h["question"]})
                messages.append({"role": "assistant", "content": h["answer"]})

            # 添加当前问题
            messages.append({"role": "user", "content": user_message})

            # 调用 DeepSeek
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            answer = response.choices[0].message.content

            # 保存到历史
            self.history.append({
                "question": user_message,
                "answer": answer,
                "timestamp": datetime.now().isoformat()
            })

            return answer

        except Exception as e:
            logger.error(f"AI 对话失败: {e}")
            return f"抱歉，AI 暂时无法响应。错误：{str(e)}"

    def _format_context(self, context: dict) -> str:
        """格式化上下文数据"""
        parts = []
        if "market_snapshot" in context:
            snap = context["market_snapshot"]
            parts.append(f"市场快照：上涨{snap.get('up_count', 0)}家，下跌{snap.get('down_count', 0)}家，涨停{snap.get('limit_up_count', 0)}家，跌停{snap.get('limit_down_count', 0)}家")
        if "stock_info" in context:
            info = context["stock_info"]
            parts.append(f"股票信息：{info.get('name', '')}（{info.get('code', '')}），当前价{info.get('price', 0)}，涨跌幅{info.get('change_pct', 0)}%")
        if "score" in context:
            score = context["score"]
            parts.append(f"评分：{score.get('total_score', 0)}分，评级{score.get('rating', '')}")
        return "\n".join(parts)

    def analyze_stock(self, stock_info: dict, score_info: dict) -> str:
        """分析个股"""
        prompt = f"""请分析以下股票：

股票：{stock_info.get('name', '')}（{stock_info.get('code', '')}）
当前价：{stock_info.get('price', 0)} 元
涨跌幅：{stock_info.get('change_pct', 0)}%
成交量：{stock_info.get('volume', 0)}
换手率：{stock_info.get('turnover_rate', 0)}%

评分结果：
总分：{score_info.get('total_score', 0)}/100
评级：{score_info.get('rating', '')}

因子详情：
{json.dumps(score_info.get('factors', {}), ensure_ascii=False, indent=2)}

请用 3-5 句话分析该股票的当前状态，重点说明：
1. 技术面的主要特征
2. 需要关注的风险点
3. 适合什么样的操作风格"""

        return self.chat(prompt)

    def generate_daily_review(self, market_data: dict) -> str:
        """生成每日复盘"""
        prompt = f"""基于以下市场数据，撰写今日 A 股复盘报告。

市场数据：
- 上涨家数：{market_data.get('up_count', 0)}
- 下跌家数：{market_data.get('down_count', 0)}
- 涨停家数：{market_data.get('limit_up_count', 0)}
- 跌停家数：{market_data.get('limit_down_count', 0)}
- 成交额：{market_data.get('total_amount_yi', 0)} 亿

请按以下结构撰写复盘（每个部分 2-3 句话）：
1. 市场整体判断
2. 情绪指标解读
3. 明日观察点"""

        return self.chat(prompt)

    def clear_history(self):
        """清空对话历史"""
        self.history = []

    def get_history(self) -> list:
        """获取对话历史"""
        return self.history
