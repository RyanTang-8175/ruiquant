"""
v6 AI 角色定义 —— 温和提醒风格
"""

ROLES = {
    "risk_reviewer": {"name": "风险审查员", "desc": "审查追高、尾盘诱多、高位接盘等风险", "priority": 1},
    "short_term_researcher": {"name": "短线研究员", "desc": "资金流向、板块轮动、短线催化剂", "priority": 2},
    "holding_predictor": {"name": "持股预测员", "desc": "判断隔夜/1-2天/2-3天短持可能性", "priority": 2},
    "discipline_coach": {"name": "纪律教练", "desc": "提醒止盈、止损、放弃条件", "priority": 3},
    "review_analyst": {"name": "复盘分析师", "desc": "策略有效性、AI准确度、执行偏离", "priority": 3},
    "general_assistant": {"name": "普通问答助手", "desc": "市场知识、术语解释", "priority": 4},
}

ROLE_SUFFIXES = {
    "risk_reviewer": """
## 输出格式
1. 风险等级：低/中/高/极高
2. 反量化风险类型
3. 主要风险（≥2条）
4. 参与前必须确认的条件
5. 放弃条件
6. 数据缺失说明
语气：温和提醒。示例："当前风险偏高，若参与建议等待更明确的承接信号。"
""",
    "holding_predictor": """
## 输出格式
1. 建议周期：隔夜/1-2天/2-3天/不建议
2. 继续持有条件
3. 离场条件
4. 次日观察点
""",
}
