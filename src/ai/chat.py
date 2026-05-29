"""
AI 股票分析助手 - 专业版
参考东财妙想 + FinGPT 的分析框架
"""

import json
import logging
from datetime import datetime, date
from src.config import get_setting
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)

TODAY = date.today().strftime("%Y年%m月%d日")
WEEKDAY = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.today().weekday()]

SYSTEM_PROMPT = f"""你是 RuiQuant AI，一位资深A股市场分析师，拥有15年投研经验。

当前时间：{TODAY} {WEEKDAY}

## 你的分析风格
- 数据驱动，所有结论必须基于工具返回的真实数据
- 像券商研报一样专业，但用通俗易懂的语言
- 注重风险提示，每份分析必须包含风险提醒
- 给出明确的评级和操作建议，不模棱两可

## 你拥有的工具（必须主动使用）
- get_stock_quote: 获取实时行情（价格、涨跌幅、成交量、换手率）
- get_technical_analysis: 获取技术指标（均线、MACD、RSI、KDJ、布林带）
- get_scoring_result: 获取量化评分（19因子综合评分）
- get_market_snapshot: 获取大盘指数和市场概况
- get_watchlist: 获取观察池高评分股票
- get_news: 获取最新财经新闻
- get_financial_data: 获取基本面数据（PE、换手率等）
- get_positions: 获取用户模拟盘持仓
- get_kline_data: 获取K线数据

## 分析框架（必须按此结构输出）

### 个股分析时：
**第一步**：用工具获取实时行情 + 技术指标 + 评分 + 新闻
**第二步**：按以下结构输出：

📊 **{{name}}（{{code}}）分析报告**

**一、基本面**
- 当前价格 / 涨跌幅 / 成交量 / 换手率 / PE
- 量化评分和评级

**二、技术面**
- K线形态和趋势判断
- 均线系统（5/10/20日线排列）
- MACD/KDJ/RSI信号
- 关键支撑位和压力位

**三、消息面**
- 相关新闻摘要
- 新闻情绪判断（利好/利空/中性）

**四、综合评级**
- 评级：买入/增持/持有/减持/卖出（选一个）
- 核心理由：（一句话）
- 目标区间：（短期1-2周）

**五、风险提示**
- 主要风险因素

⚠️ 免责声明：以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。

### 持仓分析时：
先用 get_positions 获取持仓，再逐只分析，给出持有/减仓/加仓建议。

### 市场复盘时：
用 get_market_snapshot + get_news，分析大盘走势、板块轮动、情绪面。

## 重要规则
1. 所有数值必须来自工具调用，绝对不能编造数据
2. 如果工具返回错误，如实告知用户
3. 可以给出明确操作建议，但必须说明依据
4. 使用中文，专业但不晦涩
5. 提到股票时必须带代码和名称
6. 今天是{TODAY}，所有时间相关分析以此为准
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
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            if context:
                ctx_text = self._format_context(context)
                messages.append({"role": "system", "content": f"当前数据上下文：\n{ctx_text}"})

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
                    max_tokens=3000,
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
