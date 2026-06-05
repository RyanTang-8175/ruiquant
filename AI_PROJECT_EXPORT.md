# AlphaEye v6 — 完整项目导出（AI 可读）

> **导出时间**: 2026-06-05
> **项目原名**: RuiQuant → AlphaEye
> **GitHub**: https://github.com/RyanTang-8175/ruiquant
> **部署地址**: http://47.102.106.104:8501
> **一句话**: 个人 A 股 AI 研究助手 — 盯盘、选股、评分、反量化、AI 对话、模拟交易、预测回填、自我学习

---

## 当前升级原则（2026-06-05）

1. **UI 方向**: 白色移动金融研究终端。背景、卡片、文字必须高对比，不允许黑底黑字、深色卡片白字残留或首屏导航挤占内容。
2. **AI 方向**: DeepSeek 只是底层模型。AlphaEye 自己负责工具调用、数据质量、研究记忆、研究审计和风险闸门。
3. **报告格式**: AI 回答必须文表并用，并解释三项指标：机会分（值得研究程度）、风险分（追高/诱多/回撤风险）、置信度（数据是否充分）。
4. **研究审计**: 原“实验室”升级为研究审计。AI 对具体股票输出“可观察/仅模拟/等待触发”时，系统自动生成审计假设并回放 T+1/T+2/T+3。
5. **信息雷达**: 雷达页首屏必须先显示信息雷达和数据源状态，再显示推荐选股；抓不到互动易/公告时要明示“来源不可用”，不能当作无风险。

---

## 一、项目架构总览

