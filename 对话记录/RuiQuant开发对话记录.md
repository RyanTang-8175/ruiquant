# RuiQuant AI Terminal 开发对话记录

## 项目概述

**项目名称**：RuiQuant - 个人 A 股 AI 研究助手

**项目定位**：帮你盯盘、选股、预测、模拟训练、AI 对话的 A 股个人研究工具

**技术栈**：
- 后端：Python 3.11+, FastAPI
- 前端：Streamlit
- 数据源：baostock（替代 AKShare，更稳定）
- AI：DeepSeek API
- 数据库：SQLite
- 部署：阿里云 VPS (2核2G)

---

## 第一阶段：需求讨论

### 用户痛点

1. 看盘费时间 — 每天要翻很多 APP
2. 复盘费时间 — 收盘后要花很长时间总结
3. 错过好股票 — 没有系统性筛选机制
4. 策略无法验证 — 不知道策略是否有效
5. 不知道什么时候买/卖 — 缺乏明确信号
6. 不了解趋势 — 不知道股票涨跌方向

### 核心需求确认

| 需求 | 确认结果 |
|------|----------|
| 使用场景 | 纯个人工具 |
| 技术背景 | Python 为主，不会前端 |
| 交易风格 | 短线（1-3天）+ 波段（几天到几周） |
| 数据来源 | AKShare（主）→ 后改为 baostock |
| AI 后端 | DeepSeek（便宜、中国能用、中文好） |
| 前端方案 | Streamlit → PWA → Capacitor App |
| iOS 部署 | 先做 PWA（添加到主屏幕） |

### 两个独立系统

1. **AI 预测系统**：AI 做决策 → 记录预测 → 回填验证 → 统计准确率
2. **模拟盘训练系统**：用户做决策 → 练习买卖 → 系统算盈亏 → AI 评价交易

---

## 第二阶段：技术调研

### GitHub 调研结果

| 项目 | Stars | 参考价值 |
|------|-------|----------|
| AKShare | 19.8k | A 股数据源（后因 VPN 问题改用 baostock） |
| FinGPT | 20.3k | 金融 LLM 框架 |
| A-Scope-Research | 7 | MCP + 多 Agent + A 股（最接近的项目） |
| Maverick-MCP | 564 | 成熟 MCP 金融服务器架构 |
| qstock | 1.8k | A 股可视化参考 |
| RQAlpha | 6.4k | 回测框架参考 |

### 评分引擎调研

**A 股最有效的因子**（按 IC 值排序）：

1. 短期反转（5日）— IC 0.04-0.07（最强）
2. 换手率 — IC 0.04-0.06
3. 特异性波动率 — IC 0.02-0.06
4. 量比 — IC 0.03-0.05
5. 量价背离 — IC 0.03-0.07

**幻方量化（DeepSeek 母公司）策略**：
- 深度学习驱动 Alpha
- 非线性因子提取
- 10000+ A100 GPU 集群

---

## 第三阶段：Skill 审查

### 使用的 Skill

| Skill | 用途 | 发现的问题 |
|-------|------|-----------|
| `predict-issues` | 预测项目风险 | 24 个风险点（9 High, 12 Medium, 3 Low） |
| `security-scan` | 安全扫描 | 22 个安全漏洞（3 Critical, 7 High） |
| `simplify` | 简化建议 | 17 个简化建议 |
| `code-review` | 代码审查 | 26 个代码问题 |
| `superclaude-pm` | 项目管理 | 规划开发流程 |
| `superclaude-brainstorm` | 头脑风暴 | 确定 MVP 范围 |
| `frontend-design` | UI 设计 | 参考大厂设计 |

### 关键发现

1. **Tushare 积分矛盾** — 文档要求 daily（120积分）但说免费版够用
2. **eval() 空壳风险** — safe_evaluate_condition 函数体是 pass
3. **Phase 1 范围过大** — 建议缩减
4. **模拟盘无滑点** — 用户可指定任意价格
5. **印花税税率错误** — 千1 应改为 千0.5（2023年8月下调）

