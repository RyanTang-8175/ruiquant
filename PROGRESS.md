# RuiQuant 开发进度

## 所有 Phase 完成 ✅

### Phase 0: 项目骨架 ✅

- [x] 项目目录结构
- [x] 配置文件
- [x] 数据库模型
- [x] Git + GitHub

### Phase 1: 数据层 ✅

- [x] AKShare 数据采集
- [x] 技术指标计算（MA/MACD/RSI/KDJ/BOLL）
- [x] 错误处理 + 线程安全

### Phase 2: 评分引擎 ✅

- [x] 35 个因子
- [x] IC 加权机制
- [x] 观察池生成

### Phase 3: AI 对话 ✅

- [x] DeepSeek 集成
- [x] 个股分析
- [x] 每日复盘

### Phase 4: 前端页面 ✅

- [x] 5 个 Streamlit 页面
- [x] 专业金融深色风格

### Phase 5: 模拟盘引擎 ✅

- [x] 买入/卖出功能
- [x] T+1、涨跌停检查
- [x] 费用计算

### Phase 6: AI 预测系统 ✅

- [x] 预测生成
- [x] 回填逻辑（T+1/T+3/T+5）
- [x] 预测统计

### Phase 7: AI 教练 ✅

- [x] 交易评价
- [x] 习惯分析
- [x] 个性化建议

### Phase 8: 自我学习 ✅

- [x] 预测准确率分析
- [x] 市场状态识别
- [x] 策略参数调整
- [x] 学习报告

## 启动方式

```bash
cd /Users/7yq/vibe\ coding项目/股票
source venv/bin/activate
streamlit run app.py
```

## GitHub 仓库

https://github.com/RyanTang-8175/ruiquant

## 项目文件结构

```
股票/
├── app.py                      # Streamlit 主入口
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
├── README.md                   # 项目说明
├── CLAUDE.md                   # Claude Code 上下文
├── PROGRESS.md                 # 开发进度
├── data/                       # 数据目录
│   └── ruiquant.db             # SQLite 数据库
├── scripts/
│   └── init_db.py              # 数据库初始化
└── src/
    ├── config.py               # 配置管理
    ├── data/
    │   ├── models.py           # 数据模型
    │   ├── collector.py        # 数据采集
    │   └── indicators.py       # 技术指标
    ├── scoring/
    │   ├── models.py           # 评分模型
    │   └── engine.py           # 评分引擎
    ├── ai/
    │   └── chat.py             # AI 对话
    ├── prediction/
    │   ├── models.py           # 预测模型
    │   └── predictor.py        # AI 预测
    ├── trading/
    │   ├── models.py           # 交易模型
    │   └── engine.py           # 模拟盘引擎
    ├── coach/
    │   └── coach.py            # AI 教练
    ├── learning/
    │   └── learner.py          # 自我学习
    ├── pages/
    │   ├── market.py           # 市场概览
    │   ├── watchlist.py        # 选股
    │   ├── ai_chat.py          # AI 对话
    │   ├── trading.py          # 模拟盘
    │   └── profile.py          # 我的
    └── utils/
        └── database.py         # 数据库工具
```