```
股票/
├── app.py                    # Streamlit 主入口（Mobile First UI）
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板（DeepSeek API Key）
├── start.sh                  # 启动脚本
├── CLAUDE.md                 # Claude Code 项目上下文
├── PROGRESS.md               # 开发进度（全部9个Phase完成✅）
├── README.md                 # 项目说明
├── AI_PROJECT_EXPORT.md      # ← 本文件
│
├── data/                     # 运行时数据
│   ├── ruiquant.db           # SQLite 主数据库
│   ├── settings.json         # 用户设置（API Key等）
│   ├── stock_cache.json      # 股票缓存
│   └── conversations/        # AI 对话存档
│
├── docs/                     # 设计文档
│   ├── AlphaEye升级指导地图/ # v6 升级指导
│   └── overnight-radar-design.md  # 尾盘隔夜雷达设计
│
├── ios/                      # iOS App 壳（WKWebView）
│   ├── RuiQuant/             # SwiftUI App
│   │   ├── RuiQuantApp.swift
│   │   └── ContentView.swift # WKWebView 嵌入 Streamlit
│   └── stock/                # 另一个 iOS 版本
│
├── scripts/                  # 工具脚本
│   ├── init_db.py            # 数据库初始化
│   ├── health_check.py       # 健康检查
│   └── migrate_v6.py         # v6 数据迁移
│
├── src/                      # 核心源码
│   ├── config.py             # 全局配置（数据库/AI/交易规则）
│   ├── scheduler.py          # 定时任务（APScheduler）
│   │
│   ├── data/                 # 数据层
│   │   ├── models.py         # 基础数据模型（StockBasic/DailyQuote/TechnicalIndicator）
│   │   ├── models_v6.py      # v6 扩展模型（14张新表）
│   │   ├── collector.py      # 数据采集（baostock）
│   │   ├── realtime.py       # 实时行情（腾讯+新浪双源）
│   │   ├── indicators.py     # 技术指标计算（MA/MACD/RSI/KDJ/BOLL）
│   │   ├── stock_list.py     # 股票列表
│   │   └── providers/        # 数据源抽象层
│   │       ├── base.py       # 基类
│   │       ├── akshare_provider.py
│   │       ├── cached_provider.py
│   │       ├── ifind_provider.py
│   │       ├── open_provider.py
│   │       └── registry.py
│   │
│   ├── scoring/              # 评分引擎
│   │   ├── models.py         # ScoreRecord 模型（19因子+AI因子）
│   │   ├── engine.py         # ScoringEngine(v5.2) + V6ScoringEngine(六维)
│   │   ├── schemas.py        # SixDimensionResult 数据类
│   │   ├── heat.py           # 热度维度
│   │   ├── support.py        # 承接维度
│   │   ├── theme.py          # 题材维度
│   │   ├── continuation.py   # 延续维度
│   │   ├── strategy_match.py # 策略匹配维度
│   │   └── anti_quant.py     # 反量化维度（5种风险检测）
│   │
│   ├── ai/                   # AI 引擎
│   │   ├── chat.py           # AIChat 主类（对话/早报/收盘总结/账户诊断/尾盘扫描）
│   │   ├── tools.py          # Function Calling 工具定义（10个工具）
│   │   ├── tool_executor.py  # 工具执行器
│   │   ├── prompts.py        # System Prompt + 场景 Prompt
│   │   ├── roles.py          # AI 角色定义（研究员/风控/纪律教练/复盘分析师）
│   │   ├── structured_output.py  # 结构化输出解析
│   │   └── context_builder.py    # 上下文构建
│   │
│   ├── prediction/           # AI 预测系统
│   │   ├── models.py         # Prediction 模型（T+1/T+3/T+5预测+回填）
│   │   └── predictor.py      # PredictionEngine（预测生成+自动回填）
│   │
│   ├── trading/              # 模拟盘引擎
│   │   ├── models.py         # PaperAccount/Position/Trade 模型
│   │   └── engine.py         # TradingEngine（买入/卖出/风控/统计）
│   │
│   ├── strategies/           # 交易策略
│   │   ├── base.py           # BaseStrategy 基类
│   │   ├── overnight.py      # OvernightRadar（尾盘隔夜一夜持股法）
│   │   └── risk_radar_strategy.py
│   │
│   ├── coach/                # AI 教练
│   │   └── coach.py          # 交易评价/习惯分析/个性化建议
│   │
│   ├── learning/             # 自我学习
│   │   └── learner.py        # 预测准确率分析/市场状态识别/策略参数调整
│   │
│   ├── memory/               # 记忆系统
│   │   ├── conversation_memory.py  # AI 对话持久化（SQLite）
│   │   ├── analysis_memory.py      # AI 分析结果存储
│   │   ├── stock_memory.py         # 股票记忆条目
│   │   └── user_profile.py         # 用户画像
│   │
│   ├── news/                 # 新闻模块
│   │   ├── fetcher.py        # 新闻采集（新浪+东财）
│   │   ├── analyzer.py       # 新闻分析
│   │   └── models.py         # 新闻模型
│   │
│   ├── risk/                 # 风控
│   │   └── user_state.py     # 用户风险状态管理
│   │
│   ├── lab/                  # 短线实验室
│   │   └── backfill.py       # T+1/T+2/T+3 验证回填
│   │
│   ├── agent/                # Agent 审计
│   │   └── scratchpad.py     # AI 运行日志
│   │
│   ├── auth/                 # 认证
│   │   ├── jwt_utils.py
│   │   └── models.py
│   │
│   ├── pages/                # Streamlit 页面
│   │   ├── market.py         # 行情概览
│   │   ├── watchlist.py      # 选股/观察池
│   │   ├── ai_chat.py        # AI 对话
│   │   ├── trading.py        # 模拟盘
│   │   ├── profile.py        # 我的/设置
│   │   ├── lab.py            # 短线实验室
│   │   ├── radar.py          # 板块雷达
│   │   ├── stock_detail.py   # 个股详情
│   │   └── login.py          # 登录
│   │
│   ├── ui/                   # UI 组件
│   │   └── search.py         # 搜索组件
│   │
│   └── utils/                # 工具
│       └── database.py       # SQLAlchemy Base + SessionLocal
│
├── tests/                    # 测试
│   ├── test_p0_baseline.py
│   ├── test_regression_ui_ai.py
│   └── test_upgrade_safety_architecture.py
│
├── static/
│   └── manifest.json         # PWA manifest
│
├── ui-mockups/               # UI 设计稿
│   ├── industrial.html       # Bloomberg 终端风（已采用）
│   ├── organic.html
│   └── retro-futuristic.html
│
├── 对话记录/                  # 开发对话记录
│   ├── AlphaEye升级说明_2026-06-05.md
│   ├── AlphaEye项目完整开发记录.md
│   ├── RuiQuant开发对话记录.md
│   ├── 关键决策与待办事项.md
│   └── 升级上下文记录.md
│
└── venv/                     # Python 虚拟环境
```

