"""AlphaEye AI — 短线风险审查与选股分析引擎"""

import json, logging, traceback
from datetime import datetime, date
from src.config import get_setting
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor
from src.ai.prompts import STYLE_CONTRACT, V6_SYSTEM_PROMPT, scene_prompt
from src.ai.roles import ROLES, ROLE_SUFFIXES

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
            scene = self.detect_scene(user_message)
            messages = [{"role":"system","content":self.build_system_prompt(scene, user_message)}]
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
                "### 人话结论\n"
                "如果只拿 1 万块做短线，我不会让你直接押一个方向。电力更稳，半导体弹性更大，但也更容易冲高回落。\n\n"
                "### 我会怎么做\n"
                "1. 先去雷达页分别切到电力、半导体芯片。\n"
                "2. 只看机会分靠前、承接不差、反量化风险低/中的票。\n"
                "3. 谁出现尾盘急拉无回踩、放量不涨、板块不同步，谁直接放弃。\n\n"
                "### 候选 / 风险 / 条件\n"
                f"{candidate_text}\n\n"
                "核心风险：\n"
                "1. 电力类通常波动相对稳，但短线弹性不一定强，要防止成交不足和板块不联动。\n"
                "2. 半导体类弹性更大，但更容易出现高位接盘、放量滞涨和冲高回落。\n"
                "3. 如果实时数据缺失，不能直接给买入结论，应先进入雷达页按行业/概念确认最新行情。\n\n"
                "参与条件：热度不弱、承接分高、板块仍有联动、反量化风险不高、没有明显前高压力。\n\n"
                "放弃条件：尾盘急拉无回踩、放量不涨、板块退潮、跌破分时均价线。\n\n"
                "### 资金纪律\n"
                "1 万元更适合先 2-3 成仓验证，别一把打满。先让系统挑候选，再逐只审查，错了损失小，对了再看是否加。"
            )

        return (
            "### 人话结论\n"
            "这题我能先给你交易思路，但现在没有拿到足够实时数据，所以我不会瞎编买入价、止损价或确定结论。\n\n"
            "### 我会怎么做\n"
            "先看风险，再看机会：有没有尾盘诱多、放量滞涨、板块退潮；再看承接、题材、持股周期。\n\n"
            "### 你可以这样问\n"
            "- 分析某只股票的短线风险和反量化风险\n"
            "- 按某个行业/概念筛选候选股\n"
            "- 判断一只股票更适合隔夜、1-2 天还是 2-3 天\n\n"
            "### 资金纪律\n"
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
    # 智能追问 & 场景检测 & 动态角色提示
    # ═══════════════════════════════════════

    @staticmethod
    def build_system_prompt(scene: str = "general", user_message: str = "") -> str:
        """按场景拼接基础提示、内置角色和输出契约。"""
        role_keys = AIChat.roles_for_scene(scene, user_message)
        role_lines = []
        for key in role_keys:
            role = ROLES.get(key)
            if not role:
                continue
            role_lines.append(f"- {role['name']}：{role['desc']}")
            suffix = ROLE_SUFFIXES.get(key)
            if suffix:
                role_lines.append(suffix.strip())

        return "\n\n".join([
            SYSTEM_PROMPT,
            "## 本次启用的内置技能/角色\n" + "\n".join(role_lines),
            STYLE_CONTRACT,
            scene_prompt(scene),
        ])

    @staticmethod
    def roles_for_scene(scene: str, user_message: str = "") -> list:
        """把问题场景映射到内置 AI 技能。"""
        if scene == "sector_scan":
            return ["short_term_researcher", "risk_reviewer", "discipline_coach"]
        if scene == "quick_judge":
            return ["risk_reviewer", "holding_predictor", "discipline_coach"]
        if scene == "deep_analysis":
            return ["risk_reviewer", "short_term_researcher", "holding_predictor"]
        if scene == "review":
            return ["review_analyst", "discipline_coach"]
        if scene == "learn":
            return ["general_assistant", "risk_reviewer"]
        return ["general_assistant", "risk_reviewer"]

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

    # ═══════════════════════════════════════
    # 收盘总结
    # ═══════════════════════════════════════

    def closing_summary(self) -> str:
        """生成当日收盘总结"""
        if not self.client:
            return "AI 未配置"
        try:
            # 收集持仓数据
            pos_text = "暂无持仓"
            try:
                from src.trading.engine import TradingEngine
                with TradingEngine() as eng:
                    acct = eng.get_account()
                    if acct:
                        ps = eng.get_positions()
                        if ps:
                            lines = []
                            for p in ps:
                                lines.append(f"- {p.name or p.code}({p.code}) {p.quantity}股 成本{p.cost_price}")
                            pos_text = "\n".join(lines)
                        trs = eng.get_trades(10)
                        trade_summary = "\n".join(
                            f"- {t.direction} {t.name or t.code} {t.quantity}@{t.price} {'盈亏' + str(t.pnl) if t.pnl else ''}"
                            for t in (trs or [])[:5])
            except Exception:
                trade_summary = "交易记录暂不可用"

            prompt = (
                f"请生成今日收盘总结。\n\n"
                f"## 今日持仓\n{pos_text}\n\n"
                f"## 今日交易\n{trade_summary}\n\n"
                f"## 今日 AI 对话概览\n"
                f"共 {len(self.history)} 条对话\n\n"
                f"请按以下格式输出：\n"
                f"1. 今日市场回顾（一句话）\n"
                f"2. 我的持仓表现\n"
                f"3. 今日 AI 判断回顾（哪些对了，哪些需要验证）\n"
                f"4. 明日关注方向\n"
                f"5. 操作纪律提醒\n"
                f"总长度不超过 500 字"
            )
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": V6_SYSTEM_PROMPT[:1500]},
                          {"role": "user", "content": prompt}],
                tools=TOOLS, tool_choice="auto",
                temperature=0.7, max_tokens=800, timeout=25)
            return resp.choices[0].message.content or "收盘总结生成失败"
        except Exception as e:
            return f"收盘总结暂不可用: {e}"

    # ═══════════════════════════════════════
    # 账户诊断
    # ═══════════════════════════════════════

    def account_diagnosis(self) -> str:
        """分析用户的交易行为和账户表现"""
        if not self.client:
            return "AI 未配置"
        try:
            # 收集完整交易数据
            from src.trading.engine import TradingEngine
            with TradingEngine() as eng:
                acct = eng.get_account()
                if not acct:
                    return "模拟盘账户未初始化，请先在交易页创建账户。"
                stats = eng.get_stats()
                trades = eng.get_trades(50)
                positions = eng.get_positions()

            # 统计数据
            buy_trades = [t for t in trades if t.direction == "buy"]
            sell_trades = [t for t in trades if t.direction == "sell"]
            wins = sum(1 for t in sell_trades if (t.pnl or 0) > 0)
            losses = sum(1 for t in sell_trades if (t.pnl or 0) < 0)
            total_pnl = sum(t.pnl or 0 for t in sell_trades)

            # 构建诊断数据
            data = (
                f"## 账户状态\n"
                f"- 状态: {acct.status}\n"
                f"- 现金: {acct.cash:.0f}\n"
                f"- 连续亏损: {acct.consecutive_losses}次\n"
                f"- 持仓数: {len(positions)}\n\n"
                f"## 交易统计\n"
                f"- 总交易: {len(sell_trades)}笔\n"
                f"- 胜: {wins} 负: {losses}\n"
                f"- 胜率: {wins / max(len(sell_trades), 1) * 100:.1f}%\n"
                f"- 总盈亏: {total_pnl:+.0f}\n\n"
                f"请诊断我的交易行为，指出：\n"
                f"1. 最大问题是什么（追高/不止损/集中度/频繁交易）\n"
                f"2. 和上次比有没有进步\n"
                f"3. 给出 3 个下周可执行的具体改进建议\n"
                f"总长度不超过 400 字"
            )
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": V6_SYSTEM_PROMPT[:1500]},
                          {"role": "user", "content": data}],
                temperature=0.7, max_tokens=600, timeout=25)
            return resp.choices[0].message.content or "诊断生成失败"
        except Exception as e:
            return f"账户诊断暂不可用: {e}"

    # ═══════════════════════════════════════
    # 尾盘扫描
    # ═══════════════════════════════════════

    def tail_session_scan(self) -> tuple:
        """14:30 尾盘隔夜雷达扫描，返回 (phase, candidates_text)"""
        try:
            from src.strategies.overnight import OvernightRadar
            from src.data.realtime import get_top_stocks
            from src.scoring.engine import V6ScoringEngine

            radar = OvernightRadar()
            stocks = get_top_stocks("change_pct", False, 60)
            candidates = []
            for s in (stocks or []):
                cd = s.get("code", "")
                if not cd: continue
                ok, _ = radar.check_hard_filters(s)
                if ok:
                    m = radar.compute_match(s)
                    candidates.append({
                        "code": cd, "name": s.get("name", cd),
                        "chg": s.get("change_pct", 0),
                        "match": m["match"], "status": m["status"],
                    })

            if not candidates:
                return ("初筛", "当前无符合尾盘隔夜条件的股票")

            candidates.sort(key=lambda x: x["match"], reverse=True)
            lines = [f"尾盘隔夜候选 {len(candidates)} 只"]
            for c in candidates[:5]:
                lines.append(f"- {c['name']}({c['code']}) 涨幅{c['chg']:+.1f}% 匹配{c['match']:.0f}% {c['status']}")

            # 给 AI 总结
            if self.client:
                try:
                    ctx = "\n".join(lines)
                    resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role":"system","content": V6_SYSTEM_PROMPT[:1200]},
                                  {"role":"user","content": f"尾盘扫描结果：\n{ctx}\n\n请用 2-3 句话总结今日尾盘机会和风险。"}],
                        temperature=0.7, max_tokens=200, timeout=15)
                    summary = resp.choices[0].message.content or ""
                    return ("完成", summary)
                except: pass
            return ("完成", "\n".join(lines[:8]))
        except Exception as e:
            return ("错误", f"尾盘扫描失败: {e}")
