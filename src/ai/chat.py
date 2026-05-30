"""AlphaEye AI"""

import json, logging
from datetime import datetime, date
from src.config import get_setting
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)
TODAY = date.today().strftime("%Y-%m-%d")

SYSTEM_PROMPT = f"""你是AlphaEye AI，A股分析助手。今天是{TODAY}。

工具：get_stock_quote(行情) get_scoring_result(评分) get_market_snapshot(大盘) get_watchlist(选股) get_news(新闻) get_positions(持仓)

规则：数据用工具获取不编造，最多3个工具，中文简洁，给操作建议+理由"""

class AIChat:
    def __init__(self):
        api_key = get_setting("api_key","DEEPSEEK_API_KEY","")
        base_url = get_setting("base_url","DEEPSEEK_BASE_URL","https://api.deepseek.com")
        self.model = get_setting("model","DEEPSEEK_MODEL","deepseek-chat")
        self.client = None
        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key,base_url=base_url)
            except: pass
        self.history = []
        self.tool_executor = ToolExecutor()
        self._tools_used = []

    def chat(self, user_message: str, context: dict = None) -> str:
        if not self.client: return "AI未配置。在「我的」页面设置API Key。"
        try:
            messages = [{"role":"system","content":SYSTEM_PROMPT}]
            for h in self.history[-6:]:
                messages.append({"role":"user","content":h["question"]})
                messages.append({"role":"assistant","content":h["answer"]})
            messages.append({"role":"user","content":user_message})

            self._tools_used = []; answer = ""
            for _ in range(3):
                resp = self.client.chat.completions.create(
                    model=self.model,messages=messages,
                    tools=TOOLS,tool_choice="auto",temperature=0.7,max_tokens=1500)
                choice = resp.choices[0]
                if not choice.message.tool_calls:
                    answer = choice.message.content or ""; break
                messages.append(choice.message)
                for tc in choice.message.tool_calls:
                    try: args = json.loads(tc.function.arguments)
                    except: args = {}
                    self._tools_used.append(tc.function.name)
                    result = self.tool_executor.execute(tc.function.name, args)
                    messages.append({"role":"tool","tool_call_id":tc.id,"content":result})
            else: answer = "分析超时，请简化问题重试。"

            self.history.append({"question":user_message,"answer":answer,"timestamp":datetime.now().isoformat(),"tools_used":self._tools_used.copy()})
            return answer
        except Exception as e:
            logger.error(f"AI: {e}")
            return f"AI错误: {e}"

    def get_last_tools_used(self): return self._tools_used
    def clear_history(self): self.history = []; self._tools_used = []
    def get_history(self): return self.history
