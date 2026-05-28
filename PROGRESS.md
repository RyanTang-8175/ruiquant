# RuiQuant 开发进度

## Phase 0: 项目骨架 ✅

- [x] 项目目录结构
- [x] 配置文件（.env.example, requirements.txt）
- [x] 项目文档（README, CLAUDE.md）
- [x] 数据库模型（StockBasic, DailyQuote, TechnicalIndicator, ScoreRecord, Prediction, PaperAccount, Position, Trade）
- [x] Git 初始化 + GitHub 上传

## Phase 1: 数据层 ✅

- [x] AKShare 数据采集模块（collector.py）
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
- [x] 评分汇总与评级（强关注/观察/中性/不追）
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

## Phase 5: 模拟盘训练 ⏳

- [ ] 模拟买入功能
- [ ] 模拟卖出功能
- [ ] T+1 检查
- [ ] 涨跌停检查
- [ ] 费用计算
- [ ] 交易统计

## Phase 6: AI 预测系统 ⏳

- [ ] 预测记录模型
- [ ] 预测生成（8:30 开盘前）
- [ ] 回填逻辑（T+1/T+3/T+5）
- [ ] 预测统计

## Phase 7: AI 教练 ⏳

- [ ] 交易评价
- [ ] 习惯分析
- [ ] 预测对比
- [ ] 个性化建议

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