---

## 二、技术栈

| 层 | 技术 |
|---|---|
| **前端** | Streamlit (Python) — Mobile First, max-width 480px |
| **AI 后端** | DeepSeek v4-pro (OpenAI 兼容接口) |
| **数据库** | SQLite (SQLAlchemy ORM) |
| **实时行情** | 腾讯财经 `qt.gtimg.cn` (主) + 新浪财经 `hq.sinajs.cn` (备) |
| **K线数据** | 东财 HTTP + 新浪 + 腾讯 三源自动切换 |
| **历史数据** | baostock |
| **定时任务** | APScheduler |
| **部署** | 阿里云 ECS (上海) Ubuntu 22.04 |
| **iOS App** | SwiftUI + WKWebView (嵌入 Streamlit) |

---

## 三、数据库模型（共14+张表）

### v5.2 基础表

| 表名 | 用途 |
|---|---|
| `stock_basic` | 股票基础信息（代码/名称/行业/ST标记） |
| `daily_quote` | 日线行情（OHLCV/涨跌幅/换手率） |
| `technical_indicator` | 技术指标（MA/MACD/RSI/KDJ/BOLL） |
| `score_record` | 评分记录（19因子+AI因子，0-100总分） |
| `paper_account` | 模拟盘账户（现金/状态/连续亏损） |
| `position` | 持仓（代码/数量/成本价/买入日期） |
| `trade` | 交易记录（买/卖/价格/费用/盈亏） |
| `prediction` | AI 预测（T+1/T+3/T+5方向/幅度/置信度+回填） |

### v6 新增表

| 表名 | 用途 |
|---|---|
| `stocks` | 股票档案（板块/概念/市值/量能特征/反量化历史风险） |
| `stock_snapshots` | 实时快照（价格/量比/换手/来源/质量等级） |
| `intraday_bars` | 分钟级分时数据 |
| `daily_bars` | 日线数据（含均线/影线/收盘位置） |
| `score_records_v6` | 六维评分（热度/承接/题材/延续/策略匹配/反量化） |
| `anti_quant_records` | 反量化风险详情（5种风险检测结果） |
| `strategy_signals` | 策略触发信号（条件/风险标志/次日计划） |
| `ai_sessions` | AI 会话 |
| `ai_messages` | AI 消息（含结构化输出/工具调用） |
| `ai_analysis_records` | 结构化 AI 分析结果 |
| `stock_memory_entries` | 股票记忆条目 |
| `verification_records` | 短线实验室验证记录 |
| `verification_backfills` | T+1/T+2/T+3 回填数据 |
| `user_feedback` | 用户反馈 |
| `user_preferences` | 用户偏好设置 |
| `data_quality_logs` | 数据源健康日志 |

---

## 四、核心引擎详解

### 4.1 数据采集（DataCollector）

```python
# 数据源架构
DataCollector (baostock) → 批量采集 A 股日线
RealtimeQuote (腾讯gtimg + 新浪sinajs) → 实时行情（30秒缓存）
K线三源: 东财HTTP → 新浪HTTP → 腾讯HTTP（自动切换）
新闻源: 新浪财经 feed.mix.sina.com.cn + 东财

# 股票代码规则
600xxx → sh (上交所)
000/002/300 → sz (深交所)
8xx/9xx → bj (北交所)
```

