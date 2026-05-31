"""v6 AI 上下文构建器 —— 整合评分/记忆/策略"""

class AIContextBuilder:
    def __init__(self, stock_memory=None, scoring=None, analysis=None):
        self.stock_memory = stock_memory
        self.scoring = scoring
        self.analysis = analysis

    def build(self, user_message: str, stock_code: str = None) -> str:
        parts = []
        if stock_code:
            parts.append(self._stock_context(stock_code))
        parts.append(f"用户: {user_message}")
        return "\n\n".join(parts)

    def _stock_context(self, code: str) -> str:
        lines = [f"## {code}"]
        if self.scoring:
            try:
                ctx = self.scoring.build_ai_context(code)
                if ctx: lines.append(ctx)
            except: pass
        if self.stock_memory:
            try:
                mem = self.stock_memory.get_recent_memory_summary(code)
                if mem: lines.append(mem)
            except: pass
            try:
                risk = self.stock_memory.get_risk_profile(code)
                if risk and risk.get("avg_risk", 0) > 0:
                    lines.append(f"历史反量化风险: {risk['avg_risk']}/100 ({risk['risk_level']})")
            except: pass
        if self.analysis:
            try:
                analyses = self.analysis.get_analyses(code, limit=3)
                if analyses:
                    lines.append("最近AI分析:")
                    for a in analyses:
                        lines.append(f"- [{a['type']}] 风险{a['risk_level']} ({a['created_at'][:10]})")
            except: pass
        return "\n".join(lines)
