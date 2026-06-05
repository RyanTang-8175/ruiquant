# CLAUDE.md - RuiQuant 项目上下文

## 项目概述
个人 A 股 AI 研究助手，帮你盯盘、选股、预测、模拟训练、AI 对话。

> **AI 可读导出**: 完整的项目架构、数据库模型、核心引擎说明见 [AI_PROJECT_EXPORT.md](AI_PROJECT_EXPORT.md)。其他 AI 工具应先阅读该文件以快速理解项目全貌。

## 核心原则
1. **数值与解释分离**：所有分数、指标由程序计算，AI 只写解释文字
2. **模拟盘真实**：严格遵守 T+1、涨跌停、交易费用
3. **预测必回填**：每次预测必须记录，自动验证准确率
4. **数据先行**：没有可靠数据，不做评分和预测
5. **自我学习**：每天复盘，自动调整因子权重

## 技术栈
- 后端：Python 3.11+, FastAPI
- 前端：Streamlit
- 数据库：SQLite
- 数据源：AKShare（主）
- AI：DeepSeek（OpenAI 兼容接口）
- 定时任务：APScheduler

## 目录结构
- `src/data/` - 数据采集模块
- `src/scoring/` - 评分引擎（35 因子）
- `src/prediction/` - AI 预测系统
- `src/trading/` - 模拟盘训练
- `src/coach/` - AI 教练
- `src/learning/` - 自我学习引擎
- `src/utils/` - 工具函数

## 开发规范
- API 契约见 `docs/03_API_CONTRACT.md`
- 数据质量规则见 `docs/05_DATA_QUALITY.md`
- 安全规则见 `docs/13_SECURITY.md`
- 评分因子见 `docs/06_STRATEGY_SPEC.md`

## 禁止事项
- 禁止在前端暴露任何 API key
- 禁止用 eval() 执行用户输入
- 禁止 AI 生成数值型投资结论
- 禁止在日志中打印密钥
- 禁止跳过数据质量检查

## Git 规范
- 每完成一个 Phase 就 commit + push
- commit message 格式：`Phase X: 简短描述`
- 出问题时可以回滚到上一个 Phase
