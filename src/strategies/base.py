"""
策略基类
每个策略必须有：硬门槛、加分项、扣分项、风险排除、回填验证指标
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class StrategyResult:
    strategy_name: str = ""
    suitability: str = "中"
    candidates: list = field(default_factory=list)
    current_phase: str = ""
    next_check_time: str = ""
    main_risks: list = field(default_factory=list)


class BaseStrategy(ABC):
    """短线策略基类"""

    name: str = "base"
    description: str = ""

    @abstractmethod
    def check_hard_filters(self, quote: dict, **context) -> tuple:
        ...

    @abstractmethod
    def compute_match(self, quote: dict, **context) -> dict:
        ...

    @abstractmethod
    def assess_suitability(self, market_snapshot: dict) -> str:
        ...

    def run(self, quote: dict, **context) -> StrategyResult:
        hard_pass, hard_fail = self.check_hard_filters(quote, **context)
        if not hard_pass:
            return StrategyResult(
                strategy_name=self.name,
                candidates=[{"code": quote.get("code"), "status": "排除",
                            "reasons": hard_fail}],
            )
        match = self.compute_match(quote, **context)
        return StrategyResult(
            strategy_name=self.name,
            suitability=self.assess_suitability(
                context.get("market_snapshot", {})),
            candidates=[{
                "code": quote.get("code"),
                "name": quote.get("name"),
                "match_score": match.get("match", 0),
                "status": match.get("status", ""),
                "details": match,
            }],
        )
