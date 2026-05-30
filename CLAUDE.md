# AStock AI Copilot V3 — 市场认知引擎

> 真正理解 A 股市场行为逻辑的 AI 认知系统。不是自动交易机器人，而是帮你读懂市场的 AI 分析助手。

## 技术栈

| 层 | 技术 |
|--|------|
| 前端 | Next.js 14 (App Router) + TypeScript + Tailwind CSS + Framer Motion |
| UI | shadcn/ui + lucide-react + lightweight-charts (K线) |
| 数据获取 | SWR (stale-while-revalidate) |
| 后端 | FastAPI (Python 3.10+) + uvicorn |
| 数据源 | akshare (免费 A 股数据), Tencent/Sina HTTP API, EastMoney curl_cffi |
| AI | Claude API / OpenAI API (可选, 不配置也能运行) |
| 向量 | Qdrant (local mode, 无服务器依赖) |
| 数据库 | SQLAlchemy + SQLite (默认) / PostgreSQL (可选) |
| 容器 | Docker + docker-compose (dev/prod) |
| CI | GitHub Actions (ruff + pytest + next lint + next build) |

## 项目结构

```
├── backend/                          # FastAPI 后端
│   ├── main.py                       # 入口: 生命周期, 路由注册, CORS, 限流, 全局错误处理
│   ├── config.py                     # 环境变量配置 (AI, DB, RAG, CORS, JWT)
│   ├── routers/                      # API 路由层
│   │   ├── stock.py                  #   /api/stock/* — K线, 行情, 资金流, 板块, 龙虎榜
│   │   ├── analysis.py              #   /api/analysis/* — AI分析, 本地规则, 事件引擎, RAG
│   │   ├── auth.py                  #   /api/auth/* — 注册, 登录, JWT
│   │   └── ws.py                    #   /ws/* — WebSocket 实时推送
│   ├── services/                     # 数据服务层 (多源回退 + TTL缓存 + 数据质量标记)
│   │   ├── analysis/                #   AI分析管线 (LLM客户端, 提示构建, 本地规则, 降级路径)
│   │   ├── market_data.py           #   日K线 + 股票名称解析
│   │   ├── quote_data.py            #   实时行情 + 大盘指数
│   │   ├── limit_data.py            #   涨停/跌停池 + 龙虎榜
│   │   ├── flow_data.py             #   资金流 (个股+板块)
│   │   ├── market_breadth.py        #   V3 市场宽度指标
│   │   └── data_quality.py          #   数据质量跟踪 + 置信度评分
│   ├── agents/                       # 分析 Agent
│   │   ├── stock_analysis_agent.py  #   综合分析编排
│   │   ├── main_capital_agent.py    #   主力资金行为识别 (4阶段评分)
│   │   └── emotion_cycle_agent.py   #   市场情绪周期判断 (6阶段)
│   ├── feature_engine/              # V8 共享特征计算
│   │   ├── market_features.py       #   市场级快照 (一次性计算, 消除N+1)
│   │   └── stock_features.py        #   个股结构化特征
│   ├── score_engine/                # V8 结构化评分 (纯规则, 无需LLM)
│   │   ├── market_scores.py         #   情绪评分, 龙头强度, 风险评分
│   │   ├── stock_scores.py          #   主力评分, 技术评分, 综合评分
│   │   └── score_utils.py           #   评分工具函数
│   ├── event_engine/                # 事件驱动引擎
│   │   ├── event_extractor.py       #   事件提取 + 分类 + 情感判定
│   │   ├── concept_mapper.py        #   概念/政策 → 板块/个股映射
│   │   ├── hot_tracker.py           #   热点追踪
│   │   └── timeline.py              #   当日事件时间线
│   ├── backtest/                    # 回测引擎
│   │   ├── engine.py                #   信号 → 模拟交易 → 绩效评估
│   │   └── strategies.py            #   内置策略 (MA交叉/放量突破/龙头跟随)
│   ├── database/                    # 数据持久化
│   │   ├── db.py                    #   SQLAlchemy 引擎/会话工厂
│   │   └── models.py                #   ORM: MarketSnapshot, ReviewRecord, User
│   └── schemas/                     # Pydantic 请求/响应模型
├── frontend/                         # Next.js 14 前端
│   ├── app/                          # App Router 页面
│   │   ├── page.tsx                  #   首页: 搜索, 快速入口, 功能卡片
│   │   ├── stock/page.tsx           #   个股分析: K线, AI分析, 评分
│   │   ├── market/page.tsx          #   大盘概况: 评分, 龙头, 板块轮动
│   │   ├── review/page.tsx          #   AI复盘: 每日回顾, 情绪周期
│   │   ├── workbench/page.tsx       #   实时工作台: 炸板热力图, 板块统计
│   │   └── backtest/page.tsx        #   策略回测
│   ├── components/                   # React 组件
│   │   ├── ui/                       #   shadcn/ui 基础组件
│   │   ├── KLineChart.tsx            #   K线图 (lightweight-charts)
│   │   ├── AnalysisView.tsx          #   AI分析结果渲染
│   │   ├── EmotionTimeline.tsx       #   情绪周期可视化
│   │   ├── DragonLeaderCard.tsx      #   龙头识别卡片
│   │   ├── SectorRotationCard.tsx    #   板块轮动
│   │   └── ZhabanHeatmap.tsx         #   炸板率热力图
│   └── lib/                          # 工具库
│       ├── api.ts                    #   类型安全的 API 客户端
│       ├── hooks.ts                  #   SWR 数据获取 Hooks
│       └── types.ts                  #   共享类型定义
├── emotion_cycle_engine/             # 情绪周期引擎
├── market_reasoning_engine/          # 市场推理引擎 (预期差分析)
├── sector_rotation_engine/           # 板块轮动引擎
├── dragon_leader_engine/             # 龙头识别引擎
├── review_engine/                    # 复盘引擎
├── limit_up_analysis/                # 涨停分析引擎
├── limit_down_analysis/              # 跌停分析引擎
├── rag/                              # RAG 检索增强
├── vector_db/                        # Qdrant 向量数据库客户端
├── tests/                            # pytest 测试
├── docker/                           # Docker 部署配置
└── .github/workflows/                # CI 流水线
```

