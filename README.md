# RuiQuant - 个人 A 股 AI 研究助手

一个帮你盯盘、选股、预测、模拟训练、AI 对话的 A 股个人研究工具。

## 核心功能

- **市场概览**：一眼看到今天市场全貌
- **智能选股**：35 个因子自动评分，筛选值得关注的股票
- **AI 预测**：每天开盘前预测今日走势，自动验证准确率
- **模拟训练**：真实股市数据 + 虚拟资金，练习交易
- **AI 对话**：直接问 AI 任何股票问题
- **AI 教练**：评价你的交易，帮你提高

## 技术栈

- Python 3.11+
- Streamlit（前端）
- FastAPI（后端 API）
- SQLite（数据库）
- AKShare（数据源）
- DeepSeek（AI 后端）

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key

# 3. 初始化数据库
python scripts/init_db.py

# 4. 启动应用
streamlit run app.py
```

## 项目结构

```
股票/
├── app.py                  # Streamlit 主入口
├── requirements.txt        # Python 依赖
├── .env.example           # 环境变量模板
├── README.md              # 项目说明
├── CLAUDE.md              # Claude Code 上下文
├── data/                  # 数据目录
│   └── ruiquant.db        # SQLite 数据库
├── docs/                  # 文档目录
├── scripts/               # 工具脚本
├── tests/                 # 测试代码
└── src/                   # 源代码
    ├── data/              # 数据采集模块
    ├── scoring/           # 评分引擎模块
    ├── prediction/        # AI 预测模块
    ├── trading/           # 模拟盘模块
    ├── coach/             # AI 教练模块
    ├── learning/          # 自我学习模块
    └── utils/             # 工具函数
```

## 文档导航

- [项目总记忆](docs/00_MASTER_CONTEXT.md) - 所有设计决策
- [产品规格](docs/01_PRODUCT_SPEC.md) - 功能清单
- [开发计划](docs/02_PHASE_ROADMAP.md) - 分阶段路线图
- [API 契约](docs/03_API_CONTRACT.md) - 接口定义
- [数据层设计](docs/04_DATA_PLAN.md) - 数据源与存储
- [评分引擎](docs/06_STRATEGY_SPEC.md) - 35 因子评分系统
- [模拟盘规则](docs/07_PAPER_TRADING.md) - 交易规则与费用
- [AI 预测](docs/08_PREDICTION_EVAL.md) - 预测与回填
- [风控规则](docs/09_RISK_RULES.md) - 仓位与止损
- [AI 集成](docs/10_LLM_INTEGRATION.md) - DeepSeek 集成
- [定时任务](docs/12_SCHEDULER.md) - 任务调度
- [安全设计](docs/13_SECURITY.md) - 安全规则
- [成本估算](docs/14_COST_PLAN.md) - 费用预估

## 免责声明

本工具仅供个人研究学习使用，不构成任何投资建议。股市有风险，投资需谨慎。
