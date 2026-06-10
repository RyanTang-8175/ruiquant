"""AlphaEye AI — 短线风险审查与选股分析引擎"""

from __future__ import annotations

import json, logging, os, re, traceback
from datetime import datetime, date
from src.config import get_setting
from src.ai.tools import TOOLS
from src.ai.tool_executor import ToolExecutor
from src.ai.prompts import STYLE_CONTRACT, V6_SYSTEM_PROMPT, scene_prompt, AGENT_SPECIALISTS
from src.ai.roles import ROLES, ROLE_SUFFIXES

logger = logging.getLogger(__name__)
TODAY = date.today().strftime("%Y年%m月%d日")
WDAY = ["周一","周二","周三","周四","周五","周六","周日"][date.today().weekday()]

SYSTEM_PROMPT = V6_SYSTEM_PROMPT

# In chat(), update max_tokens to 4000 for detailed responses
MAX_TOKENS = 7000
TOOL_ROUNDS = 6
HISTORY_LEN = 20


def _build_specialist_context(user_message: str, stock_code: str) -> str:
    """从主流程注入的完整上下文中裁剪出四个专精 Agent 都能读懂的数据段落。

    原则：不额外调 API，只复用主流程已经注入的 [精准报价]/[六维评分]/[反量化] 部分。
    """
    text = str(user_message or "")
    lines = text.split("\n")
    relevant: list[str] = []
    capture = False
    for line in lines:
        if "[精准报价]" in line or f"({stock_code})" in line:
            capture = True
        if capture:
            relevant.append(line)
        # 捕获到 --- 或下一个 [ 标记就停
        if capture and (line.startswith("[新闻]") or line.startswith("[系统: 用户")):
            break
    if not relevant:
        # 降级：取全文本后 3000 字符
        relevant = text[-3000:].split("\n")
    return "\n".join(relevant[-60:])  # 最多 60 行


def _append_specialist_reports(answer: str, reports: dict[str, str]) -> str:
    """将四个专精 Agent 的报告以折叠卡片形式附加到主回答末尾，不修改主回答结构。"""
    from src.ai.prompts import AGENT_SPECIALISTS

    sections = []
    for key, spec in AGENT_SPECIALISTS.items():
        text = reports.get(key, "")
        if not text or "暂不可用" in text:
            continue
        sections.append(
            f"\n<details><summary>{spec['icon']} {spec['name']}专精分析</summary>\n\n{text}\n</details>\n"
        )
    if not sections:
        return answer
    return answer + "\n\n---\n## 🔬 多维度交叉分析\n" + "\n".join(sections)


