"""
AlphaEye AI 结构化输出 Schema v7
用于强制 AI 输出标准格式：机会分/风险分/置信度/表格化证据
"""

import json
import re
from typing import Dict, Any


# ═══════════════════════════════════════════════════════════
# 结构化分析 Schema - 用于 DeepSeek response_format
# ═══════════════════════════════════════════════════════════

STRUCTURED_ANALYSIS_SCHEMA = {
    "name": "stock_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "股票代码，如 300033.SZ"
            },
            "stock_name": {
                "type": "string",
                "description": "股票名称"
            },
            "opportunity_score": {
                "type": "integer",
                "description": "机会分 0-100"
            },
            "risk_score": {
                "type": "integer",
                "description": "风险分 0-100"
            },
            "confidence": {
                "type": "string",
                "enum": ["高", "中", "低"],
                "description": "置信度"
            },
            "conclusion": {
                "type": "string",
                "description": "总体结论：可观察/仅模拟验证/等待触发/暂停关注/放弃"
            },
            "conclusion_reason": {
                "type": "string",
                "description": "结论理由"
            },
            "next_steps": {
                "type": "string",
                "description": "我会怎么做：第一人称步骤"
            },
            "core_risk": {
                "type": "string",
                "description": "最核心风险"
            },
            "data_limitations": {
                "type": "string",
                "description": "数据局限性"
            },
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "dimension": {"type": "string"},
                        "metric": {"type": "string"},
                        "explanation": {"type": "string"},
                        "impact": {"type": "string", "enum": ["正面", "中性", "负面"]}
                    },
                    "required": ["dimension", "metric", "explanation", "impact"],
                    "additionalProperties": False
                }
            },
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "risk_type": {"type": "string"},
                        "level": {"type": "string", "enum": ["高", "中", "低"]},
                        "evidence": {"type": "string"},
                        "loss_scenario": {"type": "string"},
                        "countermeasure": {"type": "string"}
                    },
                    "required": ["risk_type", "level", "evidence", "loss_scenario", "countermeasure"],
                    "additionalProperties": False
                }
            },
            "trading_plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "stage": {"type": "string"},
                        "trigger": {"type": "string"},
                        "forbidden": {"type": "string"},
                        "position": {"type": "string"},
                        "review_field": {"type": "string"}
                    },
                    "required": ["stage", "trigger", "forbidden", "position", "review_field"],
                    "additionalProperties": False
                }
            },
            "invalidation_conditions": {
                "type": "array",
                "items": {"type": "string"}
            },
            "audit_hypothesis": {
                "type": "string",
                "description": "研究假设"
            },
            "audit_trigger": {
                "type": "string",
                "description": "触发条件"
            },
            "audit_invalid": {
                "type": "string",
                "description": "失效条件"
            },
            "audit_stop_loss": {
                "type": "string",
                "description": "止损规则"
            }
        },
        "required": [
            "stock_code", "stock_name", "opportunity_score", "risk_score",
            "confidence", "conclusion", "conclusion_reason", "next_steps",
            "core_risk", "evidence", "risks", "trading_plan", "invalidation_conditions"
        ],
        "additionalProperties": False
    }
}


# ═══════════════════════════════════════════════════════════
# 格式化函数 - 将 JSON 转换为 Markdown 表格
# ═══════════════════════════════════════════════════════════