## 核心架构决策

### 1. 三层分析管线

```
┌─────────────────────────────────────────────────┐
│  ① 真实数据 + LLM  → 完整 AI 综合分析          │
│  ② 真实数据 + 本地规则 → 纯规则引擎分析 (免API) │
│  ③ Mock数据 + 降级模板 → 安全降级提示           │
└─────────────────────────────────────────────────┘
```

- 无需任何 API Key 即可运行: 使用本地规则引擎 + mock 数据
- 数据质量问题自动降级: 置信度 < 0.6 时跳过 LLM 分析

### 2. V3 统一评分架构

- **Feature Engine**: 一次性计算市场/个股特征, 消除 Agent 间的 N+1 问题
- **Score Engine**: 纯规则驱动的 0-100 结构化评分
  - 情绪周期 (6阶段多维加权)
  - 龙头强度 (8维评分: 连板/封板/封单比/板块/时间/换手/排名/舆情)
  - 风险等级 (动态权重)
  - **赚钱效应** (溢价/存活/龙头/跌停/回封 5维)
  - **主线识别** (涨停数/资金/龙头/集中度 4维)
  - **市场健康分** (情绪/龙头/风险/赚钱效应/事件 五维加权)
- **MarketBreath**: 涨跌家数/涨跌比/强弱分布
- **EventEngine V2**: 事件聚类 + 影响衰减 + 综合评分
- **DataQuality 信封**: 所有分析 API 自动注入数据质量元信息
- **Agents**: 封装业务逻辑, 消费预计算评分
- 收敛路径: FeatureEngine → ScoreEngine → AI Explain Layer

### 3. DataQuality 信封
所有 `/api/analysis/*` 端点通过中间件自动注入 `data_quality` 字段，包含 `source`、`confidence`、`status`。置信度 < 0.6 时禁止 AI 金融推理。

### 4. 多源数据回退

```
Tencent HTTP → Sina HTTP → curl_cffi(EastMoney) → akshare → Mock数据
```

每层带有 DataQuality 置信度标记, 供降级决策使用。

### 5. RAG 增强复盘

- 每日市场状态 → 6维向量存入 Qdrant
- 生成复盘时检索相似历史交易日 → 注入 LLM 提示
- 结果双写: Qdrant (向量检索) + SQLite (结构化查询)

### 6. 安全架构

- JWT 认证 (HMAC-SHA256 + PBKDF2 密码哈希)
- 速率限制 (120 req/min)
- CORS 白名单
- 飞书 Webhook 异常通知

## 开发命令

```bash
# 后端
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8005

# 前端
cd frontend && npm install && npm run dev

# 测试
pytest -v

# Docker (dev)
cd docker && docker-compose up

# Docker (prod)
cd docker && docker-compose -f docker-compose.prod.yml up -d
```

## 环境变量

核心配置见 `.env.example`。关键变量:

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_PROVIDER` | AI 提供商 (openai/claude) | openai |
| `OPENAI_API_KEY` | OpenAI/DeepSeek Key | — |
| `CLAUDE_API_KEY` | Claude API Key | — |
| `PORT` | 后端端口 | 8005 |
| `JWT_SECRET` | JWT 密钥 (生产必改) | — |
| `DATABASE_URL` | 数据库连接 | sqlite:///./data/market_memory.db |
| `RAG_ENABLED` | 启用 RAG | true |

**无需任何配置即可运行**: 不设 API Key 时自动使用本地规则引擎 + mock 数据。

## 关键模式

- **不可变数据结构**: 使用 frozen dataclass / NamedTuple
- **类型注解**: 所有函数签名包含类型注解
- **仓储模式**: 数据访问封装在 services/ 层
- **API 信封**: 统一 `{success, data, error, meta}` 响应格式
- **配置即代码**: 所有配置通过环境变量 + config.py 管理
- **错误处理**: 全局异常处理器 + 层级别错误捕获