### 4.2 评分引擎（V6ScoringEngine）

```
六维评分体系（权重可调）:

1. 热度 (Heat)       — 20% — 涨跌幅动量/量比/换手
2. 承接 (Support)    — 25% — 分时均价线/回踩支撑/多次确认
3. 题材 (Theme)      — 20% — 板块强度/概念热度/新闻催化
4. 延续 (Continuation) — 15% — 均线排列/K线形态/趋势强度
5. 策略匹配 (Strategy) — 20% — 尾盘隔夜/回调低吸/突破追涨
6. 反量化 (AntiQuant) — 惩罚项 — 5种风险检测

总分 = Σ(维度分 × 权重) - 反量化惩罚分

评级:
  ≥80: 强关注 (Strong Watch)
  ≥65: 观察 (Watch)
  ≥50: 中性 (Neutral)
  <50: 不追 (Avoid)
```

**5种反量化风险检测：**
- `late_day_lure` — 尾盘诱多
- `high_position_trap` — 高位接盘陷阱
- `intraday_pulse` — 分时脉冲出货
- `volume_stall` — 放量滞涨
- `sector_divergence` — 板块背离

### 4.3 AI 对话引擎（AIChat）

```python
# 核心流程
user_message
  → detect_scene()       # 自动检测场景(quick_judge/sector_scan/deep_analysis/review/compare)
  → build_system_prompt() # 按场景拼接角色(System Prompt + 安全闸门 + 内置技能)
  → chat()               # 多轮 Function Calling (最多6轮工具调用)
      → get_stock_quote       # 行情
      → get_technical_analysis # 技术指标
      → get_scoring_result    # 评分
      → get_market_snapshot   # 市场快照
      → get_sector_candidates # 行业候选
      → get_watchlist         # 观察池
      → get_news              # 新闻
      → get_financial_data    # 基本面
      → get_positions         # 持仓
      → get_kline_data        # K线
  → _finalize_response()  # 保存对话→磁盘+数据库+股票记忆

# 内置 AI 角色
- short_term_researcher  短线研究员
- risk_reviewer          风控审查员
- holding_predictor      持仓预测员
- discipline_coach       纪律教练
- review_analyst         复盘分析师
- general_assistant      通用助手
```

### 4.4 模拟盘引擎（TradingEngine）

```python
# 交易规则
佣金: 万2.5 (最低5元)
印花税: 千0.5 (仅卖出)
过户费: 万0.2

# 风控规则
单票最大仓位: 30%
总仓位上限: 80%
止损提醒: -8%
强制卖出: -15%
单日亏损暂停: -5%
连续亏损暂停: 3笔
T+1 锁定: 当日买入不可卖出

# 模拟交易流程
can_buy()  → 检查账户状态/涨跌停/现金/仓位/连亏
execute_buy() → 更新现金/创建或加仓/记录交易
can_sell() → 检查跌停/持仓/T+1
execute_sell() → 计算盈亏/更新现金/记录交易/更新连亏计数
```

### 4.5 AI 预测系统（PredictionEngine）

```python
# 预测流程
daily_prediction()
  → 获取观察池(评分≥65的股票)
  → 对每只股票调用 DeepSeek 生成预测
  → 保存 T+1/T+3/T+5 方向+幅度+置信度

# 回填流程
backfill_predictions()
  → 查询 status=pending 的预测
  → 根据 elapsed_days 回填:
     ≥1天 → T+1 实际收益/命中
     ≥3天 → T+3 实际收益/命中
     ≥5天 → T+5 实际收益/命中 + status=completed
     >7天 → status=expired

# 命中判定
up → actual_return > 2%
down → actual_return < -2%
neutral → |actual_return| < 2%
```

### 4.6 尾盘隔夜雷达（OvernightRadar）

