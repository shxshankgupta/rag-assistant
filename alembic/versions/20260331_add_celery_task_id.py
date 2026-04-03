"""Add celery_task_id to documents for embedding task tracking.

Revision ID: 20260331_celery
Revises:
Create Date: 2026-03-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260331_celery"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("celery_task_id", sa.String(length=64), nullable=True))
    op.create_index("ix_documents_celery_task_id", "documents", ["celery_task_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documents_celery_task_id", table_name="documents")
    op.drop_column("documents", "celery_task_id")
