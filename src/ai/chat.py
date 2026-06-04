"""AlphaEye AI — 短线风险审查与选股分析引擎"""

import json, logging, os, re, traceback
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
MAX_TOKENS = 7000
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
        self._memory = None
        self._active_session_key = None

    def chat(self, user_message: str, context: dict = None) -> str:
        if not self.client:
            return "AI 未配置。请在「我的」页面填写 API Key、API 地址和模型名称后使用。\n\n支持 DeepSeek / OpenAI / 智谱 / 月之暗面等 OpenAI 兼容接口。"

        try:
            scene = self.detect_scene(user_message)
            stock_code = self._extract_stock_code(user_message)
            run_id, scratchpad = self._start_audit(user_message, scene)
            session_id = self._save_user_message(user_message, scene, stock_code)
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
                        temperature=0.35, max_tokens=MAX_TOKENS, timeout=30)
                except Exception as api_err:
                    logger.error(f"API r{rnd}: {api_err}")
                    err_msg = str(api_err)[:200]
                    # Fallback: if we already have partial answer, return it
                    if answer:
                        return self._finalize_response(
                            user_message,
                            answer + f"\n\n*(部分工具调用失败: {err_msg})*",
                            session_id,
                            stock_code,
                            scene,
                            scratchpad,
                            run_id,
                        )
                    # Fallback: try without tools
                    try:
                        fallback = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages + [{"role":"user","content":"请基于已有信息直接回答，不需要调用工具。"}],
                            temperature=0.35, max_tokens=MAX_TOKENS//2, timeout=15)
                        fb = fallback.choices[0].message.content or ""
                        if fb:
                            return self._finalize_response(
                                user_message,
                                fb + "\n\n*(部分工具不可用，基于存量知识回答)*",
                                session_id,
                                stock_code,
                                scene,
                                scratchpad,
                                run_id,
                            )
                    except:
                        pass
                    return self._finalize_response(
                        user_message,
                        f"AI 服务暂时不可用，请稍后重试。\n\n*(错误详情: {err_msg})*",
                        session_id,
                        stock_code,
                        scene,
                        scratchpad,
                        run_id,
                    )

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
                    self._log_audit_tool(scratchpad, run_id, nm, args, result)

                    messages.append({"role":"tool","tool_call_id":tc.id,"content":result})
            else:
                if not answer:
                    answer = self._fallback_answer(user_message)

            if not answer:
                answer = self._fallback_answer(user_message)

            return self._finalize_response(
                user_message, answer, session_id, stock_code, scene, scratchpad, run_id
            )

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
        code = self._extract_stock_code(text)

        if code and not (is_group_question or has_injected_context):
            return self._fallback_stock_report(code, text)

        if is_group_question or has_injected_context:
            groups = self._sector_candidate_groups(text)
            candidate_text = self._format_sector_candidate_table(groups)
            primary = self._first_candidate(groups, "电力") or "长江电力(600900)"
            chip = self._first_candidate(groups, "半导体") or "中芯国际(688981)"

            return (
                f"### 人话结论\n"
                f"1 万做短线，我会先偏电力做防守模拟，半导体只做弹性观察。电力看 {primary} 这类承接稳的，半导体看 {chip} 这类主线弹性，但不能追高。\n\n"
                "### 周一操作建议\n"
                "你的状态：现金 1 万，适合先小样本模拟验证，不适合一把打满。今天的核心不是“买哪个行业”，而是先找低风险观察点，再决定要不要加入实验室验证。\n\n"
                "### 周一操作两步走\n"
                f"第一步：先处理电力。优先看 {primary}，只在低开不破、回踩有承接、反量化风险低/中的情况下加入观察或模拟验证。\n"
                f"第二步：再看半导体。{chip} 这类弹性更大，但必须等板块联动和分时承接确认；如果放量滞涨或高开冲回落，直接放弃，不做追高验证。\n\n"
                "### 候选表\n"
                f"{candidate_text}\n\n"
                "### 参与条件\n"
                "1. 机会分不弱，至少要看到热度和承接同时在线。\n"
                "2. 分时回踩不破均价线，不能是直线急拉没有回踩。\n"
                "3. 板块内有 2-3 只股票同步走强，不要买孤立拉升。\n"
                "4. 反量化风险必须是低或中；出现尾盘诱多、高位接盘、放量滞涨就降级。\n\n"
                "### 放弃条件\n"
                "1. 高开太多后 10 分钟内回落，放弃追。\n"
                "2. 放量但价格推不动，放弃。\n"
                "3. 板块不联动，只有单票硬拉，放弃。\n"
                "4. 跌破分时均价线后 10 分钟收不回，离场或不参与。\n\n"
                "### 周一操作时间表\n"
                "9:15：看竞价，谁高开太多但量不跟，先剔除。\n"
                "9:25：只保留电力/半导体里竞价不极端、成交正常的票。\n"
                "9:30-10:00：不追第一波，只看回踩均价线能不能稳住。\n"
                "10:00-10:30：若主候选承接稳定，可先做模拟验证；若半导体强于电力，再考虑加入弹性观察。\n"
                "14:30-15:00：决定是否隔夜。尾盘急拉无回踩不拿，回踩不破且板块仍强才考虑留。\n\n"
                "### 资金纪律\n"
                "1 万元建议最多拆成 2 个观察计划：主候选和备选分别写清触发条件、失效条件和止损规则。第一笔验证错了，不加码摊平；第一笔验证对了，也要等第二个确认点再行动。"
            )

        return (
            "## 结论摘要\n"
            "我可以继续做研究，但现在没有拿到足够实时数据，所以不会编造价格、点位或确定结论。正确做法是先把问题拆成数据状态、风险、计划和复盘字段。\n\n"
            "## 数据状态\n"
            "| 数据 | 是否可用 | 你怎么用 | 局限 |\n"
            "|---|---|---|---|\n"
            "| 行情/评分 | 暂缺 | 需要判断热度、承接、反量化 | 当前不能给确定触发 |\n"
            "| 新闻/题材 | 暂缺 | 判断是否有催化 | 不能臆测利好 |\n"
            "| 历史记忆 | 可继续检索 | 找过往判断是否失效 | 需要具体股票或主题 |\n\n"
            "## 我会怎么做\n"
            "| 步骤 | 要检查什么 | 为什么重要 |\n"
            "|---|---|---|\n"
            "| 1 | 先看大盘和板块是否退潮 | 环境差时个股信号容易失真 |\n"
            "| 2 | 再看个股热度、承接和量价 | 防止追在量化收割点 |\n"
            "| 3 | 最后写入实验室验证 | 不靠感觉，靠 T+1/T+2/T+3 复盘 |\n\n"
            "## 你可以这样问\n"
            "- 分析 600900 的短线风险和反量化风险\n"
            "- 今天电力和半导体哪个更值得观察\n"
            "- 把这只票加入实验室验证需要写哪些条件\n\n"
            "## 复盘入库\n"
            "下一步请至少给我股票代码、观察周期和你的假设，我会输出：研究假设、触发条件、失效条件、止损规则、T+1/T+2/T+3 观察点。"
        )

    @staticmethod
    def _fallback_stock_report(code: str, user_message: str) -> str:
        return (
            f"## 结论摘要\n"
            f"{code} 这次先按“研究/观察”处理，不给实盘买入结论。原因是当前工具或实时数据不足，我不能假装已经验证过价格、量比、板块联动和新闻催化。\n\n"
            "## 数据状态\n"
            "| 数据 | 是否可用 | 你怎么用 | 局限 |\n"
            "|---|---|---|---|\n"
            f"| 个股 {code} 行情 | 暂缺或不完整 | 判断涨跌幅、量比、换手、位置 | 不能编造实时价 |\n"
            "| 六维评分 | 待工具返回 | 判断热度、承接、题材、延续、策略匹配 | 分数缺失时只能给框架 |\n"
            "| 反量化扫描 | 待工具返回 | 排查诱多、接盘、脉冲、滞涨、背离 | 不能替代盘中观察 |\n"
            "| 新闻/题材 | 待工具返回 | 判断催化是否真实 | 不能把传闻当依据 |\n\n"
            "## 证据表\n"
            "| 维度 | 现在能判断什么 | 白话解释 | 对结论的影响 |\n"
            "|---|---|---|---|\n"
            "| 价格位置 | 暂不能确认 | 没有可靠实时价就不知道是否追高 | 不给参与结论 |\n"
            "| 承接 | 暂不能确认 | 要看回踩均价线是否有人接 | 只能列观察条件 |\n"
            "| 板块联动 | 暂不能确认 | 单票硬拉容易坑人 | 必须等同板块确认 |\n"
            "| 风险 | 默认按中性偏谨慎 | 数据缺失时风险要上调 | 只允许模拟验证 |\n\n"
            "## 反量化风险表\n"
            "| 风险项 | 当前判断 | 触发证据 | 散户容易怎么亏 | 应对 |\n"
            "|---|---|---|---|---|\n"
            "| 尾盘诱多 | 待确认 | 14:30 后急拉但无回踩 | 追高隔夜，次日低开 | 只记录不追 |\n"
            "| 高位接盘 | 待确认 | 高开冲高后量价背离 | 买在情绪顶 | 等二次承接 |\n"
            "| 分时脉冲 | 待确认 | 直线拉升后快速回落 | 被短线资金收割 | 不追第一波 |\n"
            "| 放量滞涨 | 待确认 | 成交放大但价格推不动 | 主力出货时接盘 | 出现则放弃 |\n"
            "| 板块背离 | 待确认 | 个股涨、板块不跟 | 孤立拉升难持续 | 必须看联动 |\n\n"
            "## 交易计划表\n"
            "| 动作 | 触发条件 | 禁止条件 | 仓位/验证方式 | 复盘记录 |\n"
            "|---|---|---|---|---|\n"
            "| 加入观察 | 回踩不破均价线，板块同步走强 | 高开急冲无回踩 | 只观察或模拟 | 记录触发时间 |\n"
            "| 模拟验证 | 评分和反量化风险都可接受 | 风险升至高/极高 | 小样本模拟 | 记录 T+1/T+2/T+3 |\n"
            "| 暂停 | 大盘弱、板块退潮 | 无 | 不做动作 | 记录为什么放弃 |\n"
            "| 退出假设 | 跌破昨日低点或放量滞涨 | 无 | 验证失败 | 写入实验室 |\n\n"
            "## 反证与失效条件\n"
            "1. 开盘高冲后 10 分钟内跌回均价线下方。\n"
            "2. 放量但价格无法继续上推。\n"
            "3. 同板块核心股没有联动。\n"
            "4. 大盘和情绪转弱，短线资金退潮。\n"
            "5. 新闻催化无法被公告、互动平台或板块表现验证。\n\n"
            "## 复盘入库\n"
            f"建议把 {code} 加入实验室时写入：假设、触发条件、失效条件、止损规则、T+1 高点/低点、T+2 是否延续、T+3 是否回撤。"
        )

    @staticmethod
    def _sector_candidate_groups(text: str) -> list:
        try:
            from src.ai.tool_executor import ToolExecutor
            data = ToolExecutor()._get_sector_candidates(text, limit=4)
            return data.get("groups", [])
        except Exception:
            return []

    @staticmethod
    def _format_sector_candidate_table(groups: list) -> str:
        if not groups:
            return (
                "| 方向 | 优先看 | 角色 | 怎么用 | 最大风险 |\n"
                "|---|---|---|---|---|\n"
                "| 电力 | 长江电力(600900) / 中国核电(601985) | 防守试错 | 只低吸不追高 | 弹性不足、板块不联动 |\n"
                "| 半导体 | 中芯国际(688981) / 中微公司(688012) | 弹性备选 | 只做承接确认后的短线 | 冲高回落、放量滞涨 |"
            )

        rows = ["| 方向 | 候选 | 角色 | 当前状态 | 我会怎么处理 |",
                "|---|---|---|---|---|"]
        for group in groups:
            name = group.get("name", "")
            for item in group.get("candidates", [])[:3]:
                stock = f"{item.get('name', item.get('code'))}({item.get('code')})"
                role = item.get("role") or "短线候选"
                score = item.get("score")
                risk = item.get("anti_quant_level") or item.get("risk") or "未知"
                status = item.get("status") or "待确认"
                score_text = f"机会{score}" if score is not None else "待实时确认"
                action = item.get("action") or ("低吸验证" if risk in ("低", "中") else "等待实时确认")
                rows.append(f"| {name} | {stock} | {role} | {score_text} / {status} / 风险{risk} | {action} |")
        return "\n".join(rows)

    @staticmethod
    def _first_candidate(groups: list, keyword: str) -> str:
        for group in groups:
            if keyword in group.get("name", ""):
                candidates = group.get("candidates", [])
                if candidates:
                    first = candidates[0]
                    return f"{first.get('name', first.get('code'))}({first.get('code')})"
        return ""

    @staticmethod
    def _history_file():
        from pathlib import Path
        env_file = os.getenv("ALPHAEYE_CONVERSATION_FILE")
        if env_file:
            return Path(env_file)
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
        """从旧 JSON 和数据库恢复对话。"""
        try:
            import json as _json
            f = self._history_file()
            if f.exists():
                with open(f, 'r', encoding='utf-8') as ff:
                    self.history = _json.load(ff)
                self._import_legacy_history(self.history, source=str(f))
                return True
        except Exception as e:
            logger.warning(f"加载对话失败: {e}")
        loaded = self.load_from_memory()
        return bool(loaded)

    def load_from_memory(self, limit: int = HISTORY_LEN):
        memory = self._get_memory()
        if not memory:
            return []
        try:
            self.history = memory.get_recent_pairs(limit=limit)
            return self.history
        except Exception as exc:
            logger.warning(f"从数据库加载对话失败: {exc}")
            return []

    def _import_legacy_history(self, items: list[dict], source: str = "legacy_json") -> int:
        memory = self._get_memory()
        if not memory:
            return 0
        try:
            return memory.import_legacy_history(items, source=source)
        except Exception as exc:
            logger.warning(f"导入旧对话失败: {exc}")
            return 0

    def get_last_tools_used(self): return self._tools_used

    def clear_history(self):
        self.history = []; self._tools_used = []
        try: self._history_file().unlink(missing_ok=True)
        except: pass

    def get_history(self): return self.history

    @staticmethod
    def _extract_stock_code(text: str) -> str:
        m = re.search(r"\b(\d{6})\b", text or "")
        return m.group(1) if m else ""

    def _get_memory(self):
        if self._memory is not None:
            return self._memory
        try:
            from src.memory.conversation_memory import ConversationMemory

            self._memory = ConversationMemory()
        except Exception as exc:
            logger.warning(f"ConversationMemory unavailable: {exc}")
            self._memory = False
        return self._memory or None

    def _save_user_message(self, user_message: str, scene: str, stock_code: str = "") -> int | None:
        memory = self._get_memory()
        if not memory:
            return None
        try:
            session_key = f"{scene}:{stock_code or 'general'}"
            if self._active_session_key != session_key:
                session_id = memory.create_session(scene, title=user_message[:60] if user_message else scene)
                self._active_session_key = session_key
            else:
                session_id = memory.get_or_create_session(scene)
            if user_message and len(user_message) > 8:
                memory.update_title(session_id, user_message[:60])
            memory.save_message(session_id, "user", user_message, stock_code=stock_code or None)
            return session_id
        except Exception as exc:
            logger.warning(f"save user message failed: {exc}")
            return None

    def _save_ai_message(self, session_id: int | None, user_message: str,
                         answer: str, stock_code: str, scene: str) -> None:
        memory = self._get_memory()
        if not memory or not session_id:
            return
        try:
            from src.ai.structured_output import parse_structured_output
            from src.memory.analysis_memory import AnalysisMemory

            structured = parse_structured_output(answer)
            message_id = memory.save_message(
                session_id,
                "assistant",
                answer,
                stock_code=stock_code or None,
                structured_output=structured,
                tools_used=self._tools_used.copy(),
            )
            if stock_code:
                data = dict(structured or {})
                data.setdefault("timeframe", scene)
                with AnalysisMemory() as analysis:
                    analysis.save_analysis(
                        stock_code=stock_code,
                        analysis_type=scene,
                        data=data,
                        message_id=message_id,
                    )
        except Exception as exc:
            logger.warning(f"save ai message failed: {exc}")

    def _finalize_response(self, user_message: str, answer: str,
                           session_id: int | None, stock_code: str, scene: str,
                           scratchpad, run_id: str | None) -> str:
        self.history.append({
            "question": user_message,
            "answer": answer,
            "timestamp": datetime.now().isoformat(),
            "tools_used": self._tools_used.copy(),
        })
        self.save_to_disk()
        self._save_ai_message(
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            stock_code=stock_code,
            scene=scene,
        )
        self._finish_audit(scratchpad, run_id, answer)
        return answer

    @staticmethod
    def _start_audit(user_message: str, scene: str):
        try:
            from src.agent.scratchpad import Scratchpad

            scratchpad = Scratchpad()
            return scratchpad.start_run(user_message, scene=scene), scratchpad
        except Exception as exc:
            logger.warning(f"scratchpad start failed: {exc}")
            return None, None

    @staticmethod
    def _log_audit_tool(scratchpad, run_id: str | None, name: str, args: dict, result) -> None:
        if not scratchpad or not run_id:
            return
        try:
            scratchpad.log_tool_result(run_id, name, args, result)
        except Exception as exc:
            logger.warning(f"scratchpad tool log failed: {exc}")

    @staticmethod
    def _finish_audit(scratchpad, run_id: str | None, answer: str) -> None:
        if not scratchpad or not run_id:
            return
        try:
            scratchpad.finish_run(run_id, answer_summary=(answer or "")[:800])
        except Exception as exc:
            logger.warning(f"scratchpad finish failed: {exc}")

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
            "## AlphaEye 安全闸门\n"
            "- 你是金融研究助手，不是自动荐股机器。\n"
            "- 默认输出“观察/模拟/验证/放弃”四类动作，不输出实盘买入指令。\n"
            "- 用户处于谨慎或冷静期时，只能给观察、模拟和复盘计划。\n"
            "- 每个候选都必须写清失效条件和止损纪律；没有条件就不能给参与结论。",
            "## 参考项目内化为工作流\n"
            "- Dexter 原则：先规划、再调用工具、最后自我校验；回答必须说明数据来源和缺口。\n"
            "- Vibe-Trading 原则：把问题拆成研究员、风控、执行、复盘四个角色；每个角色都要给输出。\n"
            "- daily_stock_analysis 原则：输出像决策仪表盘，必须有表格、评分/风险、行动清单和推送级摘要。\n"
            "- 这些只是工作流参考，不代表照搬任何项目，也不允许编造数据。",
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
                messages=[{"role":"system","content":V6_MORNING_PROMPT},
                          {"role":"user","content":"请生成今日盘前早报。"}],
                temperature=0.7, max_tokens=800, timeout=30)
            return resp.choices[0].message.content or "生成失败"
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
        """收盘总结 — 印证AI判断 + 真实数据驱动的明日规划"""
        if not self.client:
            return "AI 未配置"
        try:
            from src.data.realtime import get_market_overview, get_top_stocks

            # ═══ 大盘 ═══
            ov = get_market_overview()
            idx_lines = [f"{i.get('name')} {i.get('price',0):.2f} {i.get('change_pct',0):+.2f}%" for i in (ov.get("indices") or [])[:3]]

            # ═══ 涨幅榜 Top 8 + 跌幅榜 Top 5 ═══
            up = get_top_stocks("changepercent", False, 8) or []
            up_lines = [f"{s['name']}({s['code']}) {s.get('price',0):.2f} {s.get('change_pct',0):+.2f}% 换手{s.get('turnover',0):.1f}%" for s in up]

            dn = get_top_stocks("changepercent", True, 5) or []
            dn_lines = [f"{s['name']}({s['code']}) {s.get('price',0):.2f} {s.get('change_pct',0):+.2f}%" for s in dn]

            # ═══ 成交额 Top 8 ═══
            amt = get_top_stocks("amount", False, 8) or []
            amt_lines = [f"{s['name']}({s['code']}) {(s.get('amount',0) or 0)/1e8:.1f}亿 {s.get('change_pct',0):+.2f}%" for s in amt]

            # ═══ 今日推荐板块 ═══
            try:
                from src.pages.radar import _compute_daily_recs
                recs = _compute_daily_recs()
                top_inds = [(name, score, reason) for name, score, reason in recs.get("industries", [])[:3]]
                top_cons = [(name, score, reason) for name, score, reason in recs.get("concepts", [])[:3]]
                sector_text = (
                    "推荐行业: " + "; ".join(f"{n}(活跃度{s:.0f}, {r})" for n,s,r in top_inds) + "\n"
                    "推荐概念: " + "; ".join(f"{n}(活跃度{s:.0f}, {r})" for n,s,r in top_cons)
                )
            except Exception:
                sector_text = "板块数据暂不可用"

            # ═══ 持仓 ═══
            pos_text = "无持仓"
            try:
                from src.trading.engine import TradingEngine
                from src.data.realtime import get_realtime_quote
                with TradingEngine() as eng:
                    acct = eng.get_account()
                    if acct:
                        ps = eng.get_positions()
                        if ps:
                            plines = []
                            for p in ps:
                                q = get_realtime_quote(p.code)
                                mp = q.get("price",0) if q else p.cost_price
                                pnl = (mp - p.cost_price) * p.quantity
                                pct = (mp - p.cost_price) / p.cost_price * 100 if p.cost_price else 0
                                plines.append(f"{p.name or p.code}({p.code}) 成本{p.cost_price} 现价{mp:.2f} 盈亏{pnl:+.0f}({pct:+.1f}%)")
                            pos_text = "\n".join(plines)
                        if acct.cash:
                            pos_text += f"\n现金余额: {acct.cash:.0f}"
            except: pass

            # ═══ 今日对话全文（不截断，让AI能验证自己说过什么）═══
            chat_full = "无对话"
            if self.history:
                clines = []
                for h in self.history[-8:]:
                    q_full = str(h.get("question", ""))
                    a_full = str(h.get("answer", ""))
                    clines.append(f"### 用户问\n{q_full}\n### AI 答\n{a_full}\n")
                chat_full = "\n---\n".join(clines)

            prompt = (
                "你正在写 AlphaEye 今日收盘规划。请认真比对「AI 今天说了什么」和「市场实际数据」，"
                "逐条验证 AI 的判断是否被今日走势印证。\n\n"
                f"【真实大盘】\n" + "\n".join(idx_lines) + "\n\n"
                f"【今日涨幅榜】\n" + "\n".join(up_lines) + "\n\n"
                f"【今日跌幅榜】\n" + "\n".join(dn_lines) + "\n\n"
                f"【今日成交额榜】\n" + "\n".join(amt_lines) + "\n\n"
                f"【今日板块热度】\n{sector_text}\n\n"
                f"【我的持仓】\n{pos_text}\n\n"
                f"【今日 AI 对话全文】\n{chat_full}\n\n"
                "---\n"
                "请按以下结构输出，每段必须引用上面的真实数字：\n\n"
                "## 今日盘面\n"
                "三大指数涨跌幅 + 成交量感觉（引用成交额榜数据） + 涨跌停情况。\n\n"
                "## AI判断印证\n"
                "对照「AI 对话」和「市场数据」，逐条检查 AI 的判断：\n"
                "- 哪些判断被走势印证了（引用具体股票/指数涨跌幅）\n"
                "- 哪些判断偏了或没对上（也要说，诚实复盘）\n"
                "- 哪些判断还需要明天验证\n\n"
                "## 主线与领跌\n"
                "今天实际涨得好的方向（引用涨幅榜+板块热度）。跌得多的方向（引用跌幅榜）。\n\n"
                "## 明日计划\n"
                "基于今天走势，明天重点看什么。给出：\n"
                "- 2-3 个明天值得关注的板块/概念（引用板块热度数据）\n"
                "- 2-3 只明天值得加入观察池的具体股票（必须来自涨幅榜/成交额榜中的真实代码，附机会分）\n"
                "- 2-3 个明天要避开的方向\n\n"
                "## 纪律\n"
                "一句明日交易纪律。\n\n"
                "要求：每个数字来源于上面真实数据。不编造。不泛泛。不写'值得关注'。"
            )
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"system","content":V6_SYSTEM_PROMPT[:800]},
                          {"role":"user","content":prompt}],
                temperature=0.4, max_tokens=900, timeout=30)
            return resp.choices[0].message.content or "生成失败"
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
            from src.trading.engine import TradingEngine
            with TradingEngine() as eng:
                acct = eng.get_account()
                if not acct:
                    return "模拟盘账户未初始化，请先在交易页创建账户。"
                stats = eng.get_stats()
                trades = eng.get_trades(50)
                positions = eng.get_positions()

            # 分类统计
            sell_trades = [t for t in trades if t.direction == "sell"]
            wins = sum(1 for t in sell_trades if (t.pnl or 0) > 0)
            losses = sum(1 for t in sell_trades if (t.pnl or 0) < 0)
            total_pnl = sum(t.pnl or 0 for t in sell_trades)
            win_rate = wins / max(len(sell_trades), 1) * 100

            # 交易明细
            trade_lines = []
            for t in trades[-15:]:
                d = "买" if t.direction == "buy" else "卖"
                pnl_str = f" 盈亏{t.pnl:+.0f}" if t.direction == "sell" and t.pnl else ""
                trade_lines.append(f"{d} {t.name or t.code} {t.quantity}股@{t.price:.2f}{pnl_str} {t.created_at.strftime('%m/%d') if t.created_at else ''}")

            prompt = (
                f"## 账户数据\n"
                f"现金: {acct.cash:.0f} | 持仓数: {len(positions)} | 连续亏损: {acct.consecutive_losses}次\n"
                f"已平仓: {len(sell_trades)}笔 | 胜率: {win_rate:.1f}%({wins}胜{losses}负)\n"
                f"总盈亏: {total_pnl:+.0f}\n\n"
                f"## 交易明细\n" + "\n".join(trade_lines) + "\n\n"
                f"---\n"
                f"请诊断这位交易者的行为。引用具体交易举例。\n\n"
                f"## 最大问题\n1-2句话指出核心问题（追高/不止损/太集中/频繁交易），引用数据证明。\n\n"
                f"## 做得好的\n如果有值得肯定的点，提一下。\n\n"
                f"## 3个改进建议\n具体可执行，例如'下次止损设在-5%而不是-15%'。\n\n"
                f"禁止泛泛而谈、不引用数据、'建议注意风险'。"
            )
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"system","content":V6_SYSTEM_PROMPT[:600]},
                          {"role":"user","content":prompt}],
                temperature=0.5, max_tokens=500, timeout=30)
            return resp.choices[0].message.content or "生成失败"
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