class AIChat:
    def __init__(self):
        api_key = get_setting("api_key","DEEPSEEK_API_KEY","")
        base_url = get_setting("base_url","DEEPSEEK_BASE_URL","https://api.deepseek.com")
        self.model = get_setting("model","DEEPSEEK_MODEL","deepseek-chat")
        self.client = None
        self.client_label = ""  # "deepseek" / "mimo" / ""
        self._fallback_client = None  # 备选：Mimo
        self._fallback_model = ""
        self._fallback_label = ""

        status = self.provider_status(api_key=api_key, base_url=base_url, model=self.model)
        if status.get("ready"):
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)
                self.client_label = "deepseek"
            except Exception as e:
                logger.error(f"AI init: {e}")

        # 初始化备选 AI 客户端（DeepSeek 失败时自动切换）
        from src.config import MIMO_API_KEY, MIMO_BASE_URL, MIMO_MODEL
        mimo_key = MIMO_API_KEY or os.getenv("MIMO_API_KEY", "")
        mimo_url = MIMO_BASE_URL or os.getenv("MIMO_BASE_URL", "")
        mimo_model = MIMO_MODEL or os.getenv("MIMO_MODEL", "")
        if mimo_key and mimo_url and mimo_model:
            try:
                from openai import OpenAI
                self._fallback_client = OpenAI(api_key=mimo_key, base_url=mimo_url, timeout=30)
                self._fallback_model = mimo_model
                self._fallback_label = "mimo"
                logger.info("Mimo 备选 AI 客户端已就绪")
            except Exception as e:
                logger.warning(f"Mimo 备选客户端初始化失败: {e}")
        self.history = []
        self.tool_executor = ToolExecutor()
        self._tools_used = []
        self._memory = None
        self._active_session_key = None
        # Phase 4.1: 多轮对话上下文
        self._last_stock: str | None = None
        self._conversation_context: dict = {}
        self._request_evidence = self._empty_request_evidence()

    @classmethod
    def provider_status(cls, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> dict:
        """DeepSeek/OpenAI-compatible API 配置状态。

        只检查本地配置是否足以发起 API 调用，不做网络探测，避免打开页面就消耗额度。
        """
        api_key = api_key if api_key is not None else get_setting("api_key", "DEEPSEEK_API_KEY", "")
        base_url = base_url if base_url is not None else get_setting("base_url", "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = model if model is not None else get_setting("model", "DEEPSEEK_MODEL", "deepseek-chat")

        clean_key = str(api_key or "").strip()
        clean_url = str(base_url or "").strip()
        clean_model = str(model or "").strip()
        lowered = clean_key.lower()
        placeholder_tokens = ("placeholder", "test", "example", "your_key", "sk-xxx", "sk-...")

        if not clean_key:
            ready = False
            message = "未配置 DeepSeek API Key，AI 会进入本地兜底。"
        elif any(token in lowered for token in placeholder_tokens):
            ready = False
            message = "API Key 看起来是测试/占位值，请在“我的”页面保存真实 DeepSeek Key。"
        elif not clean_url.startswith(("http://", "https://")):
            ready = False
            message = "Base URL 格式不正确，必须以 http:// 或 https:// 开头。"
        elif not clean_model:
            ready = False
            message = "模型名为空，请配置 deepseek-chat 或兼容模型。"
        else:
            ready = True
            message = "DeepSeek API 已配置，AI 会优先调用云端模型；本地兜底只在 API 失败时启用。"

        return {
            "provider": "deepseek",
            "ready": ready,
            "base_url": clean_url,
            "model": clean_model,
            "has_api_key": bool(clean_key),
            "key_tail": clean_key[-4:] if clean_key and ready else "",
            "message": message,
        }

    def chat(self, user_message: str, context: dict = None) -> str:
        # 每轮独立保存已取得证据，最终回答校验时复用，避免重复消耗 iFinD 额度。
        self._request_evidence = self._empty_request_evidence()
        display_message = self._user_query_segment(user_message)
        model_message = user_message
        if not self.client:
            scene = self.detect_scene(display_message)
            stock_code = self._extract_stock_code(display_message)
            resolved_query = self._resolve_pronouns(display_message, stock_code)
            if resolved_query != display_message:
                model_message = resolved_query + model_message[len(display_message):]
                stock_code = self._extract_stock_code(resolved_query)
            run_id, scratchpad = self._start_audit(display_message, scene)
            session_id = self._save_user_message(display_message, scene, stock_code)
            local_answer = self._fallback_answer(resolved_query)
            return self._finalize_response(
                display_message,
                self._api_down_fallback_message(local_answer, "API Key 未配置"),
                session_id,
                stock_code,
                scene,
                scratchpad,
                run_id,
            )

        try:
            scene = self.detect_scene(display_message)
            stock_code = self._extract_stock_code(display_message)
            resolved_query = self._resolve_pronouns(display_message, stock_code)
            if resolved_query != display_message:
                model_message = resolved_query + model_message[len(display_message):]
            if not stock_code:
                stock_code = self._extract_stock_code(resolved_query)
            from src.data.stock_list import extract_stock_references

            allowed_stock_codes = extract_stock_references(resolved_query)
            run_id, scratchpad = self._start_audit(display_message, scene)
            session_id = self._save_user_message(display_message, scene, stock_code)
            messages = [{"role":"system","content":self.build_system_prompt(scene, display_message)}]
            subject_lock = self._subject_lock(stock_code)
            if subject_lock:
                messages.append({"role": "system", "content": subject_lock})
            for h in self._history_for_request(stock_code, display_message):
                messages.append({"role":"user","content":h["question"]})
                messages.append({"role":"assistant","content":h["answer"]})
            messages.append({"role":"user","content":model_message})

            # 实时行情护栏：紧贴当前问题注入最新行情，权重压过历史里的旧价格
            # 解决"AI照抄自己历史回答里的旧价格"问题
            if stock_code:
                live_guard = self._live_quote_guard(stock_code)
                if live_guard:
                    messages.append({"role": "system", "content": live_guard})

            self._tools_used = []
            answer = ""
            tool_result_cache: dict[str, str] = {}

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
                            display_message,
                            answer + f"\n\n*(部分工具调用失败: {err_msg})*",
                            session_id,
                            stock_code,
                            scene,
                            scratchpad,
                            run_id,
                        )
                    # Fallback: 第一轮 DeepSeek 失败 → 尝试切换到 Mimo 备选
                    if rnd == 0 and self._fallback_client:
                        try:
                            fb_resp = self._fallback_client.chat.completions.create(
                                model=self._fallback_model,
                                messages=messages + [{"role":"user","content":"请基于已有信息直接回答，不需要调用工具。"}],
                                temperature=0.35, max_tokens=MAX_TOKENS, timeout=30)
                            fb = fb_resp.choices[0].message.content or ""
                            if fb:
                                self.client = self._fallback_client
                                self.model = self._fallback_model
                                self.client_label = self._fallback_label
                                logger.info(f"DeepSeek 不可用，已切换到 {self._fallback_label} 备选模型")
                                return self._finalize_response(
                                    display_message,
                                    fb + f"\n\n*(DeepSeek 暂不可用，已自动切换至 {self._fallback_label.upper()} 备选模型)*",
                                    session_id, stock_code, scene, scratchpad, run_id)
                        except Exception as fb_err:
                            logger.warning(f"Mimo 备选也失败: {fb_err}")
                    # Fallback: try without tools
                    try:
                        fallback = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages + [{"role":"user","content":"请基于已有信息直接回答，不需要调用工具。"}],
                            temperature=0.35, max_tokens=MAX_TOKENS//2, timeout=15)
                        fb = fallback.choices[0].message.content or ""
                        if fb:
                            return self._finalize_response(
                                display_message,
                                fb + "\n\n*(部分工具不可用，基于存量知识回答)*",
                                session_id,
                                stock_code,
                                scene,
                                scratchpad,
                                run_id,
                            )
                    except Exception:
                        pass
                    local_answer = self._fallback_answer(resolved_query)
                    return self._finalize_response(
                        display_message,
                        self._api_down_fallback_message(local_answer, err_msg),
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
                    args, guard_error = self._guard_tool_arguments(
                        nm,
                        args,
                        allowed_stock_codes=allowed_stock_codes,
                    )
                    if guard_error:
                        result = json.dumps({"error": guard_error}, ensure_ascii=False)
                    else:
                        cache_key = json.dumps([nm, args], ensure_ascii=False, sort_keys=True, default=str)
                        if cache_key in tool_result_cache:
                            result = tool_result_cache[cache_key]
                        else:
                            try:
                                result = self.tool_executor.execute(nm, args)
                            except Exception:
                                result = json.dumps({"error": f"工具 {nm} 执行失败"}, ensure_ascii=False)
                            tool_result_cache[cache_key] = result
                    self._capture_tool_evidence(nm, result)
                    self._log_audit_tool(scratchpad, run_id, nm, args, result)

                    messages.append({"role":"tool","tool_call_id":tc.id,"content":result})
            else:
                if not answer:
                    answer = self._fallback_answer(resolved_query)

            if not answer:
                answer = self._fallback_answer(resolved_query)

            # 多 Agent 并行分析：个股场景时四个专精 Agent 同时跑，基于系统上下文交叉分析
            if stock_code and answer and scene in ("deep_analysis", "quick_judge", "general"):
                specialist_reports = self._run_specialist_agents(
                    stock_code,
                    _build_specialist_context(model_message, stock_code),
                )
                if specialist_reports:
                    answer = _append_specialist_reports(answer, specialist_reports)

            # Phase 1.1-opt: 结构化输出增强 — 对个股分析尝试格式化渲染
            if stock_code and answer and scene in ("deep_analysis", "quick_judge", "general"):
                answer = self._enrich_structured_output(answer, stock_code, scene, messages)

            return self._finalize_response(
                display_message, answer, session_id, stock_code, scene, scratchpad, run_id
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
            primary = AIChat._dynamic_top_sector_picks(groups)[0]
            chip = AIChat._dynamic_top_sector_picks(groups)[1]

            return (
                f"### 人话结论\n"
                f"机会分 64（机会分=当前方向值得研究的程度），风险分 58（风险分=追高或冲高回落的概率），置信度 中（置信度=公开数据够初筛但仍需盘中确认）。1 万做短线，我会先偏电力做防守模拟，半导体只做弹性观察。电力看 {primary} 这类承接稳的，半导体看 {chip} 这类主线弹性，但不能追高。\n\n"
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

        # 通用兜底 - 带今日大盘和领涨样本
        overview = AIChat._safe_market_overview()
        hot = AIChat._safe_top_stocks("changepercent", False, 5)
        idx_rows = "\n".join(
            f"| {i.get('name','')} | {i.get('price',0):.2f} | {i.get('change_pct',0):+.2f}% |"
            for i in (overview.get("indices") or [])[:3]
        ) or "| 暂无 | 0.00 | 0.00% |"
        hot_rows = "\n".join(AIChat._format_stock_row(s) for s in hot[:5]) or "| 暂无 | 0.00 | 0.00% | 0.0% | 0.0亿 |"
        return (
            "## 今日大盘\n\n| 指数 | 点位 | 涨跌幅 |\n|---|---|---|\n"
            f"{idx_rows}\n\n"
            "## 今日领涨\n\n| 股票 | 价格 | 涨跌幅 | 换手 | 成交额 |\n|---|---:|---:|---:|---:|\n"
            f"{hot_rows}\n\n"
            "## 下一步\n\n"
            "AI模型暂不可用，以上行情来自腾讯/新浪实时接口。你可以:\n"
            "- 输入股票代码(如601600)查看个股详情和K线\n"
            "- 到雷达页查看今日候选池\n"
            "- 等模型恢复后重新提问获取完整分析\n"
        )

    @staticmethod
    def _api_down_fallback_message(local_answer: str, error_detail: str = "") -> str:
        """模型服务异常时仍给本地研究框架，不让用户只看到死错误。"""
        detail = (error_detail or "").strip()[:160]
        return (
            "## 模型服务暂时不可用，本地兜底研究已启用\n"
            "| 项目 | 状态 | 白话解释 |\n"
            "|---|---|---|\n"
            "| DeepSeek / 模型 API | 暂不可用 | 可能是接口临时波动、Key/额度/模型配置问题，当前不能调用大模型生成深度文本 |\n"
            "| 本地兜底研究 | 已启用 | AlphaEye 会先用本地规则、公开行情框架和风险纪律给你一个可执行的研究底稿 |\n"
            f"| 错误详情 | {detail or '未返回具体错误'} | 这是技术状态，不代表股票没有机会或没有风险 |\n\n"
            "下面是本地兜底研究结果。它比完整 AI 报告保守，置信度默认较低，适合先观察/模拟，不适合直接行动。\n\n"
            f"{local_answer}"
        )

    @staticmethod
    def _metric_glossary() -> str:
        return (
            "| 指标 | 白话解释 | 怎么用 |\n"
            "|---|---|---|\n"
            "| 机会分 | 上涨条件、热度、承接、题材共振的综合程度 | 高不等于可以买，还要看风险分 |\n"
            "| 风险分 | 追高、诱多、冲高回落、数据缺失导致误判的概率 | 越高越要等回踩或直接放弃 |\n"
            "| 置信度 | 当前数据是否足够支撑结论 | 低置信度只能观察或模拟验证 |"
        )

    @staticmethod
    def _short_error(error_detail: str = "") -> str:
        return (error_detail or "未返回具体错误").strip()[:160]

    @classmethod
    def _model_down_intro(cls, task_name: str, error_detail: str = "") -> str:
        return (
            f"## 模型服务暂时不可用，本地{task_name}已启用\n"
            "| 项目 | 状态 | 白话解释 |\n"
            "|---|---|---|\n"
            "| DeepSeek / 模型 API | 暂不可用 | 当前无法调用大模型，所以不会硬编深度判断 |\n"
            f"| 本地{task_name} | 已启用 | 用公开数据、规则框架和风险纪律先生成保守底稿 |\n"
            f"| 错误详情 | {cls._short_error(error_detail)} | 这是技术状态，不代表股票本身没有机会或风险 |\n\n"
        )

    @staticmethod
    def _safe_market_overview() -> dict:
        try:
            from src.data.realtime import get_market_overview

            return get_market_overview() or {}
        except Exception:
            return {}

    @staticmethod
    def _safe_top_stocks(sort_field: str = "changepercent", asc: bool = False, limit: int = 8) -> list:
        try:
            from src.data.realtime import get_top_stocks

            return get_top_stocks(sort_field, asc, limit) or []
        except Exception:
            return []

    @staticmethod
    def _safe_quote_line(code: str) -> dict:
        try:
            from src.data.realtime import get_realtime_quote
            from src.data.stock_list import resolve_stock_name

            quote = get_realtime_quote(code) or {}
            return {
                "code": code,
                "name": resolve_stock_name(code, quote.get("name", "")),
                "price": quote.get("price", 0) or 0,
                "change_pct": quote.get("change_pct", 0) or 0,
                "turnover": quote.get("turnover", 0) or 0,
                "amount": quote.get("amount", 0) or 0,
            }
        except Exception:
            try:
                from src.data.stock_list import resolve_stock_name

                name = resolve_stock_name(code, code)
            except Exception:
                name = code
            return {"code": code, "name": name, "price": 0, "change_pct": 0, "turnover": 0, "amount": 0}

    @staticmethod
    def _format_stock_row(item: dict) -> str:
        amount = (item.get("amount", 0) or 0) / 1e8
        return (
            f"| {item.get('name', item.get('code', ''))}({item.get('code', '')}) "
            f"| {item.get('price', 0):.2f} | {item.get('change_pct', 0):+.2f}% "
            f"| {item.get('turnover', 0):.1f}% | {amount:.1f}亿 |"
        )

    def _local_morning_briefing(self, error_detail: str = "") -> str:
        overview = self._safe_market_overview()
        indices = overview.get("indices") or []
        hot = self._safe_top_stocks("changepercent", False, 6)
        idx_rows = [
            f"| {i.get('name', '指数')} | {i.get('price', 0):.2f} | {i.get('change_pct', 0):+.2f}% |"
            for i in indices[:4]
        ] or ["| 暂无 | 0.00 | 0.00% |"]
        hot_rows = [self._format_stock_row(s) for s in hot[:6]] or ["| 暂无 | 0.00 | 0.00% | 0.0% | 0.0亿 |"]
        return (
            self._model_down_intro("盘前/盘中简报", error_detail)
            +
            "## 结论摘要\n"
            "机会分 50（机会分=今天值得出手的市场条件），风险分 60（风险分=追高或误判概率），置信度 低到中（置信度=当前公开数据完整度）。模型不可用时，今天默认只做观察和模拟，不做激进追涨。\n\n"
            "## 指标说明\n"
            f"{self._metric_glossary()}\n\n"
            "## 大盘快照\n"
            "| 指数 | 点位 | 涨跌幅 |\n"
            "|---|---:|---:|\n"
            + "\n".join(idx_rows)
            + "\n\n## 热度样本\n"
            "| 股票 | 价格 | 涨跌幅 | 换手 | 成交额 |\n"
            "|---|---:|---:|---:|---:|\n"
            + "\n".join(hot_rows)
            + "\n\n## 今日纪律\n"
            "1. 第一波急拉不追，至少等一次回踩承接。\n"
            "2. 板块不联动的单票硬拉，只记录，不验证。\n"
            "3. 数据低置信度时，只能加入研究审计，不能当成买入理由。"
        )

    def _local_compare_stocks(self, code_a: str, code_b: str, error_detail: str = "") -> str:
        a = self._safe_quote_line(code_a)
        b = self._safe_quote_line(code_b)
        def rough_score(item: dict) -> tuple[int, int, str]:
            chg = item.get("change_pct", 0) or 0
            turnover = item.get("turnover", 0) or 0
            opportunity = max(30, min(78, int(50 + chg * 3 + min(turnover, 8))))
            risk = max(35, min(82, int(55 + max(chg - 3, 0) * 5 + max(turnover - 5, 0) * 2)))
            confidence = "中" if item.get("price", 0) else "低"
            return opportunity, risk, confidence
        ao, ar, ac = rough_score(a)
        bo, br, bc = rough_score(b)
        winner = a if (ao - ar * 0.35) >= (bo - br * 0.35) else b
        return (
            self._model_down_intro("个股对比", error_detail)
            +
            "## 结论摘要\n"
            f"{a['name']}({code_a}) 与 {b['name']}({code_b}) 只能做保守对比。当前更适合优先观察 {winner['name']}({winner['code']})，但必须等回踩承接，不能看到上涨就追。\n\n"
            "## 指标说明\n"
            f"{self._metric_glossary()}\n\n"
            "## 对比表\n"
            "| 股票 | 价格 | 涨跌幅 | 换手 | 机会分 | 风险分 | 置信度 | 白话结论 |\n"
            "|---|---:|---:|---:|---:|---:|---|---|\n"
            f"| {a['name']}({code_a}) | {a['price']:.2f} | {a['change_pct']:+.2f}% | {a['turnover']:.1f}% | {ao} | {ar} | {ac} | {'可观察' if ao >= 60 and ar < 70 else '等待确认'} |\n"
            f"| {b['name']}({code_b}) | {b['price']:.2f} | {b['change_pct']:+.2f}% | {b['turnover']:.1f}% | {bo} | {br} | {bc} | {'可观察' if bo >= 60 and br < 70 else '等待确认'} |\n\n"
            "## 反证与失效条件\n"
            "1. 高开急冲后跌回分时均价线下方。\n"
            "2. 放量但价格推不动，说明资金承接不足。\n"
            "3. 所在板块不联动，只有单票脉冲。\n"
            "4. 风险分高于机会分时，不做实盘动作，只保留观察。"
        )

    def _local_closing_summary(self, error_detail: str = "") -> str:
        overview = self._safe_market_overview()
        indices = overview.get("indices") or []
        up = self._safe_top_stocks("changepercent", False, 6)
        dn = self._safe_top_stocks("changepercent", True, 4)
        amt = self._safe_top_stocks("amount", False, 6)
        idx_rows = [
            f"| {i.get('name', '指数')} | {i.get('price', 0):.2f} | {i.get('change_pct', 0):+.2f}% |"
            for i in indices[:4]
        ] or ["| 暂无 | 0.00 | 0.00% |"]
        up_rows = [self._format_stock_row(s) for s in up[:6]] or ["| 暂无 | 0.00 | 0.00% | 0.0% | 0.0亿 |"]
        dn_rows = [self._format_stock_row(s) for s in dn[:4]] or ["| 暂无 | 0.00 | 0.00% | 0.0% | 0.0亿 |"]
        amt_rows = [self._format_stock_row(s) for s in amt[:6]] or ["| 暂无 | 0.00 | 0.00% | 0.0% | 0.0亿 |"]
        return (
            self._model_down_intro("收盘复盘", error_detail)
            +
            "## 今日盘面\n"
            "| 指数 | 点位 | 涨跌幅 |\n"
            "|---|---:|---:|\n"
            + "\n".join(idx_rows)
            + "\n\n## 领涨样本\n"
            "| 股票 | 价格 | 涨跌幅 | 换手 | 成交额 |\n"
            "|---|---:|---:|---:|---:|\n"
            + "\n".join(up_rows)
            + "\n\n## 领跌样本\n"
            "| 股票 | 价格 | 涨跌幅 | 换手 | 成交额 |\n"
            "|---|---:|---:|---:|---:|\n"
            + "\n".join(dn_rows)
            + "\n\n## 成交额样本\n"
            "| 股票 | 价格 | 涨跌幅 | 换手 | 成交额 |\n"
            "|---|---:|---:|---:|---:|\n"
            + "\n".join(amt_rows)
            + "\n\n## AI判断印证\n"
            "模型不可用时无法逐句重读完整推理，但系统仍保留了今日对话和研究审计记录。你明天应该重点看：今天高成交额股票是否延续、领涨方向是否有板块联动、领跌方向是否继续拖累情绪。\n\n"
            "## 明日计划\n"
            "1. 只从成交额和领涨样本里挑观察对象，低流动性票不碰。\n"
            "2. 机会分必须高于风险分，且风险分不能超过 65，才允许进入观察。\n"
            "3. 如果开盘 30 分钟没有承接，直接放弃，不做补仓摊平。"
        )

    def _local_account_diagnosis(self, error_detail: str = "") -> str:
        try:
            from src.trading.engine import TradingEngine

            with TradingEngine() as eng:
                acct = eng.get_account()
                if not acct:
                    account_text = "模拟盘账户未初始化。"
                    stats = {}
                    trades = []
                    positions = []
                else:
                    stats = eng.get_stats()
                    trades = eng.get_trades(50)
                    positions = eng.get_positions()
                    account_text = f"现金 {acct.cash:.0f}，持仓 {len(positions)} 只，连续亏损 {acct.consecutive_losses} 次。"
        except Exception as exc:
            account_text = f"账户数据读取失败：{str(exc)[:80]}"
            stats, trades, positions = {}, [], []

        sell_trades = [t for t in trades if getattr(t, "direction", "") == "sell"]
        wins = sum(1 for t in sell_trades if (getattr(t, "pnl", 0) or 0) > 0)
        losses = sum(1 for t in sell_trades if (getattr(t, "pnl", 0) or 0) < 0)
        win_rate = wins / max(len(sell_trades), 1) * 100
        return (
            self._model_down_intro("账户诊断", error_detail)
            +
            "## 本地账户诊断\n"
            f"{account_text}\n\n"
            "## 交易画像\n"
            "| 指标 | 当前值 | 白话解释 |\n"
            "|---|---:|---|\n"
            f"| 已平仓笔数 | {len(sell_trades)} | 样本太少时不要急着评价自己 |\n"
            f"| 胜率 | {win_rate:.1f}% | 胜率低不一定致命，关键是亏损单有没有被控制 |\n"
            f"| 当前持仓数 | {len(positions)} | 小资金持仓太多会分散注意力 |\n\n"
            "## 最大问题\n"
            "如果你最近亏损，优先检查三件事：有没有追第一波急拉、有没有跌破计划还不止损、有没有在高风险分时继续加仓。\n\n"
            "## 3个改进建议\n"
            "1. 每次 AI 给出“可观察”时，必须写入研究审计，记录触发条件和失效条件。\n"
            "2. 亏损单只允许复盘，不允许立刻用下一笔交易把亏损赚回来。\n"
            "3. 连续两次判断失败后，系统进入冷静模式，只允许观察/模拟/复盘。"
        )

    @staticmethod
    def _fallback_stock_report(code: str, user_message: str) -> str:
        """个股兜底 - 永远带实时行情+K线数据"""
        from src.data.realtime import get_realtime_quote, get_kline, get_market_overview
        from src.data.stock_list import resolve_stock_name

        q = get_realtime_quote(code) or {}
        price = q.get("price", 0) or 0
        chg = q.get("change_pct", 0) or 0
        chg_dir = "上涨" if chg > 0 else "下跌" if chg < 0 else "平盘"
        name = q.get("name") or resolve_stock_name(code, code)
        turnover = q.get("turnover", 0) or 0
        amount = (q.get("amount", 0) or 0) / 1e8
        vol_ratio = q.get("volume_ratio", 1.0) or 1.0
        open_p = q.get("open", 0) or 0
        high = q.get("high", 0) or 0
        low = q.get("low", 0) or 0
        pre_close = q.get("pre_close", 0) or 0
        src = q.get("source", "公开")

        kls, ma5, ma10, ma20, trend = [], "", "", "", ""
        supports, resistances = [], []
        try:
            kls = get_kline(code, period="101", count=20) or []
            if kls and len(kls) >= 5:
                closes = [k["close"] for k in kls]
                highs_k = [k["high"] for k in kls]
                lows_k = [k["low"] for k in kls]
                if len(closes) >= 5:
                    ma5 = f"{sum(closes[-5:])/5:.2f}"
                if len(closes) >= 10:
                    ma10 = f"{sum(closes[-10:])/10:.2f}"
                if len(closes) >= 20:
                    ma20 = f"{sum(closes[-20:])/20:.2f}"
                trend = "上升" if closes[-1] > closes[-5] else "下降" if closes[-1] < closes[-5] else "横盘"
                supports = sorted(set(round(x, 2) for x in lows_k[-10:] if x < price), reverse=True)[:3]
                resistances = sorted(set(round(x, 2) for x in highs_k[-10:] if x > price))[:3]
        except Exception:
            pass

        support_str = "、".join(str(s) for s in supports) if supports else "近期无明显支撑"
        resist_str = "、".join(str(r) for r in resistances) if resistances else "近期无明显阻力"

        market_note = ""
        try:
            ov = get_market_overview()
            for idx_item in (ov.get("indices") or [])[:1]:
                market_note = f"上证 {idx_item.get('price',0):.2f}（{idx_item.get('change_pct',0):+.2f}%）"
        except Exception:
            pass

        return (
            f"## {name}({code})\n\n"
            f"| 项目 | 数值 | 白话 |\n"
            f"|---|---|---|\n"
            f"| 现价 | **{price:.2f}元** | 今日{chg_dir}{abs(chg):.2f}% |\n"
            f"| 开盘/最高/最低 | {open_p:.2f}/{high:.2f}/{low:.2f} | 昨收 {pre_close:.2f} |\n"
            f"| 换手率 | {turnover:.2f}% | {'交投活跃' if turnover > 3 else '正常换手' if turnover > 1 else '低换手'} |\n"
            f"| 成交额 | {amount:.1f}亿 | {'放量' if vol_ratio > 1.2 else '缩量' if vol_ratio < 0.8 else '正常'}(量比{vol_ratio:.2f}) |\n"
            + (f"| MA5/MA10/MA20 | {ma5}/{ma10}/{ma20} | 短期趋势{trend} |\n" if ma5 else "")
            + (f"| 市场环境 | {market_note} |\n" if market_note else "")
            + f"| 数据质量 | 公开源({src}) | 腾讯/新浪免费行情 |\n\n"
            f"## 技术位参考\n\n"
            f"| 类型 | 价格区间 | 如何用 |\n"
            f"|---|---|---|\n"
            f"| 支撑位 | {support_str} | 观察回踩此处是否缩量企稳 |\n"
            f"| 阻力位 | {resist_str} | 反弹至此若放量滞涨需警惕 |\n\n"
            f"**注意**: 以上技术位来自近10日K线高低点，非买卖建议。AI模型暂不可用，此为本地规则计算，置信度较低。\n\n"
            f"## 反量化风险表\n\n"
            f"| 风险项 | 快速判断 | 应对 |\n"
            f"|---|---|---|\n"
            f"| 尾盘诱多 | {'⚠ 今日涨幅>5%需警惕' if chg > 5 else '✓ 未触发'} | 14:30后急拉不追 |\n"
            f"| 高位接盘 | {'⚠ 价格在近期阻力上方' if resistances and price > resistances[0] else '✓ 价格在阻力下方'} | 等回踩二次确认 |\n"
            f"| 分时脉冲 | 无法检测（缺少分时数据） | 不追第一波急拉 |\n"
            f"| 放量滞涨 | {'⚠ 量比>1.2但涨幅<1%，注意' if vol_ratio > 1.2 and abs(chg) < 1 else '✓ 未触发'} | 出现则放弃追高 |\n"
            f"| 板块背离 | 无法检测（缺少板块数据） | 同板块至少2只联动 |\n\n"
            f"## 操作建议\n\n"
            f"当前AI模型不可用，不能给出深度分析。基于现有数据建议:\n"
            f"1. 仅做观察/模拟验证，不实盘操作\n"
            f"2. 等模型恢复后重新请求完整分析\n"
            f"3. 手动检查板块联动和新闻催化\n"
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
    def _extract_capital_from_message(text: str) -> str:
        """从用户消息中提取真实资金量，不再硬写1万。"""
        import re
        m = re.search(r'(\d+[\d,.]*)\s*万', str(text or ""))
        if m:
            return f"{m.group(1)}万"
        m = re.search(r'(\d{4,})\s*元', str(text or ""))
        if m:
            val = int(m.group(1))
            if val >= 10000:
                return f"{val/10000:.0f}万"
            return f"{val}元"
        return ""

    @staticmethod
    def _dynamic_top_sector_picks(groups: list) -> tuple:
        """从实时行业候选中取前两名，替代硬编码的'长江电力/中芯国际'。
        如果实时数据不可用，开空窗让AI诚实说'暂无'而不编造。
        """
        first_name = "暂无实时数据"
        second_name = "暂无实时数据"
        for i, group in enumerate(groups or []):
            candidates = group.get("candidates", [])
            if candidates:
                c = candidates[0]
                name = f"{c.get('name', c.get('code', ''))}({c.get('code', '')})"
                if i == 0:
                    first_name = f"{group.get('name', '')} {name}"
                elif i == 1:
                    second_name = f"{group.get('name', '')} {name}"
                    break
        return first_name, second_name

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
        except Exception: pass

    def get_history(self): return self.history

    @staticmethod
    def _extract_stock_code(text: str) -> str:
        from src.data.stock_list import extract_stock_references

        # 只从用户原始问题提取，系统注入的上下文（用户画像600900等）会串线
        query = AIChat._user_query_segment(text)
        references = extract_stock_references(query)
        return references[0] if references else ""

    @staticmethod
    def _user_query_segment(message: str) -> str:
        """取页面注入系统上下文之前的用户原始问题。"""
        text = str(message or "")
        markers = ("\n[系统:", "\n[新闻]", "\n[用户画像]")
        cut = len(text)
        for marker in markers:
            pos = text.find(marker)
            if pos >= 0:
                cut = min(cut, pos)
        return text[:cut].strip()

    def _resolve_pronouns(self, user_message: str, current_stock_code: str) -> str:
        """Phase 4.1: 代词解析 — 把"它的风险呢"补全为"300033 它的风险呢"

        当用户输入含代词但无股票代码时，用 _last_stock 补全。
        """
        msg = (user_message or "").strip()
        if current_stock_code or not self._last_stock:
            return user_message or ""

        pronouns = ("它", "他", "她", "这只", "该股", "这股", "这票", "这个票")
        has_pronoun = any(p in msg for p in pronouns)

        if has_pronoun:
            from src.data.stock_list import normalize_stock_code, resolve_stock_name

            code = normalize_stock_code(self._last_stock)
            if code:
                name = resolve_stock_name(code, code)
                return f"{name}({code}) {msg}"
        return user_message or ""

    def _history_for_request(self, stock_code: str, user_message: str) -> list[dict]:
        """只带入同一标的的历史，避免跨股票回答串线。"""
        from src.data.stock_list import normalize_stock_code

        target = normalize_stock_code(stock_code)
        scoped = []
        for item in self.history[-HISTORY_LEN:]:
            item_code = normalize_stock_code(item.get("stock_code", ""))
            if not item_code:
                item_code = self._extract_stock_code(item.get("question", ""))
            if target:
                if item_code == target:
                    scoped.append(item)
            elif not item_code:
                scoped.append(item)
        return scoped

    @staticmethod
    def _guard_tool_arguments(
        tool_name: str,
        arguments: dict,
        allowed_stock_codes: list[str],
    ) -> tuple[dict, str]:
        """把个股工具锁定到本轮用户明确提到的标的。"""
        args = dict(arguments or {})
        if tool_name not in ToolExecutor._STOCK_CODE_TOOLS:
            return args, ""

        from src.data.stock_list import normalize_stock_code

        allowed = []
        for value in allowed_stock_codes or []:
            code = normalize_stock_code(value)
            if code and code not in allowed:
                allowed.append(code)
        if not allowed:
            return {}, "当前问题没有明确股票，已阻止随机个股工具调用"
        if len(allowed) == 1:
            args["code"] = allowed[0]
            return args, ""

        requested = normalize_stock_code(args.get("code", ""))
        if requested not in allowed:
            return {}, "工具请求的股票不在本轮明确标的中，已阻止调用"
        args["code"] = requested
        return args, ""

    @staticmethod
    def _subject_lock(stock_code: str) -> str:
        from src.data.stock_list import normalize_stock_code, resolve_stock_name

        code = normalize_stock_code(stock_code)
        if not code:
            return ""
        name = resolve_stock_name(code, code)
        return (
            "[本轮股票身份锁 · 最高优先级]\n"
            f"本轮唯一研究标的是 {name}({code})。\n"
            "不得把其他股票的名称、代码、行情、持仓、历史结论或工具结果混入回答。"
            "若历史内容与本标的不一致，必须忽略；所有个股工具只能查询该代码。"
        )

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
                    analysis_id = analysis.save_analysis(
                        stock_code=stock_code,
                        analysis_type=scene,
                        data=data,
                        message_id=message_id,
                    )
                    self._auto_create_research_audit(
                        analysis=analysis,
                        analysis_id=analysis_id,
                        stock_code=stock_code,
                        user_message=user_message,
                        answer=answer,
                        scene=scene,
                        structured=data,
                    )
        except Exception as exc:
            logger.warning(f"save ai message failed: {exc}")

    @staticmethod
    def _auto_create_research_audit(analysis, analysis_id: int, stock_code: str,
                                    user_message: str, answer: str, scene: str,
                                    structured: dict) -> None:
        """把 AI 的可观察判断自动转成研究审计，不再要求用户手动抄表。"""
        if not stock_code or not answer:
            return
        text = f"{user_message}\n{answer}"
        action = AIChat._extract_action_label(text)
        if not action:
            return

        if action in ("暂停", "放弃", "暂不碰"):
            return

        try:
            from src.data.stock_list import resolve_stock_name
            from src.data.realtime import get_realtime_quote

            quote = get_realtime_quote(stock_code)
            stock_name = resolve_stock_name(stock_code, quote.get("name", "") if quote else "")
        except Exception:
            stock_name = stock_code

        period = structured.get("suggested_holding_period") or AIChat._extract_period(answer)
        if not period:
            period = "1-2天" if action in ("可观察", "仅模拟") else "待触发"

        opportunity, risk_score, confidence = AIChat._extract_score_triplet(answer)
        risk_level = structured.get("risk_level") or AIChat._risk_level_from_score(risk_score)
        confidence_level = confidence or structured.get("confidence_level") or "中"

        hypothesis = AIChat._build_hypothesis_summary(
            stock_code=stock_code,
            stock_name=stock_name,
            action=action,
            opportunity=opportunity,
            risk_score=risk_score,
            confidence=confidence_level,
            answer=answer,
        )
        entry_conditions = AIChat._extract_section_items(answer, ["参与条件", "触发条件", "交易计划表"])[:5]
        invalidation = AIChat._extract_section_items(answer, ["反证与失效条件", "放弃条件", "退出", "失效条件"])[:5]
        if not entry_conditions:
            entry_conditions = ["回踩不破分时均价线", "板块联动不背离", "反量化风险不升至高/极高"]
        if not invalidation:
            invalidation = ["放量滞涨", "冲高回落跌破均价线", "板块不联动或大盘明显转弱"]

        analysis.create_verification(
            "ai_prediction",
            stock_code,
            stock_name,
            datetime.now(),
            strategy_name=f"AI研究审计/{scene}",
            suggested_period=period,
            source_id=analysis_id,
            hypothesis=hypothesis,
            entry_conditions=entry_conditions,
            invalidation_conditions=invalidation,
            stop_loss_rule=AIChat._extract_stop_rule(answer) or "只做观察/模拟验证；若 T+1 最大回撤超过 3% 记为高风险样本",
            risk_level=risk_level,
            confidence_level=confidence_level,
            allow_real_trade=False,
            max_loss_pct=3.0,
        )

    @staticmethod
    def _extract_action_label(text: str) -> str:
        for label in ("可观察", "仅模拟", "等待触发", "暂停", "放弃", "暂不碰"):
            if label in text:
                return label
        if "加入观察" in text:
            return "可观察"
        if "模拟验证" in text:
            return "仅模拟"
        return ""

    @staticmethod
    def _extract_score_triplet(text: str) -> tuple[int | None, int | None, str | None]:
        def num(pattern: str):
            m = re.search(pattern, text)
            return int(m.group(1)) if m else None
        opportunity = num(r"机会分\s*[:：]?\s*(\d{1,3})")
        risk = num(r"风险分\s*[:：]?\s*(\d{1,3})")
        cm = re.search(r"置信度\s*[:：]?\s*(高|中|低)", text)
        return opportunity, risk, cm.group(1) if cm else None

    @staticmethod
    def _risk_level_from_score(score: int | None) -> str:
        if score is None:
            return "中"
        if score >= 80:
            return "极高"
        if score >= 65:
            return "高"
        if score >= 45:
            return "中"
        return "低"

    @staticmethod
    def _extract_period(text: str) -> str:
        for period in ("隔夜", "1-2天", "2-3天", "3-5天", "不建议"):
            if period in text:
                return period
        return ""

    @staticmethod
    def _build_hypothesis_summary(stock_code: str, stock_name: str, action: str,
                                  opportunity: int | None, risk_score: int | None,
                                  confidence: str, answer: str) -> str:
        score_line = []
        if opportunity is not None:
            score_line.append(f"机会分{opportunity}")
        if risk_score is not None:
            score_line.append(f"风险分{risk_score}")
        score_line.append(f"置信度{confidence}")
        core = "，".join(score_line)
        first = next((line.strip() for line in answer.splitlines()
                      if line.strip() and not line.strip().startswith("|") and not line.strip().startswith("#")), "")
        return f"{stock_name}({stock_code}) AI结论为{action}，{core}。待审计假设：{first[:160]}"

    @staticmethod
    def _extract_section_items(text: str, section_names: list[str]) -> list[str]:
        items = []
        lines = text.splitlines()
        active = False
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            is_heading = line.startswith("#")
            if is_heading:
                active = any(name in line for name in section_names)
                continue
            if active:
                if line.startswith("|") and "---" not in line:
                    cells = [c.strip() for c in line.strip("|").split("|") if c.strip()]
                    if cells and cells[0] not in ("动作", "风险项", "维度"):
                        items.append(" / ".join(cells[:3]))
                elif re.match(r"^(\d+\.|-|•)", line):
                    items.append(re.sub(r"^(\d+\.|-|•)\s*", "", line))
                if len(items) >= 8:
                    break
        return [x[:120] for x in items if len(x) >= 3]

    @staticmethod
    def _extract_stop_rule(text: str) -> str:
        for raw in text.splitlines():
            line = raw.strip()
            if "止损" in line or "退出" in line:
                clean = re.sub(r"^[|\-\d\.\s]+", "", line).strip("| ")
                if 6 <= len(clean) <= 160:
                    return clean
        return ""

    def _enrich_structured_output(self, answer: str, stock_code: str, scene: str, messages: list) -> str:
        """用本地解析结果渲染结构化表格，不额外消耗一次模型 API。"""
        from src.ai.structured_output import parse_structured_output, format_structured_analysis

        # 步骤1：尝试从已有回答中提取结构化数据
        structured = parse_structured_output(answer)
        has_full_structure = (
            structured
            and structured.get("opportunity_score") is not None
            and structured.get("risk_score") is not None
        )

        if not has_full_structure:
            # 步骤2：尝试用 markdown 表格模式提取分数
            opp, risk, conf = self._extract_score_triplet(answer)
            if opp is not None and risk is not None:
                # 从文本中提取了分数，构建基本结构化数据
                structured = {
                    "stock_code": stock_code,
                    "stock_name": "",
                    "opportunity_score": opp,
                    "risk_score": risk,
                    "confidence": conf or "中",
                    "conclusion": self._extract_action_label(answer) or "观察",
                    "conclusion_reason": "",
                    "next_steps": "",
                    "core_risk": "",
                    "evidence": [],
                    "risks": [],
                    "trading_plan": [],
                    "invalidation_conditions": [],
                }

        # 用 parse_structured_output 的结果做基本表格渲染
        if structured and structured.get("opportunity_score") is not None:
            try:
                # 补充股票名称
                if not structured.get("stock_name"):
                    from src.data.stock_list import resolve_stock_name
                    structured["stock_name"] = resolve_stock_name(stock_code, stock_code)
                if not structured.get("stock_code"):
                    structured["stock_code"] = stock_code
                formatted_md = format_structured_analysis(structured)
                return formatted_md + "\n\n---\n## 📝 AI 完整分析原文\n\n" + answer
            except Exception as e:
                logger.debug(f"表格渲染失败: {e}")

        return answer

    def _finalize_response(self, user_message: str, answer: str,
                           session_id: int | None, stock_code: str, scene: str,
                           scratchpad, run_id: str | None) -> str:
        answer, guard_report = self._apply_answer_evidence_guard(
            answer=answer,
            user_message=user_message,
            stock_code=stock_code,
        )
        if guard_report:
            self._log_audit_tool(
                scratchpad,
                run_id,
                "answer_evidence_guard",
                {"stock_code": stock_code},
                guard_report,
            )

        # Phase 4.1: 追踪多轮对话上下文
        if stock_code:
            self._last_stock = stock_code
            self._conversation_context["last_stock"] = stock_code
            self._conversation_context["last_scene"] = scene
        self.history.append({
            "question": user_message,
            "answer": answer,
            "timestamp": datetime.now().isoformat(),
            "tools_used": self._tools_used.copy(),
            "stock_code": stock_code or "",
            "scene": scene,
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
    def _empty_request_evidence() -> dict:
        return {"quotes": {}, "positions": {}, "trades": []}

    def _capture_tool_evidence(self, tool_name: str, result) -> None:
        """把本轮工具结果保存为最终回答的硬校验证据。"""
        try:
            payload = json.loads(result) if isinstance(result, str) else result
            if not isinstance(payload, dict):
                return
            if tool_name == "get_stock_quote" and payload.get("code"):
                code = str(payload.get("code"))
                amount = payload.get("amount")
                if amount is None:
                    amount_text = str(payload.get("amount_display") or "")
                    match = re.search(r"(\d+(?:\.\d+)?)\s*亿", amount_text)
                    amount = float(match.group(1)) * 1e8 if match else 0
                quote = dict(payload)
                quote["amount"] = amount or 0
                quote["source"] = payload.get("data_source") or payload.get("source") or ""
                quote["_fallback"] = quote["source"] not in ("ifind", "")
                self._request_evidence.setdefault("quotes", {})[code] = quote
            elif tool_name == "get_positions":
                for item in payload.get("positions") or []:
                    code = str(item.get("code") or "")
                    if code:
                        self._request_evidence.setdefault("positions", {})[code] = dict(item)
        except Exception as exc:
            logger.debug(f"capture tool evidence failed: {exc}")

    def _apply_answer_evidence_guard(
        self,
        answer: str,
        user_message: str,
        stock_code: str,
    ) -> tuple[str, dict]:
        if not stock_code:
            return answer, {}
        try:
            from src.ai.evidence_guard import AnswerEvidenceGuard

            evidence = self._request_evidence or self._empty_request_evidence()
            quotes = evidence.setdefault("quotes", {})
            quote = quotes.get(stock_code)
            if not quote:
                from src.data.realtime import get_realtime_quote

                quote = get_realtime_quote(stock_code) or {}
                if quote:
                    quotes[stock_code] = quote

            positions = evidence.setdefault("positions", {})
            trades = evidence.setdefault("trades", [])
            if not positions.get(stock_code) or not trades:
                local_position, local_trades = self._load_local_trade_evidence(stock_code)
                if local_position and not positions.get(stock_code):
                    positions[stock_code] = local_position
                if local_trades and not trades:
                    trades.extend(local_trades)

            return AnswerEvidenceGuard().validate_and_rewrite(
                answer=answer,
                user_message=user_message,
                stock_code=stock_code,
                quote=quote,
                verified_position=positions.get(stock_code) or {},
                verified_trades=trades,
            )
        except Exception as exc:
            logger.warning(f"answer evidence guard failed {stock_code}: {exc}")
            return answer, {"error": str(exc)[:120], "stock_code": stock_code}

    def _run_specialist_agents(self, stock_code: str, context: str) -> dict[str, str]:
        """并行调用 4 个分角色 Agent，只分析系统注入的上下文，不调工具。

        返回 {"technical": "...", "fundamental": "...", "capital": "...", "risk": "..."}
        """
        results: dict[str, str] = {}
        if not self.client:
            return results

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _ask_specialist(key: str, spec: dict) -> tuple[str, str]:
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": f"你是 AlphaEye {spec['name']}专精分析师。\n\n{spec['prompt']}"},
                        {"role": "user", "content": f"以下是 {spec['name']} 相关的行情和评分数据，请基于这些数据分析，不要编造数据。\n\n{context}"},
                    ],
                    temperature=0.3, max_tokens=600, timeout=20,
                )
                return key, resp.choices[0].message.content or ""
            except Exception as e:
                logger.warning(f"Agent {spec['name']} 失败: {e}")
                return key, f"*{spec['name']}分析暂不可用*"

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_ask_specialist, key, spec): key
                for key, spec in AGENT_SPECIALISTS.items()
            }
            for future in as_completed(futures):
                key, text = future.result()
                results[key] = text

        return results

    @staticmethod
    def _load_local_trade_evidence(stock_code: str) -> tuple[dict, list]:
        """读取模拟盘持仓/交易，仅用于核验模型对用户交易行为的陈述。"""
        try:
            from src.trading.engine import TradingEngine

            with TradingEngine() as engine:
                position = next(
                    (item for item in engine.get_positions() if str(item.code) == stock_code),
                    None,
                )
                trades = [
                    {
                        "code": str(item.code),
                        "direction": item.direction,
                        "quantity": item.quantity,
                        "price": item.price,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    }
                    for item in engine.get_trades(limit=50)
                    if str(item.code) == stock_code
                ]
            position_data = {}
            if position:
                position_data = {
                    "code": str(position.code),
                    "quantity": position.quantity,
                    "cost_price": position.cost_price,
                    "buy_date": position.buy_date.isoformat() if position.buy_date else None,
                }
            return position_data, trades
        except Exception:
            return {}, []

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
    # Phase 2.2: 研究审计自动回填
    # ═══════════════════════════════════════

    @staticmethod
    def auto_backfill() -> dict:
        """每交易日收盘后自动回填待验证记录。

        对每条 status='pending' 的记录，用 iFinD/公开源 K线回填
        T+1/T+2/T+3 实际涨跌幅，达到 T+3 后自动判定准确/偏差。
        返回 {'processed': N, 'verified': N, 'errors': N}
        """
        result = {"processed": 0, "verified": 0, "errors": 0}
        try:
            from datetime import date, timedelta
            from src.memory.analysis_memory import AnalysisMemory
            from src.data.realtime import get_kline

            with AnalysisMemory() as analysis:
                pending = analysis.get_pending_verifications(limit=200)
                if not pending:
                    return result

                today = date.today()
                for rec in pending:
                    try:
                        predict_date = rec.get("predicted_at") or rec.get("created_at")
                        if isinstance(predict_date, str):
                            predict_date = datetime.fromisoformat(predict_date).date()
                        if isinstance(predict_date, datetime):
                            predict_date = predict_date.date()
                        if not predict_date:
                            continue

                        code = rec.get("code") or rec.get("stock_code")
                        if not code:
                            continue

                        # 获取 K线数据用于回填
                        from datetime import timedelta
                        start = (predict_date - timedelta(days=1)).strftime("%Y-%m-%d")
                        end = today.strftime("%Y-%m-%d")
                        try:
                            klines = get_kline(code, period="101", count=60)
                        except Exception:
                            klines = []

                        # 按日期索引
                        kline_map = {}
                        for k in klines:
                            kdate = (k.get("date") or "")[:10]
                            kline_map[kdate] = k

                        # 获取预测日的收盘价作为基准
                        pred_date_str = predict_date.strftime("%Y-%m-%d")
                        base_k = kline_map.get(pred_date_str)
                        base_close = base_k.get("close", 0) if base_k else 0

                        updated = False
                        for n in (1, 2, 3):
                            target_date = predict_date + timedelta(days=n)
                            # 跳过周末
                            while target_date.weekday() >= 5:
                                target_date += timedelta(days=1)
                            if target_date > today:
                                continue

                            target_k = kline_map.get(target_date.strftime("%Y-%m-%d"))
                            if not target_k:
                                continue

                            target_close = target_k.get("close", 0)
                            if base_close and target_close:
                                ret = (target_close - base_close) / base_close * 100
                                # 回填 T+N 收益率
                                analysis.update_verification_field(
                                    rec["id"], f"t{n}_return", round(ret, 2)
                                )
                                updated = True

                        if updated:
                            result["processed"] += 1

                        # T+3 到了就自动判定
                        t3_date = predict_date + timedelta(days=3)
                        while t3_date.weekday() >= 5:
                            t3_date += timedelta(days=1)
                        if today >= t3_date:
                            opp = rec.get("opportunity_score") or 0
                            risk = rec.get("risk_score") or 0
                            t3_ret = rec.get("t3_return") or 0
                            # 数值规则判定（AI 不参与）
                            if opp >= 70 and t3_ret > 5:
                                verdict = "机会判断准确"
                            elif risk >= 70 and t3_ret < -3:
                                verdict = "风险预警准确"
                            else:
                                verdict = "判断偏差"
                            analysis.update_verification_field(rec["id"], "result", verdict)
                            analysis.update_verification_field(rec["id"], "status", "verified")
                            result["verified"] += 1

                    except Exception:
                        result["errors"] += 1

        except Exception as e:
            logger.error(f"auto_backfill 失败: {e}")
            result["errors"] += 1

        return result

    # ═══════════════════════════════════════
    # 智能追问 & 场景检测 & 动态角色提示
    # ═══════════════════════════════════════

    def _live_quote_guard(self, stock_code: str) -> str:
        """生成实时行情护栏文本：紧贴当前问题注入，权重压过历史旧价格。

        解决 AI 照抄自己历史回答里旧价格的问题——明确给出当前真实行情，
        并指令 AI 忽略对话历史/记忆里的任何旧价格。
        """
        try:
            from src.data.realtime import get_realtime_quote
            from src.data.stock_list import resolve_stock_name
            q = get_realtime_quote(stock_code)
            if not q or not q.get("price"):
                return ""
            self._request_evidence.setdefault("quotes", {})[stock_code] = dict(q)
            name = q.get("name") or resolve_stock_name(stock_code, stock_code)
            price = q.get("price", 0)
            pct = q.get("change_pct", 0)
            turnover = q.get("turnover", 0) or 0
            amount = (q.get("amount", 0) or 0) / 1e8
            src = q.get("source", "")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return (
                f"[实时行情护栏 · 最高优先级 · 来源 {src} · {ts}]\n"
                f"{name}({stock_code}) 此刻实时行情：\n"
                f"现价={price:.2f}元 | 涨跌幅={pct:+.2f}% | 换手率={turnover:.2f}% | 成交额={amount:.1f}亿\n"
                f"\n"
                f"铁律（违反会导致回答数据错误）：\n"
                f"1. 你调工具后可能返回旧缓存里的K线/PE数据，那些基于几天前的旧价——已被本条护栏作废。"
                f"如果工具返回的K线价与本条 {price:.2f}元 明显不同，以护栏为准。\n"
                f"2. 回答中的价格只能是 {price:.2f}元。\n"
                f"3. 绝不说'复用缓存/复用底稿'来沿用旧价。\n"
                f"4. 护栏(新) > 工具缓存(旧)，护栏优先。"
            )
        except Exception as e:
            logger.warning(f"live_quote_guard 失败 {stock_code}: {e}")
            return ""

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
            return self._local_morning_briefing("API Key 未配置")
        try:
            from src.ai.prompts import V6_MORNING_PROMPT
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"system","content":V6_MORNING_PROMPT},
                          {"role":"user","content":"请生成今日盘前早报。"}],
                temperature=0.7, max_tokens=800, timeout=30)
            return resp.choices[0].message.content or "生成失败"
        except Exception as e:
            return self._local_morning_briefing(str(e))

    def compare_stocks(self, code_a: str, code_b: str) -> str:
        """对比两只股票"""
        if not self.client:
            return self._local_compare_stocks(code_a, code_b, "API Key 未配置")
        try:
            from src.ai.prompts import V6_COMPARE_PROMPT
            # 对比入口保持轻量，避免模型/数据源异常时被完整评分链拖住。
            qa = self._safe_quote_line(code_a)
            qb = self._safe_quote_line(code_b)
            ctx_a = (
                f"{qa['name']}({code_a}) 现价={qa['price']:.2f} "
                f"涨跌幅={qa['change_pct']:+.2f}% 换手={qa['turnover']:.1f}% "
                f"成交额={(qa['amount'] or 0)/1e8:.1f}亿"
            )
            ctx_b = (
                f"{qb['name']}({code_b}) 现价={qb['price']:.2f} "
                f"涨跌幅={qb['change_pct']:+.2f}% 换手={qb['turnover']:.1f}% "
                f"成交额={(qb['amount'] or 0)/1e8:.1f}亿"
            )
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
            return self._local_compare_stocks(code_a, code_b, str(e))

    # ═══════════════════════════════════════
    # 收盘总结
    # ═══════════════════════════════════════

    def closing_summary(self) -> str:
        """收盘总结 — 印证AI判断 + 真实数据驱动的明日规划"""
        if not self.client:
            return self._local_closing_summary("API Key 未配置")
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
            except Exception: pass

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
            return self._local_closing_summary(str(e))

    # ═══════════════════════════════════════
    # 账户诊断
    # ═══════════════════════════════════════

    def account_diagnosis(self) -> str:
        """分析用户的交易行为和账户表现"""
        if not self.client:
            return self._local_account_diagnosis("API Key 未配置")
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
            return self._local_account_diagnosis(str(e))

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
                except Exception: pass
            return ("完成", "\n".join(lines[:8]))
        except Exception as e:
            return ("错误", f"尾盘扫描失败: {e}")
