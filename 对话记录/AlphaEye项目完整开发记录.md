# AlphaEye 项目完整开发记录

> 项目原名: RuiQuant → 改名为 AlphaEye  
> 开发周期: 2026-05-28 至 2026-05-31  
> 部署地址: http://47.102.106.104:8501  
> GitHub: https://github.com/RyanTang-8175/ruiquant

---

## 一、项目概述

**AlphaEye** 是一个个人 A 股 AI 研究助手，帮助你盯盘、选股、评分、AI 对话、模拟交易。核心目标：用 AI + 量化因子帮你避开量化收割，辅助短线决策。

### 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Streamlit (Python) |
| AI 后端 | DeepSeek v4-pro (OpenAI 兼容接口) |
| 数据库 | SQLite |
| 实时行情 | 腾讯财经 gtimg.cn + 新浪财经 sina.com.cn |
| K线数据 | 东财 HTTP + 新浪 + 腾讯三源 |
| 定时任务 | APScheduler |
| 部署 | 阿里云 ECS (上海) Ubuntu 22.04 |

---

## 二、UI 设计演变

### 设计决策过程

1. 使用 `frontend-design` skill，从8个锚点中选择了 **Industrial 风格**（Bloomberg 终端风格）
2. 放弃的备选方案：Retro-Futuristic（赛博朋克）、Organic（大地色温润）
3. UI mockup 文件位于 `ui-mockups/` 目录
4. 名字从 RuiQuant 改为 **AlphaEye**（穿透量化迷雾的眼睛）

### Industrial 风格核心 CSS token

```css
--bg: #0B0C0A; --card: #131510; --border: #2A2B26
--text: #E8E8E5; --muted: #6B6C68
--red: #FF3B30; --green: #00D26A; --amber: #FFB800
font: 'JetBrains Mono', monospace
```

### 导航结构

- 底部 4 Tab 导航（行情/选股/AI/我的）
- 顶栏显示 AlphaEye logo + 用户手机号
- 实时滚动 ticker bar 显示三大指数
- 响应式布局，max-width 800px 模拟手机宽度

---

## 三、数据层架构

### 实时行情：腾讯+新浪双源融合

| 源 | 端点 | 用途 |
|---|---|---|
| 腾讯 | `qt.gtimg.cn` | 单股行情/大盘指数（主） |
| 新浪 | `hq.sinajs.cn` | 备用行情 |
| 新浪 | `vip.stock.finance.sina.com.cn` | 排行榜（涨跌幅/成交额/换手率服务端排序） |
| 东财 | `push2his.eastmoney.com` | K线历史数据（约5929条日线） |
| 新浪K线 | `money.finance.sina.com.cn` | K线备用 |
| 腾讯K线 | `web.ifzq.gtimg.cn` | K线第三源 |

### 关键数据发现

- 阿里云 ECS 对 HTTP 外网有限制，东财 API 不通，腾讯和新浪 HTTP 可用
- 新浪排行榜 API 支持 `sort=changepercent&asc=1` 直接服务端按涨跌幅排序
- K线三源顺序：东财HTTP → 新浪HTTP → 腾讯HTTP（任一失败自动切换）
- 北交所股票代码格式：`8xxxxx`/`9xxxxx`，需要 `bj` 前缀
- 腾讯返回数据：`v_sh600519="1~贵州茅台~600519~1326.00~..."` 用 `~` 分隔

### 新闻源

- 新浪财经 HTTP（主源）— feed.mix.sina.com.cn
- 东方财富 column=350（今日新闻，不是 column=357）
- 新闻标签：利好（红色）/ 利空（绿色）/ 政策（蓝色）

---

## 四、评分引擎

### 当前实现（v5.2 Quick Score）

- 5 个快速因子：momentum（涨跌幅动量）、turnover（换手率）、volatility（日内波动）、volume_ratio（量能）、trend（收盘在日内位置）
- 基于实时行情计算，不依赖 K 线数据（因为 K 线 API 超时）
- 评分范围 0-100，评级：强关注(≥80)/观察(≥65)/中性(≥50)/不追(<50)
- `get_watchlist()` 从成交额榜 Top100 评分排序

