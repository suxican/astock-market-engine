"""全局配置"""
import os
from dotenv import load_dotenv

load_dotenv()

# Claude API 配置
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_API_BASE = os.getenv("CLAUDE_API_BASE", "https://api.anthropic.com")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# OpenAI API 配置（备用 / DeepSeek 等兼容接口）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

# AI 提供商选择: "claude" 或 "openai"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")

# 服务器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Database
#   SQLite（本地开发）: sqlite:///./data/market_memory.db
#   PostgreSQL（生产）:  postgresql://user:pass@host:5432/market_memory
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/market_memory.db")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1h recycle for PG

# RAG Settings
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
RAG_SIMILAR_DAYS_COUNT = int(os.getenv("RAG_SIMILAR_DAYS_COUNT", "5"))
RAG_QDRANT_PATH = os.getenv("RAG_QDRANT_PATH", "./data/qdrant_storage")
