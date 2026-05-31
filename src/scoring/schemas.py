"""
六维评分数据模型
"""

from dataclasses import dataclass, field


@dataclass
class DimensionScore:
    """单个维度评分"""
    score: float = 50.0
    weight: float = 0.0
    sub_scores: dict = field(default_factory=dict)
    explanation: str = ""


@dataclass
class AntiQuantResult:
    """反量化扫描结果"""
    total_risk: float = 0.0
    risk_level: str = "低"
    late_day_lure: dict = field(default_factory=dict)
    high_position_trap: dict = field(default_factory=dict)
    intraday_pulse: dict = field(default_factory=dict)
    volume_stall: dict = field(default_factory=dict)
    sector_divergence: dict = field(default_factory=dict)
    penalty: float = 0.0
    triggers: list = field(default_factory=list)


@dataclass
class SixDimensionResult:
    """六维综合评分结果"""
    code: str = ""
    name: str = ""

    heat: DimensionScore = field(default_factory=DimensionScore)
    support: DimensionScore = field(default_factory=DimensionScore)
    theme: DimensionScore = field(default_factory=DimensionScore)
    continuation: DimensionScore = field(default_factory=DimensionScore)
    strategy_match: DimensionScore = field(default_factory=DimensionScore)
    anti_quant: AntiQuantResult = field(default_factory=AntiQuantResult)

    total_score: float = 50.0
    status_label: str = "可盯盘"
    risk_level: str = "中"

    matched_strategies: list = field(default_factory=list)
    dimension_details: dict = field(default_factory=dict)

    WEIGHTS = {
        "heat": 0.20, "support": 0.25, "theme": 0.20,
        "continuation": 0.15, "strategy_match": 0.20,
    }

    def compute_total(self):
        base = (
            self.heat.score * self.WEIGHTS["heat"]
            + self.support.score * self.WEIGHTS["support"]
            + self.theme.score * self.WEIGHTS["theme"]
            + self.continuation.score * self.WEIGHTS["continuation"]
            + self.strategy_match.score * self.WEIGHTS["strategy_match"]
        )
        self.total_score = max(0, min(100, base - self.anti_quant.penalty))

        risk = self.anti_quant.total_risk
        if self.anti_quant.risk_level == "极高" or risk >= 71:
            self.status_label = "不建议参与"
        elif any(getattr(self, d).score < 30 for d in ["heat", "support"]
                 if hasattr(self, d)):
            self.status_label = "已排除"
        elif risk >= 41:
            self.status_label = "风险偏高"
        elif self.total_score >= 70 and risk <= 40:
            self.status_label = "可执行"
        elif self.total_score >= 60:
            self.status_label = "等待确认"
        else:
            self.status_label = "可盯盘"

        self.risk_level = self.anti_quant.risk_level
        return self.total_score

    def to_dict(self) -> dict:
        return {
            "code": self.code, "name": self.name,
            "total_score": round(self.total_score, 1),
            "status_label": self.status_label,
            "risk_level": self.risk_level,
            "heat": {"score": round(self.heat.score, 1), "sub": self.heat.sub_scores},
            "support": {"score": round(self.support.score, 1), "sub": self.support.sub_scores},
            "theme": {"score": round(self.theme.score, 1), "sub": self.theme.sub_scores},
            "continuation": {"score": round(self.continuation.score, 1), "sub": self.continuation.sub_scores},
            "strategy_match": {"score": round(self.strategy_match.score, 1), "sub": self.strategy_match.sub_scores},
            "anti_quant": {
                "risk": round(self.anti_quant.total_risk, 1),
                "level": self.anti_quant.risk_level,
                "penalty": round(self.anti_quant.penalty, 1),
                "triggers": self.anti_quant.triggers,
            },
            "matched_strategies": self.matched_strategies,
            "dimension_details": self.dimension_details,
        }
