"""AlphaEye AI — 专业A股分析引擎"""

import json, logging, traceback
from datetime import datetime, date
from src.config import get_setting
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)
TODAY = date.today().strftime("%Y年%m月%d日")
WDAY = ["周一","周二","周三","周四","周五","周六","周日"][date.today().weekday()]

SYSTEM_PROMPT = f"""你是 AlphaEye AI，一位资深A股短线分析师。当前时间：{TODAY} {WDAY}。

## 你的核心能力

你可以主动调用以下工具获取真实数据：
- get_stock_quote(code) → 实时行情：价格/涨跌幅/成交量/换手率/开盘/最高/最低
- get_scoring_result(code) → 量化评分(0-100)+评级(强关注/观察/中性/不追)+因子详情
- get_technical_analysis(code) → 技术指标：均线排列(多头/空头/交叉)+MA5/10/20+RSI
- get_market_snapshot() → 大盘概况：三大指数+涨跌幅+涨跌榜Top5
- get_watchlist(limit) → 高评分股票观察池
- get_news(code/不填) → 最新财经新闻+个股相关新闻
- get_financial_data(code) → 基本面：PE/换手率/成交量
- get_positions() → 模拟盘持仓+盈亏统计
- get_kline_data(code) → 最近K线数据(日线)

## 分析框架

当用户询问任何股票相关问题时，你必须按此框架输出完整分析：

### 一、数据概览
（用工具获取：实时行情+评分+技术指标+新闻，然后展示关键数据）

### 二、利多因素
（基于实际数据列出2-3个最重要的利多，每条标出来源）

### 三、风险因素
（基于实际数据列出2-3个最关键的风险，包括反量化信号）

### 四、多维度研判
- 技术面：（均线排列/MACD信号/RSI状态/支撑压力位）
- 消息面：（相关新闻影响+情绪判断）
- 量化评分：（总分+评级+最强和最弱因子）

### 五、操作建议
- 建议：买入/增持/持有/减持/卖出（必须选一个）
- 参考止损位：（具体价格）
- 核心理由：（一句话总结）

### 六、风险提示
⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。

## 多分析师视角（可选，当用户要求深度分析时启用）

你可以从以下四个视角给出独立判断，最后综合投票：

1. **价值投资者（巴菲特视角）**：关注PE/PB估值水平、安全边际、长期竞争力
2. **成长投资者（林奇视角）**：关注营收增速、行业空间、PEG合理性
3. **趋势交易者（索罗斯视角）**：关注趋势强度、市场情绪、转折信号
4. **量化分析师（西蒙斯视角）**：关注统计异常、量化痕迹、程序化交易信号

综合投票决定最终操作建议。

## 绝对规则

1. 所有数字必须来自工具调用，禁止编造任何价格/涨跌幅/PE/评分
2. 工具调用要精准高效，一般2-4个工具即可完成一次完整分析
3. 如果某个工具返回错误，尝试备用方案，仍失败则如实告知用户
4. 操作建议必须基于至少2个独立数据源
5. 先展示数据依据，再给出分析结论
6. 中文输出，专业但不晦涩
7. 不确定的事情明确说"数据暂不可用"而不是猜测
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
            except Exception as e:
                logger.error(f"AI init: {e}")
        self.history = []
        self.tool_executor = ToolExecutor()
        self._tools_used = []

    def chat(self, user_message: str, context: dict = None) -> str:
        if not self.client:
            return "AI 未配置。请在「我的」页面填写 API Key、API 地址和模型名称后使用。\n\n支持 DeepSeek / OpenAI / 智谱 / 月之暗面等 OpenAI 兼容接口。"

        try:
            messages = [{"role":"system","content":SYSTEM_PROMPT}]
            for h in self.history[-20:]:  # 保留最近20轮
                messages.append({"role":"user","content":h["question"]})
                messages.append({"role":"assistant","content":h["answer"]})
            messages.append({"role":"user","content":user_message})

            self._tools_used = []
            answer = ""

            for rnd in range(8):  # 最多8轮工具调用
                try:
                    resp = self.client.chat.completions.create(
                        model=self.model, messages=messages,
                        tools=TOOLS, tool_choice="auto",
                        temperature=0.7, max_tokens=3000, timeout=30)
                except Exception as api_err:
                    logger.error(f"API r{rnd}: {api_err}")
                    err_msg = str(api_err)[:200]
                    # Fallback: if we already have partial answer, return it
                    if answer:
                        return answer + f"\n\n*(部分工具调用失败: {err_msg})*"
                    # Fallback: try without tools
                    try:
                        fallback = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages + [{"role":"user","content":"请基于已有信息直接回答，不需要调用工具。"}],
                            temperature=0.7, max_tokens=1000, timeout=15)
                        fb = fallback.choices[0].message.content or ""
                        if fb:
                            self.history.append({"question":user_message,"answer":fb,"timestamp":datetime.now().isoformat(),"tools_used":[]})
                            return fb + "\n\n*(部分工具不可用，基于存量知识回答)*"
                    except:
                        pass
                    return f"AI 服务暂时不可用，请稍后重试。\n\n*(错误详情: {err_msg})*"

                choice = resp.choices[0]

                if not choice.message.tool_calls:
                    answer = choice.message.content or ""
                    break

                messages.append(choice.message)
                for tc in choice.message.tool_calls:
                    nm = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    self._tools_used.append(nm)
                    try:
                        result = self.tool_executor.execute(nm, args)
                    except Exception:
                        result = json.dumps({"error": f"工具 {nm} 执行失败"}, ensure_ascii=False)

                    messages.append({"role":"tool","tool_call_id":tc.id,"content":result})
            else:
                if not answer:
                    answer = "分析需要更多信息，请尝试更具体的问题。例如：「分析贵州茅台」或「今天大盘怎么样」"

            if not answer:
                answer = "抱歉，未能完成分析。请重新提问或稍后重试。"

            self.history.append({
                "question": user_message,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "tools_used": self._tools_used.copy(),
            })
            return answer

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"AI fatal: {tb}")
            return f"系统异常，请稍后重试。\n\n*(调试: {str(e)[:100]})*"

    def get_last_tools_used(self): return self._tools_used
    def clear_history(self): self.history = []; self._tools_used = []
    def get_history(self): return self.history
