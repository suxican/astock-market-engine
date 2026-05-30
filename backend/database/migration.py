"""数据库迁移管理 — SQLite / PostgreSQL 兼容

提供 Alembic 迁移支持和数据库升级路径。
SQLite 用户无需迁移（create_all 自动建表）。
PostgreSQL 用户使用 Alembic 管理 schema 变更。

用法:
    # 初始化迁移（仅 PostgreSQL）
    python -m backend.database.migration init

    # 执行迁移
    python -m backend.database.migration upgrade

    # 查看当前版本
    python -m backend.database.migration current
"""
import logging
import os
from pathlib import Path

from backend.config import DATABASE_URL

logger = logging.getLogger("market_engine.migration")

_is_pg = DATABASE_URL.startswith(("postgresql", "postgres"))

# 迁移脚本目录
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_db_type() -> str:
    """返回当前数据库类型"""
    return "postgresql" if _is_pg else "sqlite"


def ensure_tables():
    """确保所有表存在（幂等操作）"""
    from backend.database.db import init_db
    init_db()
    logger.info("数据库表已就绪 (%s)", get_db_type())


def add_column_if_not_exists(table: str, column: str, col_type: str):
    """安全添加列（PostgreSQL 专用，SQLite 不支持 ALTER TABLE ADD COLUMN IF NOT EXISTS）"""
    if not _is_pg:
        logger.debug("SQLite 不支持条件添加列，跳过 %s.%s", table, column)
        return

    from backend.database.db import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # 检查列是否存在
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column"
            ), {"table": table, "column": column})
            if result.fetchone():
                return  # 列已存在

            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            conn.commit()
            logger.info("已添加列 %s.%s (%s)", table, column, col_type)
    except Exception as e:
        logger.warning("添加列失败 %s.%s: %s", table, column, e)


def get_current_revision() -> str | None:
    """获取当前数据库版本（Alembic）"""
    if not _is_pg:
        return "sqlite-auto"
    try:
        from backend.database.db import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def list_pending_migrations() -> list[str]:
    """列出待执行的迁移"""
    if not _MIGRATIONS_DIR.exists():
        return []
    current = get_current_revision()
    # 简化: 返回所有迁移文件
    migrations = sorted(f.stem for f in _MIGRATIONS_DIR.glob("*.py") if f.stem != "__init__")
    if current and current in migrations:
        idx = migrations.index(current)
        return migrations[idx + 1:]
    return migrations


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "init":
        ensure_tables()
        print(f"数据库初始化完成 ({get_db_type()})")
    elif cmd == "upgrade":
        ensure_tables()
        print(f"数据库升级完成 ({get_db_type()})")
    elif cmd == "current":
        rev = get_current_revision()
        print(f"当前版本: {rev or '未初始化'}")
    elif cmd == "status":
        print(f"数据库类型: {get_db_type()}")
        print(f"URL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
        rev = get_current_revision()
        print(f"当前版本: {rev or '未初始化'}")
        pending = list_pending_migrations()
        if pending:
            print(f"待执行迁移: {len(pending)} 个")
        else:
            print("无待执行迁移")
    else:
        print(f"未知命令: {cmd}")
        print("用法: python -m backend.database.migration [init|upgrade|current|status]")

def stamp_head():
    """标记当前数据库为最新版本（首次使用 Alembic 时）"""
    if not _is_pg:
        logger.info("SQLite 不需要 Alembic stamp")
        return
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))
        command.stamp(alembic_cfg, "head")
        logger.info("已标记数据库为最新版本")
    except Exception as e:
        logger.warning("Alembic stamp 失败: %s", e)


def run_alembic_upgrade():
    """执行 Alembic 迁移"""
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic 迁移完成")
    except Exception as e:
        logger.warning("Alembic 迁移失败: %s", e)
        # 降级到 create_all
        ensure_tables()