### 计划中的 v6.0 评分重构

参考 Qlib Alpha158 + FinGPT 多 Agent + 东财妙想 skills：

- 20 核心因子 + 5 反量化信号
- IC 加权 + AI 调整层 + 规则引擎
- 反量化雷达：量化足迹/收割三阶段/对倒检测/价格运动学异常/资金流向背离
- 13 个反量化信号（Group A 快速上线/Group B 核心引擎/Group C 高阶防御）
- 信号回测引擎（命中率统计）
- AI 只解读数字，不编造结论

---

## 五、AI 系统（v5.2）

### 架构

```
用户提问
  → 工具调用循环（最多8轮，每轮25秒超时）
  → 丰富系统提示词（含日期注入 + 9段分析框架 + 5个内置技能）
  → 4000 token 输出
  → 失败时 fallback 不用工具直接回答
  → 对话历史持久化到 data/conversations/latest_conversation.json
```

### 系统提示词核心元素

1. **角色定义**：15年A股短线分析师
2. **时间注入**：`{TODAY} {WEEKDAY}` 让 AI 知道当前日期
3. **9 个工具说明**
4. **九段详细分析框架**：
   - 一、基本信息
   - 二、技术面深度分析
   - 三、量化评分详解
   - 四、利多因素（至少3条）
   - 五、风险因素（至少3条+量化风险等级）
   - 六、消息面分析
   - 七、大盘环境
   - 八、综合研判与操作建议
   - 九、风险提示
5. **5 个内置自动技能**
6. **防幻觉约束**：不准编造数字、标注数据来源、不确定说"数据暂不可用"

### 5 个内置 AI 技能

| # | 技能 | 功能 | 来源参考 |
|---|---|---|---|
| 1 | 置信度标注 | 每条结论标注高/中/低置信度 | Confidence Check |
| 2 | 风险预判 | 3种最坏情景+触发条件+应对策略 | Predict Issues |
| 3 | 反量化雷达 | 量化足迹评分+量化收割预警+散户建议 | Security Scan 改版 |
| 4 | 头脑风暴选股 | 提问缩小范围→推荐匹配股票 | Brainstorming |
| 5 | 交易策略审查 | 分析策略逻辑+指出漏洞+优化建议 | Code Review 改版 |

### 9 个可调用工具

| 工具 | 超时 | 数据源 |
|---|---|---|
| get_stock_quote | 8s | 腾讯→新浪 |
| get_technical_analysis | 8s | 东财K线→新浪→腾讯 |
| get_scoring_result | 8s | 评分引擎 |
| get_market_snapshot | 8s | 腾讯+新浪 |
| get_watchlist | 8s | 评分引擎 |
| get_news | 10s | 新浪+东财 |
| get_financial_data | 8s | 腾讯实时 |
| get_positions | 8s | 模拟盘SQLite |
| get_kline_data | 8s | 东财三源 |

### AI 对话历史

- 每次对话自动保存到 `data/conversations/latest_conversation.json`
- 刷新页面/切换Tab/重启服务器后自动加载
- 支持清空操作

---

## 六、页面结构

| 文件 | 行数 | 功能 |
|---|---|---|
| `app.py` | 130 | 主入口：CSS + 登录检查 + 导航 + 路由 |
| `src/pages/login.py` | 38 | AlphaEye 登录页（手机号+API Key配置） |
| `src/pages/market.py` | 74 | 行情中心（搜索+指数条+4排行榜+新闻） |
| `src/pages/watchlist.py` | 78 | 选股（行业筛选+概念筛选+评分排名） |
| `src/pages/stock_detail.py` | 66 | 股票详情（K线+评分+AI分析+新闻） |
| `src/pages/ai_chat.py` | 57 | AI 对话（6技能按钮+对话历史持久化） |
| `src/pages/trading.py` | 93 | 模拟交易（实时行情持仓+买卖） |
| `src/pages/profile.py` | 50 | 我的（交易统计+AI配置+退出登录） |

### 路由逻辑

