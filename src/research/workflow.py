"""文件化金融研究 SOP。

工作流层只组织已有 Research Harness 的证据，执行质量门、来源追踪和人工签核。
它不直接交易、不自动发布，也不允许模型自行把草稿标记为人工通过。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from src.research.harness import ResearchHarness


class ResearchWorkflowRegistry:
    """加载并校验文件化研究 playbook。"""

    REQUIRED = {
        "id",
        "name",
        "version",
        "kind",
        "description",
        "stages",
        "required_evidence",
        "quota_budget",
        "deliverables",
        "review_required",
    }

    def __init__(self, playbook_dir: str | Path | None = None):
        self.playbook_dir = (
            Path(playbook_dir)
            if playbook_dir
            else Path(__file__).resolve().parent / "playbooks"
        )

    def list(self) -> list[dict]:
        return [self._load(path) for path in sorted(self.playbook_dir.glob("*.json"))]

    def get(self, workflow_id: str) -> dict:
        for item in self.list():
            if item["id"] == workflow_id:
                return deepcopy(item)
        raise KeyError(f"未知研究工作流: {workflow_id}")

    def _load(self, path: Path) -> dict:
        payload = json.loads(path.read_text(encoding="utf-8"))
        missing = sorted(self.REQUIRED - set(payload))
        if missing:
            raise ValueError(f"{path.name} 缺少字段: {', '.join(missing)}")
        if not isinstance(payload["stages"], list) or not payload["stages"]:
            raise ValueError(f"{path.name} stages 必须是非空数组")
        if payload["review_required"] is not True:
            raise ValueError(f"{path.name} 必须要求人工复核")
        return payload


class WorkflowRunStore:
    """持久化工作流草稿和人工复核状态。"""

    _LOCK = threading.RLock()

    def __init__(self, path: str | Path | None = None):
        raw = path or os.getenv("ALPHAEYE_RESEARCH_WORKFLOW_PATH")
        self.path = (
            Path(raw)
            if raw
            else Path(__file__).resolve().parents[2] / "data" / "research_workflows.json"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, run: dict) -> dict:
        stored = deepcopy(run)
        if not str(stored.get("run_id") or "").strip():
            raise ValueError("工作流运行缺少 run_id")
        with self._LOCK:
            data = self._load()
            runs = data.setdefault("runs", [])
            runs = [item for item in runs if item.get("run_id") != stored["run_id"]]
            runs.insert(0, stored)
            data["runs"] = runs[:300]
            self._write(data)
        return stored

    def list(self, limit: int = 20) -> list[dict]:
        with self._LOCK:
            return deepcopy(
                self._load().get("runs", [])[: max(1, int(limit or 20))]
            )

    def get(self, run_id: str) -> dict:
        with self._LOCK:
            for item in self._load().get("runs", []):
                if item.get("run_id") == run_id:
                    return deepcopy(item)
        raise KeyError(f"未知工作流运行: {run_id}")

    def review(self, run_id: str, decision: str, notes: str = "") -> dict:
        if decision not in {"approved", "rejected"}:
            raise ValueError("人工复核只能是 approved 或 rejected")
        with self._LOCK:
            run = self.get(run_id)
            if decision == "approved" and not (run.get("quality_gate") or {}).get("passed"):
                raise ValueError("质量门未通过，不能标记为人工批准")
            run["review"] = {
                "status": decision,
                "notes": str(notes or "")[:1000],
                "reviewed_at": datetime.now().isoformat(),
                "reviewer": "human_ui",
            }
            return self.save(run)

    def _load(self) -> dict:
        if not self.path.exists():
            return {"runs": []}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {"runs": []}
        except Exception:
            return {"runs": []}

    def _write(self, payload: dict) -> None:
        temp = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        temp.replace(self.path)


class ResearchWorkflowRunner:
    """运行研究 SOP，并产出草稿、来源账本和质量门结果。"""

    FINANCIAL_EVENT_WORDS = (
        "年度报告",
        "半年度报告",
        "季度报告",
        "一季报",
        "三季报",
        "业绩预告",
        "业绩快报",
        "业绩说明会",
        "年报",
        "半年报",
    )

    def __init__(
        self,
        harness=None,
        registry: ResearchWorkflowRegistry | None = None,
        store_path: str | Path | None = None,
    ):
        self.harness = harness or ResearchHarness()
        self.registry = registry or ResearchWorkflowRegistry()
        self.store = WorkflowRunStore(store_path)

    def preview(self, workflow_id: str) -> dict:
        playbook = self.registry.get(workflow_id)
        return {
            key: deepcopy(playbook[key])
            for key in (
                "id",
                "name",
                "description",
                "stages",
                "required_evidence",
                "quota_budget",
                "deliverables",
                "review_required",
            )
        }

    def run(
        self,
        workflow_id: str,
        subject: str,
        code: str = "",
        seed: dict | None = None,
    ) -> dict:
        playbook = self.registry.get(workflow_id)
        clean_code = self._normalize_code(code)
        clean_subject = str(subject or clean_code or playbook["name"]).strip()[:200]
        before = self._usage_snapshot()
        started_at = datetime.now()

        if playbook["kind"] in {"company", "earnings"}:
            payload = self._company_payload(clean_code, seed)
        else:
            payload = self._theme_payload(clean_subject)

        source_ledger = self._source_ledger(playbook["kind"], payload)
        quality_gate = self._quality_gate(playbook["kind"], payload, source_ledger)
        after = self._usage_snapshot()
        quota = self._quota_assessment(
            budget=playbook["quota_budget"],
            before=before,
            after=after,
        )
        if not quota["within_budget"]:
            quality_gate["checks"].append(self._check("额度预算", False))
            quality_gate["missing"].append("额度预算")
            quality_gate["passed"] = False
        artifacts = self._artifacts(
            playbook["kind"],
            clean_subject,
            clean_code,
            payload,
            source_ledger,
            quality_gate,
        )
        if quota["within_budget"] and quality_gate["passed"]:
            status = "draft"
        elif not quota["within_budget"]:
            status = "blocked_quota_overrun"
        else:
            status = "blocked_missing_evidence"
        run_id = self._run_id(workflow_id, clean_subject, clean_code, started_at)
        run = {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "workflow_name": playbook["name"],
            "workflow_version": playbook["version"],
            "subject": clean_subject,
            "code": clean_code,
            "status": status,
            "review_required": True,
            "review": {"status": "pending", "notes": "", "reviewed_at": None},
            "stages": self._stage_statuses(playbook["stages"], quality_gate["passed"]),
            "source_ledger": source_ledger,
            "quality_gate": quality_gate,
            "quota": quota,
            "artifacts": artifacts,
            "created_at": started_at.isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self.store.save(run)
        self._record_knowledge(run)
        return run

    def list_runs(self, limit: int = 20) -> list[dict]:
        return self.store.list(limit=limit)

    def review(self, run_id: str, decision: str, notes: str = "") -> dict:
        return self.store.review(run_id, decision, notes)

    def _company_payload(self, code: str, seed: dict | None) -> dict:
        if not code:
            return {"code": "", "evidence": {}, "scenario_report": []}
        if (
            seed
            and self._normalize_code(seed.get("code")) == code
            and seed.get("evidence")
        ):
            return deepcopy(seed)
        return self.harness.company_research(code, profile="deep")

    @staticmethod
    def _normalize_code(code: Any) -> str:
        match = re.search(r"(?<!\d)(\d{6})(?!\d)", str(code or "").strip())
        return match.group(1) if match else ""

    def _theme_payload(self, subject: str) -> dict:
        queries = [
            f"{subject} 行业龙头 主力资金流入 非ST",
            f"{subject} 政策利好 业绩增长 非ST",
            f"{subject} 低位放量 换手活跃 非ST",
        ]
        return self.harness.market_radar(queries=queries)

    def _usage_snapshot(self) -> dict:
        provider = getattr(self.harness, "provider", None)
        if provider and hasattr(provider, "usage_stats"):
            try:
                usage = provider.usage_stats() or {}
                return {
                    "today": deepcopy(usage.get("today_by_endpoint") or {}),
                    "month": deepcopy(usage.get("month_by_endpoint") or {}),
                }
            except Exception:
                pass
        return {"today": {}, "month": {}}

    @staticmethod
    def _usage_delta(before: dict, after: dict) -> dict:
        result = {"today": {}, "month": {}}
        for period in result:
            keys = set((before.get(period) or {})) | set((after.get(period) or {}))
            for key in keys:
                delta = int((after.get(period) or {}).get(key, 0)) - int(
                    (before.get(period) or {}).get(key, 0)
                )
                if delta:
                    result[period][key] = delta
        return result

    def _quota_assessment(self, budget: dict, before: dict, after: dict) -> dict:
        delta = self._usage_delta(before, after)
        today_delta = delta.get("today") or {}
        month_delta = delta.get("month") or {}
        endpoints = set(today_delta) | set(month_delta)
        violations = []
        for endpoint in sorted(endpoints):
            actual = max(
                int(today_delta.get(endpoint, 0)),
                int(month_delta.get(endpoint, 0)),
            )
            allowed = int((budget or {}).get(endpoint, 0))
            if actual > allowed:
                violations.append({
                    "endpoint": endpoint,
                    "actual": actual,
                    "budget": allowed,
                })
        return {
            "budget": deepcopy(budget or {}),
            "before": before,
            "after": after,
            "delta": delta,
            "within_budget": not violations,
            "violations": violations,
        }

    def _source_ledger(self, kind: str, payload: dict) -> list[dict]:
        if kind == "theme":
            return self._theme_sources(payload)
        evidence = payload.get("evidence") or {}
        ledger: list[dict] = []

        quote = evidence.get("行情") or {}
        if quote.get("price"):
            ledger.append(self._source(
                "行情",
                f"{quote.get('name') or payload.get('code')} 最新可用行情",
                quote.get("source") or payload.get("source") or "unknown",
                published_at=quote.get("retrieved_at") or quote.get("quote_time"),
                status="verified",
            ))

        bars = evidence.get("K线") or []
        if bars:
            ledger.append(self._source(
                "K线",
                f"最近 {len(bars)} 条日线",
                bars[-1].get("source") or payload.get("source") or "unknown",
                published_at=bars[-1].get("date"),
                status="verified",
            ))

        for item in evidence.get("公告") or []:
            has_title = bool(item.get("title"))
            has_url = bool(item.get("url"))
            ledger.append(self._source(
                "公告",
                item.get("title") or "未命名公告",
                item.get("source") or "unknown",
                published_at=item.get("published_at"),
                url=item.get("url"),
                status=(
                    "verified_document"
                    if has_title and has_url
                    else "verified_metadata"
                    if has_title
                    else "incomplete"
                ),
            ))

        basics = evidence.get("基础数据") or {}
        usable_basics = {
            key: value
            for key, value in basics.items()
            if not str(key).startswith("_") and value not in (None, "", 0, "--")
            and not str(value).startswith("unavailable")
        }
        if usable_basics:
            ledger.append(self._source(
                "基础数据",
                "、".join(usable_basics.keys()),
                payload.get("source") or "ifind",
                status="verified",
            ))

        for item in evidence.get("智能选股") or []:
            ledger.append(self._source(
                "智能选股",
                f"{item.get('name') or item.get('code') or '候选'} 智能选股命中",
                item.get("source") or "ifind_wencai",
                status="candidate_only",
            ))
        return self._number_sources(ledger)

    def _theme_sources(self, payload: dict) -> list[dict]:
        ledger = []
        for theme in payload.get("themes") or []:
            query = theme.get("query") or "主题查询"
            for row in theme.get("rows") or []:
                ledger.append(self._source(
                    "主题候选",
                    f"{row.get('name') or row.get('code') or '候选'} · {query}",
                    row.get("source") or "ifind_wencai",
                    status="candidate_only",
                ))
        return self._number_sources(ledger)

    @staticmethod
    def _source(
        category: str,
        title: str,
        source: str,
        published_at: Any = None,
        url: Any = None,
        status: str = "verified",
    ) -> dict:
        return {
            "category": category,
            "title": str(title or ""),
            "source": str(source or "unknown"),
            "published_at": str(published_at or ""),
            "url": str(url or ""),
            "status": status,
        }

    @staticmethod
    def _number_sources(ledger: list[dict]) -> list[dict]:
        return [
            {"source_id": f"S{index}", **item}
            for index, item in enumerate(ledger, 1)
        ]

    def _quality_gate(self, kind: str, payload: dict, ledger: list[dict]) -> dict:
        if kind == "theme":
            themes = payload.get("themes") or []
            candidates = self._candidate_shortlist(themes)
            checks = [
                self._check("至少一个查询有结果", any(theme.get("rows") for theme in themes)),
                self._check("去重候选>=3", len(candidates) >= 3),
                self._check("候选保留来源", all(item.get("source") for item in candidates)),
            ]
        else:
            evidence = payload.get("evidence") or {}
            quote = evidence.get("行情") or {}
            basics = self._usable_basics(evidence.get("基础数据") or {})
            announcements = evidence.get("公告") or []
            smart = evidence.get("智能选股") or []
            checks = [
                self._check(
                    "有效股票代码",
                    bool(re.fullmatch(r"\d{6}", str(payload.get("code") or ""))),
                ),
                self._check("可靠行情", self._is_reliable_quote(quote)),
                self._check("基础指标>=2", len(basics) >= 2),
            ]
            if kind == "company":
                checks.extend([
                    self._check("K线", bool(evidence.get("K线"))),
                    self._check("公告或智能选股", bool(announcements or smart)),
                ])
            else:
                financial_events = [
                    item
                    for item in announcements
                    if self._is_financial_event(item.get("title"))
                ]
                checks.extend([
                    self._check(
                        "财报事件公告",
                        bool(financial_events),
                    ),
                    self._check(
                        "财报原文链接",
                        any(item.get("url") for item in financial_events),
                    ),
                ])
        missing = [item["name"] for item in checks if not item["passed"]]
        return {
            "passed": not missing,
            "checks": checks,
            "missing": missing,
            "source_count": len(ledger),
        }

    @staticmethod
    def _check(name: str, passed: bool) -> dict:
        return {"name": name, "passed": bool(passed)}

    def _is_financial_event(self, title: str | None) -> bool:
        text = str(title or "")
        return any(word in text for word in self.FINANCIAL_EVENT_WORDS)

    @staticmethod
    def _is_reliable_quote(quote: dict) -> bool:
        if float((quote or {}).get("price") or 0) <= 0:
            return False
        source = str((quote or {}).get("source") or "").lower()
        quality = str((quote or {}).get("quality_level") or "").lower()
        if source == "ifind":
            return quality in {"professional", "high", "ok", ""}
        return bool(source and source != "unknown" and quality not in {
            "open_unverified",
            "unavailable",
            "low",
        })

    @staticmethod
    def _usable_basics(basics: dict) -> dict:
        return {
            key: value
            for key, value in (basics or {}).items()
            if not str(key).startswith("_")
            and value not in (None, "", 0, "--")
            and not str(value).startswith("unavailable")
        }

    def _artifacts(
        self,
        kind: str,
        subject: str,
        code: str,
        payload: dict,
        ledger: list[dict],
        quality_gate: dict,
    ) -> dict:
        if kind == "theme":
            return self._theme_artifacts(subject, payload, ledger, quality_gate)
        if kind == "earnings":
            return self._earnings_artifacts(subject, code, payload, ledger, quality_gate)
        return self._company_artifacts(subject, code, payload, ledger, quality_gate)

    def _company_artifacts(
        self,
        subject: str,
        code: str,
        payload: dict,
        ledger: list[dict],
        quality_gate: dict,
    ) -> dict:
        evidence = payload.get("evidence") or {}
        quote = evidence.get("行情") or {}
        name = quote.get("name") or subject or code
        refs = self._category_refs(ledger)
        basics = self._usable_basics(evidence.get("基础数据") or {})
        note = [
            f"# {name}({code}) 单公司研究草稿",
            "",
            "> 状态：仅供人工复核，不构成投资建议或交易指令。",
            "",
            "## 当前证据",
            f"- 最新可用价格：{float(quote.get('price') or 0):.2f} 元 {refs.get('行情', '')}".rstrip(),
            f"- 涨跌幅：{float(quote.get('change_pct') or 0):+.2f}% {refs.get('行情', '')}".rstrip(),
            f"- 基础指标：{self._basic_summary(basics)} {refs.get('基础数据', '')}".rstrip(),
            f"- 公告数量：{len(evidence.get('公告') or [])} {refs.get('公告', '')}".rstrip(),
            "",
            "## 质量门",
            "通过" if quality_gate["passed"] else f"阻断：{', '.join(quality_gate['missing'])}",
            "",
            "## 下一步",
            "由研究员核对来源账本、公告原文和失效条件后，再决定是否进入审计。",
        ]
        return {
            "research_note": "\n".join(note),
            "evidence_table": [
                {
                    "dimension": item["category"],
                    "evidence": item["title"],
                    "source_id": item["source_id"],
                }
                for item in ledger
            ],
            "scenario_report": deepcopy(payload.get("scenario_report") or []),
            "risk_flags": quality_gate["missing"],
        }

    def _earnings_artifacts(
        self,
        subject: str,
        code: str,
        payload: dict,
        ledger: list[dict],
        quality_gate: dict,
    ) -> dict:
        evidence = payload.get("evidence") or {}
        events = [
            item
            for item in evidence.get("公告") or []
            if self._is_financial_event(item.get("title"))
        ]
        if not quality_gate["passed"]:
            return {
                "earnings_review_note": (
                    f"# {subject or code} 财报复核草稿\n\n"
                    "当前证据不足，禁止形成业绩方向判断。请先补齐："
                    f"{'、'.join(quality_gate['missing'])}。"
                ),
                "financial_events": [],
                "evidence_gaps": quality_gate["missing"],
            }

        refs = self._category_refs(ledger)
        basics = self._usable_basics(evidence.get("基础数据") or {})
        note = [
            f"# {subject or code} 财报复核草稿",
            "",
            "> 仅核对已披露材料；未接入一致预期时，不判断相对市场预期的偏差。",
            "",
            f"- 财报事件：{'；'.join(item.get('title', '') for item in events)} {refs.get('公告', '')}".rstrip(),
            f"- 当前基础指标：{self._basic_summary(basics)} {refs.get('基础数据', '')}".rstrip(),
            f"- 当前行情：{float((evidence.get('行情') or {}).get('price') or 0):.2f} 元 {refs.get('行情', '')}".rstrip(),
            "",
            "下一步：人工打开公告原文，核对报告期、单位、同比口径和管理层表述。",
        ]
        return {
            "earnings_review_note": "\n".join(note),
            "financial_events": events,
            "evidence_gaps": [],
        }

    def _theme_artifacts(
        self,
        subject: str,
        payload: dict,
        ledger: list[dict],
        quality_gate: dict,
    ) -> dict:
        themes = payload.get("themes") or []
        candidates = self._candidate_shortlist(themes)
        source_map = {
            item["title"].split(" · ", 1)[0]: item["source_id"]
            for item in ledger
        }
        for item in candidates:
            key = item.get("name") or item.get("code") or "候选"
            item["source_id"] = source_map.get(key, "")
        query_summary = [
            {"query": item.get("query"), "count": len(item.get("rows") or [])}
            for item in themes
        ]
        note_lines = [
            f"# {subject} 主题市场研究草稿",
            "",
            "> 候选只代表研究入口，不是买入建议。",
            "",
        ]
        for item in candidates:
            ref = f"[{item['source_id']}]" if item.get("source_id") else ""
            note_lines.append(
                f"- {item.get('name') or item.get('code')}({item.get('code', '')}) {ref}".rstrip()
            )
        if not quality_gate["passed"]:
            note_lines.extend(["", f"质量门阻断：{', '.join(quality_gate['missing'])}"])
        return {
            "theme_note": "\n".join(note_lines),
            "candidate_shortlist": candidates,
            "query_summary": query_summary,
        }

    @staticmethod
    def _candidate_shortlist(themes: list[dict]) -> list[dict]:
        seen = set()
        rows = []
        for theme in themes or []:
            query = theme.get("query") or ""
            for raw in theme.get("rows") or []:
                code = str(raw.get("code") or "")
                if not code or code in seen:
                    continue
                seen.add(code)
                rows.append({
                    **deepcopy(raw),
                    "query": query,
                    "source": raw.get("source") or "ifind_wencai",
                })
        return rows[:10]

    @staticmethod
    def _category_refs(ledger: list[dict]) -> dict:
        refs: dict[str, list[str]] = {}
        for item in ledger:
            refs.setdefault(item["category"], []).append(f"[{item['source_id']}]")
        return {key: "".join(value) for key, value in refs.items()}

    @staticmethod
    def _basic_summary(basics: dict) -> str:
        if not basics:
            return "暂无可靠基础指标"
        return "；".join(f"{key}={value}" for key, value in list(basics.items())[:6])

    @staticmethod
    def _stage_statuses(stages: list[str], passed: bool) -> list[dict]:
        output = []
        for stage in stages:
            if "人工复核" in stage:
                status = "pending"
            elif not passed and ("草稿" in stage or "变化复核" in stage or "主题草稿" in stage):
                status = "blocked"
            else:
                status = "completed"
            output.append({"name": stage, "status": status})
        return output

    @staticmethod
    def _run_id(workflow_id: str, subject: str, code: str, created_at: datetime) -> str:
        raw = f"{workflow_id}|{subject}|{code}|{created_at.isoformat()}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        return f"{created_at.strftime('%Y%m%d%H%M%S')}-{digest}"

    def _record_knowledge(self, run: dict) -> None:
        knowledge = getattr(self.harness, "knowledge", None)
        if not knowledge or not hasattr(knowledge, "record_run"):
            return
        try:
            knowledge.record_run({
                "fingerprint": run["run_id"],
                "kind": f"workflow:{run['workflow_id']}",
                "code": run.get("code"),
                "title": f"{run['workflow_name']} · {run['subject']}",
                "quality": "high" if run["quality_gate"]["passed"] else "low",
                "evidence": {
                    item["source_id"]: item["category"]
                    for item in run["source_ledger"]
                },
                "summary_cards": [
                    {"title": "来源", "value": len(run["source_ledger"]), "note": "可追溯"},
                    {"title": "质量门", "value": "通过" if run["quality_gate"]["passed"] else "阻断", "note": ""},
                ],
            })
        except Exception:
            pass
