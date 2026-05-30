"""AlphaEye AI — 全量历史 + 自动压缩"""

import json, logging, os
from datetime import datetime, date
from pathlib import Path
from src.config import get_setting
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)
TODAY = date.today().strftime("%Y年%m月%d日")
WDAY = ["周一","周二","周三","周四","周五","周六","周日"][date.today().weekday()]
ARCHIVE_DIR = Path(__file__).parent.parent.parent / "data" / "conversations"

SYSTEM_PROMPT = f"""你是 AlphaEye AI，一位资深A股短线分析师。当前时间：{TODAY} {WDAY}

## 工具
- get_stock_quote(code) → 实时行情
- get_scoring_result(code) → 量化评分0-100
- get_technical_analysis(code) → 均线/MACD趋势
- get_market_snapshot() → 大盘+涨跌榜
- get_watchlist(limit) → 高评分股
- get_news(code/不填) → 财经新闻
- get_financial_data(code) → PE/换手
- get_positions() → 模拟持仓
- get_kline_data(code) → K线

## 规则
1. 数据工具获取，不编造 2. 2-3个工具即可 3. 工具失败诚实告知
4. 中文简洁 5. 数据→分析→建议 6. 明确操作+止损位 7. 末尾加风险提示"""


class AIChat:
    MAX_TOKENS_ESTIMATE = 8000   # 估计 token 上限，超过触发压缩

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
        self.history = []          # 全量历史
        self._compressed_count = 0 # 已压缩轮数
        self.tool_executor = ToolExecutor()
        self._tools_used = []

    @staticmethod
    def _estimate_tokens(messages: list) -> int:
        """粗略估计 token 数：中文约 1.5 字符/token，英文约 4 字符/token"""
        total = 0
        for m in messages:
            content = m.get("content","") or ""
            total += len(content) // 2  # 粗略估计
        return total

    def _should_compress(self) -> bool:
        """检查是否需要压缩"""
        msgs = [{"role":"system","content":SYSTEM_PROMPT}]
        for h in self.history:
            msgs.append({"role":"user","content":h["question"]})
            msgs.append({"role":"assistant","content":h["answer"][:500]})  # 只取前500字估算
        return self._estimate_tokens(msgs) > self.MAX_TOKENS_ESTIMATE

    def _compress_to_markdown(self) -> str:
        """将历史对话压缩为 Markdown 文件"""
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = ARCHIVE_DIR / filename

        lines = [
            f"# AlphaEye 对话记录",
            f"",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**轮数**: {len(self.history)} 轮",
            f"",
            f"---",
            f"",
        ]
        for i, h in enumerate(self.history):
            lines.append(f"## 第 {i+1} 轮")
            lines.append(f"")
            lines.append(f"### 用户")
            lines.append(f"{h['question']}")
            lines.append(f"")
            lines.append(f"### AlphaEye AI")
            lines.append(f"{h['answer']}")
            if h.get('tools_used'):
                lines.append(f"")
                lines.append(f"*工具: {', '.join(h['tools_used'])}*")
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"对话压缩完成: {filepath}")
        return str(filepath)

    def chat(self, user_message: str, context: dict = None) -> str:
        if not self.client: return "AI未配置。请在「我的」页面设置API Key后使用。"

        try:
            # 检查是否需要压缩
            compressed_file = None
            if self._should_compress() and len(self.history) > 6:
                compressed_file = self._compress_to_markdown()
                self._compressed_count = len(self.history)
                self.history = []  # 清空历史，开启新一轮

            messages = [{"role":"system","content":SYSTEM_PROMPT}]

            # 全量历史（已压缩则只有本轮）
            for h in self.history:
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
                    # 可能是上下文太长
                    if "context" in str(api_err).lower() or "token" in str(api_err).lower() or "length" in str(api_err).lower():
                        if len(self.history) > 2:
                            cf = self._compress_to_markdown()
                            self.history = []
                            return f"对话上下文过长，已自动保存到 `{cf}`。请重新提问。"
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
                answer = answer or "分析超时，请简化问题。"

            if not answer: answer = "未能完成分析，请重试。"

            # 如果有压缩，在回答开头提示
            if compressed_file:
                answer = f"*对话历史已保存: `{compressed_file}`*\n\n{answer}"

            self.history.append({
                "question": user_message,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "tools_used": self._tools_used.copy(),
            })
            return answer
        except Exception as e:
            logger.error(f"AI: {e}")
            return f"AI异常: {str(e)[:200]}"

    def get_last_tools_used(self): return self._tools_used
    def clear_history(self): self.history = []; self._tools_used = []

    def get_history(self) -> list:
        """获取全量历史（含压缩信息）"""
        result = list(self.history)
        if self._compressed_count > 0:
            result.insert(0, {
                "question": "",
                "answer": f"*(之前的 {self._compressed_count} 轮对话已压缩存档)*",
                "timestamp": "",
                "tools_used": [],
                "is_compression_marker": True,
            })
        return result

    @staticmethod
    def get_archived_files() -> list:
        """获取所有压缩存档列表"""
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        files = sorted(ARCHIVE_DIR.glob("conversation_*.md"), reverse=True)
        return [str(f) for f in files]
