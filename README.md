# AStock AI Copilot V2 - 市场认知引擎

真正理解 A 股市场行为逻辑的 AI 认知系统。不是自动交易机器人，而是帮你读懂市场的 AI 分析助手。

## 核心功能

| 功能 | 说明 |
|------|------|
| AI 个股分析 | 输入股票代码，输出大白话综合分析 |
| 主力行为识别 | 判断主力处于吸筹/洗盘/主升/出货阶段 |
| 情绪周期判断 | 识别市场处于冰点/修复/主升/高潮/分歧/退潮 |
| 大盘概况 | 实时指数 + 市场情绪温度 |
| AI 复盘 | 每日市场情绪复盘（开发中） |

## 快速启动

### 方式一：一键启动（推荐）

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

**2. 配置 API Key（可选）**
```bash
# 编辑 .env 文件，填入你的 API Key
# 不配置也能启动，会使用本地规则引擎分析
```

**3. 启动后端**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**4. 安装前端依赖 + 启动**
```bash
cd frontend
npm install
npm run dev
```

**5. 打开浏览器**
```
http://localhost:3000
```

## 技术栈

- **前端**：Next.js 14 + shadcn/ui + Framer Motion + Tailwind CSS
- **后端**：FastAPI (Python)
- **数据**：akshare（免费 A 股数据）
- **AI**：Claude API / OpenAI API（可选，不配置也能运行）

## 项目结构

```
├── frontend/          # Next.js 前端
├── backend/           # FastAPI 后端
│   ├── routers/       # API 路由
│   ├── services/      # 数据服务 + AI 分析
│   └── agents/        # 分析 Agent
├── emotion_cycle_engine/   # 情绪周期引擎
├── market_reasoning_engine/ # 市场推理引擎
├── sector_rotation_engine/  # 板块轮动引擎
├── dragon_leader_engine/    # 龙头识别引擎
├── review_engine/           # 复盘引擎
└── docker/                  # Docker 部署配置
```

## 免责声明

本系统仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
