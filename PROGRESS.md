# RuiQuant 开发进度

## Phase 0: 项目骨架 ✅

- [x] 项目目录结构
- [x] 配置文件（.env.example, requirements.txt）
- [x] 项目文档（README, CLAUDE.md）
- [x] 数据库模型
- [x] Git 初始化 + GitHub 上传

## Phase 1: 数据层 ✅

- [x] AKShare 数据采集模块
- [x] 股票基础信息获取
- [x] 日线行情数据获取
- [x] 技术指标计算（MA/MACD/RSI/KDJ/BOLL）
- [x] 数据库唯一约束
- [x] 线程安全配置
- [x] 错误处理优化

## Phase 2: 评分引擎 ✅

- [x] 35 个因子定义
- [x] 14 个量化因子计算函数
- [x] IC 加权机制
- [x] 权重归一化
- [x] 评分汇总与评级
- [x] 观察池生成

## Phase 3: AI 对话 ✅

- [x] DeepSeek API 集成
- [x] 对话历史管理
- [x] 个股分析功能
- [x] 每日复盘生成

## Phase 4: 前端页面 ✅

- [x] 专业金融深色风格
- [x] 市场概览页面
- [x] 选股/观察池页面
- [x] AI 对话页面
- [x] 模拟盘页面
- [x] 我的页面

## Phase 5: 模拟盘引擎 ✅

- [x] 模拟买入功能
- [x] 模拟卖出功能
- [x] T+1 检查
- [x] 涨跌停检查
- [x] 费用计算（佣金/印花税/过户费）
- [x] 仓位限制检查
- [x] 连续亏损暂停机制
- [x] 交易统计功能

## Phase 6: AI 预测系统 ✅

- [x] 预测记录模型
- [x] 预测生成（DeepSeek）
- [x] 回填逻辑（T+1/T+3/T+5）
- [x] 命中判定
- [x] 预测统计

## Phase 7: AI 教练 ✅

- [x] 交易评价
- [x] 每周交易习惯分析
- [x] 与 AI 预测对比
- [x] 个性化建议

## Phase 8: 自我学习 ⏳

- [ ] 因子权重自动调整
- [ ] 市场状态识别
- [ ] 策略参数调整
- [ ] 学习报告

## GitHub 仓库

https://github.com/RyanTang-8175/ruiquant

## 启动方式

```bash
cd /Users/7yq/vibe\ coding项目/股票
source venv/bin/activate
streamlit run app.py
```

## 技术栈

- Python 3.11+
- Streamlit（前端）
- AKShare（数据源）
- DeepSeek（AI 后端）
- SQLite（数据库）
- OpenAI SDK（DeepSeek 兼容）

## 已完成模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 数据采集 | src/data/collector.py | AKShare 数据采集 |
| 技术指标 | src/data/indicators.py | MA/MACD/RSI/KDJ/BOLL |
| 评分引擎 | src/scoring/engine.py | 35 因子评分 |
| AI 对话 | src/ai/chat.py | DeepSeek 对话 |
| 模拟盘 | src/trading/engine.py | 模拟交易引擎 |
| AI 预测 | src/prediction/predictor.py | 预测与回填 |
| AI 教练 | src/coach/coach.py | 交易评价与建议 |
| 前端页面 | src/pages/*.py | 5 个 Streamlit 页面 |