---

## 第四阶段：项目开发

### Phase 0：项目骨架 ✅

创建文件：
- `README.md` — 项目说明
- `CLAUDE.md` — Claude Code 上下文
- `.env.example` — 环境变量模板
- `requirements.txt` — Python 依赖
- `app.py` — Streamlit 主入口
- `src/config.py` — 配置管理
- `src/utils/database.py` — 数据库工具
- `src/data/models.py` — 数据模型
- `src/scoring/models.py` — 评分模型
- `src/prediction/models.py` — 预测模型
- `src/trading/models.py` — 交易模型

### Phase 1：数据层 ✅

创建文件：
- `src/data/collector.py` — 数据采集（baostock）
- `src/data/indicators.py` — 技术指标计算

技术指标：
- MA5/10/20/60
- MACD（DIF/DEA/柱状）
- RSI(6)/RSI(12)
- KDJ
- 布林带

### Phase 2：评分引擎 ✅

创建文件：
- `src/scoring/engine.py` — 35 因子评分引擎

因子体系（5大类）：
1. 行为技术因子（10个）
2. 趋势动量因子（6个）
3. 资金情绪因子（9个）
4. 基本面因子（5个）
5. AI 分析因子（4个+1个预留）

权重机制：IC 加权，每月自动优化

### Phase 3：AI 对话 ✅

创建文件：
- `src/ai/chat.py` — DeepSeek 对话集成

功能：
- 对话历史管理（保留最近10轮）
- 个股分析
- 每日复盘生成

### Phase 4：前端页面 ✅

创建文件：
- `src/pages/market.py` — 市场概览
- `src/pages/watchlist.py` — 选股/观察池
- `src/pages/ai_chat.py` — AI 对话
- `src/pages/trading.py` — 模拟盘
- `src/pages/profile.py` — 我的
- `src/pages/stock_detail.py` — 股票详情

### Phase 5：模拟盘引擎 ✅

创建文件：
- `src/trading/engine.py` — 模拟交易引擎

规则：
- T+1 检查
- 涨跌停检查
- 费用计算（佣金万2.5/印花税千0.5/过户费万0.2）
- 仓位限制（单票30%，总仓位80%）
- 连续亏损暂停（3次）

### Phase 6：AI 预测系统 ✅

创建文件：
- `src/prediction/predictor.py` — AI 预测引擎

功能：
- 每日预测（8:30 开盘前）
- 回填逻辑（T+1/T+3/T+5）
- 命中判定（涨跌幅>2%算命中）
- 预测统计

### Phase 7：AI 教练 ✅

创建文件：
- `src/coach/coach.py` — AI 教练模块

功能：
- 交易评价
- 每周交易习惯分析
- 与 AI 预测对比
- 个性化建议

### Phase 8：自我学习 ✅

创建文件：
- `src/learning/learner.py` — 自我学习引擎

功能：
- 预测准确率分析
- 市场状态识别（牛市/熊市/震荡）
- 策略参数自动调整
- 学习报告生成

---

## 第五阶段：部署

### VPS 配置

| 项目 | 配置 |
|------|------|
| 厂商 | 阿里云 |
| 地域 | 华东2（上海） |
| 配置 | 2核2G |
| 系统 | Ubuntu 22.04 |
| IP | 47.102.106.104 |
| 费用 | ¥50-70/月 |

### 部署过程

1. 购买阿里云 ECS 实例
2. 通过 Workbench 连接
3. 安装 Python 依赖
4. 克隆代码（GitHub 仓库设为公开）
5. 初始化数据库
6. 启动 Streamlit

### 遇到的问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| AKShare 无法连接 | VPN/代理拦截 | 改用 baostock |
| SSH 无法密码登录 | 服务器配置 | 使用 Workbench |
| 数据采集 NaN 错误 | baostock 返回空值 | 添加 NaN 处理 |
| 评分计算失败 | 数据库连接问题 | 修复连接逻辑 |
| AI 报错 401 | API Key 未配置 | 需要配置 .env |

---

