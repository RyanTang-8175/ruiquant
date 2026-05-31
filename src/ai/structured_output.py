"""v6 结构化输出解析 —— 从 AI 回复提取结构化字段"""

import json, re

EXPECTED_FIELDS = [
    "risk_level", "anti_quant_level", "suggested_holding_period",
    "status_label", "risk_points", "participation_conditions",
    "exit_conditions", "watch_points", "timeframe",
]


def parse_structured_output(text: str) -> dict:
    """从 AI 回复中提取结构化 JSON 或推断"""
    # 尝试 ```json 代码块
    m = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        try: return _validate(json.loads(m.group(1)))
        except: pass

    # 尝试裸 JSON
    m = re.search(r'\{[^{}]*"risk_level"[^{}]*\}', text, re.DOTALL)
    if m:
        try: return _validate(json.loads(m.group(0)))
        except: pass

    return _extract_from_text(text)


def _validate(data: dict) -> dict:
    out = {}
    for f in EXPECTED_FIELDS:
        out[f] = data.get(f)
    if out.get("risk_level"):
        rl = out["risk_level"]
        if rl not in ("低", "中", "高", "极高"):
            rl_map = {"low": "低", "medium": "中", "high": "高", "critical": "极高"}
            out["risk_level"] = rl_map.get(str(rl).lower(), "中")
    return out


def _extract_from_text(text: str) -> dict:
    out = {}
    for pat, level in [
        (r'风险等级[：:]\s*(极高)', "极高"),
        (r'风险等级[：:]\s*(高)', "高"),
        (r'风险等级[：:]\s*(中)', "中"),
        (r'风险等级[：:]\s*(低)', "低"),
    ]:
        if re.search(pat, text):
            out["risk_level"] = level; break

    for pat, period in [
        (r'[建议]*.*(2-3\s*天)', "2-3天"),
        (r'[建议]*.*(1-2\s*天)', "1-2天"),
        (r'[建议]*.*(隔夜)', "隔夜"),
        (r'[建议]*.*(不建议)', "不建议"),
    ]:
        if re.search(pat, text):
            out["suggested_holding_period"] = period; break

    return out
