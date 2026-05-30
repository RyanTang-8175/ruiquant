"""AlphaEye AI — 专业A股分析助手"""

import json, logging, time
from datetime import datetime, date
from src.config import get_setting
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)
TODAY = date.today().strftime("%Y年%m月%d日")
WDAY = ["周一","周二","周三","周四","周五","周六","周日"][date.today().weekday()]

SYSTEM_PROMPT = f"""你是 AlphaEye AI，一位资深A股短线分析师。

当前时间：{TODAY} {WDAY}

## 你的工具
- get_stock_quote(code) → 实时行情
- get_scoring_result(code) → 量化评分0-100
- get_technical_analysis(code) → 均线/MACD趋势
- get_market_snapshot() → 大盘+涨跌榜
- get_watchlist(limit) → 高评分股
- get_news(code/不填) → 财经新闻
- get_financial_data(code) → PE/换手
- get_positions() → 模拟持仓
- get_kline_data(code) → K线数据

## 规则
1. 数据必须来自工具调用，禁止编造
2. 一般调用2-3个工具即可，不要过度调用
3. 工具失败时尝试替代工具或如实告知
4. 中文输出，专业简洁
5. 先给数据→再分析→最后建议
6. 操作建议明确：买入/增持/持有/减持/卖出 + 止损位
7. 每份分析末尾加风险提示
"""

class AIChat:
    def __init__(self):
        api_key = get_setting("api_key","DEEPSEEK_API_KEY","")
        base_url = get_setting("base_url","DEEPSEEK_BASE_URL","https://api.deepseek.com")
        self.model = get_setting("model","DEEPSEEK_MODEL","deepseek-chat")
        self.client = None
        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)
            except: pass
        self.history = []
        self.tool_executor = ToolExecutor()
        self._tools_used = []

    def chat(self, user_message: str, context: dict = None) -> str:
        if not self.client: return "AI未配置。请在「我的」页面设置API Key后使用。"
        try:
            messages = [{"role":"system","content":SYSTEM_PROMPT}]
            for h in self.history[-8:]:
                messages.append({"role":"user","content":h["question"]})
                messages.append({"role":"assistant","content":h["answer"]})
            messages.append({"role":"user","content":user_message})

            self._tools_used = []; answer = ""

            for rnd in range(5):
                try:
                    resp = self.client.chat.completions.create(
                        model=self.model, messages=messages,
                        tools=TOOLS, tool_choice="auto",
                        temperature=0.7, max_tokens=2000, timeout=25)
                except Exception as api_err:
                    logger.error(f"API round {rnd}: {api_err}")
                    if answer: return answer
                    return f"AI错误: {str(api_err)[:150]}"

                choice = resp.choices[0]
                if not choice.message.tool_calls:
                    answer = choice.message.content or ""; break

                messages.append(choice.message)
                for tc in choice.message.tool_calls:
                    try: args = json.loads(tc.function.arguments)
                    except: args = {}
                    nm = tc.function.name
                    self._tools_used.append(nm)
                    try:
                        result = self.tool_executor.execute(nm, args)
                    except Exception as te:
                        result = json.dumps({"error":str(te)[:80]}, ensure_ascii=False)
                    messages.append({"role":"tool","tool_call_id":tc.id,"content":result})
            else:
                answer = answer or "分析超时，请简化问题。例如「分析贵州茅台」或「今天大盘怎么样」。"

            if not answer: answer = "未能完成分析，请重试。"
            self.history.append({"question":user_message,"answer":answer,"timestamp":datetime.now().isoformat(),"tools_used":self._tools_used.copy()})
            return answer
        except Exception as e:
            logger.error(f"AI: {e}")
            return f"AI异常: {str(e)[:200]}"

    def get_last_tools_used(self): return self._tools_used
    def clear_history(self): self.history = []; self._tools_used = []
    def get_history(self): return self.history