## 第六阶段：UI 优化

### 用户反馈

1. UI 太丑，不充实
2. 没有新闻
3. 数据显示不全
4. 切换页面任务停止
5. 页面功能太少
6. 不知道是否在采集数据
7. 评分总是显示无数据

### UI 改进

- 专业金融深色风格
- 顶部导航栏
- 底部导航按钮
- 卡片式布局
- 股票详情页（K线图、技术指标、评分详情）
- 市场温度条
- 涨跌幅榜/成交额榜

---

## GitHub 仓库

**地址**：https://github.com/RyanTang-8175/ruiquant

**提交记录**：

| 提交 | 说明 |
|------|------|
| Phase 0 | 项目骨架 |
| Phase 1 | 数据层 |
| Phase 2 | 评分引擎 |
| Phase 3 | AI 对话 |
| Phase 4 | 前端页面 |
| Phase 5 | 模拟盘引擎 |
| Phase 6 | AI 预测系统 |
| Phase 7 | AI 教练 |
| Phase 8 | 自我学习 |
| UI 优化 | 重新设计界面 |

---

## 待解决问题

1. **AI 功能**：需要配置 DeepSeek API Key
2. **新闻功能**：尚未实现
3. **推送功能**：尚未实现
4. **数据实时性**：baostock 数据有延迟
5. **UI 完善**：用户仍不满意，需要继续优化

---

## 项目文件结构

```
ruiquant/
├── app.py                      # Streamlit 主入口
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
├── README.md                   # 项目说明
├── CLAUDE.md                   # Claude Code 上下文
├── PROGRESS.md                 # 开发进度
├── data/                       # 数据目录
├── scripts/
│   └── init_db.py              # 数据库初始化
├── src/
│   ├── config.py               # 配置管理
│   ├── data/
│   │   ├── models.py           # 数据模型
│   │   ├── collector.py        # 数据采集（baostock）
│   │   └── indicators.py       # 技术指标
│   ├── scoring/
│   │   ├── models.py           # 评分模型
│   │   └── engine.py           # 评分引擎（35因子）
│   ├── ai/
│   │   └── chat.py             # AI 对话（DeepSeek）
│   ├── prediction/
│   │   ├── models.py           # 预测模型
│   │   └── predictor.py        # AI 预测
│   ├── trading/
│   │   ├── models.py           # 交易模型
│   │   └── engine.py           # 模拟盘引擎
│   ├── coach/
│   │   └── coach.py            # AI 教练
│   ├── learning/
│   │   └── learner.py          # 自我学习
│   ├── pages/
│   │   ├── market.py           # 市场概览
│   │   ├── watchlist.py        # 选股
│   │   ├── ai_chat.py          # AI 对话
│   │   ├── trading.py          # 模拟盘
│   │   ├── profile.py          # 我的
│   │   └── stock_detail.py     # 股票详情
│   └── utils/
│       └── database.py         # 数据库工具
├── static/
│   ├── manifest.json           # PWA 配置
│   └── icon.svg                # 应用图标
└── ios/
    └── RuiQuant/               # iOS App 代码
```

---

## 重要决策记录

| 决策 | 结论 | 原因 |
|------|------|------|
| 数据源 | baostock（替代 AKShare） | VPN 环境下 AKShare 无法使用 |
| AI 后端 | DeepSeek | 便宜、中国能用、中文好 |
| 前端 | Streamlit | 用户不会前端，纯 Python |
| 部署 | 阿里云 VPS | 需要公网访问，不能依赖本地 |
| 评分引擎 | 35 因子 + IC 加权 | 参考幻方量化和学术研究 |
| UI 风格 | 专业金融深色风格 | 参考同花顺/新浪财经 |

---

## 时间线

| 日期 | 事项 |
|------|------|
| 2026-05-28 | 开始讨论项目需求 |
| 2026-05-29 | 完成所有 Phase 开发 |
| 2026-05-29 | 部署到阿里云 VPS |
| 2026-05-29 | UI 优化迭代 |

---

*对话记录生成时间：2026-05-29*
