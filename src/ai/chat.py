"""
AI 对话模块
支持工具调用的专业 A 股分析助手
"""

import json
import logging
from datetime import datetime
from openai import OpenAI
from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是 RuiQuant AI，一个专业的 A 股短线分析助手。

你拥有以下工具能力，应该主动使用它们来获取数据和进行分析：
- get_stock_quote: 获取个股最新行情
- get_technical_analysis: 获取技术指标（均线、MACD、RSI、KDJ、布林带）
- get_scoring_result: 获取量化评分（35因子评分系统）
- get_market_snapshot: 获取市场整体概况
- get_watchlist: 获取观察池高评分股票
- get_news: 获取最新财经新闻
- get_financial_data: 获取基本面数据
- get_positions: 获取模拟盘持仓
- get_kline_data: 获取K线数据

分析流程：
1. 当用户问某只股票时，先用 get_stock_quote 获取最新行情
2. 用 get_technical_analysis 获取技术指标
3. 用 get_scoring_result 获取量化评分
4. 用 get_news 获取相关新闻
5. 综合以上数据给出分析结论

规则：
1. 所有数值数据必须来自工具调用，不要编造数据
2. 可以给出明确的操作建议（如"建议关注"、"谨慎追高"），但必须说明依据
3. 分析要结构化：技术面 + 消息面 + 综合判断
4. 使用中文，语言专业简洁
5. 提到具体股票时，带上代码和名称
"""


class AIChat:
    """AI 对话管理器（支持工具调用）"""

    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        self.model = DEEPSEEK_MODEL
        self.history = []
        self.tool_executor = ToolExecutor()
        self._tools_used = []  # 记录最近一次对话使用的工具

    def chat(self, user_message: str, context: dict = None) -> str:
        """与 AI 对话（支持多轮工具调用）"""
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            if context:
                context_text = self._format_context(context)
                messages.append({"role": "system", "content": f"当前数据上下文：\n{context_text}"})

            for h in self.history[-10:]:
                messages.append({"role": "user", "content": h["question"]})
                messages.append({"role": "assistant", "content": h["answer"]})

            messages.append({"role": "user", "content": user_message})

            self._tools_used = []

            # 工具调用循环（最多 5 轮）
            answer = ""
            for _ in range(5):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=2000,
                )

                choice = response.choices[0]

                # 没有工具调用，结束
                if not choice.message.tool_calls:
                    answer = choice.message.content or ""
                    break

                # 处理工具调用
                messages.append(choice.message)
                for tool_call in choice.message.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    self._tools_used.append(func_name)
                    logger.info(f"AI 调用工具: {func_name}({args})")

                    result = self.tool_executor.execute(func_name, args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            else:
                answer = "分析过程中调用了过多工具，请尝试更具体的问题。"

            self.history.append({
                "question": user_message,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "tools_used": self._tools_used.copy(),
            })

            return answer

        except Exception as e:
            logger.error(f"AI 对话失败: {e}")
            return f"抱歉，AI 暂时无法响应。错误：{str(e)}"

    def get_last_tools_used(self) -> list:
        """获取最近一次对话使用的工具列表"""
        return self._tools_used

    def _format_context(self, context: dict) -> str:
        """格式化上下文数据"""
        parts = []
        if "market_snapshot" in context:
            snap = context["market_snapshot"]
            parts.append(f"市场快照：上涨{snap.get('up_count', 0)}家，下跌{snap.get('down_count', 0)}家")
        if "stock_info" in context:
            info = context["stock_info"]
            parts.append(f"股票：{info.get('name', '')}（{info.get('code', '')}），价格{info.get('price', 0)}")
        if "score" in context:
            score = context["score"]
            parts.append(f"评分：{score.get('total_score', 0)}分，{score.get('rating', '')}")
        return "\n".join(parts)

    def analyze_stock(self, stock_info: dict, score_info: dict) -> str:
        """分析个股（兼容旧接口）"""
        prompt = f"请对 {stock_info.get('name', '')}（{stock_info.get('code', '')}）做全面的技术面和消息面分析"
        return self.chat(prompt)

    def generate_daily_review(self, market_data: dict) -> str:
        """生成每日复盘（兼容旧接口）"""
        return self.chat("帮我做一个今日市场复盘，分析大盘走势和情绪")

    def clear_history(self):
        """清空对话历史"""
        self.history = []
        self._tools_used = []

    def get_history(self) -> list:
        """获取对话历史"""
        return self.history
