#!/bin/bash
# AStock AI Copilot V2 - 市场认知引擎 启动脚本

echo "============================================"
echo "  AStock AI Copilot V2 - 市场认知引擎"
echo "============================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到 Python3"
    exit 1
fi
echo "✅ Python3 已安装"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 未检测到 Node.js"
    exit 1
fi
echo "✅ Node.js 已安装"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 安装后端依赖
echo "📦 安装后端依赖..."
pip3 install -r "$SCRIPT_DIR/backend/requirements.txt" -q
echo "✅ 后端依赖安装完成"

# 安装前端依赖
echo "📦 安装前端依赖..."
cd "$SCRIPT_DIR/frontend"
npm install --silent 2>/dev/null
cd "$SCRIPT_DIR"
echo "✅ 前端依赖安装完成"
echo ""

# 启动后端
echo "🚀 启动后端服务 (http://localhost:8000)..."
cd "$SCRIPT_DIR"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 3

# 启动前端
echo "🚀 启动前端服务 (http://localhost:3000)..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

cd "$SCRIPT_DIR"
echo ""
echo "============================================"
echo "  ✅ 启动完成！"
echo ""
echo "  前端地址：http://localhost:3000"
echo "  后端地址：http://localhost:8000"
echo "  API文档：http://localhost:8000/docs"
echo "============================================"
echo ""
echo "按 Ctrl+C 关闭所有服务"

# 优雅关闭
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
