# AStock AI Copilot V2 — 市场认知引擎

<p align="center">
  <strong>真正理解 A 股市场行为逻辑的 AI 认知系统</strong><br />
  不是自动交易机器人，而是帮你读懂市场的 AI 分析助手
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/node-20%2B-green" alt="Node 20+" />
  <img src="https://img.shields.io/badge/react-18%2B-61DAFB" alt="React 18+" />
  <img src="https://img.shields.io/badge/next.js-14-black" alt="Next.js 14" />
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License MIT" />
</p>

---

## 🚀 特性

| 功能 | 说明 |
|------|------|
| **AI 个股分析** | 输入股票代码，输出大白话综合分析（主力行为 + 技术面 + 资金面） |
| **主力行为识别** | 自动判断主力处于吸筹 / 洗盘 / 主升 / 出货阶段，附带置信度评分 |
| **情绪周期判断** | 识别市场处于冰点 / 修复 / 主升 / 高潮 / 分歧 / 退潮 |
| **大盘概况** | 实时指数 + 市场情绪温度 + 涨跌家数 + 涨停跌停统计 |
| **龙头识别** | 多维评分自动识别市场总龙头、板块龙头、日内先锋 |
| **板块轮动** | 行业 + 概念双维度分析，判断板块处于加强/持续/退潮/反弹 |
| **涨停跌停分析** | 政策催化 / 资金驱动 / 情绪炒作 / 龙头带动 / 基本面驱动 多维度分类 |
| **AI 复盘** | 每日自动生成市场复盘报告，RAG 增强（检索相似历史交易日） |
| **事件驱动引擎** | 实时提取新闻事件 → 概念映射 → 关联个股 → 热点追踪 |
| **策略回测** | 内置 MA 交叉 / 放量突破 / 龙头跟随策略，支持绩效评估 |
| **实时工作台** | WebSocket 实时推送 + 炸板率热力图 + 板块轮动监控 |
| **预期差分析** | 6 种市场异常行为模式识别（利好不涨、利空落地反涨等） |
| **本地规则引擎** | **无需 API Key**，纯规则驱动的分析能力，即使断网也能用 |
| **多源数据回退** | 5 层数据源级联回退，最大程度保证数据可达 |
| **一键部署** | Docker Compose 一键启动全栈服务 |

## 🖥️ 快速启动

### 方式一：一键启动

**Windows：**
```bash
双击 start.bat
# 或
python start.bat
```

**Mac / Linux：**
```bash
chmod +x start.sh
./start.sh
```

### 方式二：手动启动

**1. 安装后端依赖**
```bash
pip install -r backend/requirements.txt
```

**2. 启动后端**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8005 --reload
```

后端默认运行在 `http://localhost:8005`，API 文档自动生成于 `http://localhost:8005/docs`。

**3. 启动前端**
```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`。

**4. 打开浏览器访问** `http://localhost:3000`

> 💡 **无需 API Key** — 不配置 AI 密钥也能运行，系统会自动降级到本地规则引擎。

### 方式三：Docker 部署

```bash
# 开发环境（热重载）
cd docker && docker-compose up

# 生产环境
cd docker && docker-compose -f docker-compose.prod.yml up -d
```

## 📖 使用指南

### 基础使用

| 页面 | 功能 | 访问路径 |
|------|------|----------|
| 首页 | 搜索股票、快速入口 | `/` |
| 个股分析 | K 线图 + AI 分析 + 主力行为 + 资金流 | `/stock?code=600519` |
| 大盘概况 | 市场评分 + 龙头列表 + 板块轮动 + 情绪周期 | `/market` |
| AI 复盘 | 每日市场情绪复盘 + 相似历史对比 | `/review` |
| 实时工作台 | 炸板热力图 + 板块资金流 + 实时推送 | `/workbench` |
| 策略回测 | 策略选择 → 回测 → 绩效分析 | `/backtest` |

### 配置 AI 分析

创建 `.env` 文件（可参考 `.env.example`）：

