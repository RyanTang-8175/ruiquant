"""
AI 股票分析助手
支持工具调用 + 持仓分析 + 专业技能
"""

import json
import logging
from datetime import datetime
from src.config import get_setting
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是 RuiQuant AI，一个专业的 A 股分析助手。

你拥有以下工具，应该主动使用它们获取数据：
- get_stock_quote: 实时行情
- get_technical_analysis: 技术指标
- get_scoring_result: 量化评分
- get_market_snapshot: 市场概况
- get_watchlist: 观察池
- get_news: 财经新闻
- get_financial_data: 基本面
- get_positions: 模拟盘持仓
- get_kline_data: K线数据

分析流程：
1. 先用工具获取实时数据（不要编造数据）
2. 结合技术面、消息面、量化评分综合分析
3. 给出明确的操作建议和风险提示

你可以帮助用户：
- 分析个股：技术面+消息面+量化评分+操作建议
- 分析持仓：查看用户持仓，给出持有/减仓/加仓建议
- 选股推荐：基于当前市场状态推荐值得关注的股票
- 市场复盘：分析大盘走势、板块轮动、情绪指标
- 风险评估：评估个股或持仓的风险

规则：
1. 所有数值必须来自工具调用
2. 可以给出明确建议（持有/减仓/加仓/关注/回避），但必须说明依据
3. 分析结构化：技术面 → 消息面 → 量化评分 → 综合判断 → 操作建议
4. 使用中文，专业简洁
5. 提到股票时带代码和名称
"""


class AIChat:
    """AI 股票分析助手"""

    def __init__(self):
        api_key = get_setting("api_key", "DEEPSEEK_API_KEY", "")
        base_url = get_setting("base_url", "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = get_setting("model", "DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            self.client = None
        else:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key, base_url=base_url)
            except Exception:
                self.client = None

        self.history = []
        self.tool_executor = ToolExecutor()
        self._tools_used = []

    def chat(self, user_message: str, context: dict = None) -> str:
        """与 AI 对话"""
        if not self.client:
            return "⚠️ AI 未配置。请在「我的」页面配置 API Key 后使用。"

        try:
            from openai import OpenAI
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            if context:
                ctx_text = self._format_context(context)
                messages.append({"role": "system", "content": f"当前数据上下文：\n{ctx_text}"})

            # 保留最近 10 轮历史
            for h in self.history[-10:]:
                messages.append({"role": "user", "content": h["question"]})
                messages.append({"role": "assistant", "content": h["answer"]})

            messages.append({"role": "user", "content": user_message})

            self._tools_used = []
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

                if not choice.message.tool_calls:
                    answer = choice.message.content or ""
                    break

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
            return f"AI 响应失败: {e}"

    def get_last_tools_used(self) -> list:
        return self._tools_used

    def _format_context(self, context: dict) -> str:
        parts = []
        if "market_snapshot" in context:
            snap = context["market_snapshot"]
            parts.append(f"市场：上涨{snap.get('up_count', 0)}家 下跌{snap.get('down_count', 0)}家")
        if "stock_info" in context:
            info = context["stock_info"]
            parts.append(f"股票：{info.get('name', '')}({info.get('code', '')}) 价格{info.get('price', 0)}")
        if "score" in context:
            s = context["score"]
            parts.append(f"评分：{s.get('total_score', 0)}分 {s.get('rating', '')}")
        return "\n".join(parts)

    def clear_history(self):
        self.history = []
        self._tools_used = []

    def get_history(self) -> list:
        return self.history
