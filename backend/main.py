"""AStock AI Copilot V2 - 市场认知引擎 FastAPI 后端入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import CORS_ORIGINS
from backend.routers import stock, analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭生命周期管理"""
    # Startup: 初始化数据库 + 预热 Qdrant
    try:
        from backend.database.db import init_db
        init_db()
        from vector_db.client import get_client
        get_client()
    except Exception as e:
        print(f"[V7] DB/Vector init: {e}")
    yield
    # Shutdown: 无需清理（SQLite + 本地 Qdrant 自动持久化）


app = FastAPI(
    title="AStock AI Copilot V2 - 市场认知引擎",
    description="真正理解A股市场行为逻辑的AI认知系统",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stock.router)
app.include_router(analysis.router)


@app.get("/")
def root():
    """健康检查"""
    return {
        "service": "AStock AI Copilot V2",
        "status": "running",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
