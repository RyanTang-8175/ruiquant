"""
AlphaEye Scratchpad。

每次 AI 深度研究都可以写入 JSONL 审计文件：用户问题、工具调用、工具结果摘要、
最终答案摘要。目的不是展示花哨思维链，而是保留可复盘的数据证据。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path


class Scratchpad:
    def __init__(self, root: str | Path | None = None):
        base = root or os.getenv("ALPHAEYE_SCRATCHPAD_DIR")
        if not base:
            base = Path(__file__).resolve().parents[2] / "data" / "scratchpad"
        self.root = Path(base)
        self.root.mkdir(parents=True, exist_ok=True)
        self._runs: dict[str, Path] = {}

    def start_run(self, question: str, scene: str = "general") -> str:
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        path = self.root / f"{run_id}.jsonl"
        self._runs[run_id] = path
        self._write(path, {
            "type": "run_start",
            "run_id": run_id,
            "scene": scene,
            "question": question,
            "timestamp": datetime.now().isoformat(),
        })
        return run_id

    def log_tool_result(self, run_id: str, tool_name: str, args: dict, result) -> None:
        path = self._path_for(run_id)
        self._write(path, {
            "type": "tool_result",
            "run_id": run_id,
            "tool_name": tool_name,
            "args": args or {},
            "result": self._compact(result),
            "timestamp": datetime.now().isoformat(),
        })

    def finish_run(self, run_id: str, answer_summary: str = "") -> str:
        path = self._path_for(run_id)
        self._write(path, {
            "type": "run_finish",
            "run_id": run_id,
            "answer_summary": answer_summary,
            "timestamp": datetime.now().isoformat(),
        })
        return str(path)

    def _path_for(self, run_id: str) -> Path:
        if run_id not in self._runs:
            self._runs[run_id] = self.root / f"{run_id}.jsonl"
        return self._runs[run_id]

    @staticmethod
    def _compact(value):
        if isinstance(value, str):
            text = value
            try:
                parsed = json.loads(value)
                return Scratchpad._compact(parsed)
            except Exception:
                return text[:4000]
        if isinstance(value, dict):
            return {k: Scratchpad._compact(v) for k, v in list(value.items())[:40]}
        if isinstance(value, list):
            return [Scratchpad._compact(v) for v in value[:30]]
        return value

    @staticmethod
    def _write(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