```python
tabs = [("market","行情"), ("watchlist","选股"), ("ai_chat","AI"), ("profile","我的")]
# 用 st.button + type="primary"/"secondary" 区分当前页
# 登录检查: st.session_state["logged_in"] 或 settings.json 中的 phone 字段
```

---

## 七、VPS 部署详情

### 服务器信息

| 项目 | 值 |
|---|---|
| 厂商 | 阿里云 ECS |
| 地域 | 华东2（上海） |
| IP | 47.102.106.104 |
| 端口 | 8501 |
| 项目路径 | /opt/ruiquant |
| Python venv | /opt/ruiquant/venv |
| 启动脚本 | /opt/ruiquant/start.sh |

### 启动脚本

```bash
#!/bin/bash
cd /opt/ruiquant
source venv/bin/activate
pkill -f streamlit
sleep 1
nohup streamlit run app.py --server.headless true --server.address 0.0.0.0 --server.port 8501 > /tmp/ae.log 2>&1 &
echo "PID: $!"
```

### VPS 更新流程

由于阿里云 ECS 无法直接访问 GitHub（TCP 被墙），使用 Python 下载 zip 包：

```bash
cd /opt/ruiquant && python3 -c "
import urllib.request,os,zipfile,io
d = urllib.request.urlopen('https://codeload.github.com/RyanTang-8175/ruiquant/zip/refs/heads/main', timeout=120).read()
with zipfile.ZipFile(io.BytesIO(d)) as z: z.extractall('/tmp/ru')
src, dst = '/tmp/ru/ruiquant-main', '/opt/ruiquant'
for r,_,fs in os.walk(src):
    rel = os.path.relpath(r, src)
    os.makedirs(os.path.join(dst,rel), exist_ok=True)
    for f in fs:
        with open(os.path.join(r,f),'rb') as sf:
            open(os.path.join(dst,rel,f),'wb').write(sf.read())
"
rm -f /opt/ruiquant/data/stock_cache.json  # 删除旧缓存
/opt/ruiquant/start.sh  # 重启
```

### VPS 常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| 503 错误 | nohup 的 `>` 重定向被终端字符拼接 | 使用 `start.sh` 脚本 |
| 东财 API 不通 | 阿里云 ECS HTTP 被墙 | 改用腾讯 gtimg.cn + 新浪 API |
| 进程立即退出 | 代码 SyntaxError | 前台运行 `streamlit run app.py` 看报错 |
| 数据缓存问题 | 旧 stock_cache.json 仅30页 | `rm -f data/stock_cache.json` 删除后重启 |
| Python 模块找不到 | venv 未激活 | 必须在 `/opt/ruiquant` 下 `source venv/bin/activate` |

---

## 八、数据准确性问题及修复历程

| # | 问题 | 根因 | 修复 | 日期 |
|---|---|---|---|---|
| 1 | 排行榜与同花顺不一致 | 新浪API用 `sort=symbol` 拉取后本地排序不准确 | 改为 `sort=changepercent&asc=1` 服务端排序 | 05-30 |
| 2 | 涨幅跌幅放反 | asc 参数方向错误 | 互换 True/False | 05-30 |
| 3 | 宁德时代(300750)搜不到 | fetch_all_stocks() 只拉30页，300段在第49页 | 选股页改用排行榜API | 05-30 |
| 4 | 实时行情数据验证 | 腾讯=新浪=1326.00/3.92% | 双源验证一致 | 05-30 |
| 5 | 新闻全是旧新闻 | 东财API column=357 返回旧新闻 | 改为 column=350 | 05-30 |
| 6 | 选股页崩溃无数据 | 拉80页全量超时 | 改用成交额榜Top100 | 05-30 |
| 7 | K线出不来 | 腾讯K线 API 阿里云被墙 | 东财HTTP→新浪→腾讯三源顺序 | 05-30 |
| 8 | 评分全部返回None | 评分引擎依赖K线数据但K线没数据 | 改为实时行情快速评分 | 05-30 |
| 9 | 评分选股不一致 | 详情页走实时API，选股页读数据库缓存 | 统一走实时API | 05-30 |
| 10 | AI死循环"调用过多工具" | 提示词要求调用太多工具，5轮不够 | 精简提示词+最多3轮 | 05-30 |

