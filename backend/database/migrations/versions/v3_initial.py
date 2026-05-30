"""初始迁移 — 基于 V3 models.py 自动生成

Revision ID: v3_initial
Revises: None
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "v3_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建所有 V3 表 — 幂等操作"""
    # 表已由 Base.metadata.create_all() 创建，
    # 此迁移仅作为 Alembic 版本追踪起点。
    # 后续 schema 变更通过新迁移脚本管理。
    pass


def downgrade() -> None:
    pass
