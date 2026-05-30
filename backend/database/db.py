"""数据库引擎与会话管理 — 支持 SQLite / PostgreSQL"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from backend.config import DATABASE_URL, DB_MAX_OVERFLOW, DB_POOL_RECYCLE, DB_POOL_SIZE
from backend.database.models import Base

_is_pg = DATABASE_URL.startswith(("postgresql", "postgres"))

if _is_pg:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_recycle=DB_POOL_RECYCLE,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表并补齐缺失的列"""
    Base.metadata.create_all(bind=engine)
    # SQLite: 补齐 V3 新增列（CREATE TABLE IF NOT EXISTS 不会修改已有表）
    _migrate_sqlite_columns()


def _migrate_sqlite_columns():
    """安全添加缺失的列（SQLite 不支持 IF NOT EXISTS ADD COLUMN）"""
    if _is_pg:
        return  # PostgreSQL 由 Alembic 管理
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        existing = {col["name"] for col in inspector.get_columns("users")}
        needed = {
            "role": "VARCHAR(20) DEFAULT 'viewer'",
            "preferences_json": "TEXT",
            "last_login_at": "DATETIME",
        }
        with engine.connect() as conn:
            for col, col_def in needed.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_def}"))
            conn.commit()
    except Exception:
        pass  # 表可能还不存在，create_all 会处理


def get_db():
    """获取数据库会话（用于 FastAPI 依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