---

## 九、Git 提交时间线

```
2026-05-30 21:30  99b5e47 fix: 选股页改用排行榜API
2026-05-30 21:20  42c9abd fix: fetch_all_stocks扩展到80页覆盖全A股
2026-05-30 21:15  ec69385 fix: 涨幅榜/跌幅榜顺序互换
2026-05-30 21:00  06633b3 fix: 排行榜直接调用新浪API排序(与同花顺一致)
2026-05-30 20:40  710ce6e feat: AI对话持久化到磁盘
2026-05-30 20:30  2559457 fix: 删除get_archived_files引用+AI回复markdown
2026-05-30 20:25  7249a09 fix: 删除字符串外残留提示词文本
2026-05-30 20:15  7eba32b feat: 5个内置AI技能集成
2026-05-30 20:10  780453c feat: AI提示词大幅扩展-九段分析框架+4000token
2026-05-30 20:00  80ba459 feat: AI终极升级-多层fallback
2026-05-30 19:50  9008bac feat: 对话历史全量保留+自动压缩
2026-05-30 19:40  62cdc4b feat: AI全面升级-系统提示词+超时保护
2026-05-30 19:20  ede8929 fix: 排行榜拉取1000条后本地排序
2026-05-30 19:00  5c6a649 fix: AI精简提示词+选股评分Top30
2026-05-30 18:50  c94e91c fix: K线三源(东财→新浪→腾讯)+AI界面重设计
2026-05-30 18:30  0d6abe3 feat: 选股页整合搜索+31行业+20概念+评分
2026-05-30 18:00  4ee2e07 fix: 移除不存在的factors_json列(SQLite崩溃)
2026-05-30 17:50  6d1861f fix: 排序字段映射到新浪API
2026-05-30 17:40  577c300 fix: 评分引擎改为实时快速评分+北交所修复
2026-05-30 17:30  e0b6b84 fix: 排行榜按钮key冲突
2026-05-30 17:20  a02c81c fix: 数据源全面改用腾讯+新浪(阿里云ECS兼容)
2026-05-30 17:10  2321f14 feat: 实时行情四源融合
2026-05-30 17:00  323e6a1 fix: 数据源改为腾讯财经(主)+东财(备)
2026-05-30 16:00  3112d3e v5.0 AlphaEye Industrial: 全部页面重写完成
2026-05-30 15:00  48cbf42 v5.0 AlphaEye Industrial: 核心页面重写
2026-05-30 14:00  debbf5a 添加 UI mockup 三设计对比
2026-05-30 13:00  6f6c81b fix: 评分选股一致+登录持久化+名字+选股路由
2026-05-30 12:00  45ea122 v4.1: 全面UI重设计
2026-05-29  168ca87 v4.0: 全面重写
2026-05-29  6a232b9 fix: AI系统提示词转义修复
```

---

## 十、文件结构

```
股票/
├── app.py                      # 主入口
├── requirements.txt
├── .streamlit/config.toml
├── scripts/init_db.py
├── ui-mockups/                 # UI设计对比（仅供参考）
│   ├── industrial.html
│   ├── retro-futuristic.html
│   └── organic.html
├── data/
│   ├── ruiquant.db
│   ├── settings.json           # 用户配置(phone/api_key/base_url/model)
│   ├── stock_cache.json        # 全A股列表缓存
│   ├── factor_weights.json
│   └── conversations/
│       └── latest_conversation.json  # AI对话历史
├── src/
│   ├── config.py               # 配置管理
│   ├── scheduler.py            # 定时任务
│   ├── ai/
│   │   ├── chat.py             # AI核心（系统提示词+工具调用循环）
│   │   ├── tool_executor.py    # 9个工具实现
│   │   └── tools.py            # 工具定义（DeepSeek function calling）
│   ├── auth/
│   │   ├── models.py           # User模型
│   │   └── jwt_utils.py        # JWT+密码哈希
│   ├── data/
│   │   ├── realtime.py         # 实时行情（腾讯+新浪+东财融合）
│   │   ├── stock_list.py       # 行业+概念板块分类
│   │   ├── collector.py        # baostock数据采集（遗留）
│   │   ├── indicators.py       # 技术指标计算（遗留）
│   │   └── models.py
│   ├── scoring/
│   │   ├── engine.py           # 快速评分引擎
│   │   └── models.py
│   ├── pages/
│   │   ├── login.py
│   │   ├── market.py
│   │   ├── watchlist.py
│   │   ├── stock_detail.py
│   │   ├── ai_chat.py
│   │   ├── trading.py
│   │   └── profile.py
│   ├── news/
│   │   ├── fetcher.py          # 新闻抓取（新浪+东财）
│   │   ├── analyzer.py         # 新闻情绪分析
│   │   └── models.py
│   ├── trading/
│   │   ├── engine.py           # 模拟交易引擎
│   │   └── models.py
│   ├── prediction/
│   ├── coach/
│   ├── learning/
│   └── utils/database.py
└── 对话记录/
    ├── RuiQuant开发对话记录.md
    ├── 关键决策与待办事项.md
    └── AlphaEye项目完整开发记录.md   # 本文档
```

