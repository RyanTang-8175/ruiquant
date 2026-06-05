"""轻量研究知识库。

把每次 Harness 研究的摘要、证据源和结论写入 JSON 文件。它不是聊天记录，
而是跨 session 复用的研究经验：哪些问题查过、哪些方向需要回避、哪些数据源有效。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


class ResearchKnowledge:
    def __init__(self, path: str | Path | None = None):
        raw = path or os.getenv("ALPHAEYE_RESEARCH_KNOWLEDGE")
        self.path = Path(raw) if raw else Path(__file__).resolve().parents[2] / "data" / "research_knowledge.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record_run(self, payload: dict) -> None:
        data = self._load()
        runs = data.setdefault("runs", [])
        item = {
            "id": payload.get("fingerprint"),
            "kind": payload.get("kind", "research"),
            "code": payload.get("code"),
            "title": payload.get("title"),
            "quality": payload.get("quality", "unknown"),
            "evidence_keys": list((payload.get("evidence") or {}).keys()),
            "summary_cards": payload.get("summary_cards", [])[:6],
            "created_at": datetime.now().isoformat(),
        }
        if item["id"] and not any(r.get("id") == item["id"] for r in runs):
            runs.insert(0, item)
        data["runs"] = runs[:300]
        if item["id"] and payload.get("quality") == "low":
            dead_ends = data.setdefault("dead_ends", [])
            if not any(d.get("id") == item["id"] for d in dead_ends):
                dead_ends.insert(0, {
                    "id": item["id"],
                    "kind": item["kind"],
                    "code": item["code"],
                    "title": item["title"],
                    "reason": "证据块不足，后续同类问题应先补数据再下结论。",
                    "created_at": item["created_at"],
                })
            data["dead_ends"] = dead_ends[:100]
        data["insights"] = self._derive_insights(data["runs"])
        self._save(data)

    def recent_context(self, limit: int = 8) -> dict:
        data = self._load()
        return {
            "runs": data.get("runs", [])[:limit],
            "insights": data.get("insights", [])[:limit],
            "dead_ends": data.get("dead_ends", [])[:limit],
        }

    @staticmethod
    def _derive_insights(runs: list) -> list:
        counts = {}
        for run in runs:
            for key in run.get("evidence_keys", []):
                counts[key] = counts.get(key, 0) + 1
        insights = []
        for key, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            confidence = min(0.9, 0.35 + count * 0.08)
            insights.append({
                "topic": key,
                "summary": f"{key} 已在 {count} 次研究中提供证据，后续同类问题优先复用。",
                "confidence": round(confidence, 2),
            })
        return insights[:20]

    def _load(self) -> dict:
        if not self.path.exists():
            return {"runs": [], "insights": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"runs": [], "insights": [], "dead_ends": []}

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