```ini
# 使用 Claude
AI_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-xxxxx

# 或使用 DeepSeek（默认）
AI_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxx
OPENAI_API_BASE=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

不配置 AI 时，系统自动使用本地规则引擎，纯 Python 代码完成分析。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend (Next.js 14)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ 个股分析  │ │ 大盘概况  │ │ AI复盘   │ │ 实时工作台/回测    │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬──────────┘  │
│       └────────────┴────────────┴────────────────┘              │
│                          │ SWR + typed API                      │
├──────────────────────────┴──────────────────────────────────────┤
│                     Backend (FastAPI)                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Feature Engine (V8)   ←──   Score Engine (V8)           │   │
│  │  · 市场级快照           · 情绪评分 0-100                 │   │
│  │  · 个股特征             · 主力评分 0-100                 │   │
│  │  · 一次性计算, 消除N+1  · 技术评分                       │   │
│  └────────────────────┬─────────────────────────────────────┘   │
│                       │ 共享结构化数据                            │
│  ┌────────────────────┴─────────────────────────────────────┐   │
│  │  Agents (分析 Agent)                                     │   │
│  │  主力行为Agent │ 情绪周期Agent │ 龙头识别Agent │ 板块轮动  │   │
│  │  AI 综合分析Agent │ 复盘Agent │ 事件引擎Agent             │   │
│  └───────┬──────────────────────────────────────────┬────────┘   │
│          │ 路由                                      │            │
│  ┌───────┴──────────────────────────────────────────┴────────┐  │
│  │  Services (数据服务层) — 多源回退 + TTL缓存 + 质量标记      │  │
│  │  Tencent HTTP → Sina → EastMoney → akshare → Mock         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Qdrant   │ │ SQLite/  │ │ Redis    │ │ Feishu Bot       │   │
│  │ 向量存储  │ │ PostgreSQL│ │ (future) │ │ 通知服务          │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 三层分析管线

```
① 真实数据 + LLM   →  完整 AI 综合分析  (需配置 API Key)
② 真实数据 + 本地规则 →  纯规则引擎分析  (无需 API)
③ Mock数据 + 降级模板 →  安全降级提示     (数据源全部不可用时)
```

### 核心流程

1. **数据层**：从多源获取数据，每层标记数据质量置信度
2. **特征层**：Feature Engine 一次性计算市场/个股特征
3. **评分层**：Score Engine 纯规则驱动输出结构化评分（0-100）
4. **分析层**：Agent 编排业务逻辑，评分注入 LLM 提示
5. **持久化**：结果写入 Qdrant + 数据库，供 RAG 检索

## 📁 项目结构

```
├── README.md
├── CLAUDE.md                     # Claude Code 项目上下文
├── .env.example                  # 环境变量模板
├── ruff.toml                     # Ruff 代码检查配置
├── start.bat / start.sh          # 一键启动脚本
│
├── backend/                      # FastAPI 后端
│   ├── main.py                   #   应用入口
│   ├── config.py                 #   全局配置
│   ├── routers/                  #   API 路由
│   │   ├── stock.py              #     数据查询接口
│   │   ├── analysis.py           #     AI 分析接口
│   │   ├── auth.py               #     认证接口
│   │   └── ws.py                 #     WebSocket 推送
│   ├── services/                 #   数据服务
│   │   ├── analysis/             #     AI 分析管线
│   │   ├── market_data.py        #     日K线数据
│   │   ├── quote_data.py         #     实时行情
│   │   ├── limit_data.py         #     涨停跌停池
│   │   ├── flow_data.py          #     资金流
│   │   └── data_quality.py       #     数据质量追踪
│   ├── agents/                   #   分析 Agent
│   ├── feature_engine/           #   特征计算引擎 (V8)
│   ├── score_engine/             #   结构化评分引擎 (V8)
│   ├── event_engine/             #   事件驱动引擎
│   ├── backtest/                 #   策略回测引擎
│   ├── database/                 #   数据库模型
│   └── schemas/                  #   Pydantic 模型
│
├── frontend/                     # Next.js 14 前端
│   ├── app/                      #   App Router 页面
│   ├── components/               #   UI 组件
│   │   ├── ui/                   #     shadcn/ui
│   │   ├── KLineChart.tsx        #     K线图
│   │   ├── AnalysisView.tsx      #     AI分析渲染
│   │   ├── EmotionTimeline.tsx   #     情绪周期可视化
│   │   ├── DragonLeaderCard.tsx  #     龙头识别卡片
│   │   └── ...
│   └── lib/                      #   工具库
│       ├── api.ts                #     类型安全 API 客户端
│       ├── hooks.ts              #     SWR 数据获取
│       └── types.ts              #     共享类型
│
├── emotion_cycle_engine/          # 情绪周期引擎
├── market_reasoning_engine/       # 市场推理引擎（预期差分析）
├── sector_rotation_engine/        # 板块轮动引擎
├── dragon_leader_engine/          # 龙头识别引擎
├── review_engine/                 # 复盘引擎
├── limit_up_analysis/             # 涨停分析引擎
├── limit_down_analysis/           # 跌停分析引擎
├── rag/                           # RAG 检索增强
├── vector_db/                     # Qdrant 向量数据库客户端
├── tests/                         # pytest 测试
├── docker/                        # Docker 部署
└── .github/workflows/             # CI 流水线
```

## ⚙️ 配置参考

### 环境变量

| 变量 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| `AI_PROVIDER` | AI 提供商 (`openai` / `claude`) | `openai` | ❌ |
| `OPENAI_API_KEY` | OpenAI / DeepSeek API Key | — | ❌ |
| `CLAUDE_API_KEY` | Claude API Key | — | ❌ |
| `CLAUDE_MODEL` | Claude 模型 | `claude-sonnet-4-20250514` | ❌ |
| `OPENAI_API_BASE` | OpenAI 兼容接口地址 | `https://api.deepseek.com/v1` | ❌ |
| `OPENAI_MODEL` | 模型名称 | `deepseek-chat` | ❌ |
| `PORT` | 后端监听端口 | `8005` | ❌ |
| `CORS_ORIGINS` | 允许的跨域来源 | `http://localhost:3000` | ❌ |
| `JWT_SECRET` | JWT 签名密钥 | `change-me-to-...` | 生产环境 ✅ |
| `DATABASE_URL` | 数据库连接 | `sqlite:///./data/market_memory.db` | ❌ |
| `RAG_ENABLED` | 启用 RAG 检索增强 | `true` | ❌ |
| `RAG_QDRANT_PATH` | Qdrant 存储路径 | `./data/qdrant_storage` | ❌ |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook | — | ❌ |
| `NEXT_PUBLIC_API_BASE_URL` | 前端 API 地址 | `http://localhost:8005` | ❌ |

