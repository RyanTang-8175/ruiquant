"""轻量策略探索与四档管理。

不是复杂回测系统，只用于把研究假设做成可审计的探索记录。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path


class StrategyGovernor:
    """根据证据评分、审计命中率和回撤给出四档动作。"""

    def decide(self, metrics: dict) -> dict:
        opportunity = float(metrics.get("opportunity_score") or 0)
        risk = float(metrics.get("risk_score") or 100)
        confidence = str(metrics.get("confidence") or "低")
        hit_rate = float(metrics.get("hit_rate") or 0)
        drawdown = float(metrics.get("drawdown") or 0)
        env_ok = bool(metrics.get("environment_match", True))

        if risk >= 78 or drawdown >= 10 or (hit_rate and hit_rate < 30) or not env_ok:
            tier = "正式下线"
            actions = ["停止配钱", "只允许复盘", "记录死路"]
            reason = "风险、回撤、命中率或环境匹配已经明显失真。"
        elif risk >= 65 or drawdown >= 6 or confidence == "低":
            tier = "主动降权"
            actions = ["降低关注权重", "只做小样本模拟", "等待复核"]
            reason = "异常开始累积，先把风险预算降下来。"
        elif opportunity >= 58 and risk <= 68:
            tier = "进入观察"
            actions = ["保持观察", "写入审计", "等待触发条件"]
            reason = "有研究价值，但还没有到放大验证的状态。"
        else:
            tier = "继续持有"
            actions = ["继续观察", "允许小幅加仓验证", "严格按失效条件退出"]
            reason = "表现仍在预期区间，结构和风险尚可。"

        if opportunity >= 68 and risk <= 58 and confidence in {"中", "高"} and hit_rate >= 55 and drawdown <= 5:
            tier = "继续持有"
            actions = ["继续持有", "加仓", "保留退出线"]
            reason = "机会、风险、置信度和历史验证都处在较好区间。"

        return {
            "tier": tier,
            "allowed_actions": actions,
            "reason": reason,
            "allow_real_trade": False,
            "metrics": {
                "opportunity_score": opportunity,
                "risk_score": risk,
                "confidence": confidence,
                "hit_rate": hit_rate,
                "drawdown": drawdown,
                "environment_match": env_ok,
            },
        }


class StrategyExplorer:
    """记录轻量参数探索，带指纹去重和覆盖率。"""

    def __init__(self, store_path: str | Path | None = None):
        self.store_path = Path(store_path) if store_path else Path(__file__).resolve().parents[2] / "data" / "strategy_explorer.json"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def sweep_filter_values(self, base_config: dict, dimension: str, values: list) -> dict:
        store = self._load()
        runs = store.setdefault("runs", [])
        known = {item.get("fingerprint") for item in runs}
        executed = []
        skipped = 0
        for value in values:
            config = dict(base_config or {})
            config[dimension] = value
            fp = self._fingerprint(config)
            if fp in known:
                skipped += 1
                continue
            result = self._score_config(config)
            item = {
                "fingerprint": fp,
                "config": config,
                "score": result["score"],
                "risk": result["risk"],
                "created_at": datetime.now().isoformat(),
            }
            runs.insert(0, item)
            known.add(fp)
            executed.append(item)
        store["runs"] = runs[:2000]
        store["coverage"] = self._coverage(store["runs"])
        self._save(store)
        return {
            "executed": len(executed),
            "skipped_duplicates": skipped,
            "results": executed,
            "coverage": store["coverage"],
            "top": sorted(store["runs"], key=lambda x: x.get("score", 0), reverse=True)[:10],
        }

    @staticmethod
    def _score_config(config: dict) -> dict:
        risk_limit = float(config.get("risk_limit") or 65)
        holding = str(config.get("holding") or "")
        score = 55 + max(0, 75 - risk_limit) * 0.25
        if "1-2" in holding:
            score += 4
        risk = max(20, min(90, risk_limit))
        return {"score": round(score, 1), "risk": round(risk, 1)}

    @staticmethod
    def _coverage(runs: list[dict]) -> dict:
        coverage = {}
        for item in runs:
            for key, value in (item.get("config") or {}).items():
                coverage.setdefault(key, set()).add(str(value))
        return {key: len(values) for key, values in coverage.items()}

    @staticmethod
    def _fingerprint(config: dict) -> str:
        raw = json.dumps(config, ensure_ascii=False, sort_keys=True)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _load(self) -> dict:
        if not self.store_path.exists():
            return {"runs": [], "coverage": {}}
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception:
            return {"runs": [], "coverage": {}}

    def _save(self, store: dict) -> None:
        self.store_path.write_text(json.dumps(store, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