```
一夜持股法 — 尾盘筛选隔夜候选

时间规则:
  14:30-14:45  初筛（只生成候选，不买入）
  14:45-14:50  观察尾盘承接
  14:50-14:55  最终确认
  14:55 后     只允许放弃

硬条件:
  - 涨幅 2.5%-6%（理想3%-5%）
  - 量比 ≥ 1.2
  - 换手率 5%-10%
  - 流通市值 50-200亿
  - K线多头排列 (price > MA5 > MA10 > MA20)
  - 收盘位置 ≥ 70%（阳线实体偏上）
  - 上影线 ≤ 35%（抛压不大）
  - 近5日涨幅 ≤ 25%
  - 分时均线上方 ≥ 70%

匹配度:
  ≥90%: 可执行
  ≥75%: 等待确认
  ≥50%: 初筛候选
  <50%: 排除
```

---

## 五、AI 安全设计

### 核心原则

1. **数值与解释分离**: 所有分数、指标由程序计算，AI 只写解释文字
2. **默认不荐股**: 输出"观察/模拟/验证/放弃"四类动作，不给实盘买入指令
3. **必须写清失效条件**: 每个候选都要写止损纪律和放弃条件
4. **数据来源标注**: 回答必须说明数据来源和缺口
5. **安全闸门**: 用户处于谨慎/冷静期时，只能给观察、模拟、复盘计划

### System Prompt 结构

```
1. 角色定义（你是一个金融研究助手...）
2. 安全闸门条款
3. 参考项目内化工作流（Dexter → Vibe-Trading → daily_stock_analysis）
4. 按场景启用的内置角色
5. 输出风格契约（STYLE_CONTRACT）
6. 场景专用 Prompt（scene_prompt）
```

---

## 六、前端 UI

### 设计系统

```
风格: Industrial（Bloomberg 终端风，浅色版）
色彩:
  --bg: #F4F7FA         背景
  --card: #FFFFFF       卡片
  --text: #17212F       主文字
  --muted: #5D6B7C      辅助文字
  --red: #E53935        跌/风险
  --green: #0A9B66      涨/安全
  --amber: #D88312      警告
  --ai: #246BFE         AI 品牌色

字体:
  数字: SF Mono / DIN Alternate / Menlo
  中文: PingFang SC / HarmonyOS Sans

布局:
  max-width: 480px (Mobile First)
  margin: 0 auto (居中)
  底部 4 Tab 导航: 行情/选股/AI/我的
  Sticky 顶栏: Logo + 实时指数滚动
```

### 页面结构

| Tab | 页面 | 功能 |
|---|---|---|
| 行情 | market.py | 三大指数/涨跌统计/涨幅榜/跌幅榜/成交额榜/板块雷达 |
| 选股 | watchlist.py | 观察池评分排名/六维评分/反量化风险标记 |
| AI | ai_chat.py | AI 对话/个股分析/对比/行业扫描/智能追问 |
| 我的 | profile.py | API Key/模型配置/账户设置/数据管理/风险状态 |

---

## 七、部署架构

```
┌─────────────────────────────────┐
│      阿里云 ECS (上海)          │
│      Ubuntu 22.04              │
│      IP: 47.102.106.104        │
│                                │
│  ┌──────────────────────────┐  │
│  │   Streamlit :8501        │  │
│  │   ├── AlphaEye Web UI    │  │
│  │   ├── Mobile First CSS   │  │
│  │   └── max-width: 480px   │  │
│  └──────────────────────────┘  │
│              │                  │
│  ┌───────────┴──────────────┐  │
│  │   SQLite (ruiquant.db)   │  │
│  │   实时行情缓存            │  │
│  │   评分/持仓/预测/AI对话   │  │
│  └──────────────────────────┘  │
│              │                  │
│  ┌───────────┴──────────────┐  │
│  │   外部 API               │  │
│  │   ├── DeepSeek API       │  │
│  │   ├── 腾讯 qt.gtimg.cn   │  │
│  │   ├── 新浪 hq.sinajs.cn  │  │
│  │   └── 东财 K线 API       │  │
│  └──────────────────────────┘  │
└─────────────────────────────────┘
         │
    ┌────┴────┐
    │  iPhone  │  ← WKWebView iOS App
    │  浏览器   │  ← 直接访问 :8501
    └─────────┘
```