def format_structured_analysis(data: Dict[str, Any]) -> str:
    """将结构化 JSON 转换为用户友好的 Markdown 表格格式"""
    output = []

    # 标题
    output.append("━" * 60)
    output.append(f"📊 {data.get('stock_name', '未知')} ({data.get('stock_code', '')}) 深度研究备忘录")
    output.append("━" * 60)
    output.append(f"更新时间: {_now_str()}\n")

    # 结论摘要
    opp = data.get('opportunity_score', 0)
    risk = data.get('risk_score', 0)
    conf = data.get('confidence', '中')

    output.append("## 💡 结论摘要\n")
    output.append(f"**机会分**: {opp}/100 ({'上涨条件充足' if opp >= 70 else '上涨条件一般' if opp >= 50 else '上涨条件不足'})")
    output.append(f"**风险分**: {risk}/100 ({'追高风险高' if risk >= 70 else '追高风险中' if risk >= 50 else '追高风险低'})")
    output.append(f"**置信度**: {conf} ({'数据完整' if conf == '高' else '数据基本够用' if conf == '中' else '数据不足'})")
    output.append(f"\n**结论**: {data.get('conclusion', '观察')}")
    output.append(f"**理由**: {data.get('conclusion_reason', '暂无')}\n")

    # 我会怎么做
    if data.get('next_steps'):
        output.append("## 🎯 我会怎么做\n")
        output.append(data['next_steps'])
        output.append("")

    # 数据局限
    if data.get('data_limitations'):
        output.append("## 📋 数据状态\n")
        output.append(f"**局限**: {data['data_limitations']}\n")

    # 证据表
    evidence = data.get('evidence', [])
    if evidence:
        output.append("## 📈 证据表 (支撑机会分的依据)\n")
        output.append("| 观察维度 | 数值指标 | 白话解释 | 对结论影响 |")
        output.append("|---------|---------|---------|-----------|")
        for ev in evidence:
            impact = ev.get('impact', '中性')
            icon = {"正面": "📈", "中性": "📊", "负面": "📉"}.get(impact, "📊")
            output.append(f"| {ev['dimension']} | {ev['metric']} | {ev['explanation']} | {icon} {impact} |")
        output.append("")

    # 反量化风险表
    risks = data.get('risks', [])
    if risks:
        output.append("## ⚠️ 反量化风险表 (支撑风险分的依据)\n")
        output.append("| 风险类型 | 等级 | 触发证据 | 散户容易亏损 | 应对策略 |")
        output.append("|---------|-----|---------|------------|---------|")
        for r in risks:
            output.append(f"| {r['risk_type']} | {r['level']} | {r['evidence']} | {r['loss_scenario']} | {r['countermeasure']} |")

        if data.get('core_risk'):
            output.append(f"\n**最核心风险**: {data['core_risk']}\n")

    # 交易计划表
    plan = data.get('trading_plan', [])
    if plan:
        output.append("## 📋 交易计划表\n")
        output.append("| 动作阶段 | 触发条件 | 禁止动作 | 仓位/方式 | 复盘字段 |")
        output.append("|---------|---------|---------|----------|---------|")
        for p in plan:
            output.append(f"| {p['stage']} | {p['trigger']} | {p['forbidden']} | {p['position']} | {p['review_field']} |")
        output.append("")

    # 反证与失效条件
    invalid = data.get('invalidation_conditions', [])
    if invalid:
        output.append("## 🔍 反证与失效条件\n")
        output.append("什么情况说明我的判断错了:\n")
        for i, cond in enumerate(invalid, 1):
            output.append(f"{i}. {cond}")
        output.append("")

    # 复盘入库
    if any([data.get('audit_hypothesis'), data.get('audit_trigger'), data.get('audit_invalid')]):
        output.append("## 📝 复盘入库建议\n")
        output.append("| 字段 | 内容 |")
        output.append("|------|------|")
        if data.get('audit_hypothesis'):
            output.append(f"| 研究假设 | {data['audit_hypothesis']} |")
        if data.get('audit_trigger'):
            output.append(f"| 触发条件 | {data['audit_trigger']} |")
        if data.get('audit_invalid'):
            output.append(f"| 失效条件 | {data['audit_invalid']} |")
        if data.get('audit_stop_loss'):
            output.append(f"| 止损规则 | {data['audit_stop_loss']} |")
        output.append("\n系统会自动在 T+1/T+2/T+3 回填实际表现。\n")

    output.append("━" * 60)
    output.append("💬 **追问建议**")
    output.append("━" * 60)
    output.append("• \"同行业还有哪些股票可以对比？\"")
    output.append("• \"如果明天开盘急跌该怎么办？\"")
    output.append(f"• \"{data.get('stock_name', '')}的最新公告有什么？\"")

    return "\n".join(output)


def _now_str() -> str:
    """当前时间字符串"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════
# 旧版兼容 - 从文本提取
# ═══════════════════════════════════════════════════════════

# 旧版结构化字段（供 DB/记忆层使用，从文本推断）
_EXPECTED_FIELDS = [
    "risk_level", "anti_quant_level", "suggested_holding_period",
    "status_label", "risk_points", "participation_conditions",
    "exit_conditions", "watch_points", "timeframe",
]


def parse_structured_output(text: str) -> dict:
    """从 AI 回复中提取结构化 JSON 或从文本推断（兼容旧版 DB/记忆层）"""
    # 尝试 ```json 代码块
    m = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        try:
            return _validate_legacy(json.loads(m.group(1)))
        except Exception:
            pass

    # 尝试裸 JSON（含 risk_level 字段）
    m = re.search(r'\{[^{}]*"risk_level"[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return _validate_legacy(json.loads(m.group(0)))
        except Exception:
            pass

    return _extract_from_text(text)


def _validate_legacy(data: dict) -> dict:
    out = {}
    for f in _EXPECTED_FIELDS:
        out[f] = data.get(f)
    if out.get("risk_level"):
        rl = out["risk_level"]
        if rl not in ("低", "中", "高", "极高"):
            rl_map = {"low": "低", "medium": "中", "high": "高", "critical": "极高"}
            out["risk_level"] = rl_map.get(str(rl).lower(), "中")
    return out


def _extract_from_text(text: str) -> dict:
    """从自然语言文本中提取风险等级、持有周期等关键字段"""
    out = {}
    for pat, level in [
        (r'风险等级[：:]\s*(极高)', "极高"),
        (r'风险等级[：:]\s*(高)', "高"),
        (r'风险等级[：:]\s*(中)', "中"),
        (r'风险等级[：:]\s*(低)', "低"),
    ]:
        if re.search(pat, text):
            out["risk_level"] = level
            break

    for pat, period in [
        (r'(2-3\s*天)', "2-3天"),
        (r'(1-2\s*天)', "1-2天"),
        (r'(隔夜)', "隔夜"),
        (r'(不建议)', "不建议"),
    ]:
        if re.search(pat, text):
            out["suggested_holding_period"] = period
            break

    return out
