"""现有 schema 基线戳记

已有部署通过 create_all 与启动补列维护表结构；本 revision 仅建立 Alembic 版本链。
后续 schema 变更请新增 revision，逐步替代 database.py 中的补列逻辑。

Revision ID: 0001
Revises:
Create Date: 2025-06-08

"""
from __future__ import annotations

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
