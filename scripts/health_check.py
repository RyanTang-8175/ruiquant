"""
RuiQuant health check.

Verifies the local runtime can import core dependencies and project modules
before long-running data, scoring, AI, or scheduler work starts.
"""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REQUIRED_IMPORTS = [
    "requests",
    "streamlit",
    "sqlalchemy",
    "openai",
    "pandas",
    "numpy",
    "plotly",
    "apscheduler",
    "jwt",
    "pytest",
    "src.config",
    "src.utils.database",
    "src.data.realtime",
    "src.scoring.engine",
    "src.trading.engine",
    "src.ai.chat",
    "src.scheduler",
]


def check_imports() -> list[str]:
    failures = []
    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            failures.append(f"{module_name}: {exc}")
    return failures


def check_runtime_contracts() -> list[str]:
    failures = []

    from src.scoring.engine import ScoringEngine
    from src.trading.engine import TradingEngine

    if not hasattr(ScoringEngine, "get_watchlist"):
        failures.append("ScoringEngine.get_watchlist missing")
    if not hasattr(ScoringEngine, "save_scores"):
        failures.append("ScoringEngine.save_scores missing")
    if not hasattr(TradingEngine, "execute_buy"):
        failures.append("TradingEngine.execute_buy missing")
    if not hasattr(TradingEngine, "execute_sell"):
        failures.append("TradingEngine.execute_sell missing")

    return failures


def main() -> int:
    failures = check_imports() + check_runtime_contracts()
    if failures:
        print("HEALTH CHECK FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("HEALTH CHECK OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
