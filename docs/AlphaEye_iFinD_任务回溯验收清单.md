# AlphaEye iFinD 投研工作台任务回溯验收清单

更新时间：2026-06-05

本清单用于防止目标漂移。后续升级必须先回看这里，再决定是否继续写代码。

## 总目标

AlphaEye 要升级为 iFinD 驱动的小型个人投研工作台：

发现信息 -> 判断真假热点 -> 生成候选 -> 公司研究 -> 证据化 AI 结论 -> 写入审计 -> T+1/T+2/T+3 回放。

边界：

- 不做真正自动交易。
- 不做复杂回测系统。
- 不做完整多 Agent 框架。
- 不做黑色/炫酷 UI，继续以白色背景为主。
- 不把所有 iFinD 接口一次性铺满页面。

## 必须完成项与状态

| 任务 | 状态 | 代码证据 |
|---|---|---|
| 雷达页恢复推荐股票，并升级为中国 A 股候选股池 | 已落地 | `src/pages/radar.py::_show_recommendation_candidate_pool` |
| 候选股池合并旧六维评分与 iFinD Evidence Score | 已落地 | `src/pages/radar.py::_build_candidate_pool_rows` |
| 雷达页包含政策、公告、互动问答、机构观点、行业异动、智能选股 | 已落地 | `src/news/radar.py::fetch_radar_market_overview` |
| iFinD 智能选股模板 | 已落地 | `src/pages/radar.py::_show_ifind_smart_picks` |
| 公司研究工作台 | 已落地 | `src/pages/research.py` |
| 研究底稿聚合行情、K线、公告、基础数据、智能选股 | 已落地 | `src/research/harness.py::company_research` |
| MiroFish 式轻量情景推演 | 已落地 | `src/research/harness.py::_scenario_report` |
| iFinD Evidence Score 六维评分 | 已落地 | `src/scoring/evidence.py` |
| 旧评分保留，新评分并行验证 | 已落地 | `src/pages/research.py`、`src/research/evaluator.py` |
| AI 证据闸门与 iFinD 工具矩阵 | 已落地 | `src/ai/prompts.py`、`src/ai/tools.py`、`src/ai/tool_executor.py` |
| DeepSeek API 优先，本地兜底只在 API 不可用时启用 | 已落地 | `src/ai/chat.py::provider_status` |
| AI 页显示 DeepSeek/本地兜底状态 | 已落地 | `src/pages/ai_chat.py` |
| 我的页显示 AI 状态、iFinD 配置和额度 | 已落地 | `src/pages/profile.py` |
| Research Harness 指纹、缓存、裁剪、记忆 | 已落地 | `src/research/harness.py`、`src/research/knowledge.py` |
| iFinD 月额度治理和接口调用统计 | 已落地 | `src/data/providers/ifind_provider.py::usage_stats` |
| 研究审计入库和 T+1/T+2/T+3 回放 | 已落地 | `src/pages/lab.py`、`src/memory/analysis_memory.py` |
| 新旧评分命中率对比 | 已落地 | `src/pages/lab.py::_score_comparison_panel` |
| 轻量策略探索与指纹去重 | 已落地 | `src/research/strategy.py::StrategyExplorer` |
| 策略加减停四档机制 | 已落地 | `src/research/strategy.py::StrategyGovernor` |
| 周一盘前计划入口 | 已落地 | `src/pages/ai_chat.py::_quick_tasks` |
| 白色背景与可读 UI | 持续约束 | `src/pages/*`、`tests/test_regression_ui_ai.py` |

## 仍需持续遵守

- 周一或任何交易日都不能无证据直接输出“买哪只”。必须先给候选、条件、禁止动作和审计字段。
- iFinD 有月度额度限制，页面刷新不能自动反复调用高消耗接口。
- AI 回答如果没有行情、公告、新闻或 iFinD 数据，必须降低置信度。
- DeepSeek Key 如果是测试/占位值，必须显示本地兜底原因，不能假装云端 AI 可用。
- 运行数据、缓存、对话记录不进入 Git 提交。

## 当前验证命令

```bash
PYTHONPATH=. ./venv/bin/pytest tests/test_upgrade_safety_architecture.py -q
PYTHONPATH=. ./venv/bin/pytest -q
```