### 依赖安装

```bash
# 后端
pip install -r backend/requirements.txt

# 前端
cd frontend && npm install
```

## 🧪 测试

```bash
# 运行所有测试
pytest -v

# 带覆盖率报告
pytest --cov=backend --cov-report=term-missing

# 前端检查
cd frontend && npm run lint
```

## 🐳 Docker

```bash
# 开发环境
cd docker && docker-compose up
# 后端 :8005 (热重载), 前端 :3000 (热重载)

# 生产环境
cd docker && docker-compose -f docker-compose.prod.yml up -d
# 通过 Nginx (端口 80) 访问
```

## 🧰 技术栈

| 类别 | 技术 |
|------|------|
| 前端框架 | Next.js 14 (App Router) |
| 语言 | TypeScript |
| UI | shadcn/ui + Tailwind CSS + Framer Motion |
| 图表 | lightweight-charts (K线) + lucide-react (图标) |
| 数据获取 | SWR (stale-while-revalidate) |
| 后端 | FastAPI + uvicorn |
| 数据源 | akshare, Tencent/Sina HTTP API |
| AI | Claude API / OpenAI API / DeepSeek |
| 向量存储 | Qdrant (local mode) |
| 数据库 | SQLAlchemy + SQLite / PostgreSQL |
| 部署 | Docker + docker-compose + Nginx |
| CI | GitHub Actions (lint + test + build) |

## 🔒 安全

- 密码使用 PBKDF2 哈希存储
- API 访问需 JWT 认证
- 全局速率限制 (120 req/min)
- CORS 白名单机制
- RAG 向量数据库本地存储，无数据外泄风险

## 📜 免责声明

> **本系统仅供学习和研究使用，不构成任何投资建议。**
>
> 所有分析结果基于历史数据和规则引擎，不保证对未来市场走势的预测准确性。
> 股市有风险，投资需谨慎。**请勿将本系统的分析结果作为实际交易决策的唯一依据。**

## 🔗 相关资源

- [akshare](https://github.com/akfamily/akshare) — A 股数据接口
- [FastAPI](https://fastapi.tiangolo.com/) — 后端框架
- [Next.js](https://nextjs.org/) — 前端框架
- [Qdrant](https://qdrant.tech/) — 向量搜索引擎

## 📄 License

MIT License — 详见 [LICENSE](LICENSE) 文件。
