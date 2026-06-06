"""AI 最终回答的确定性证据校验。

提示词只能降低幻觉概率，不能保证模型一定遵守。这个模块在回答持久化和展示前，
用统一行情与可核验持仓事实纠正当前价、涨跌幅、换手率、成交额和交易行为陈述。
"""

from __future__ import annotations

import re
from datetime import datetime


class AnswerEvidenceGuard:
    """对模型最终文本做轻量、确定性的事实校验。"""

    _PRICE_PATTERN = re.compile(
        r"(?P<label>当前(?:价)?|现价|最新(?:收盘)?价|最新报价)"
        r"\s*(?:为|是|在|：|:)?\s*(?P<value>\d+(?:\.\d+)?)\s*元"
    )
    _CHANGE_PATTERN = re.compile(
        r"(?P<label>周[一二三四五六日天]|今日|今天|当前|最新交易日)"
        r"(?:收盘)?\s*(?:涨跌幅(?:为|是|：|:)?|上涨|下跌|跌|涨)"
        r"\s*(?P<value>[+-]?\d+(?:\.\d+)?)\s*%"
    )
    _TURNOVER_PATTERN = re.compile(
        r"(?P<label>当前换手率|换手率|换手)"
        r"\s*(?:为|是|：|:)?\s*(?P<value>\d+(?:\.\d+)?)\s*%"
    )
    _AMOUNT_PATTERN = re.compile(
        r"(?P<label>当前成交额|成交额|成交)"
        r"\s*(?:为|是|：|:)?\s*(?P<value>\d+(?:\.\d+)?)\s*亿"
    )
    _UNVERIFIED_TRADE_PATTERNS = (
        re.compile(
            r"(?:，|。)?(?:你|您)?(?:在)?"
            r"(?P<when>周[一二三四五六日天](?:收盘前|开盘后)?|今天|刚刚|刚才)"
            r"(?:还|又|已经)?(?P<action>加仓|减仓|买入|卖出)了"
        ),
        re.compile(
            r"(?:，|。)?(?:你|您)(?:刚刚|刚才|已经|又)"
            r"(?P<action>加仓|减仓|买入|卖出)了"
        ),
    )

    def validate_and_rewrite(
        self,
        answer: str,
        user_message: str,
        stock_code: str,
        quote: dict | None = None,
        verified_position: dict | None = None,
        verified_trades: list | None = None,
        validated_at: datetime | None = None,
    ) -> tuple[str, dict]:
        text = str(answer or "")
        quote = quote or {}
        verified_position = verified_position or {}
        verified_trades = verified_trades or []
        issues: list[str] = []
        checked_at = validated_at or datetime.now()

        price = self._num(quote.get("price"))
        change_pct = self._num(quote.get("change_pct"))
        turnover = self._num(quote.get("turnover"))
        amount = self._num(quote.get("amount"))

        if price > 0:
            text = self._replace_numeric_fact(
                text,
                self._PRICE_PATTERN,
                price,
                lambda match: f"{match.group('label')}{price:.2f}元",
                "当前价格",
                issues,
                tolerance=0.005,
                skip_when=self._is_non_current_context,
            )
        else:
            def remove_unverified_price(match: re.Match) -> str:
                issues.append(f"删除无可靠来源的当前价格：{match.group('value')}")
                return "当前价格暂无可靠数据"

            text = self._PRICE_PATTERN.sub(remove_unverified_price, text)
        if quote.get("change_pct") is not None:
            text = self._replace_numeric_fact(
                text,
                self._CHANGE_PATTERN,
                change_pct,
                lambda match: f"{match.group('label')}涨跌幅{change_pct:+.2f}%",
                "最新涨跌幅",
                issues,
                tolerance=0.01,
                skip_when=self._is_non_current_context,
            )
        if quote.get("turnover") is not None:
            text = self._replace_numeric_fact(
                text,
                self._TURNOVER_PATTERN,
                turnover,
                lambda _match: f"换手率{turnover:.2f}%",
                "当前换手率",
                issues,
                tolerance=0.01,
                skip_when=self._is_non_current_context,
            )
        if amount > 0:
            amount_yi = amount / 1e8
            text = self._replace_numeric_fact(
                text,
                self._AMOUNT_PATTERN,
                amount_yi,
                lambda _match: f"成交额{amount_yi:.1f}亿",
                "当前成交额",
                issues,
                tolerance=0.05,
                skip_when=self._is_non_current_context,
            )

        text = self._qualify_position_claim(
            text,
            user_message=user_message,
            verified_position=verified_position,
            issues=issues,
        )
        text = self._remove_unsupported_trade_claims(
            text,
            user_message=user_message,
            verified_trades=verified_trades,
            checked_at=checked_at,
            issues=issues,
        )

        source_label = self._source_label(quote)
        header = self._validation_header(
            stock_code=stock_code,
            quote=quote,
            source_label=source_label,
            checked_at=checked_at,
            issues=issues,
        )
        if header:
            text = f"{header}\n\n{text}".strip()

        report = {
            "corrected": bool(issues),
            "issues": issues,
            "stock_code": stock_code,
            "price": price or None,
            "change_pct": change_pct if quote.get("change_pct") is not None else None,
            "turnover": turnover if quote.get("turnover") is not None else None,
            "amount": amount or None,
            "source": source_label,
            "validated_at": checked_at.isoformat(),
        }
        return text, report

    @classmethod
    def _replace_numeric_fact(
        cls,
        text: str,
        pattern: re.Pattern,
        correct_value: float,
        replacement,
        issue_name: str,
        issues: list[str],
        tolerance: float,
        skip_when=None,
    ) -> str:
        def repl(match: re.Match) -> str:
            if skip_when and skip_when(match, text):
                return match.group(0)
            old = cls._num(match.group("value"))
            if abs(old - correct_value) > tolerance:
                issues.append(f"{issue_name}由 {old:g} 纠正为 {correct_value:g}")
            return replacement(match)

        return pattern.sub(repl, text)

    @staticmethod
    def _is_non_current_context(match: re.Match, text: str) -> bool:
        """避免把未来情景、条件句或明确历史区间改写成当前行情。"""
        prefix = text[max(0, match.start() - 40):match.start()]
        clause = re.split(r"[。！？!?\n；;]", prefix)[-1]
        return bool(
            re.search(
                r"(?:如果|若|假如|预计|可能|计划|目标|情景|"
                r"(?:19|20)\d{2}年|去年|前年|上月|上季度|"
                r"[一二三四]季度|Q[1-4]|历史|当时|过去)",
                clause,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _qualify_position_claim(
        text: str,
        user_message: str,
        verified_position: dict,
        issues: list[str],
    ) -> str:
        pattern = re.compile(r"(?<!按你本轮口述，)(?:你|您)持有(?P<qty>\d+(?:\.\d+)?万?)股")
        user_reported = bool(
            re.search(
                r"(?:手上|目前|现在)?.{0,8}(?:买了|持有|有).{0,8}"
                r"(?:\d+(?:\.\d+)?万?|[一二三四五六七八九十百千万]+)股",
                user_message or "",
            )
        )
        verified_qty = int(verified_position.get("quantity") or 0)

        def repl(match: re.Match) -> str:
            claimed = match.group("qty")
            if user_reported:
                issues.append("持仓数量已标注为用户口述")
                return f"按你本轮口述，你持有{claimed}股"
            if verified_qty > 0:
                issues.append("持仓数量已按模拟盘记录标注")
                return f"模拟盘记录显示你持有{verified_qty}股"
            issues.append("删除无证据持仓数量")
            return "当前没有可核验的持仓数量记录"

        return pattern.sub(repl, text)

    def _remove_unsupported_trade_claims(
        self,
        text: str,
        user_message: str,
        verified_trades: list,
        checked_at: datetime,
        issues: list[str],
    ) -> str:
        user_text = user_message or ""

        def has_verified_action(action: str, when: str) -> bool:
            direction = "buy" if action in ("加仓", "买入") else "sell"
            weekday_map = {
                "周一": 0,
                "周二": 1,
                "周三": 2,
                "周四": 3,
                "周五": 4,
                "周六": 5,
                "周日": 6,
                "周天": 6,
            }
            for item in verified_trades:
                if str(item.get("direction") or "").lower() != direction:
                    continue
                raw_time = item.get("created_at")
                try:
                    trade_time = datetime.fromisoformat(str(raw_time))
                except (TypeError, ValueError):
                    continue
                if when.startswith("周"):
                    target = next((day for label, day in weekday_map.items() if when.startswith(label)), None)
                    if target is not None and trade_time.weekday() == target:
                        return True
                elif when == "今天" and trade_time.date() == checked_at.date():
                    return True
                elif when in ("刚刚", "刚才"):
                    delta = checked_at - trade_time
                    if 0 <= delta.total_seconds() <= 2 * 3600:
                        return True
            return False

        for pattern in self._UNVERIFIED_TRADE_PATTERNS:
            def repl(match: re.Match) -> str:
                action = match.groupdict().get("action") or ""
                matched = match.group(0).strip("，。")
                when = match.groupdict().get("when") or "此前"
                if (
                    self._user_explicitly_reported_action(user_text, action, when)
                    or has_verified_action(action, when)
                ):
                    return match.group(0)
                issues.append(f"删除无证据交易行为：{matched}")
                return f"；关于是否在{when}{action}，当前没有可核验记录"

            text = pattern.sub(repl, text)
        return text

    @staticmethod
    def _user_explicitly_reported_action(user_text: str, action: str, when: str) -> bool:
        """只把明确完成的交易陈述当证据，疑问、计划和建议请求不算。"""
        text = str(user_text or "")
        if not action or action not in text:
            return False
        question_patterns = (
            rf"(?:是否|要不要|该不该|能不能|可不可以|建议|如何|怎么|准备|计划|想|考虑)"
            rf".{{0,10}}{re.escape(action)}",
            rf"{re.escape(action)}.{{0,10}}(?:吗|么|呢|？|\?)",
        )
        if any(re.search(pattern, text) for pattern in question_patterns):
            return False

        when_pattern = re.escape(when) if when and when != "此前" else r".{0,8}"
        affirmative_patterns = (
            rf"(?:我|本人).{{0,12}}{when_pattern}.{{0,8}}{re.escape(action)}"
            rf"(?:了|过|一笔|部分|一些|仓位)?",
            rf"(?:我|本人).{{0,12}}{re.escape(action)}.{{0,8}}{when_pattern}"
            rf"(?:了|过|一笔|部分|一些|仓位)?",
        )
        return any(re.search(pattern, text) for pattern in affirmative_patterns)

    @staticmethod
    def _source_label(quote: dict) -> str:
        source = str(quote.get("source") or quote.get("data_source") or "unknown").lower()
        fallback = bool(quote.get("_fallback"))
        if source == "ifind" and not fallback:
            return "iFinD"
        if source == "tencent":
            return "腾讯公开源兜底（iFinD 本次未成功返回该报价）"
        if source == "sina":
            return "新浪公开源兜底（iFinD 本次未成功返回该报价）"
        if fallback:
            return f"{source or '公开源'}兜底（iFinD 本次未成功返回该报价）"
        return source or "未知来源"

    @staticmethod
    def _validation_header(
        stock_code: str,
        quote: dict,
        source_label: str,
        checked_at: datetime,
        issues: list[str],
    ) -> str:
        price = AnswerEvidenceGuard._num(quote.get("price"))
        if price <= 0:
            return ""
        name = quote.get("name") or stock_code
        facts = [f"{price:.2f}元"]
        if quote.get("change_pct") is not None:
            pct = AnswerEvidenceGuard._num(quote.get("change_pct"))
            facts.append(f"涨跌幅{pct:+.2f}%")
        if quote.get("turnover") is not None:
            turnover = AnswerEvidenceGuard._num(quote.get("turnover"))
            facts.append(f"换手率{turnover:.2f}%")
        if quote.get("amount") is not None:
            amount = AnswerEvidenceGuard._num(quote.get("amount")) / 1e8
            facts.append(f"成交额{amount:.1f}亿")
        corrections = f"；已纠正 {len(issues)} 项冲突" if issues else ""
        return (
            f"> **数据硬校验**：{name}({stock_code}) 最新可用报价 "
            f"{'，'.join(facts)}；来源：{source_label}；"
            f"校验时间：{checked_at.strftime('%Y-%m-%d %H:%M')}{corrections}。"
        )

    @staticmethod
    def _num(value) -> float:
        try:
            if value in (None, "", "--"):
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0