---

## 十一、关键决策记录

| 决策 | 结论 | 原因 | 日期 |
|---|---|---|---|
| 数据源 | 腾讯gtimg.cn + 新浪（替代东财） | 阿里云ECS HTTP被墙 | 05-30 |
| AI模型 | DeepSeek v4-pro | 用户指定 | 05-30 |
| UI设计 | Industrial（Bloomberg终端风） | frontend-design skill 8锚点评估 | 05-30 |
| 项目名 | AlphaEye | 量化之眼，看透量化操纵 | 05-30 |
| 前端框架 | Streamlit（不做React/Vue） | 用户Python技术栈，快速迭代 | 05-28 |
| 部署 | 阿里云ECS | 需要公网访问，不能依赖本地 | 05-28 |
| 评分方向 | 反量化（避开量化股） | 用户被量化收割 | 05-30 |
| 对话历史 | 持久化到JSON文件 | 刷新不丢失 | 05-30 |
| N+1修复 | 批量查询替代循环查询 | 性能优化 | 05-29 |
| 评分选股一致 | 统一走实时API | 数据库缓存和实时API不一致 | 05-30 |

---

## 十二、v6.0 待实施清单

| 模块 | 功能 | 复杂度 | 优先级 |
|---|---|---|---|
| 评分引擎 | 20因子+IC加权+AI调整层 | 高 | P0 |
| 反量化雷达 | 5信号+回测引擎 | 中 | P0 |
| 历史数据 | baostock全A股历史导入SQLite | 中 | P1 |
| AI多Agent | 技术/基本面/消息面/风险4Agent | 高 | P1 |
| K线缓存 | 多周期K线本地缓存 | 中 | P1 |
| 股票全量缓存 | 后台增量拉取不阻塞前端 | 中 | P1 |
| PWA | manifest+service worker+iOS主屏 | 低 | P2 |
| iOS打包 | Capacitor生成Xcode项目 | 高 | P3 |
| 推送通知 | 行情预警/新闻推送 | 中 | P3 |
| 微信登录 | 替代手机号登录 | 低 | P3 |

---

## 十三、已知问题和注意事项

1. **K线数据**：东财API在阿里云可能不通，需三源切换
2. **新闻**：新浪HTTP可用但可能返回国际财经新闻（非A股）
3. **数据库权限**：`data/` 目录需要写权限
4. **Streamlit 热重载**：改代码后需手动重启（`pkill -f streamlit`）
5. **VPS 网络**：`git pull` 和 `curl github.com` 都超时，只能用 `codeload.github.com` 下载 zip
6. **start.sh 脚本**：必须在 `/opt/ruiquant` 目录执行，且 `venv/bin/activate` 必须 source
7. **空 label 警告**：Streamlit 的 `st.text_input("")` 会产生 warning，可忽略
8. **评分因子太少**：当前只有5个快速因子，v6.0需要扩展到20+

---

*文档生成时间：2026-05-31 00:53*  
*当前版本：v5.2 (AlphaEye Industrial)*  
*最新 commit：99b5e47*  
*对应 GitHub：RyanTang-8175/ruiquant @ main*
