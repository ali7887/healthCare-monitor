"""phase20 reasoning summary

Revision ID: 0003_phase20
Revises: 0002_phase10
Create Date: 2026-07-04 00:00:00.000000

Adds a human-readable, step-by-step reasoning summary to each run so the trace
viewer can explain *why* a run was routed the way it was.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_phase20'
down_revision: Union[str, None] = '0002_phase10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('runs', sa.Column('reasoning_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('runs', 'reasoning_summary')
