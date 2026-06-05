"""研究复盘评估。

把审计回放记录整理成新旧评分对比、低质量方向和复盘结论。
"""

from __future__ import annotations


class ResearchEvaluator:
    """对研究审计结果做轻量归因。"""

    def compare_score_systems(self, verification_rows: list[dict]) -> dict:
        groups = {
            "ifind": {"total": 0, "hits": 0, "returns": []},
            "legacy": {"total": 0, "hits": 0, "returns": []},
            "unknown": {"total": 0, "hits": 0, "returns": []},
        }
        for row in verification_rows or []:
            key = self._score_family(row)
            groups[key]["total"] += 1
            for bf in row.get("backfills") or []:
                if bf.get("hit_2pct"):
                    groups[key]["hits"] += 1
                if bf.get("hold_1d") is not None:
                    groups[key]["returns"].append(float(bf.get("hold_1d") or 0))

        packed = {name: self._pack_stats(data) for name, data in groups.items()}
        ifind_rate = packed["ifind"]["hit_rate"]
        legacy_rate = packed["legacy"]["hit_rate"]
        winner = "ifind" if ifind_rate > legacy_rate else "legacy" if legacy_rate > ifind_rate else "tie"
        packed["winner"] = winner
        packed["summary"] = self._summary(packed)
        return packed

    @staticmethod
    def _score_family(row: dict) -> str:
        text = " ".join(str(row.get(k) or "") for k in ("strategy_name", "hypothesis", "source_type"))
        if "iFinD" in text or "ifind" in text or "新评分" in text or "Evidence" in text:
            return "ifind"
        if "旧评分" in text or "六维" in text or "legacy" in text:
            return "legacy"
        return "unknown"

    @staticmethod
    def _pack_stats(data: dict) -> dict:
        total = int(data.get("total") or 0)
        hits = int(data.get("hits") or 0)
        returns = data.get("returns") or []
        return {
            "total": total,
            "hits": hits,
            "hit_rate": round(hits / max(total, 1) * 100, 1),
            "avg_1d_return": round(sum(returns) / max(len(returns), 1), 2),
        }

    @staticmethod
    def _summary(report: dict) -> str:
        if report["winner"] == "ifind":
            return "iFinD 新评分在现有审计样本里更占优，继续作为主线并扩大样本。"
        if report["winner"] == "legacy":
            return "旧评分在现有审计样本里更占优，新评分需要降低权重并复查维度。"
        return "新旧评分暂未拉开差距，继续并行验证。"
