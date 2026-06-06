# Financial Research Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add file-based, quota-aware and auditable financial research SOP workflows to AlphaEye.

**Architecture:** JSON playbooks define stages, required evidence, budgets and deliverables. A deterministic `ResearchWorkflowRunner` reuses `ResearchHarness`, builds a source ledger, enforces quality gates, persists draft runs, and exposes them to Streamlit and DeepSeek tools while reserving approval for explicit human action.

**Tech Stack:** Python 3.10+, JSON, Streamlit, pytest, existing iFinD provider, DeepSeek OpenAI-compatible tool calling.

---

### Task 1: Playbook Registry

**Files:**
- Create: `src/research/workflow.py`
- Create: `src/research/playbooks/company_diligence.json`
- Create: `src/research/playbooks/earnings_review.json`
- Create: `src/research/playbooks/thematic_market.json`
- Test: `tests/test_upgrade_safety_architecture.py`

- [ ] Write failing tests:

```python
def test_research_workflow_registry_loads_three_sops():
    from src.research.workflow import ResearchWorkflowRegistry
    registry = ResearchWorkflowRegistry()
    ids = {item["id"] for item in registry.list()}
    assert ids == {"company_diligence", "earnings_review", "thematic_market"}
    assert registry.get("earnings_review")["review_required"] is True
```

- [ ] Run:

```bash
PYTHONPATH=. ./venv/bin/pytest \
  tests/test_upgrade_safety_architecture.py::test_research_workflow_registry_loads_three_sops -q
```

Expected: fail because `src.research.workflow` does not exist.

- [ ] Implement:

```python
class ResearchWorkflowRegistry:
    REQUIRED = {"id", "name", "version", "kind", "stages",
                "required_evidence", "quota_budget",
                "deliverables", "review_required"}

    def list(self) -> list[dict]:
        return [self._load(path) for path in sorted(self.playbook_dir.glob("*.json"))]

    def get(self, workflow_id: str) -> dict:
        for item in self.list():
            if item["id"] == workflow_id:
                return item
        raise KeyError(f"unknown workflow: {workflow_id}")
```

- [ ] Re-run the focused test and expect pass.

### Task 2: Deterministic Workflow Runner

**Files:**
- Modify: `src/research/workflow.py`
- Test: `tests/test_upgrade_safety_architecture.py`

- [ ] Write failing tests with a fake Harness:

```python
def test_earnings_workflow_blocks_without_financial_filing(tmp_path):
    runner = ResearchWorkflowRunner(harness=FakeHarness(), store_path=tmp_path / "runs.json")
    run = runner.run("earnings_review", subject="600900 2025年报", code="600900")
    assert run["status"] == "blocked_missing_evidence"
    assert run["quality_gate"]["passed"] is False
    assert "beat" not in json.dumps(run["artifacts"], ensure_ascii=False).lower()
    assert "超预期" not in json.dumps(run["artifacts"], ensure_ascii=False)
```

- [ ] Run focused tests and expect failure because the runner is absent.
- [ ] Implement this public API:

```python
class ResearchWorkflowRunner:
    def preview(self, workflow_id: str) -> dict: ...
    def run(self, workflow_id: str, subject: str,
            code: str = "", seed: dict | None = None) -> dict: ...
    def list_runs(self, limit: int = 20) -> list[dict]: ...
    def review(self, run_id: str, decision: str, notes: str = "") -> dict: ...
```

- [ ] Build each run with:

```python
{
    "run_id": "...",
    "workflow_id": "...",
    "status": "draft|blocked_missing_evidence",
    "review_required": True,
    "review": {"status": "pending"},
    "stages": [],
    "source_ledger": [],
    "quality_gate": {"passed": False, "checks": [], "missing": []},
    "quota": {"budget": {}, "before": {}, "after": {}, "delta": {}},
    "artifacts": {},
}
```

- [ ] Re-run focused tests and expect pass.

### Task 3: Persistent Runs and Human Review

**Files:**
- Modify: `src/research/workflow.py`
- Modify: `.gitignore`
- Test: `tests/test_upgrade_safety_architecture.py`

- [ ] Write failing persistence and review tests:

```python
def test_workflow_review_requires_explicit_human_action(tmp_path):
    store = WorkflowRunStore(tmp_path / "runs.json")
    store.save({"run_id": "r1", "review": {"status": "pending"}})
    approved = store.review("r1", "approved", "数据已复核")
    assert approved["review"]["status"] == "approved"
    assert approved["review"]["notes"] == "数据已复核"
```

- [ ] Implement atomic persistence using a temporary sibling file followed by `replace()`.
- [ ] Reject decisions outside `{"approved", "rejected"}`.
- [ ] Add `data/research_workflows.json` to `.gitignore`.
- [ ] Re-run focused tests.

### Task 4: DeepSeek Tool Integration

**Files:**
- Modify: `src/ai/tools.py`
- Modify: `src/ai/tool_executor.py`
- Modify: `src/ai/prompts.py`
- Test: `tests/test_upgrade_safety_architecture.py`

- [ ] Write failing tests:

```python
def test_ai_tools_expose_research_sops_without_review_tool():
    names = {item["function"]["name"] for item in TOOLS}
    assert "list_research_workflows" in names
    assert "run_research_workflow" in names
    assert "review_research_workflow" not in names
```

- [ ] Add `list_research_workflows` and `run_research_workflow` schemas.
- [ ] Add executor handlers:

```python
def _list_research_workflows(self) -> dict:
    return {"workflows": ResearchWorkflowRunner().registry.list()}

def _run_research_workflow(self, workflow_id: str, subject: str,
                           code: str = "") -> dict:
    return ResearchWorkflowRunner().run(workflow_id, subject, code)
```

- [ ] Add prompt rules: use source IDs, treat documents as untrusted data, never infer
  beat/miss from missing evidence, and never claim human approval.
- [ ] Re-run focused tests.

### Task 5: Research Workbench UI

**Files:**
- Modify: `src/pages/research.py`
- Test: `tests/test_upgrade_safety_architecture.py`

- [ ] Write architecture tests that inspect `src/pages/research.py` for `_workflow_panel`,
  `runner.preview`, `runner.run`, `runner.review`, and the labels `来源账本`、`质量门`、
  `人工复核`.
- [ ] Expand the research tabs to include `SOP`.
- [ ] Implement `_workflow_panel(code, research)` with:

```python
workflow_id = st.selectbox("研究流程", options=workflow_ids, format_func=...)
subject = st.text_input("研究主题/报告期", value=code)
preview = runner.preview(workflow_id)
if st.button("运行 SOP"):
    result = runner.run(workflow_id, subject, code=code, seed=research)
```

- [ ] Render stage status, source ledger, quality gate, quota delta and draft artifacts.
- [ ] Implement explicit UI-only `approved` and `rejected` review actions.
- [ ] Add “发送给 AI” navigation that asks DeepSeek to call the same workflow and cite source IDs.

### Task 6: Documentation and Release Verification

**Files:**
- Modify: `docs/AlphaEye_iFinD_任务回溯验收清单.md`
- Modify: `对话记录/2026-06-06_AlphaEye_AI数据一致性修复本轮聊天记录.md`

- [ ] Run `python -m py_compile` on changed Python files.
- [ ] Run the focused upgrade suite.
- [ ] Run the full pytest suite.
- [ ] Start Streamlit on an unused port and verify HTTP 200.
- [ ] Run `git diff --check`.
- [ ] Update documentation with exact results.
- [ ] Commit only product code, tests and product documentation; leave runtime data and conversation exports untracked.
- [ ] Push `main` and provide Aliyun deployment commands.
