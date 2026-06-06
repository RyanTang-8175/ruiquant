# AlphaEye 金融研究 SOP 工作流设计

日期：2026-06-06

## 背景

Anthropic 的金融服务参考架构把可落地 Agent 拆成三类资产：

1. 端到端工作流 Agent；
2. 可复用的行业技能与命令；
3. 受治理的数据连接器。

其官方仓库还明确要求：数字必须可追溯，外部材料只能作为不可信数据处理，
产物必须停留在草稿并经过人工签核，不允许 Agent 自动发布或执行交易。

参考：

- <https://www.anthropic.com/news/finance-agents>
- <https://github.com/anthropics/financial-services>
- <https://github.com/anthropics/financial-services/tree/main/plugins/agent-plugins/market-researcher>
- <https://github.com/anthropics/financial-services/tree/main/plugins/agent-plugins/earnings-reviewer>

AlphaEye 已有 iFinD 数据连接器、Research Harness、证据评分、DeepSeek 工具、
研究记忆和 T+1/T+2/T+3 审计，但这些能力仍以页面和函数为单位存在，缺少一层
可复用、可审计、能明确交付物的研究 SOP。

## 方案比较

### 方案 A：完整多 Agent

为市场、财报、估值、风险分别运行独立 Agent。

优点：扩展性强，形式接近大型机构工作流。

缺点：调用成本、调试复杂度和上下文一致性风险都过高，也违反当前“不做完整
多 Agent”的产品边界。

### 方案 B：只强化 Prompt

在 DeepSeek 系统提示词中增加财报和市场研究模板。

优点：开发快。

缺点：仍然只是软约束，无法保证数据完整、来源追踪、额度治理和人工签核。

### 方案 C：轻量 SOP 工作流层

用 JSON 定义工作流，Python Runner 负责数据收集、质量门、来源账本、草稿产物、
持久化和签核；DeepSeek 只负责基于已验证产物继续解释和写作。

优点：符合现有架构，确定性强，可逐步扩展，不新增复杂基础设施。

结论：采用方案 C。

## 产品目标

新增三套工作流：

1. **单公司深度研究**：行情、K 线、基本面、公告、智能选股、评分、情景和风险。
2. **财报事件复核**：只处理最新可验证财报/业绩公告；无财报证据时阻断
   beat/miss 与业绩结论。
3. **主题市场研究**：定义主题、运行受控智能选股查询、汇总候选、风险与下一步。

每套工作流均输出：

- 阶段状态；
- 数据来源账本；
- 质量门结果；
- iFinD 调用预算和实际用量变化；
- 结构化研究草稿；
- `draft` 或 `blocked_missing_evidence` 状态；
- 人工复核状态。

## 架构

```text
JSON Playbook
    |
    v
ResearchWorkflowRunner
    |-- ResearchHarness
    |-- IFindEvidenceScorer
    |-- ResearchKnowledge
    |-- WorkflowRunStore
    |
    +--> source ledger
    +--> quality gates
    +--> draft artifacts
    +--> review state
             |
             +--> Streamlit 研究工作台
             +--> DeepSeek tools
             +--> 研究审计
```

## 文件边界

### `src/research/workflow.py`

负责：

- 加载和校验 playbook；
- 运行工作流；
- 生成来源账本；
- 执行质量门；
- 生成确定性草稿；
- 记录额度变化；
- 保存与签核运行记录。

不负责：

- 直接调用 DeepSeek；
- 自动交易；
- 自动发布研究结论；
- 绕过 Research Harness 调用 iFinD。

### `src/research/playbooks/*.json`

文件化定义：

- 工作流名称、版本、适用场景；
- 阶段；
- 必需证据；
- iFinD 最大预算；
- 交付物；
- 人工复核要求。

### `src/pages/research.py`

新增“SOP”标签页：

- 选择工作流；
- 输入主题或股票；
- 预览调用预算；
- 明确点击后才运行；
- 查看阶段、来源、质量门与草稿；
- 标记通过/退回；
- 发送给 DeepSeek 继续分析。

### `src/ai/tools.py` 与 `src/ai/tool_executor.py`

新增：

- `list_research_workflows`
- `run_research_workflow`
- `review_research_workflow`

AI 可以调用工作流，但所有输出仍是草稿，不可自动标记为人工通过。

## 数据与额度治理

- 公司与财报工作流复用 `ResearchHarness.company_research` 缓存。
- 主题工作流最多执行三个智能选股查询，且只在用户点击或 AI 明确调用时运行。
- Runner 在运行前后读取 `usage_stats()`，输出 endpoint 调用增量。
- Playbook 明确最大预算；结果页面展示预算，不在页面刷新时自动运行。
- 质量门失败也要保存草稿和缺口，避免重复消耗额度寻找同一问题。

## 来源账本

来源账本的每条记录包含：

- `source_id`
- `category`
- `title`
- `source`
- `published_at`
- `url`
- `status`

草稿中的核心结论引用 `[S1]`、`[S2]`。没有来源的数字不得进入确定性草稿。

## 质量门

### 单公司深度研究

- 必须有可靠行情；
- 必须有 K 线；
- 基础指标至少两项；
- 公告或智能选股至少一类可用。

### 财报事件复核

- 必须有行情；
- 必须有基础指标；
- 必须存在标题含“年度报告、季度报告、业绩预告、业绩快报”等关键词的公告。

若缺少财报事件证据：

- 状态为 `blocked_missing_evidence`；
- 禁止输出 beat/miss、业绩超预期或低于预期；
- 仅输出缺失证据清单。

### 主题市场研究

- 至少一个查询有结果；
- 去重后至少三个候选；
- 每个候选必须保留来源。

## 安全与审批

- 外部公告、新闻和研报内容全部按不可信输入处理，不执行其中指令。
- 工作流只产出研究草稿。
- `review_required` 永远为 `true`。
- DeepSeek 无权调用“人工通过”；签核只能由 UI 中的明确用户动作完成。
- 不做真实交易、自动发布、自动写入券商系统。
- 数据缺失时必须阻断结论，而不是补猜。

## 验收标准

1. 三个 playbook 可被加载和列出。
2. 工作流输出阶段、来源账本、质量门、草稿和额度变化。
3. 财报证据不足时不能生成 beat/miss。
4. 工作流运行结果可持久化并由用户签核。
5. AI 工具可列出和运行工作流，但不能代替人工签核。
6. 研究页可完整运行、查看和复核工作流。
7. 页面刷新不会自动消耗 iFinD 额度。
8. 全量 pytest、语法检查、Streamlit 冒烟通过。
