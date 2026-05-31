"""AlphaEye AI — 短线风险审查与选股分析引擎"""

import json, logging, traceback
from datetime import datetime, date
from src.config import get_setting
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor
from src.ai.prompts import V6_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
TODAY = date.today().strftime("%Y年%m月%d日")
WDAY = ["周一","周二","周三","周四","周五","周六","周日"][date.today().weekday()]

SYSTEM_PROMPT = V6_SYSTEM_PROMPT

# In chat(), update max_tokens to 4000 for detailed responses
MAX_TOKENS = 3200
TOOL_ROUNDS = 6
HISTORY_LEN = 20


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
            for h in self.history[-HISTORY_LEN:]:
                messages.append({"role":"user","content":h["question"]})
                messages.append({"role":"assistant","content":h["answer"]})
            messages.append({"role":"user","content":user_message})

            self._tools_used = []
            answer = ""

            for rnd in range(TOOL_ROUNDS):
                try:
                    resp = self.client.chat.completions.create(
                        model=self.model, messages=messages,
                        tools=TOOLS, tool_choice="auto",
                        temperature=0.7, max_tokens=MAX_TOKENS, timeout=30)
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
                            temperature=0.7, max_tokens=MAX_TOKENS//2, timeout=15)
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
                    answer = self._fallback_answer(user_message)

            if not answer:
                answer = self._fallback_answer(user_message)

            self.history.append({
                "question": user_message,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "tools_used": self._tools_used.copy(),
            })
            self.save_to_disk()
            return answer

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"AI fatal: {tb}")
            return f"系统异常，请稍后重试。\n\n*(调试: {str(e)[:100]})*"

    def _fallback_answer(self, user_message: str) -> str:
        """在工具/模型未给出内容时，仍按 AlphaEye 结构回答，避免无效兜底。"""
        text = user_message or ""
        is_group_question = any(k in text for k in [
            "行业", "概念", "板块", "电力", "半导体", "芯片", "买什么", "推荐", "股票池", "候选",
        ])
        has_injected_context = "用户问题是行业/概念选股" in text or "静态候选池" in text

        if is_group_question or has_injected_context:
            candidates = []
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("- ") and ("(" in stripped or "静态候选池" in stripped):
                    candidates.append(stripped)

            candidate_text = "\n".join(candidates[:8]) if candidates else (
                "- 电力方向：优先去雷达页按「电力/公用事业」筛选，重点看承接分和反量化风险。\n"
                "- 半导体方向：优先去雷达页按「半导体芯片」筛选，重点看题材分、放量滞涨和高位接盘风险。"
            )

            return (
                "### 短线结论\n"
                "我先按行业/概念选股处理，不要求你必须给单只股票代码。当前更适合先做候选池筛选，再让 AI 对候选逐只做风险审查。\n\n"
                "### 候选与方向\n"
                f"{candidate_text}\n\n"
                "### 风险审查\n"
                "1. 电力类通常波动相对稳，但短线弹性不一定强，要防止成交不足和板块不联动。\n"
                "2. 半导体类弹性更大，但更容易出现高位接盘、放量滞涨和冲高回落。\n"
                "3. 如果实时数据缺失，不能直接给买入结论，应先进入雷达页按行业/概念确认最新行情。\n\n"
                "### 参与条件\n"
                "优先选择：热度不弱、承接分高、题材仍在主线、反量化风险不高、没有明显前高压力的个股。\n\n"
                "### 放弃条件\n"
                "如果出现尾盘急拉无回踩、放量不涨、板块退潮、跌破分时均价线，建议放弃本次机会。\n\n"
                "### 验证建议\n"
                "你可以在雷达页按行业/概念筛出候选，再把 2-5 只加入短线实验室验证。1 万元资金更适合轻仓、分批、先验证，不适合满仓押单只。"
            )

        return (
            "### 短线结论\n"
            "我可以先按 AlphaEye 的风险审查框架回答，但当前没有拿到足够的实时数据，所以不会编造买入价、止损价或确定结论。\n\n"
            "### 你可以这样问\n"
            "- 分析某只股票的短线风险和反量化风险\n"
            "- 按某个行业/概念筛选候选股\n"
            "- 判断一只股票更适合隔夜、1-2 天还是 2-3 天\n\n"
            "### 下一步\n"
            "如果你给出行业、概念或股票代码，我会先做风险审查，再给参与条件、放弃条件和验证建议。"
        )

    @staticmethod
    def _history_file():
        from pathlib import Path
        d = Path(__file__).parent.parent.parent / "data" / "conversations"
        d.mkdir(parents=True, exist_ok=True)
        return d / "latest_conversation.json"

    def save_to_disk(self):
        """持久化对话到文件"""
        try:
            import json as _json
            with open(self._history_file(), 'w', encoding='utf-8') as f:
                _json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存对话失败: {e}")

    def delete_history_item(self, index: int) -> bool:
        """删除单条对话记录"""
        try:
            if 0 <= index < len(self.history):
                self.history.pop(index)
                self.save_to_disk()
                return True
        except Exception as e:
            logger.warning(f"删除对话失败: {e}")
        return False

    def load_from_disk(self):
        """从文件恢复对话"""
        try:
            import json as _json
            f = self._history_file()
            if f.exists():
                with open(f, 'r', encoding='utf-8') as ff:
                    self.history = _json.load(ff)
                return True
        except Exception as e:
            logger.warning(f"加载对话失败: {e}")
        return False

    def get_last_tools_used(self): return self._tools_used

    def clear_history(self):
        self.history = []; self._tools_used = []
        try: self._history_file().unlink(missing_ok=True)
        except: pass

    def get_history(self): return self.history

    # ═══════════════════════════════════════
    # 智能追问 & 场景检测
    # ═══════════════════════════════════════

    @staticmethod
    def detect_scene(user_message: str) -> str:
        """自动检测用户问题类型"""
        msg = user_message or ""
        # 对比分析
        if any(k in msg for k in ["对比", "比较", "哪个好", "A和B", "还是", "选哪个"]):
            if len([c for c in msg if c.isdigit()]) >= 10:
                return "compare"
        # 快速判断
        if any(k in msg for k in ["能买", "能不能", "可以参与", "可以买", "买不买", "可不可以"]):
            return "quick_judge"
        # 行业/概念扫描
        if any(k in msg for k in ["行业", "概念", "板块", "有什么机会", "推荐", "买什么"]):
            return "sector_scan"
        # 复盘
        if any(k in msg for k in ["复盘", "我的交易", "账户", "持仓表现", "盈亏"]):
            return "review"
        # 详细分析
        if any(k in msg for k in ["分析", "详细", "深度", "审查", "全面"]):
            return "deep_analysis"
        # 学习
        if any(k in msg for k in ["什么是", "解释", "教我", "什么意思", "怎么用"]):
            return "learn"
        return "general"

    @staticmethod
    def follow_up_questions(user_message: str, answer: str) -> list:
        """根据用户问题生成2-3个智能追问"""
        scene = AIChat.detect_scene(user_message)
        import re
        code = None
        m = re.search(r'\b(\d{6})\b', user_message)
        if m: code = m.group(1)

        if scene == "quick_judge" and code:
            return [
                f"详细分析 {code} 的六维评分每项含义",
                f"{code} 和同行业其他股票比怎么样",
                f"如果今天不参与 {code}，有什么替代方向",
            ]
        if scene == "deep_analysis" and code:
            return [
                f"{code} 明天开盘如果高开2%怎么办",
                f"{code} 的止损位应该设在哪里",
                f"{code} 适合持有几天",
            ]
        if scene == "sector_scan":
            return [
                "这些候选里哪只风险最低？",
                "如果大盘明天走弱，这些候选还成立吗",
                "给我最推荐的那只做深度分析",
            ]
        if scene == "review":
            return [
                "我最大的问题是什么？",
                "和上个月比有没有进步？",
                "给我3个下周改进的具体建议",
            ]
        if scene == "compare":
            return [
                "换个角度再比较一下反量化风险",
                "如果只能选一个，选哪个",
                "两只都不选的话，有什么替代",
            ]
        # default
        return [
            "帮我总结一下当前最需要注意的风险",
            "今天有什么板块值得关注",
            "解释一下反量化风险是什么意思",
        ]

    # ═══════════════════════════════════════
    # 盘前早报
    # ═══════════════════════════════════════

    def morning_briefing(self) -> str:
        """生成盘前早报"""
        if not self.client:
            return "AI 未配置"
        try:
            from src.ai.prompts import V6_MORNING_PROMPT
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": V6_MORNING_PROMPT},
                          {"role": "user", "content": "请生成今日盘前早报。如果有数据就引用，没有就说暂无。"}],
                tools=TOOLS, tool_choice="auto",
                temperature=0.7, max_tokens=800, timeout=25)
            return resp.choices[0].message.content or "早报生成失败"
        except Exception as e:
            return f"早报服务暂不可用: {e}"

    def compare_stocks(self, code_a: str, code_b: str) -> str:
        """对比两只股票"""
        if not self.client:
            return "AI 未配置"
        try:
            from src.ai.prompts import V6_COMPARE_PROMPT
            # 注入评分上下文
            ctx_a, ctx_b = "", ""
            try:
                from src.scoring.engine import V6ScoringEngine
                with V6ScoringEngine() as e:
                    ctx_a = e.build_ai_context(code_a)
                    ctx_b = e.build_ai_context(code_b)
            except: pass
            msg = (
                f"请对比 {code_a} 和 {code_b}。\n\n"
                f"[{code_a} 数据]\n{ctx_a}\n\n"
                f"[{code_b} 数据]\n{ctx_b}"
            )
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"system","content":V6_COMPARE_PROMPT},
                          {"role":"user","content":msg}],
                temperature=0.7, max_tokens=600, timeout=25)
            return resp.choices[0].message.content or "对比失败"
        except Exception as e:
            return f"对比服务暂不可用: {e}"