### 访问方式

1. **Web 浏览器**: 直接打开 `http://47.102.106.104:8501`
2. **iPhone Safari**: 打开网址 → 分享 → 添加到主屏幕
3. **iOS App**: Xcode 运行 ios/RuiQuant → WKWebView 嵌入

### 启动命令

```bash
cd "/Users/7yq/vibe coding项目/股票"
source venv/bin/activate
streamlit run app.py
```

---

## 八、开发阶段完成情况

| Phase | 内容 | 状态 |
|---|---|---|
| Phase 0 | 项目骨架/配置/数据库模型/Git | ✅ |
| Phase 1 | AKShare + baostock 数据采集/技术指标 | ✅ |
| Phase 2 | 评分引擎 (35因子 → 六维评分) | ✅ |
| Phase 3 | DeepSeek AI 对话 | ✅ |
| Phase 4 | Streamlit 5 页面 + 白色 Mobile First 金融 UI | ✅ |
| Phase 5 | 模拟盘引擎 (T+1/涨停跌停/费用) | ✅ |
| Phase 6 | AI 预测系统 (预测+回填) | ✅ |
| Phase 7 | AI 教练 (交易评价/习惯/建议) | ✅ |
| Phase 8 | 自我学习引擎 (准确率/市场状态/权重调整) | ✅ |

---

## 九、当前已知问题与待办

### 技术债务
1. **Streamlit 不适合 PWA**: manifest.json 已创建但 Streamlit 不原生支持 Service Worker
2. **K线 API 不稳定**: 东财 HTTP 在阿里云 ECS 上不可用，依赖腾讯+新浪
3. **数据实时性**: 腾讯行情 30秒缓存，非真正实时
4. **用户认证**: JWT 模块已有但未强制启用
5. **无 HTTPS**: 部署在 :8501 明文传输

### 建议的下一步
1. **加 HTTPS + 域名**: 用 nginx 反代 + Let's Encrypt
2. **改 PWA 支持**: 加 Service Worker + 离线缓存
3. **移动端优化**: 完善 manifest.json + 推送通知
4. **数据质量**: 完善 DataQualityLog 检查，等待 iFinD 接入后提升行情/公告/财务可信度
5. **研究审计**: 继续增加自动回放指标和“AI错/策略错/用户执行错”归因
6. **回测系统**: 策略回测验证历史表现

---

## 十、环境变量

```bash
# .env 文件
DEEPSEEK_API_KEY=sk-xxx           # DeepSeek API Key（必填）
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DATABASE_PATH=data/ruiquant.db
LOG_LEVEL=INFO
INITIAL_CAPITAL=100000            # 模拟盘初始资金
```

---

## 十一、Git 仓库信息

- **GitHub**: https://github.com/RyanTang-8175/ruiquant
- **最近提交** (top 10):
  - `64fb1d7` fix: CSS全面暗色→浅色
  - `094b0ef` feat: redesign AI desk and restore legacy chat
  - `b99f7fa` fix: harden deployment readiness issues
  - `f722ec1` docs: record AlphaEye upgrade rollout
  - `02131af` feat: upgrade AI research memory
  - `841661a` feat: upgrade lab validation workflow
  - `eef0b6a` feat: persist auditable AI conversations
  - `873e496` feat: add financial AI safety foundations
  - `fe8b253` 收盘总结重磅升级: AI判断印证 + 真实数据明日计划
  - `7f2c6ee` 收盘总结/账户诊断重写: 注入真实数据+具体模板

---

*本文档由 AI 自动生成，覆盖了 AlphaEye v6 项目的完整代码结构、数据库模型、核心引擎逻辑、AI 安全设计、前端 UI 和部署架构。任何 AI 工具都可以通过阅读本文档快速理解项目全貌。*
