"""experiments table

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_column", sa.String(length=255), nullable=False),
        sa.Column("feature_columns", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("problem_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("test_size", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.Column("best_model_name", sa.String(length=100), nullable=True),
        sa.Column("model_path", sa.String(length=512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_experiments_dataset_id", "experiments", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_experiments_dataset_id", table_name="experiments")
    op.drop_table("experiments")
